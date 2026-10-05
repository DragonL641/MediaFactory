"""FILE 模式 GET 流式下载契约（本地 HTTP 服务器，零外网依赖）"""

import http.server
import hashlib
import threading
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]


class _StubHandler(http.server.BaseHTTPRequestHandler):
    """按路径回放预置内容；未知路径 404"""

    payload = b"\x00" * 300_000  # 300KB 假权重
    seen_headers: dict = {}
    seen_paths: list = []

    def do_GET(self):  # noqa: N802
        _StubHandler.seen_paths.append(self.path)
        _StubHandler.seen_headers = dict(self.headers)
        if self.path.endswith("/RealESRGAN_x4plus.pth"):
            body = _StubHandler.payload
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.endswith("/no-length.pth"):
            # 无 content-length 的分块响应（镜像/CDN 边缘情况）
            body = _StubHandler.payload
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # 静默
        pass


@pytest.fixture
def mirror_server():
    _StubHandler.seen_paths = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", server
    server.shutdown()


class TestDownloadFileViaGet:
    def test_streams_to_custom_path_and_reports_progress(self, tmp_path, mirror_server):
        endpoint, _ = mirror_server
        from mediafactory.models.model_download import download_model

        out = tmp_path / "RealESRGAN_x4plus.pth"
        progress: list[tuple[float, str]] = []

        download_model(
            "RealESRGAN_x4plus",
            custom_path=str(out),
            download_source=endpoint,
            progress_callback=lambda p, m: progress.append((p, m)),
        )

        assert out.read_bytes() == _StubHandler.payload
        assert progress, "进度回调未被调用"
        assert progress[-1][0] == pytest.approx(1.0)
        assert not out.with_suffix(out.suffix + ".part").exists()

    def test_404_after_retries_raises_and_cleans(self, tmp_path, mirror_server, monkeypatch):
        endpoint, _ = mirror_server
        monkeypatch.setattr("mediafactory.models.model_download.time.sleep", lambda s: None)
        from mediafactory.models.model_download import download_model

        out = tmp_path / "missing.pth"
        with pytest.raises(Exception, match="Download failed"):
            download_model(
                "NAFNet-GoPro-width64",  # 已注册条目；stub 对其文件名 404
                custom_path=str(out),
                download_source=endpoint,
            )
        assert not out.exists()
        assert not Path(str(out) + ".part").exists()

    def test_token_forwarded_as_authorization(self, tmp_path, mirror_server):
        endpoint, _ = mirror_server
        from mediafactory.models.model_download import download_model

        download_model(
            "RealESRGAN_x4plus",
            custom_path=str(tmp_path / "RealESRGAN_x4plus.pth"),
            download_source=endpoint,
            hf_token="hf_test_token",
        )
        assert _StubHandler.seen_headers.get("Authorization") == "Bearer hf_test_token"

    def test_revision_in_url(self, tmp_path, mirror_server):
        endpoint, _ = mirror_server
        from mediafactory.models.model_download import _download_file_via_get

        _download_file_via_get(
            repo_id="leonelhs/facexlib",
            filename="RealESRGAN_x4plus.pth",  # stub 按文件名回放
            local_path=tmp_path / "f.pth",
            endpoint=endpoint,
            revision="v2",
        )
        assert any("/resolve/v2/" in p for p in _StubHandler.seen_paths)

    def test_unknown_content_length_reports_mb_progress(self, tmp_path, mirror_server):
        endpoint, _ = mirror_server
        from mediafactory.models.model_download import _download_file_via_get

        progress: list[tuple[float, str]] = []
        _download_file_via_get(
            repo_id="r",
            filename="no-length.pth",
            local_path=tmp_path / "nl.pth",
            endpoint=endpoint,
            progress_callback=lambda p, m: progress.append((p, m)),
        )
        assert (tmp_path / "nl.pth").read_bytes() == _StubHandler.payload
        # 无 total 时：进度未知不虚报，消息携带已下载 MB 数
        assert all(p == 0.0 for p, _ in progress)
        assert progress and "MB" in progress[-1][1]

    def test_sha256_mismatch_raises_and_cleans(self, tmp_path, mirror_server):
        endpoint, _ = mirror_server
        from mediafactory.models.model_download import _download_file_via_get

        out = tmp_path / "bad.pth"
        with pytest.raises(Exception, match="checksum"):
            _download_file_via_get(
                repo_id="r",
                filename="RealESRGAN_x4plus.pth",
                local_path=out,
                endpoint=endpoint,
                expected_sha256="0" * 64,
            )
        assert not out.exists()
        assert not Path(str(out) + ".part").exists()

    def test_sha256_match_passes(self, tmp_path, mirror_server):
        endpoint, _ = mirror_server
        from mediafactory.models.model_download import _download_file_via_get

        good = hashlib.sha256(_StubHandler.payload).hexdigest()
        _download_file_via_get(
            repo_id="r",
            filename="RealESRGAN_x4plus.pth",
            local_path=tmp_path / "ok.pth",
            endpoint=endpoint,
            expected_sha256=good,
        )
        assert (tmp_path / "ok.pth").exists()
