"""Prompt 加载器测试

覆盖 get_prompt、list_prompts 和 reload_cache 功能。
"""

import pytest

from mediafactory.utils.prompt_loader import get_prompt, list_prompts, reload_cache

pytestmark = [pytest.mark.unit]


# ============================================================================
# 1. get_prompt()
# ============================================================================


class TestGetPrompt:
    """get_prompt 函数测试"""

    def test_returns_string_for_existing_prompt(self):
        result = get_prompt("translate/batch")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string_for_single_prompt(self):
        result = get_prompt("translate/single")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_nonexistent_prompt_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            get_prompt("nonexistent/prompt")

    def test_variable_substitution(self):
        """${variable} 语法应被正确替换"""
        result = get_prompt("translate/batch", target_language="Chinese")
        assert "Chinese" in result
        # ${target_language} 应被替换，不应出现 ${target_language} 字面量
        assert "${target_language}" not in result

    def test_multiple_variable_substitution(self):
        """多个变量同时替换"""
        result = get_prompt(
            "translate/single",
            source_language="English",
            target_language="Chinese",
            prev_text="Hello",
            current_text="World",
            next_text="!",
            custom_instructions="",
        )
        assert "Chinese" in result
        assert "English" in result

    def test_safe_substitute_unreplaced_vars_remain(self):
        """safe_substitute 不会对未提供的变量报错，保留原始占位符"""
        result = get_prompt("translate/batch")
        # 未传入 target_language，${target_language} 应保留
        assert "${target_language}" in result


# ============================================================================
# 2. list_prompts()
# ============================================================================


class TestListPrompts:
    """list_prompts 函数测试"""

    def test_returns_list(self):
        result = list_prompts()
        assert isinstance(result, list)

    def test_contains_known_prompts(self):
        result = list_prompts()
        assert "translate/batch" in result
        assert "translate/single" in result

    def test_items_are_strings(self):
        result = list_prompts()
        for item in result:
            assert isinstance(item, str)

    def test_items_no_md_extension(self):
        result = list_prompts()
        for item in result:
            assert not item.endswith(".md")

    def test_excludes_readme(self):
        result = list_prompts()
        for item in result:
            assert "README" not in item


# ============================================================================
# 3. reload_cache()
# ============================================================================


class TestReloadCache:
    """reload_cache 函数测试"""

    def test_does_not_raise(self):
        reload_cache()

    def test_cache_cleared_and_reload_works(self):
        """清缓存后重新加载，结果应一致"""
        reload_cache()
        result = get_prompt("translate/batch")
        assert isinstance(result, str)
        assert len(result) > 0
