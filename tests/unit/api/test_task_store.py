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


def test_update_changes_whitelisted_fields(tmp_path):
    store = make_store(tmp_path)
    store.insert(task_id="a", name="A", config_json="{}", created_at=1.0)
    store.update("a", status="running", progress=12.5, output_path="/tmp/o.wav")
    row = store.get("a")
    assert row["status"] == "running"
    assert row["progress"] == 12.5
    assert row["output_path"] == "/tmp/o.wav"


def test_update_rejects_unknown_field(tmp_path):
    store = make_store(tmp_path)
    store.insert(task_id="a", name="A", config_json="{}", created_at=1.0)
    with pytest.raises(ValueError):
        store.update("a", hack="x")


def test_delete_removes_row(tmp_path):
    store = make_store(tmp_path)
    store.insert(task_id="a", name="A", config_json="{}", created_at=1.0)
    store.delete("a")
    assert store.get("a") is None


def test_queue_marker_roundtrip(tmp_path):
    store = make_store(tmp_path)
    store.insert(task_id="a", name="A", config_json="{}", created_at=1.0)
    store.insert(task_id="b", name="B", config_json="{}", created_at=2.0)
    assert store.get_queued_ids() == []  # 新任务不在队列
    store.set_queued("a", True)
    store.set_queued("b", True)
    assert store.get_queued_ids() == ["a", "b"]  # 按 queued_at 升序（FIFO）
    store.set_queued("a", False)  # 出队
    assert store.get_queued_ids() == ["b"]
    assert store.get("a")["queued_at"] is None


def test_queued_ids_only_count_pending(tmp_path):
    # 已完成的任务即使残留 queued_at 也不进队列视图
    store = make_store(tmp_path)
    store.insert(task_id="a", name="A", config_json="{}", created_at=1.0)
    store.set_queued("a", True)
    store.update("a", status="completed")
    assert store.get_queued_ids() == []
