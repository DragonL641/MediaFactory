"""FILE 模式 GET 流式下载契约（本地 HTTP 服务器，零外网依赖）"""

import http.server
import threading
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]


class _StubHandler(http.server.BaseHTTPRequestHandler):
    """按路径回放预置内容；未知路径 404"""

    payload = b"\x00" * 300_000  # 300KB 假权重

    def do_GET(self):  # noqa: N802
        if self.path.endswith("/RealESRGAN_x4plus.pth"):
            self.send_response(200)
            self.send_header("Content-Length", str(len(self.payload)))
            self.end_headers()
            self.wfile.write(self.payload)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # 静默
        pass


@pytest.fixture
def mirror_server():
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

    def test_404_after_retries_raises_and_cleans(self, tmp_path, mirror_server):
        endpoint, _ = mirror_server
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
