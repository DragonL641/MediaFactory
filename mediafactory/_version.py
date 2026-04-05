"""Version management utilities for MediaFactory.

Uses pyproject.toml as the single source of truth for version information.
"""

from __future__ import annotations

__all__ = ["get_version", "__version__", "_parse_version_simple"]

from functools import lru_cache
from pathlib import Path


from typing import Optional


def _get_version_from_pyproject() -> str:
    """Read version from pyproject.toml.

    Returns:
        Version string from pyproject.toml

    Raises:
        RuntimeError: If pyproject.toml cannot be found or parsed
    """
    # mediafactory/_version.py → parent (mediafactory/) → parent (project root)
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"

    if not pyproject_path.exists():
        raise RuntimeError(f"pyproject.toml not found at {pyproject_path}")

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            tomllib = None

    if tomllib is not None:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    else:
        # 简单解析器 fallback（当 tomli/tomllib 不可用时）
        return _parse_version_simple(pyproject_path)


def _parse_version_simple(pyproject_path: Path) -> str:
    """简单版本解析器，仅提取 version 字段。"""
    with open(pyproject_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("version = "):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise RuntimeError("Could not find version in pyproject.toml")


@lru_cache(maxsize=1)
def get_version() -> str:
    """获取包版本号（缓存避免重复读文件）。"""
    return _get_version_from_pyproject()


__version__ = get_version()


if __name__ == "__main__":
    # 允许构建脚本直接调用: python mediafactory/_version.py
    print(get_version())
