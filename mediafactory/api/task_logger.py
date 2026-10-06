"""任务级日志：worker 子进程执行期挂 per-task 文件 sink。

worker 存活期=单任务执行期，子进程内全部日志即该任务的日志——
无需 bind/filter，engine 层零改动。追加模式，每次执行带分隔头
（尝试序号 = 文件既有分隔头数 + 1，重试历史完整保留）。
"""

import logging
import re
from datetime import datetime
from pathlib import Path

_SEP_RE = re.compile(r"^==== attempt \d+ @ ", re.MULTILINE)

logger = logging.getLogger(__name__)


def task_log_path(task_id: str) -> Path:
    from mediafactory.config import get_data_root_dir

    d = get_data_root_dir() / "logs" / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{task_id}.log"


def _next_attempt(path: Path) -> int:
    if not path.exists():
        return 1
    return len(_SEP_RE.findall(path.read_text(encoding="utf-8", errors="replace"))) + 1


def attach_task_log_sink(task_id: str, config_summary: str) -> int:
    """挂 per-task 文件 sink 并写分隔头；返回 loguru sink id。"""
    from loguru import logger as _loguru

    path = task_log_path(task_id)
    attempt = _next_attempt(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"==== attempt {attempt} @ {datetime.now().isoformat()} ====\n")
        f.write(f"config: {config_summary}\n")
    return _loguru.add(
        str(path),
        level="INFO",
        enqueue=False,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {message}",
    )


def detach_task_log_sink(sink_id: int) -> None:
    from loguru import logger as _loguru

    try:
        _loguru.remove(sink_id)
    except Exception:  # noqa: BLE001  # sink 已失效/进程退出竞态，静默
        pass


def read_task_log_tail(task_id: str, max_lines: int = 1000) -> list[str]:
    """读任务日志尾部（端点用）；文件不存在返回空表。"""
    from mediafactory.config import get_data_root_dir

    path = get_data_root_dir() / "logs" / "tasks" / f"{task_id}.log"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-max_lines:]


def cleanup_task_log(task_id: str) -> None:
    """删除任务时清理其日志文件（幂等，失败仅告警不阻断删除）。"""
    try:
        p = task_log_path(task_id)
        if p.exists():
            p.unlink()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to remove task log for {task_id}: {e}")
