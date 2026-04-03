"""API 错误处理模块测试

覆盖 sanitize_error() 对各类异常的转换逻辑。
"""

import pytest

from mediafactory.api.error_handler import sanitize_error
from mediafactory.exceptions import (
    ConfigurationError,
    MediaFactoryError,
    ProcessingError,
)
from mediafactory.i18n import init_i18n

pytestmark = [pytest.mark.unit]


@pytest.fixture(autouse=True)
def setup_i18n():
    """每个测试前初始化 i18n（确保翻译文件已加载）"""
    init_i18n()


# ============================================================================
# 1. MediaFactoryError
# ============================================================================


class TestSanitizeMediaFactoryError:
    """MediaFactoryError 应直接使用其 .message"""

    def test_returns_error_message(self):
        err = MediaFactoryError("Something went wrong")
        result = sanitize_error(err)
        assert result == "Something went wrong"

    def test_processing_error_message(self):
        err = ProcessingError("Transcription failed due to audio error")
        result = sanitize_error(err)
        assert result == "Transcription failed due to audio error"

    def test_configuration_error_message(self):
        err = ConfigurationError("Invalid API key")
        result = sanitize_error(err)
        assert result == "Invalid API key"

    def test_message_with_context(self):
        err = MediaFactoryError("Load failed", context={"model": "whisper-large"})
        result = sanitize_error(err)
        assert "Load failed" in result


# ============================================================================
# 2. 标准异常类型
# ============================================================================


class TestSanitizeStandardErrors:
    """标准异常应返回 i18n 翻译的友好消息"""

    def test_file_not_found_error(self):
        err = FileNotFoundError("/path/to/missing.mp4")
        result = sanitize_error(err)
        assert isinstance(result, str)
        assert len(result) > 0
        # 应该是友好消息，不应包含文件路径
        assert "/path/to/missing.mp4" not in result

    def test_permission_error(self):
        err = PermissionError("/protected/file.wav")
        result = sanitize_error(err)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "/protected/file.wav" not in result

    def test_connection_error(self):
        err = ConnectionError("Connection refused")
        result = sanitize_error(err)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_connection_refused_error(self):
        err = ConnectionRefusedError("127.0.0.1:8765")
        result = sanitize_error(err)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_connection_reset_error(self):
        err = ConnectionResetError("reset by peer")
        result = sanitize_error(err)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_timeout_error(self):
        err = TimeoutError("Operation timed out after 30s")
        result = sanitize_error(err)
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# 3. 未知异常
# ============================================================================


class TestSanitizeGenericError:
    """未知异常应返回通用消息，不泄漏内部细节"""

    def test_generic_exception_returns_generic_message(self):
        err = RuntimeError("Internal stack trace details secret=abc123")
        result = sanitize_error(err)
        assert isinstance(result, str)
        assert len(result) > 0
        # 不应包含异常的原始详细信息
        assert "secret=abc123" not in result
        assert "Internal stack trace" not in result

    def test_value_error_returns_generic_message(self):
        err = ValueError("Cannot parse config: malformed TOML at line 42")
        result = sanitize_error(err)
        assert isinstance(result, str)
        # 不应泄漏具体解析错误
        assert "malformed TOML" not in result

    def test_type_error_returns_generic_message(self):
        err = TypeError("expected str, got int")
        result = sanitize_error(err)
        assert isinstance(result, str)
        assert "expected str, got int" not in result
