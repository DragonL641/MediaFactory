"""system 路由（browse/reveal）单元测试。"""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mediafactory.api.main import get_app

pytestmark = [pytest.mark.unit]


@pytest.fixture
def client():
    return TestClient(get_app())


def make_tree(tmp_path: Path) -> Path:
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "a.mp4").write_text("x")
    (tmp_path / "videos" / "b.srt").write_text("x")
    (tmp_path / "videos" / "sub").mkdir()
    (tmp_path / "notes.txt").write_text("x")
    return tmp_path


class TestBrowse:
    def test_lists_dirs_and_filters_files_by_ext(self, client, tmp_path):
        root = make_tree(tmp_path)
        resp = client.get(
            "/api/system/browse",
            params={"path": str(root / "videos"), "ext": "mp4"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["path"] == str(root / "videos")
        assert data["parent"] == str(root)
        names = {e["name"]: e["is_dir"] for e in data["entries"]}
        assert names["a.mp4"] is False  # 匹配扩展名
        assert names["sub"] is True  # 目录始终显示
        assert "b.srt" not in names  # 不匹配扩展名的文件被过滤
        assert "notes.txt" not in names  # 其他目录的文件不出现在本目录

    def test_browse_without_ext_returns_all_files(self, client, tmp_path):
        root = make_tree(tmp_path)
        resp = client.get("/api/system/browse", params={"path": str(root / "videos")})
        names = {e["name"] for e in resp.json()["entries"]}
        assert names == {"a.mp4", "b.srt", "sub"}

    def test_browse_missing_path_returns_400(self, client, tmp_path):
        resp = client.get("/api/system/browse", params={"path": str(tmp_path / "nope")})
        assert resp.status_code == 400
        assert "detail" in resp.json()

    def test_browse_file_path_returns_400(self, client, tmp_path):
        root = make_tree(tmp_path)
        resp = client.get(
            "/api/system/browse", params={"path": str(root / "notes.txt")}
        )
        assert resp.status_code == 400

    def test_entries_sorted_dirs_first(self, client, tmp_path):
        root = make_tree(tmp_path)
        resp = client.get("/api/system/browse", params={"path": str(root / "videos")})
        entries = resp.json()["entries"]
        is_dirs = [e["is_dir"] for e in entries]
        assert is_dirs == sorted(is_dirs, reverse=True)  # 目录在前


class TestReveal:
    def test_reveal_calls_platform_command(self, client, tmp_path, monkeypatch):
        target = tmp_path / "out.mp4"
        target.write_text("x")
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)

        monkeypatch.setattr(subprocess, "run", fake_run)
        resp = client.post("/api/system/reveal", json={"path": str(target)})
        assert resp.status_code == 204
        assert calls, "应调用系统命令"
        if sys.platform == "darwin":
            assert calls[0][:2] == ["open", "-R"]
        elif sys.platform == "win32":
            assert "explorer" in calls[0][0]

    def test_reveal_missing_path_returns_400(self, client, tmp_path):
        resp = client.post(
            "/api/system/reveal", json={"path": str(tmp_path / "nope.mp4")}
        )
        assert resp.status_code == 400
