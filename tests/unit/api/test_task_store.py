"""TaskStore（SQLite 任务持久层）单元测试。"""

import pytest

from mediafactory.api.task_store import TaskStore

pytestmark = [pytest.mark.unit]


def make_store(tmp_path):
    return TaskStore(tmp_path / "tasks.db")


def test_insert_and_get_roundtrip(tmp_path):
    store = make_store(tmp_path)
    store.insert(
        task_id="abc12345",
        name="Task A",
        config_json='{"task_type": "audio"}',
        created_at=1000.0,
    )
    row = store.get("abc12345")
    assert row is not None
    assert row["id"] == "abc12345"
    assert row["name"] == "Task A"
    assert row["config_json"] == '{"task_type": "audio"}'
    assert row["status"] == "pending"  # 默认值
    assert row["queued_at"] is None  # 新任务不在队列
    assert row["created_at"] == 1000.0


def test_get_missing_returns_none(tmp_path):
    store = make_store(tmp_path)
    assert store.get("nope") is None


def test_get_all_returns_all_rows(tmp_path):
    store = make_store(tmp_path)
    store.insert(task_id="a", name="A", config_json="{}", created_at=1.0)
    store.insert(task_id="b", name="B", config_json="{}", created_at=2.0)
    ids = {row["id"] for row in store.get_all()}
    assert ids == {"a", "b"}


def test_memory_store_when_no_path():
    # 不传路径 → 内存库（测试默认隔离，不落盘）
    store = TaskStore()
    store.insert(task_id="m", name="M", config_json="{}", created_at=1.0)
    assert store.get("m") is not None
