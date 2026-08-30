"""system 路由（browse/reveal/shutdown）单元测试。"""

import asyncio
import os
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mediafactory.api import server_ref
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

    def test_browse_defaults_to_home(self, client):
        resp = client.get("/api/system/browse")
        assert resp.status_code == 200
        assert resp.json()["path"] == str(Path.home())

    def test_browse_ext_normalization(self, client, tmp_path):
        (tmp_path / "V.MP4").write_text("x")
        (tmp_path / "c.mov").write_text("x")
        resp = client.get(
            "/api/system/browse",
            params={"path": str(tmp_path), "ext": " .MP4 ,, avi"},
        )
        names = {e["name"] for e in resp.json()["entries"]}
        assert "V.MP4" in names
        assert "c.mov" not in names

    def test_browse_root_parent_is_none(self, client):
        resp = client.get("/api/system/browse", params={"path": "/"})
        assert resp.json()["parent"] is None

    def test_browse_skips_dotfiles(self, client, tmp_path):
        (tmp_path / ".hidden").write_text("x")
        (tmp_path / "visible.mp4").write_text("x")
        resp = client.get(
            "/api/system/browse", params={"path": str(tmp_path), "ext": "mp4"}
        )
        names = {e["name"] for e in resp.json()["entries"]}
        assert ".hidden" not in names
        assert "visible.mp4" in names

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="POSIX 权限语义；Windows chmod 不移除目录遍历权",
    )
    def test_browse_skips_unstattable_entries(self, client, tmp_path):
        # POSIX 复现 Windows junction 场景：目录去掉 x 权限后可列名，
        # 但其下条目 is_dir() 抛 EACCES——应跳过条目而非 400
        locked = tmp_path / "locked"
        locked.mkdir()
        (locked / "a.mp4").write_text("x")
        (locked / "sub").mkdir()
        os.chmod(locked, 0o644)
        try:
            resp = client.get("/api/system/browse", params={"path": str(locked)})
            assert resp.status_code == 200
            assert resp.json()["entries"] == []
        finally:
            os.chmod(locked, 0o755)  # 还原权限，避免影响 tmp_path 清理


class TestReveal:
    def test_reveal_calls_platform_command(self, client, tmp_path, monkeypatch):
        target = tmp_path / "out.mp4"
        target.write_text("x")
        calls = []

        class FakeProc:
            async def wait(self):
                return 0

        async def fake_spawn(*cmd, **kwargs):
            calls.append(cmd)
            return FakeProc()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_spawn)
        resp = client.post("/api/system/reveal", json={"path": str(target)})
        assert resp.status_code == 204
        assert calls, "应调用系统命令"
        if sys.platform == "darwin":
            assert calls[0][:2] == ("open", "-R")
        elif sys.platform == "win32":
            assert "explorer" in calls[0][0]

    def test_reveal_missing_path_returns_400(self, client, tmp_path):
        resp = client.post(
            "/api/system/reveal", json={"path": str(tmp_path / "nope.mp4")}
        )
        assert resp.status_code == 400

    def test_reveal_unsupported_platform_returns_400(
        self, client, tmp_path, monkeypatch
    ):
        target = tmp_path / "x.mp4"
        target.write_text("x")
        monkeypatch.setattr(sys, "platform", "linux")
        resp = client.post("/api/system/reveal", json={"path": str(target)})
        assert resp.status_code == 400


class TestShutdownEndpoint:
    """POST /api/system/shutdown：壳退出时触发 uvicorn 优雅停机"""

    def test_shutdown_sets_should_exit(self, client, monkeypatch):
        fake_server = types.SimpleNamespace(should_exit=False)
        monkeypatch.setattr(server_ref, "_server", fake_server)
        resp = client.post("/api/system/shutdown")
        assert resp.status_code == 200
        assert resp.json()["status"] == "shutting_down"
        assert fake_server.should_exit is True

    def test_shutdown_without_server_returns_503(self, client, monkeypatch):
        monkeypatch.setattr(server_ref, "_server", None)
        resp = client.post("/api/system/shutdown")
        assert resp.status_code == 503
