"""任务历史 API 路由测试。

TestClient + monkeypatch _get_repo 指向 tmp_path 文件库；
锁定响应形状（camelCase / ISO 时间戳 / durationMs）、404、删除、清空。
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from mediafactory.api.main import get_app
from mediafactory.api.routes import history as history_routes
from mediafactory.persistence import HistoryRepository, TaskHistoryEntry

pytestmark = [pytest.mark.unit]


def make_entry(
    task_id: str,
    status: str = "completed",
    completed_at: float = 1000.0,
    started_at: float | None = 990.0,
) -> TaskHistoryEntry:
    return TaskHistoryEntry(
        task_id=task_id,
        name=f"Task {task_id}",
        task_type="audio",
        status=status,
        input_path="v.mp4",
        output_path="out.wav" if status == "completed" else None,
        error=None if status == "completed" else "boom",
        error_type=None if status == "completed" else "ProcessingError",
        metadata={},
        created_at=completed_at - 20,
        started_at=started_at,
        completed_at=completed_at,
    )


@pytest.fixture()
def client_with_repo(tmp_path, monkeypatch):
    repo = HistoryRepository(db_path=tmp_path / "history.db")
    monkeypatch.setattr(history_routes, "_get_repo", lambda: repo)
    client = TestClient(get_app())
    yield client, repo
    client.close()


class TestListHistory:
    def test_empty_list(self, client_with_repo):
        client, _ = client_with_repo
        resp = client.get("/api/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"total": 0, "items": []}

    def test_item_shape_camel_case_iso_duration(self, client_with_repo):
        client, repo = client_with_repo
        asyncio.run(repo.upsert(make_entry("t1")))

        resp = client.get("/api/history")
        item = resp.json()["items"][0]
        assert item["taskId"] == "t1"
        assert item["type"] == "audio"
        assert item["status"] == "completed"
        assert item["outputPath"] == "out.wav"
        # ISO 8601 UTC（含时区）
        assert item["createdAt"].endswith("+00:00")
        assert item["completedAt"].endswith("+00:00")
        # 990 → 1000 = 10s = 10000ms
        assert item["durationMs"] == 10000

    def test_duration_null_when_no_started_at(self, client_with_repo):
        client, repo = client_with_repo
        asyncio.run(repo.upsert(make_entry("t2", started_at=None)))
        item = client.get("/api/history").json()["items"][0]
        assert item["durationMs"] is None
        assert item["startedAt"] is None

    def test_filters_and_pagination(self, client_with_repo):
        client, repo = client_with_repo
        for i, status in enumerate(["completed", "failed", "completed"]):
            asyncio.run(repo.upsert(make_entry(f"f{i}", status=status)))

        body = client.get("/api/history", params={"status": "completed"}).json()
        assert body["total"] == 2

        body = client.get("/api/history", params={"limit": 1, "offset": 1}).json()
        assert body["total"] == 3
        assert len(body["items"]) == 1

    def test_ordering_completed_at_desc(self, client_with_repo):
        client, repo = client_with_repo
        asyncio.run(repo.upsert(make_entry("old", completed_at=100.0)))
        asyncio.run(repo.upsert(make_entry("new", completed_at=200.0)))
        items = client.get("/api/history").json()["items"]
        assert [i["taskId"] for i in items] == ["new", "old"]


class TestGetDeleteClear:
    def test_get_single_404(self, client_with_repo):
        client, _ = client_with_repo
        assert client.get("/api/history/nope").status_code == 404

    def test_get_single_found(self, client_with_repo):
        client, repo = client_with_repo
        asyncio.run(repo.upsert(make_entry("t1")))
        resp = client.get("/api/history/t1")
        assert resp.status_code == 200
        assert resp.json()["taskId"] == "t1"

    def test_delete_single_404_and_ok(self, client_with_repo):
        client, repo = client_with_repo
        assert client.delete("/api/history/nope").status_code == 404
        asyncio.run(repo.upsert(make_entry("t1")))
        assert client.delete("/api/history/t1").json() == {"deleted": True}

    def test_clear(self, client_with_repo):
        client, repo = client_with_repo
        asyncio.run(repo.upsert(make_entry("a")))
        asyncio.run(repo.upsert(make_entry("b")))
        assert client.delete("/api/history").json() == {"deleted": 2}
        assert client.get("/api/history").json()["total"] == 0
