"""daemon 实例锁：保证任何时刻至多一个 daemon 进程。

data/daemon.lock 记录持锁 PID：
- 原子创建（O_CREAT|O_EXCL）抢锁
- 文件存在时检查持锁进程是否存活：活着则拒绝启动（DaemonAlreadyRunning），
  已死则视为陈锁接管
- atexit 兜底释放；正常路径由调用方显式 release
"""

import atexit
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class DaemonAlreadyRunning(RuntimeError):
    """另一个 daemon 实例正在运行。"""


class DaemonLock:
    """PID 文件实例锁（单进程内单次 acquire，非线程锁语义）。"""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._acquired = False

    def acquire(self) -> None:
        """抢锁；被活实例持有则抛 DaemonAlreadyRunning。"""
        if self._acquired:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # 原子抢锁：文件已存在则失败
            fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            holder = self._read_holder_pid()
            if holder is not None and self._pid_alive(holder):
                raise DaemonAlreadyRunning(
                    f"另一个 MediaFactory daemon 正在运行（PID {holder}）。"
                    f"请先停止它，或删除锁文件 {self._path} 后重试。"
                )
            # 持锁进程已死：接管陈锁
            logger.warning(f"接管陈旧锁文件（原 PID {holder}）: {self._path}")
            fd = os.open(self._path, os.O_WRONLY | os.O_TRUNC)
        with os.fdopen(fd, "w") as f:
            f.write(str(os.getpid()))
        self._acquired = True
        atexit.register(self.release)

    def release(self) -> None:
        """释放锁（只删自己的锁文件；未持有时为 no-op）。"""
        if not self._acquired:
            return
        self._acquired = False
        try:
            current = self._read_holder_pid()
            if current == os.getpid():
                self._path.unlink(missing_ok=True)
        except OSError as e:  # 释放失败不影响退出
            logger.warning(f"释放实例锁失败（忽略）: {e}")

    def _read_holder_pid(self) -> "int | None":
        try:
            return int(self._path.read_text().strip())
        except (OSError, ValueError):
            return None

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)  # 信号 0 = 仅探测存在性
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # 进程存在但属他人——保守视为存活
        return True
