"""exception_wrapper 模块测试

覆盖异常层次结构、异常转换和上下文管理器功能。
"""

import pytest

from mediafactory.exceptions import (
    ConfigurationError,
    ErrorSeverity,
    MediaFactoryError,
    OperationCancelledError,
    ProcessingError,
    get_error_severity,
    is_retryable_error,
)
from mediafactory.core.exception_wrapper import convert_exception, wrap_exceptions

pytestmark = [pytest.mark.unit]


# ============================================================================
# 1. 异常层次结构
# ============================================================================


class TestExceptionHierarchy:
    """异常继承和默认严重性级别测试"""

    def test_media_factory_error_is_base(self):
        """所有自定义异常都应继承自 MediaFactoryError"""
        assert issubclass(ProcessingError, MediaFactoryError)
        assert issubclass(ConfigurationError, MediaFactoryError)
        assert issubclass(OperationCancelledError, MediaFactoryError)

    def test_processing_error_default_severity_recoverable(self):
        err = ProcessingError("test")
        assert err.severity == ErrorSeverity.RECOVERABLE.value

    def test_configuration_error_default_severity_fatal(self):
        err = ConfigurationError("test")
        assert err.severity == ErrorSeverity.FATAL.value

    def test_operation_cancelled_error_default_severity_warning(self):
        err = OperationCancelledError("test")
        assert err.severity == ErrorSeverity.WARNING.value

    def test_custom_severity_overrides_default(self):
        err = ProcessingError("test", severity=ErrorSeverity.FATAL)
        assert err.severity == ErrorSeverity.FATAL.value

    def test_media_factory_error_stores_context(self):
        ctx = {"file": "audio.wav", "step": "extract"}
        err = MediaFactoryError("boom", context=ctx)
        assert err.context == ctx

    def test_media_factory_error_default_empty_context(self):
        err = MediaFactoryError("boom")
        assert err.context == {}

    def test_to_dict(self):
        err = ProcessingError("test", context={"key": "val"})
        d = err.to_dict()
        assert d["error_type"] == "ProcessingError"
        assert d["message"] == "test"
        assert d["context"] == {"key": "val"}
        assert d["severity"] == "recoverable"
        assert d["is_retryable"] is True


# ============================================================================
# 2. ErrorSeverity 枚举
# ============================================================================


class TestErrorSeverity:
    """ErrorSeverity 枚举值测试"""

    def test_enum_values(self):
        assert ErrorSeverity.FATAL.value == "fatal"
        assert ErrorSeverity.RECOVERABLE.value == "recoverable"
        assert ErrorSeverity.WARNING.value == "warning"

    def test_enum_members(self):
        members = list(ErrorSeverity)
        assert len(members) == 3


# ============================================================================
# 3. get_error_severity()
# ============================================================================


class TestGetErrorSeverity:
    """get_error_severity 函数分类测试"""

    def test_media_factory_error_fatal(self):
        err = ConfigurationError("bad config")
        assert get_error_severity(err) == ErrorSeverity.FATAL

    def test_media_factory_error_recoverable(self):
        err = ProcessingError("transcription failed")
        assert get_error_severity(err) == ErrorSeverity.RECOVERABLE

    def test_media_factory_error_warning(self):
        err = OperationCancelledError("user cancelled")
        assert get_error_severity(err) == ErrorSeverity.WARNING

    def test_permission_error_is_fatal(self):
        assert get_error_severity(PermissionError("denied")) == ErrorSeverity.FATAL

    def test_file_not_found_is_fatal(self):
        assert get_error_severity(FileNotFoundError("missing")) == ErrorSeverity.FATAL

    def test_value_error_is_fatal(self):
        assert get_error_severity(ValueError("bad value")) == ErrorSeverity.FATAL

    def test_type_error_is_fatal(self):
        assert get_error_severity(TypeError("wrong type")) == ErrorSeverity.FATAL

    def test_timeout_error_is_recoverable(self):
        assert get_error_severity(TimeoutError("timed out")) == ErrorSeverity.RECOVERABLE

    def test_connection_error_is_recoverable(self):
        assert get_error_severity(ConnectionError("refused")) == ErrorSeverity.RECOVERABLE

    def test_string_auth_keywords_are_fatal(self):
        """包含认证关键词的普通异常应归类为 FATAL"""
        err = RuntimeError("unauthorized access")
        assert get_error_severity(err) == ErrorSeverity.FATAL

    def test_string_auth_401_is_fatal(self):
        err = RuntimeError("Got 401 response")
        assert get_error_severity(err) == ErrorSeverity.FATAL

    def test_string_invalid_api_key_is_fatal(self):
        err = RuntimeError("invalid api key provided")
        assert get_error_severity(err) == ErrorSeverity.FATAL

    def test_string_timeout_keyword_is_recoverable(self):
        err = RuntimeError("connection timeout occurred")
        assert get_error_severity(err) == ErrorSeverity.RECOVERABLE

    def test_string_connection_keyword_is_recoverable(self):
        err = RuntimeError("connection reset by peer")
        assert get_error_severity(err) == ErrorSeverity.RECOVERABLE

    def test_string_server_error_500_is_recoverable(self):
        err = RuntimeError("server returned 500")
        assert get_error_severity(err) == ErrorSeverity.RECOVERABLE

    def test_string_503_is_recoverable(self):
        err = RuntimeError("service unavailable 503")
        assert get_error_severity(err) == ErrorSeverity.RECOVERABLE

    def test_unknown_error_defaults_to_fatal(self):
        err = RuntimeError("something weird happened")
        assert get_error_severity(err) == ErrorSeverity.FATAL


# ============================================================================
# 4. is_retryable_error()
# ============================================================================


class TestIsRetryableError:
    """is_retryable_error 函数测试"""

    def test_recoverable_is_retryable(self):
        err = ProcessingError("fail")
        assert is_retryable_error(err) is True

    def test_timeout_is_retryable(self):
        assert is_retryable_error(TimeoutError("timeout")) is True

    def test_connection_error_is_retryable(self):
        assert is_retryable_error(ConnectionError("lost")) is True

    def test_fatal_is_not_retryable(self):
        err = ConfigurationError("bad")
        assert is_retryable_error(err) is False

    def test_value_error_is_not_retryable(self):
        assert is_retryable_error(ValueError("bad")) is False

    def test_warning_is_not_retryable(self):
        """WARNING 严重性不是 RECOVERABLE，所以 is_retryable 返回 False"""
        err = OperationCancelledError("cancelled")
        # is_retryable_error 检查的是 RECOVERABLE，不是 WARNING
        assert is_retryable_error(err) is False


# ============================================================================
# 5. convert_exception()
# ============================================================================


class TestConvertException:
    """convert_exception 关键词分类测试"""

    def test_auth_keyword_produces_configuration_error(self):
        """认证相关关键词应转换为 ConfigurationError"""
        exc = RuntimeError("unauthorized")
        result = convert_exception(exc)
        assert isinstance(result, ConfigurationError)
        assert result.severity == ErrorSeverity.FATAL.value

    def test_forbidden_keyword_produces_configuration_error(self):
        exc = RuntimeError("access forbidden")
        result = convert_exception(exc)
        assert isinstance(result, ConfigurationError)

    def test_authentication_keyword_produces_configuration_error(self):
        exc = RuntimeError("authentication failed")
        result = convert_exception(exc)
        assert isinstance(result, ConfigurationError)

    def test_missing_keyword_produces_configuration_error(self):
        exc = RuntimeError("missing configuration")
        result = convert_exception(exc)
        assert isinstance(result, ConfigurationError)

    def test_timeout_keyword_produces_processing_error(self):
        """可恢复关键词应转换为 ProcessingError (RECOVERABLE)"""
        exc = RuntimeError("request timeout")
        result = convert_exception(exc)
        assert isinstance(result, ProcessingError)
        assert result.severity == ErrorSeverity.RECOVERABLE.value

    def test_connection_keyword_produces_processing_error(self):
        exc = RuntimeError("connection refused")
        result = convert_exception(exc)
        assert isinstance(result, ProcessingError)
        assert result.severity == ErrorSeverity.RECOVERABLE.value

    def test_network_keyword_produces_processing_error(self):
        exc = RuntimeError("network error")
        result = convert_exception(exc)
        assert isinstance(result, ProcessingError)
        assert result.severity == ErrorSeverity.RECOVERABLE.value

    def test_cuda_keyword_produces_processing_error(self):
        exc = RuntimeError("cuda out of memory")
        result = convert_exception(exc)
        assert isinstance(result, ProcessingError)
        assert result.severity == ErrorSeverity.RECOVERABLE.value

    def test_default_produces_processing_error(self):
        """不匹配任何关键词时，默认转换为 ProcessingError"""
        exc = RuntimeError("something went wrong")
        result = convert_exception(exc)
        assert isinstance(result, ProcessingError)
        # 默认 ProcessingError 严重性是 RECOVERABLE
        assert result.severity == ErrorSeverity.RECOVERABLE.value

    def test_context_is_preserved(self):
        """传入的 context 应被保留并扩展"""
        exc = ValueError("bad value")
        result = convert_exception(exc, context={"file": "test.wav"})
        assert result.context["file"] == "test.wav"
        assert result.context["original_exception"] == "ValueError"

    def test_original_exception_type_recorded(self):
        exc = TypeError("type failure")
        result = convert_exception(exc)
        assert result.context["original_exception"] == "TypeError"

    def test_message_preserved(self):
        exc = RuntimeError("original message")
        result = convert_exception(exc)
        assert result.message == "original message"


# ============================================================================
# 6. wrap_exceptions() 上下文管理器
# ============================================================================


class TestWrapExceptions:
    """wrap_exceptions 上下文管理器测试"""

    def test_happy_path_no_exception(self):
        """无异常时正常退出"""
        with wrap_exceptions():
            x = 1 + 1
        assert x == 2

    def test_media_factory_error_passes_through(self):
        """MediaFactoryError 应原样抛出，不包装"""
        original = ProcessingError("original")
        with pytest.raises(ProcessingError) as exc_info:
            with wrap_exceptions():
                raise original
        assert exc_info.value is original

    def test_configuration_error_passes_through(self):
        original = ConfigurationError("config bad")
        with pytest.raises(ConfigurationError) as exc_info:
            with wrap_exceptions():
                raise original
        assert exc_info.value is original

    def test_generic_exception_converted(self):
        """非 MediaFactoryError 应被转换"""
        with pytest.raises(MediaFactoryError):
            with wrap_exceptions():
                raise RuntimeError("generic error")

    def test_generic_runtime_error_converted_to_processing_error(self):
        """普通 RuntimeError 应被转换为 ProcessingError"""
        with pytest.raises(ProcessingError):
            with wrap_exceptions():
                raise RuntimeError("something failed")

    def test_context_passed_to_converted_exception(self):
        """wrap_exceptions 的 context 参数应传递到转换后的异常"""
        with pytest.raises(MediaFactoryError) as exc_info:
            with wrap_exceptions(context={"file": "audio.mp3"}):
                raise RuntimeError("fail")
        assert exc_info.value.context["file"] == "audio.mp3"

    def test_operation_added_to_context(self):
        """operation 参数应添加到上下文"""
        with pytest.raises(MediaFactoryError) as exc_info:
            with wrap_exceptions(operation="extract"):
                raise RuntimeError("fail")
        assert exc_info.value.context["operation"] == "extract"

    def test_reraise_types_not_wrapped(self):
        """reraise_types 中的异常应原样抛出"""
        with pytest.raises(ValueError):
            with wrap_exceptions(reraise_types=(ValueError,)):
                raise ValueError("do not wrap me")

    def test_keyboard_interrupt_converted_to_cancelled(self):
        """KeyboardInterrupt 应转换为 OperationCancelledError"""
        with pytest.raises(OperationCancelledError):
            with wrap_exceptions():
                raise KeyboardInterrupt

    def test_chained_from_original(self):
        """转换后的异常应通过 __cause__ 链接到原始异常"""
        original = RuntimeError("source error")
        with pytest.raises(MediaFactoryError) as exc_info:
            with wrap_exceptions():
                raise original
        assert exc_info.value.__cause__ is original
