"""i18n 国际化模块测试

覆盖 t() 翻译、语言切换和初始化功能。
注意：i18n 使用全局状态，测试之间需要重置状态。
"""

import pytest

from mediafactory.i18n import (
    get_language,
    init_i18n,
    set_language,
    t,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture(autouse=True)
def reset_i18n():
    """每个测试前重置 i18n 到默认英文状态"""
    init_i18n()
    yield
    init_i18n()


# ============================================================================
# 1. t() 已知 key
# ============================================================================


class TestTranslationKnownKey:
    """t() 对已知 key 的翻译测试"""

    def test_simple_key(self):
        result = t("progress.audioExtractionStart")
        assert isinstance(result, str)
        assert len(result) > 0
        # 英文翻译应包含 audio 相关词
        assert "audio" in result.lower()

    def test_nested_key_error_section(self):
        result = t("error.generic.fileNotFound")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_top_level_key(self):
        result = t("progress.completed")
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# 2. t() 未知 key
# ============================================================================


class TestTranslationUnknownKey:
    """t() 对未知 key 应返回 key 本身"""

    def test_unknown_key_returns_key(self):
        result = t("nonexistent.key")
        assert result == "nonexistent.key"

    def test_completely_unknown_key(self):
        result = t("this.key.does.not.exist")
        assert result == "this.key.does.not.exist"


# ============================================================================
# 3. t() 变量插值 {{var}}
# ============================================================================


class TestTranslationInterpolation:
    """t() {{variable}} 插值测试"""

    def test_single_variable(self):
        result = t("progress.processingAudio", processed="10", total="30")
        assert "10" in result
        assert "30" in result

    def test_multiple_variables(self):
        result = t(
            "progress.translatingSegment",
            current="5",
            total="20",
        )
        assert "5" in result
        assert "20" in result

    def test_model_name_interpolation(self):
        result = t("progress.loadingModel", model="whisper-large")
        assert "whisper-large" in result

    def test_no_interpolation_without_kwargs(self):
        """不传变量时，{{var}} 占位符应保留原样"""
        result = t("progress.processingAudio")
        assert "{{processed}}" in result


# ============================================================================
# 4. set_language() / get_language()
# ============================================================================


class TestLanguageSwitching:
    """语言切换测试"""

    def test_default_language_is_en(self):
        lang = get_language()
        assert lang == "en"

    def test_set_language_to_chinese(self):
        set_language("zh-CN")
        assert get_language() == "zh-CN"

    def test_set_language_back_to_english(self):
        set_language("zh-CN")
        set_language("en")
        assert get_language() == "en"

    def test_chinese_translation_works(self):
        set_language("zh-CN")
        result = t("progress.audioExtractionStart")
        # 中文翻译应包含中文字符
        assert any("\u4e00" <= c <= "\u9fff" for c in result)

    def test_unknown_language_falls_back_to_en(self):
        """设置不存在的语言时，翻译应回退到英文"""
        set_language("xx-XX")
        result = t("progress.completed")
        # 应返回英文翻译而非 key 本身
        assert isinstance(result, str)
        assert result != "progress.completed"


# ============================================================================
# 5. init_i18n()
# ============================================================================


class TestInitI18n:
    """init_i18n 初始化测试"""

    def test_does_not_raise(self):
        init_i18n()

    def test_sets_language_to_en(self):
        set_language("zh-CN")
        init_i18n()
        assert get_language() == "en"

    def test_translation_works_after_init(self):
        init_i18n()
        result = t("progress.completed")
        assert isinstance(result, str)
        assert len(result) > 0
