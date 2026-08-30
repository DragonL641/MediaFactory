"""DaemonLock（daemon 实例 PID 锁）单元测试。

存活探测的平台分支：Windows 走 ctypes OpenProcess（仅在 win32 生效），
本测试套在 POSIX 分支上运行，Windows 分支以代码评审背书。
"""

import os
import sys

import pytest

from mediafactory.api.daemon_lock import DaemonAlreadyRunning, DaemonLock

pytestmark = [pytest.mark.unit]


def test_acquire_creates_lock_with_own_pid(tmp_path):
    lock = DaemonLock(tmp_path / "daemon.lock")
    lock.acquire()
    assert (tmp_path / "daemon.lock").exists()
    assert (tmp_path / "daemon.lock").read_text().strip() == str(os.getpid())
    lock.release()


def test_second_acquire_raises_while_holder_alive(tmp_path):
    lock1 = DaemonLock(tmp_path / "daemon.lock")
    lock1.acquire()
    # 自己的 pid 一定存活——模拟持锁进程活着
    lock2 = DaemonLock(tmp_path / "daemon.lock")
    with pytest.raises(DaemonAlreadyRunning) as exc_info:
        lock2.acquire()
    # 报错信息含持锁 PID，便于用户定位
    assert str(os.getpid()) in str(exc_info.value)
    lock1.release()


def test_release_allows_reacquire(tmp_path):
    lock = DaemonLock(tmp_path / "daemon.lock")
    lock.acquire()
    lock.release()
    assert not (tmp_path / "daemon.lock").exists()
    lock2 = DaemonLock(tmp_path / "daemon.lock")
    lock2.acquire()  # 释放后可重新获取
    lock2.release()


def test_stale_lock_from_dead_process_is_taken_over(tmp_path):
    # 写入一个必然不存在的 PID（Unix 上 999999 级别空闲；若极端占用则测试环境异常）
    lock_file = tmp_path / "daemon.lock"
    lock_file.write_text("999999")
    lock = DaemonLock(lock_file)
    lock.acquire()  # 陈锁：持锁进程已死 → 接管，不抛
    assert lock_file.read_text().strip() == str(os.getpid())
    lock.release()


def test_release_without_acquire_is_noop(tmp_path):
    lock = DaemonLock(tmp_path / "daemon.lock")
    lock.release()  # 不抛即通过


def test_release_does_not_delete_foreign_lock(tmp_path):
    lock_file = tmp_path / "daemon.lock"
    lock_file.write_text("999999")
    lock = DaemonLock(lock_file)
    lock.release()  # 未 acquire 过，不得动别人的锁文件
    assert lock_file.read_text().strip() == "999999"


def test_release_does_not_delete_rewritten_foreign_lock(tmp_path):
    lock_file = tmp_path / "daemon.lock"
    lock = DaemonLock(lock_file)
    lock.acquire()
    lock_file.write_text("999999")  # 模拟锁文件被改写为他者 PID
    lock.release()
    assert lock_file.read_text().strip() == "999999"


class TestEntryWiring:
    def test_main_module_wires_lock(self, monkeypatch, tmp_path):
        # __main__.main() 在启动 uvicorn 前抢锁；锁被占时立刻报错退出
        import mediafactory.__main__ as entry

        lock_path = tmp_path / "daemon.lock"
        monkeypatch.setattr(entry, "_daemon_lock_path", lambda: lock_path)
        lock_path.write_text(str(os.getpid()))  # 活实例持锁

        with pytest.raises(SystemExit) as exc_info:
            entry.main()
        assert exc_info.value.code == 1

    def test_main_module_registers_server(self, monkeypatch, tmp_path):
        """__main__ 生产分支（frozen exe 主路径）必须注册 server_ref，否则壳只能 503 回退硬杀"""
        import mediafactory.__main__ as entry
        from mediafactory.api import server_ref

        monkeypatch.setattr(
            entry, "_daemon_lock_path", lambda: tmp_path / "daemon.lock"
        )
        monkeypatch.setattr(
            server_ref, "_server", None
        )  # teardown 自动还原，防全局污染
        monkeypatch.setattr(sys, "argv", ["mediafactory"])  # 默认参数 → 生产分支

        ran = []

        class FakeServer:
            def __init__(self, config):
                self.config = config

            def run(self):
                ran.append(True)

        # 与 start_server happy-path 同形态：只 stub Server，不碰真实 8765
        monkeypatch.setattr("uvicorn.Server", FakeServer)
        entry.main()
        assert ran == [True]  # 生产分支正常启动
        assert server_ref._server is not None  # Server 已注册（供 shutdown 端点）

    def test_start_server_wires_lock(self, monkeypatch, tmp_path):
        import mediafactory.api.main as api_main

        lock_path = tmp_path / "daemon.lock"
        monkeypatch.setattr(api_main, "_daemon_lock_path", lambda: lock_path)
        lock_path.write_text(str(os.getpid()))  # 活实例持锁

        started = []

        class FakeServer:
            def __init__(self, config):
                started.append("constructed")

            def run(self):
                started.append("ran")

        # 入口手动构造 uvicorn.Server（供 /api/system/shutdown 优雅停机）
        monkeypatch.setattr("uvicorn.Server", FakeServer)

        with pytest.raises(SystemExit) as exc_info:
            api_main.start_server()
        assert exc_info.value.code == 1
        assert started == []  # 锁失败时 Server 根本不构造

    def test_start_server_happy_path_runs_uvicorn_and_releases(
        self, monkeypatch, tmp_path
    ):
        import mediafactory.api.main as api_main
        from mediafactory.api import server_ref

        lock_path = tmp_path / "daemon.lock"
        monkeypatch.setattr(api_main, "_daemon_lock_path", lambda: lock_path)
        # 先钉住全局 _server，teardown 自动还原（防 set_server 污染后续测试）
        monkeypatch.setattr(server_ref, "_server", None)

        ran = []

        class FakeServer:
            def __init__(self, config):
                self.config = config

            def run(self):
                ran.append(True)

        monkeypatch.setattr("uvicorn.Server", FakeServer)
        api_main.start_server()
        assert ran == [True]  # 锁成功 → uvicorn 正常启动
        assert server_ref._server is not None  # Server 已注册（供 shutdown 端点）
        assert lock_path.read_text().strip() == str(os.getpid())  # 持锁为本进程
        # 进程退出时 atexit 释放——测试内不断言文件删除（atexit 在进程退出才跑）
