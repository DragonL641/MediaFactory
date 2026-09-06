"""HistoryRepository 单元测试。

锁定历史库契约：upsert 覆盖（retry 语义）、completed_at 降序、
status/type 过滤、分页 + 总数、单删/清空、内存库隔离。
"""

import asyncio

import pytest

from mediafactory.persistence import HistoryRepository, TaskHistoryEntry

pytestmark = [pytest.mark.unit]


def make_entry(
    task_id: str = "abc12345",
    status: str = "completed",
    task_type: str = "audio",
    completed_at: float = 100.0,
    name: str = "Task abc12345",
) -> TaskHistoryEntry:
    return TaskHistoryEntry(
        task_id=task_id,
        name=name,
        task_type=task_type,
        status=status,
        input_path="v.mp4",
        output_path="out.wav" if status == "completed" else None,
        error=None if status == "completed" else "boom",
        error_type=None if status == "completed" else "ProcessingError",
        metadata={"key": "value"},
        created_at=completed_at - 10,
        started_at=completed_at - 5,
        completed_at=completed_at,
    )


def run(coro):
    return asyncio.run(coro)


class TestUpsertAndList:
    def test_upsert_and_list_ordering(self):
        async def scenario():
            repo = HistoryRepository()  # 内存库
            await repo.upsert(make_entry("id2", completed_at=200.0))
            await repo.upsert(make_entry("id1", completed_at=300.0))
            await repo.upsert(make_entry("id3", completed_at=100.0))
            return await repo.list_records()

        items, total = run(scenario())
        assert total == 3
        # completed_at 降序
        assert [i.task_id for i in items] == ["id1", "id2", "id3"]
        assert items[0].status == "completed"
        assert items[0].metadata == {"key": "value"}
        assert items[0].started_at is not None

    def test_upsert_same_task_id_overwrites(self):
        """retry 重跑同 task_id：最新一次结果覆盖，不产生第二行"""

        async def scenario():
            repo = HistoryRepository()
            await repo.upsert(make_entry("t1", status="failed", completed_at=100.0))
            await repo.upsert(make_entry("t1", status="completed", completed_at=200.0))
            return await repo.list_records()

        items, total = run(scenario())
        assert total == 1
        assert items[0].task_id == "t1"
        assert items[0].status == "completed"

    def test_memory_db_isolated_between_instances(self):
        async def scenario():
            repo_a = HistoryRepository()
            await repo_a.upsert(make_entry("only-a"))
            repo_b = HistoryRepository()
            return await repo_b.list_records(), await repo_a.list_records()

        (items_b, total_b), (items_a, total_a) = run(scenario())
        assert total_b == 0 and items_b == []
        assert total_a == 1


async def _seed_async(repo):
    await repo.upsert(
        make_entry("e1", status="completed", task_type="audio", completed_at=400.0)
    )
    await repo.upsert(
        make_entry("e2", status="failed", task_type="audio", completed_at=300.0)
    )
    await repo.upsert(
        make_entry("e3", status="completed", task_type="subtitle", completed_at=200.0)
    )
    await repo.upsert(
        make_entry("e4", status="cancelled", task_type="translate", completed_at=100.0)
    )


class TestFilters:
    def test_filter_by_status(self):
        async def scenario():
            repo = HistoryRepository()
            await _seed_async(repo)
            return await repo.list_records(status="completed")

        items, total = run(scenario())
        assert total == 2
        assert all(i.status == "completed" for i in items)

    def test_filter_by_type(self):
        async def scenario():
            repo = HistoryRepository()
            await _seed_async(repo)
            return await repo.list_records(task_type="audio")

        items, total = run(scenario())
        assert total == 2
        assert all(i.task_type == "audio" for i in items)

    def test_pagination_with_total(self):
        async def scenario():
            repo = HistoryRepository()
            await _seed_async(repo)
            return (
                await repo.list_records(limit=2, offset=0),
                await repo.list_records(limit=2, offset=2),
            )

        (page1, total1), (page2, total2) = run(scenario())
        assert total1 == 4 and total2 == 4
        assert len(page1) == 2 and len(page2) == 2
        assert [i.task_id for i in page1] == ["e1", "e2"]
        assert [i.task_id for i in page2] == ["e3", "e4"]


class TestGetDeleteClear:
    def test_get_record_found_and_missing(self):
        async def scenario():
            repo = HistoryRepository()
            await repo.upsert(make_entry("t9"))
            return await repo.get_record("t9"), await repo.get_record("nope")

        found, missing = run(scenario())
        assert found is not None and found.task_id == "t9"
        assert missing is None

    def test_delete_record(self):
        async def scenario():
            repo = HistoryRepository()
            await repo.upsert(make_entry("t1"))
            deleted = await repo.delete_record("t1")
            again = await repo.delete_record("t1")
            _, total = await repo.list_records()
            return deleted, again, total

        deleted, again, total = run(scenario())
        assert deleted is True and again is False and total == 0

    def test_clear_returns_count(self):
        async def scenario():
            repo = HistoryRepository()
            await _seed_async(repo)
            n = await repo.clear()
            _, total = await repo.list_records()
            return n, total

        n, total = run(scenario())
        assert n == 4 and total == 0

    def test_close_and_reopen_same_file_db(self, tmp_path):
        """close 后同文件库重新打开，数据仍在（daemon 重启保留历史的基础）"""
        db_file = tmp_path / "history.db"

        async def scenario():
            repo1 = HistoryRepository(db_path=db_file)
            await repo1.upsert(make_entry("persist-me"))
            await repo1.close()
            repo2 = HistoryRepository(db_path=db_file)
            found = await repo2.get_record("persist-me")
            await repo2.close()
            return found

        found = run(scenario())
        assert found is not None and found.status == "completed"
