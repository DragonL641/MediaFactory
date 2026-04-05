"""File-related utility functions."""

import os
import subprocess
import platform
from typing import Optional
from pathlib import Path

from ..logging import log_info, log_error


def open_file_location(file_path: str) -> bool:
    """Open the file manager and select/highlight the specified file.

    This function provides cross-platform support for:
    - Windows: Opens Explorer and selects the file
    - macOS: Opens Finder and reveals the file
    - Linux: Opens the parent directory (file selection not supported)

    Args:
        file_path: Path to the file to select

    Returns:
        True if successful, False otherwise
    """
    # Ensure path is absolute
    abs_path = os.path.abspath(file_path)

    # Check if file exists
    if not os.path.exists(abs_path):
        log_error(f"File not found: {abs_path}")
        return False

    try:
        system = platform.system()

        if system == "Windows":
            # Windows: select file in Explorer
            subprocess.run(["explorer", "/select,", abs_path], check=False)
        else:
            # macOS: reveal file in Finder (using -R flag)
            subprocess.run(["open", "-R", abs_path], check=False)

        log_info(f"Opened location: {abs_path}")
        return True

    except FileNotFoundError:
        log_error("File manager command not found")
        return False
    except Exception as e:
        log_error(f"Unable to open folder: {e}")
        return False


def ensure_directory_exists(file_path: str) -> None:
    """Ensure the parent directory of a file path exists.

    Args:
        file_path: Path to a file (directory will be created if needed)
    """
    parent_dir = os.path.dirname(file_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)


def generate_output_path(
    input_path: str,
    output_dir: Optional[str] = None,
    suffix: Optional[str] = None,
    prefix: str = "",
) -> str:
    """Generate an output path based on an input path.

    Args:
        input_path: Input file path
        output_dir: Output directory (defaults to input file's directory)
        suffix: Suffix to add before the extension (e.g., "_translated")
        prefix: Prefix to add to the filename (e.g., "new_")

    Returns:
        Generated output path
    """
    input_path_obj = Path(input_path)
    stem = input_path_obj.stem
    extension = input_path_obj.suffix

    # Build new filename
    new_stem = f"{prefix}{stem}{suffix}" if suffix else f"{prefix}{stem}"
    new_filename = f"{new_stem}{extension}"

    # Determine output directory
    if output_dir:
        return str(Path(output_dir) / new_filename)
    else:
        return str(input_path_obj.parent / new_filename)


__all__ = [
    "open_file_location",
    "ensure_directory_exists",
    "generate_output_path",
]
