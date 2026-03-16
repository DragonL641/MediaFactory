"""
Download Worker Subprocess Module

Executes download tasks in an independent subprocess, supporting true forced termination.
This solves the problem that Python threads cannot be forcefully terminated.

Usage:
    python download_worker.py <json_params>

The json_params should contain:
    - mode: "repo" or "file"
    - repo_id: HuggingFace repository ID
    - local_dir: Local directory to save the model
    - filename: (file mode only) The filename to download
    - endpoint: (optional) Custom HuggingFace endpoint
"""

import sys
import json
import time
import traceback
from pathlib import Path
from typing import Dict, Any


def _log(message: str) -> None:
    """Log message to stderr (captured by parent process)."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [DownloadWorker] {message}", file=sys.stderr, flush=True)


def download_repo_worker(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Repository download worker function.

    Args:
        params: Download parameters containing:
            - repo_id: HuggingFace repository ID
            - local_dir: Local directory path
            - endpoint: (optional) Custom endpoint
            - allow_patterns: (optional) List of glob patterns for files to include
            - ignore_patterns: (optional) List of glob patterns for files to exclude
            - timeout: (optional) HTTP request timeout in seconds

    Returns:
        Dict with 'success' boolean and optional 'error' message
    """
    import os
    from huggingface_hub import snapshot_download

    try:
        repo_id = params["repo_id"]
        local_dir = params["local_dir"]
        endpoint = params.get("endpoint")
        allow_patterns = params.get("allow_patterns")
        ignore_patterns = params.get("ignore_patterns")
        timeout = params.get("timeout", 30)

        # 设置 huggingface_hub 超时环境变量
        os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = str(timeout)
        os.environ["HF_HUB_ETAG_TIMEOUT"] = str(timeout)

        # 记录下载源
        download_source = endpoint if endpoint else "https://huggingface.co"
        _log(f"Starting repo download: {repo_id}")
        _log(f"Download source: {download_source}")
        _log(f"Target directory: {local_dir}")
        _log(f"Request timeout: {timeout}s")
        if allow_patterns:
            _log(f"Allow patterns: {allow_patterns}")
        if ignore_patterns:
            _log(f"Ignore patterns: {ignore_patterns}")

        # Ensure local directory exists
        Path(local_dir).mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        _log("Calling snapshot_download...")

        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            endpoint=endpoint,
            allow_patterns=allow_patterns,
            ignore_patterns=ignore_patterns,
        )

        elapsed = time.time() - start_time
        _log(f"Download completed in {elapsed:.1f} seconds")

        return {"success": True}

    except Exception as e:
        _log(f"Download failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def download_file_worker(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Single file download worker function.

    Args:
        params: Download parameters containing:
            - repo_id: HuggingFace repository ID
            - filename: The file to download
            - local_dir: Local directory path
            - endpoint: (optional) Custom endpoint
            - local_filename: (optional) Target filename after download
            - timeout: (optional) HTTP request timeout in seconds

    Returns:
        Dict with 'success' boolean and optional 'error' message
    """
    import os
    import shutil
    from huggingface_hub import hf_hub_download

    try:
        repo_id = params["repo_id"]
        filename = params["filename"]
        local_dir = params["local_dir"]
        endpoint = params.get("endpoint")
        local_filename = params.get("local_filename")
        timeout = params.get("timeout", 30)

        # 设置 huggingface_hub 超时环境变量
        os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = str(timeout)
        os.environ["HF_HUB_ETAG_TIMEOUT"] = str(timeout)

        # 记录下载源
        download_source = endpoint if endpoint else "https://huggingface.co"
        _log(f"Starting file download: {repo_id}/{filename}")
        _log(f"Download source: {download_source}")
        _log(f"Target directory: {local_dir}")
        _log(f"Request timeout: {timeout}s")
        if local_filename:
            _log(f"Will rename to: {local_filename}")

        # Ensure local directory exists
        Path(local_dir).mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        _log("Calling hf_hub_download...")

        # Download the file
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=local_dir,
            endpoint=endpoint,
        )

        _log(f"File downloaded to: {downloaded_path}")

        # Rename if local_filename is specified and different
        if local_filename:
            downloaded_file = Path(downloaded_path)
            target_file = Path(local_dir) / local_filename

            if downloaded_file.exists() and downloaded_file != target_file:
                if target_file.exists():
                    target_file.unlink()
                shutil.move(str(downloaded_file), str(target_file))
                _log(f"File renamed to: {local_filename}")

        elapsed = time.time() - start_time
        _log(f"Download completed in {elapsed:.1f} seconds")

        return {"success": True}

    except Exception as e:
        _log(f"Download failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def main():
    """Subprocess entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No parameters provided"}))
        sys.exit(1)

    try:
        params = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    mode = params.get("mode", "repo")

    if mode == "repo":
        result = download_repo_worker(params)
    elif mode == "file":
        result = download_file_worker(params)
    else:
        result = {"success": False, "error": f"Unknown mode: {mode}"}

    # Output result as JSON to stdout
    print(json.dumps(result))

    # Exit with appropriate code
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    main()
