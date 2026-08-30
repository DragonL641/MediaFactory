"""DaemonLock（daemon 实例 PID 锁）单元测试。

存活探测的平台分支：Windows 走 ctypes OpenProcess（仅在 win32 生效），
本测试套在 POSIX 分支上运行，Windows 分支以代码评审背书。
"""

import os

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
