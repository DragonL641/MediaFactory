"""Version management utilities for MediaFactory.

Uses pyproject.toml as the single source of truth for version information.
"""

from __future__ import annotations

__all__ = ["get_version", "__version__", "_parse_version_simple"]

import sys
from functools import lru_cache
from pathlib import Path


def _get_version_from_pyproject() -> str:
    """Read version from pyproject.toml.

    Returns:
        Version string from pyproject.toml

    Raises:
        RuntimeError: If pyproject.toml cannot be found or parsed
    """
    # Start from the current file and search upwards for pyproject.toml
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent  # Go up to project root

    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        # Fallback: try frozen build location
        if getattr(sys, "frozen", False):
            # In frozen builds, version may be embedded in package metadata
            try:
                from importlib.metadata import version

                return version("mediafactory")
            except Exception:
                pass
        raise RuntimeError(f"pyproject.toml not found at {pyproject_path}")

    try:
        import tomli
    except ImportError:
        try:
            import tomllib as tomli
        except ImportError:
            # Python < 3.11 without tomli - simple TOML parser for our needs
            tomli = None

    if tomli is not None:
        with open(pyproject_path, "rb") as f:
            data = tomli.load(f)
            return data["project"]["version"]
    else:
        # Simple parser fallback for when tomli/tomllib is unavailable
        return _parse_version_simple(pyproject_path)


def _parse_version_simple(pyproject_path: Path) -> str:
    """Simple version parser for pyproject.toml when tomli is unavailable.

    This is a minimal parser that only extracts the version field.
    """
    with open(pyproject_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("version = "):
                # Extract version value, handle both single and double quotes
                version = line.split("=", 1)[1].strip().strip("\"'")
                return version
    raise RuntimeError("Could not find version in pyproject.toml")


@lru_cache(maxsize=1)
def get_version() -> str:
    """Get the package version.

    This function is cached to avoid repeated file reads.

    Returns:
        Version string (e.g., "3.1.0")
    """
    return _get_version_from_pyproject()


__version__ = get_version()


if __name__ == "__main__":
    # 允许构建脚本直接调用: python src/mediafactory/_version.py
    print(get_version())
