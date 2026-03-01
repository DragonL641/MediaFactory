"""Resource management utilities for MediaFactory.

Provides context managers for automatic resource cleanup.
"""

import os
import tempfile
from contextlib import contextmanager
from typing import Optional, Generator


@contextmanager
def temporary_audio_file(base_path: str) -> Generator[str, None, None]:
    """Context manager for temporary audio file cleanup.

    Args:
        base_path: Base path used for naming the temporary file

    Yields:
        Path to the temporary audio file

    Example:
        with temporary_audio_file("/path/to/video.mp4") as audio_path:
            # Process audio
            pass
        # Temporary file is automatically cleaned up
    """
    # Create temporary file in same directory as base_path
    base_dir = os.path.dirname(base_path) or "."
    base_name = os.path.splitext(os.path.basename(base_path))[0]
    temp_name = f".{base_name}.temp.wav"
    temp_path = os.path.join(base_dir, temp_name)

    try:
        yield temp_path
    finally:
        # Clean up temporary file if it exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                # Log but don't raise - cleanup failure shouldn't break processing
                pass


@contextmanager
def temporary_file(
    suffix: str = ".tmp", prefix: str = "mf_"
) -> Generator[str, None, None]:
    """Context manager for temporary file cleanup using system temp directory.

    Args:
        suffix: File suffix (e.g., ".wav", ".txt")
        prefix: File prefix

    Yields:
        Path to the temporary file

    Example:
        with temporary_file(".wav", "audio_") as temp_path:
            # Write to temp file
            pass
        # File is automatically cleaned up
    """
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)  # Close file descriptor, we'll manage the path

    try:
        yield temp_path
    finally:
        # Clean up temporary file if it exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                # Log but don't raise - cleanup failure shouldn't break processing
                pass


@contextmanager
def cleanup_on_error(
    file_path: str, remove_on_success: bool = False
) -> Generator[None, None, None]:
    """Context manager that cleans up a file on error, optionally on success too.

    Args:
        file_path: Path to the file to clean up
        remove_on_success: If True, remove file even if no error occurs

    Yields:
        None

    Example:
        with cleanup_on_error(audio_path):
            process_audio(audio_path)
        # File cleaned up only if exception raised
    """
    try:
        yield
    except Exception:
        # Only clean up on error
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise
    else:
        # Clean up on success if requested
        if remove_on_success and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


def safe_remove_file(file_path: str) -> bool:
    """Safely remove a file without raising exceptions.

    Args:
        file_path: Path to the file to remove

    Returns:
        True if file was removed, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False


def safe_move_file(src: str, dst: str) -> bool:
    """Safely move a file, removing destination if it exists.

    Args:
        src: Source file path
        dst: Destination file path

    Returns:
        True if move succeeded, False otherwise
    """
    try:
        # Remove destination if it exists
        if os.path.exists(dst):
            os.remove(dst)
        # Move file
        os.rename(src, dst)
        return True
    except Exception:
        return False
