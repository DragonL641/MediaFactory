"""daemon 伺服 SPA（webui 静态目录）测试。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import mediafactory.api.main as api_main
from mediafactory.api.main import get_app

pytestmark = [pytest.mark.unit]


@pytest.fixture
def webui(tmp_path: Path, monkeypatch) -> Path:
    """伪造一个构建产物目录并让 daemon 指向它。"""
    webui_dir = tmp_path / "webui"
    (webui_dir / "assets").mkdir(parents=True)
    (webui_dir / "index.html").write_text(
        "<!doctype html><html><body>SPA</body></html>"
    )
    (webui_dir / "assets" / "app.js").write_text("console.log(1)")
    monkeypatch.setattr(api_main, "_webui_dir", lambda: webui_dir)
    # get_app 是懒加载单例——patch 目录后必须重置，否则 mount 用旧目录
    monkeypatch.setattr(api_main, "_app", None)
    return webui_dir


@pytest.fixture
def client(webui):
    # 依赖 webui 保证目录 patch 先于 app 创建
    return TestClient(get_app())


class TestSpaServing:
    def test_root_serves_index(self, client, webui):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "SPA" in resp.text

    def test_client_side_routes_serve_index(self, client, webui):
        for path in ("/tasks", "/settings"):
            resp = client.get(path)
            assert resp.status_code == 200, path
            assert "SPA" in resp.text

    def test_assets_served_from_static_files(self, client, webui):
        resp = client.get("/assets/app.js")
        assert resp.status_code == 200
        assert resp.text == "console.log(1)"

    def test_api_routes_unaffected(self, client, webui):
        resp = client.get("/api/config/")
        assert resp.status_code == 200  # 既有 API 照常

    def test_health_and_ws_paths_unaffected(self, client, webui):
        assert client.get("/health").status_code == 200

    def test_missing_webui_dir_degrades_gracefully(self, tmp_path, monkeypatch):
        monkeypatch.setattr(api_main, "_webui_dir", lambda: tmp_path / "nope")
        monkeypatch.setattr(api_main, "_app", None)
        client = TestClient(get_app())
        # 纯 API 模式：API 照常，根路径 404 但不崩
        assert client.get("/api/config/").status_code == 200
        assert client.get("/").status_code == 404
