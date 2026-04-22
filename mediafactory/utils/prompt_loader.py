"""Prompt 模板加载器。

从 resources/prompts/ 目录加载 Markdown 格式的 prompt 模板，支持变量替换。

使用示例:
    from mediafactory.utils.prompt_loader import get_prompt

    # 加载 prompt
    prompt = get_prompt("translate/batch")

    # 带参数替换
    prompt = get_prompt("translate/batch", target_language="中文")
"""

from pathlib import Path
from string import Template
import functools


def _get_prompts_dir() -> Path:
    """获取 prompts 目录路径（位于 resources/prompts/）。"""
    return Path(__file__).parent.parent / "resources" / "prompts"


PROMPTS_DIR = _get_prompts_dir()


@functools.lru_cache(maxsize=32)
def _load_prompt_file(prompt_path: str) -> str:
    """从文件加载 prompt（带 LRU 缓存）。

    Args:
        prompt_path: prompt 相对路径，如 "translate/batch"

    Returns:
        prompt 原始文本

    Raises:
        FileNotFoundError: prompt 文件不存在
    """
    file_path = PROMPTS_DIR / f"{prompt_path}.md"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}.md\n"
            f"Expected location: {file_path}"
        )

    return file_path.read_text(encoding="utf-8")


def get_prompt(prompt_path: str, **kwargs) -> str:
    """获取 prompt 并进行变量替换。

    Args:
        prompt_path: prompt 路径，如 "translate/batch"
        **kwargs: 模板变量，用于替换 prompt 中的 ${variable}

    Returns:
        处理后的 prompt 文本

    Examples:
        >>> get_prompt("translate/batch")
        >>> get_prompt("translate/batch", target_language="中文")
    """
    # 加载原始 prompt
    raw_prompt = _load_prompt_file(prompt_path)

    # 如果没有参数，直接返回
    if not kwargs:
        return raw_prompt

    # 使用 Template 进行变量替换
    template = Template(raw_prompt)
    return template.safe_substitute(**kwargs)


def list_prompts() -> list[str]:
    """列出所有可用的 prompt 路径。

    Returns:
        prompt 路径列表，如 ["translate/batch", "translate/single"]
    """
    prompts = []
    for md_file in PROMPTS_DIR.rglob("*.md"):
        if md_file.name == "README.md":
            continue
        # 转换为相对路径，去掉 .md 后缀
        rel_path = md_file.relative_to(PROMPTS_DIR)
        prompt_path = str(rel_path.with_suffix("")).replace("\\", "/")
        prompts.append(prompt_path)
    return sorted(prompts)


def reload_cache():
    """清空 prompt 缓存（用于开发模式热重载）。"""
    _load_prompt_file.cache_clear()


__all__ = ["get_prompt", "list_prompts", "reload_cache"]
