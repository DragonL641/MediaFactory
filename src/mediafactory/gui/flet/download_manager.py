"""
Download Queue Manager

Provides serial download queue, thread-safe state management, and cleanup on download failure.
Supports both HuggingFace models and enhancement model downloads (all via HuggingFace Hub).
Uses threads for downloads with cooperative cancellation.
"""

import shutil
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from mediafactory.logging import log_error, log_info

# Retry configuration
MAX_RETRIES = 3  # Maximum retry attempts
RETRY_DELAY = 5  # Retry interval (seconds)
# Download timeout (seconds) - 1 hour default
DOWNLOAD_TIMEOUT = 3600

from mediafactory.models.model_registry import (
    MODEL_REGISTRY,
    DownloadMode,
    ModelType,
    get_enhancement_models_dir,
    get_models_base_dir,
    is_model_complete,
)


class DownloadStatus(Enum):
    """Download status enumeration"""

    IDLE = "idle"  # Idle, not downloading
    WAITING = "waiting"  # Queued
    DOWNLOADING = "downloading"  # Downloading
    CANCELLING = "cancelling"  # Cancelling (waiting for current file to complete)
    COMPLETED = "completed"  # Completed
    FAILED = "failed"  # Failed
    CANCELLED = "cancelled"  # Cancelled
    DELETING = "deleting"  # Deleting


class DownloadManager:
    """
    Serial Download Queue Manager (Singleton)

    Manages model download queue, provides thread-safe state access.
    Uses threads for downloads with cooperative cancellation.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Avoid repeated initialization
        if DownloadManager._initialized:
            return
        DownloadManager._initialized = True

        self._lock = threading.Lock()
        self._queue: List[str] = []  # Queued model_id list
        self._current: Optional[str] = None  # Currently downloading model_id
        self._statuses: Dict[str, DownloadStatus] = {}  # {model_id: status}
        self._progress: Dict[str, float] = {}  # {model_id: progress_percent}
        self._messages: Dict[str, str] = {}  # {model_id: status message}
        self._callbacks: List[Callable[[str, DownloadStatus, float, str], None]] = []
        self._cancel_requested: Dict[str, bool] = {}  # {model_id: cancel_flag}
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

        # Polling thread management
        self._poll_threads: Dict[str, threading.Thread] = {}
        self._poll_stop_events: Dict[str, threading.Event] = {}

        # Download thread management (replaces subprocess)
        self._download_thread: Optional[threading.Thread] = None
        self._download_result: Dict[str, Any] = {}  # Store download result

    def enqueue(self, model_id: str) -> bool:
        """
        Add model to download queue

        Args:
            model_id: Model ID

        Returns:
            True if successfully added to queue
        """
        callback_data = None

        with self._lock:
            # Check if already in queue or downloading
            if model_id in self._queue:
                log_info(f"Model {model_id} already in queue")
                return False
            if self._current == model_id:
                log_info(f"Model {model_id} already downloading")
                return False

            # Set status
            if self._current is None:
                # Queue empty, start download directly
                self._current = model_id
                self._statuses[model_id] = DownloadStatus.DOWNLOADING
                self._progress[model_id] = 0.0
                self._messages[model_id] = "Starting download..."
                self._cancel_requested[model_id] = False
                # Start worker thread
                self._start_worker()
            else:
                # Add to queue
                self._queue.append(model_id)
                self._statuses[model_id] = DownloadStatus.WAITING
                self._progress[model_id] = 0.0
                self._messages[model_id] = "Waiting in queue..."

            log_info(f"Model {model_id} enqueued, status: {self._statuses[model_id]}")
            # Prepare callback data (within lock)
            callback_data = self._get_callback_data(model_id)

        # Call callback outside lock
        if callback_data:
            self._notify_callbacks_unlocked(*callback_data)
        return True

    def cancel(self, model_id: str) -> bool:
        """
        Cancel download (queued or downloading)

        Args:
            model_id: Model ID

        Returns:
            True if successfully cancelled
        """
        callback_data = None
        success = False

        with self._lock:
            # Check if in queue
            if model_id in self._queue:
                self._queue.remove(model_id)
                # Clear status, return to IDLE (no files downloaded while queued)
                self._statuses.pop(model_id, None)
                self._progress.pop(model_id, None)
                self._messages.pop(model_id, None)
                log_info(f"Model {model_id} cancelled from queue, status cleared")
                callback_data = (model_id, DownloadStatus.IDLE, 0.0, "")
                success = True
            # Check if currently downloading
            elif self._current == model_id:
                self._cancel_requested[model_id] = True
                self._statuses[model_id] = DownloadStatus.CANCELLING
                self._messages[model_id] = "Cancelling, please wait for current file to complete..."
                log_info(f"Model {model_id} cancel requested, waiting for download to stop")
                callback_data = self._get_callback_data(model_id)
                success = True

        # Notify UI outside lock
        if callback_data:
            self._notify_callbacks_unlocked(*callback_data)
        return success

    def get_status(self, model_id: str) -> DownloadStatus:
        """
        Get model download status

        Args:
            model_id: HuggingFace model ID

        Returns:
            Current download status
        """
        with self._lock:
            return self._statuses.get(model_id, DownloadStatus.IDLE)

    def get_progress(self, model_id: str) -> float:
        """
        Get model download progress

        Args:
            model_id: HuggingFace model ID

        Returns:
            Download progress (0-100)
        """
        with self._lock:
            return self._progress.get(model_id, 0.0)

    def get_message(self, model_id: str) -> str:
        """
        Get model download status message

        Args:
            model_id: HuggingFace model ID

        Returns:
            Status message
        """
        with self._lock:
            return self._messages.get(model_id, "")

    def is_in_queue(self, model_id: str) -> bool:
        """
        Check if model is in queue or downloading

        Args:
            model_id: HuggingFace model ID

        Returns:
            True if in queue or downloading
        """
        with self._lock:
            return model_id in self._queue or self._current == model_id

    def register_callback(
        self, callback: Callable[[str, DownloadStatus, float, str], None]
    ) -> None:
        """
        Register state change callback function

        Args:
            callback: Callback function, receives (model_id, status, progress, message)
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def unregister_callback(
        self, callback: Callable[[str, DownloadStatus, float, str], None]
    ) -> None:
        """
        Unregister state change callback function

        Args:
            callback: Callback function to unregister
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _notify_callbacks(self, model_id: str) -> None:
        """
        Notify all callbacks of state change (called within lock, releases lock before calling callbacks)

        Args:
            model_id: Model ID with state change
        """
        # Get callback data (within lock)
        callback_data = self._get_callback_data(model_id)
        callbacks = list(self._callbacks)

        # Call callbacks outside lock
        for callback in callbacks:
            try:
                callback(*callback_data)
            except Exception as e:
                log_error(f"Callback error: {e}")

    def _get_callback_data(self, model_id: str) -> Tuple[str, DownloadStatus, float, str]:
        """
        Get callback required data (called within lock)

        Args:
            model_id: Model ID

        Returns:
            (model_id, status, progress, message)
        """
        status = self._statuses.get(model_id, DownloadStatus.IDLE)
        progress = self._progress.get(model_id, 0.0)
        message = self._messages.get(model_id, "")
        return (model_id, status, progress, message)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _start_progress_polling(self, model_id: str) -> None:
        """Start progress polling thread"""
        stop_event = threading.Event()
        self._poll_stop_events[model_id] = stop_event

        def poll_progress():
            """Poll download progress"""
            from mediafactory.models.model_download import get_downloaded_size, get_models_dir

            # Get model total size (from registry)
            model_info = MODEL_REGISTRY.get(model_id)
            if not model_info:
                return

            total_size = model_info.model_size_mb * 1024 * 1024  # Convert to bytes

            while not stop_event.is_set():
                try:
                    # Determine path based on download mode
                    if model_info.download_mode == DownloadMode.FILE:
                        # Single file mode
                        filename = model_info.local_filename or model_info.huggingface_filename
                        if filename:
                            model_path = get_enhancement_models_dir() / filename
                        else:
                            model_path = get_enhancement_models_dir()
                    else:
                        # Repository mode
                        model_path = get_models_dir() / model_id

                    downloaded = get_downloaded_size(model_path) if model_path.is_dir() else (
                        model_path.stat().st_size if model_path.exists() else 0
                    )

                    if total_size > 0:
                        progress = min(100, int(downloaded / total_size * 100))
                        message = f"{progress}% ({self._format_size(downloaded)} / {self._format_size(total_size)})"

                        # Update status
                        callback_data = None
                        with self._lock:
                            if model_id in self._statuses:
                                self._progress[model_id] = float(progress)
                                self._messages[model_id] = message
                                callback_data = self._get_callback_data(model_id)

                        # Notify observers outside lock
                        if callback_data:
                            self._notify_callbacks_unlocked(*callback_data)

                except Exception as e:
                    log_info(f"Poll progress error: {e}")

                # Wait 1 second
                stop_event.wait(1.0)

        thread = threading.Thread(target=poll_progress, daemon=True)
        self._poll_threads[model_id] = thread
        thread.start()

    def _stop_progress_polling(self, model_id: str) -> None:
        """Stop progress polling thread"""
        if model_id in self._poll_stop_events:
            self._poll_stop_events[model_id].set()
        if model_id in self._poll_threads:
            self._poll_threads[model_id].join(timeout=2.0)
            del self._poll_threads[model_id]
        if model_id in self._poll_stop_events:
            del self._poll_stop_events[model_id]

    def _notify_callbacks_unlocked(self, model_id: str, status: DownloadStatus,
                                    progress: float, message: str) -> None:
        """
        Safely notify all callbacks outside lock

        Args:
            model_id: Model ID
            status: Download status
            progress: Progress
            message: Status message
        """
        with self._lock:
            callbacks = list(self._callbacks)

        for callback in callbacks:
            try:
                callback(model_id, status, progress, message)
            except Exception as e:
                log_error(f"Callback error: {e}")

    def _start_worker(self) -> None:
        """Start worker thread"""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return

        self._running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def _process_queue(self) -> None:
        """Worker thread for processing download queue"""
        while self._running:
            model_id = None

            with self._lock:
                if self._current is None and len(self._queue) > 0:
                    self._current = self._queue.pop(0)
                    self._statuses[self._current] = DownloadStatus.DOWNLOADING
                    self._progress[self._current] = 0.0
                    self._messages[self._current] = "Starting download..."
                    self._cancel_requested[self._current] = False
                    model_id = self._current

            if model_id is None:
                with self._lock:
                    if self._current is None:
                        self._running = False
                        break
                    model_id = self._current

            # Execute download
            self._download_model(model_id)

            # Check for next task
            with self._lock:
                self._current = None
                if len(self._queue) == 0:
                    self._running = False
                    break

    def _download_model(self, model_id: str) -> None:
        """
        Download single model (unified entry point)

        Downloads based on model's download_mode:
        - REPO: Use snapshot_download to download entire repository
        - FILE: Use hf_hub_download to download single file

        Args:
            model_id: Model ID
        """
        model_info = MODEL_REGISTRY.get(model_id)
        if not model_info:
            self._handle_failure(model_id, f"Unknown model: {model_id}")
            return

        if model_info.download_mode == DownloadMode.FILE:
            self._download_single_file(model_id, model_info)
        else:
            self._download_repo(model_id, model_info)

    def _download_repo(self, model_id: str, model_info) -> None:
        """
        Download entire HuggingFace repository using thread (with retry mechanism)

        Args:
            model_id: Model ID
            model_info: Model info
        """
        from mediafactory.config import get_config

        config = get_config()
        download_source = config.model.download_source
        endpoint = None if download_source == "https://huggingface.co" else download_source
        local_path = get_models_base_dir() / model_id

        # Update status
        self._update_status(model_id, "Downloading from HuggingFace...")

        # Check if cancelled
        if self._cancel_requested.get(model_id, False):
            self._handle_cancel(model_id)
            return

        # Start progress polling
        self._start_progress_polling(model_id)

        # 根据模型类型设置文件过滤规则
        # 注意：翻译模型现在使用 safetensors 格式（不再使用 GGUF）
        allow_patterns = None
        ignore_patterns = None

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                # Check if cancelled
                if self._cancel_requested.get(model_id, False):
                    self._stop_progress_polling(model_id)
                    self._handle_cancel(model_id)
                    return

                # Update retry status
                if attempt > 0:
                    self._update_status(model_id, f"Retrying ({attempt + 1}/{MAX_RETRIES})...")
                    log_info(f"Download retry {attempt + 1}/{MAX_RETRIES} for {model_id}")

                # Prepare download parameters
                params = {
                    "mode": "repo",
                    "repo_id": model_info.huggingface_repo,
                    "local_dir": str(local_path),
                    "endpoint": endpoint,
                    "allow_patterns": allow_patterns,
                    "ignore_patterns": ignore_patterns,
                    "timeout": config.model.download_timeout,
                }

                # Execute download in thread
                success = self._run_download_thread(model_id, params)

                # Stop progress polling
                self._stop_progress_polling(model_id)

                # If cancelled during download execution
                if self._cancel_requested.get(model_id, False):
                    self._handle_cancel(model_id)
                    return

                if success:
                    # Verify download integrity
                    if is_model_complete(model_id):
                        self._handle_success(model_id)
                    else:
                        self._handle_failure(model_id, "Download completed but verification failed")
                else:
                    # Download failed, will retry
                    raise Exception("Download failed")
                return

            except Exception as ex:
                last_error = ex
                error_msg = str(ex)[:100]
                log_error(f"Download failed for {model_id} (attempt {attempt + 1}/{MAX_RETRIES}): {error_msg}")

                # Check if cancelled
                if self._cancel_requested.get(model_id, False):
                    self._stop_progress_polling(model_id)
                    self._handle_cancel(model_id)
                    return

                # Not last retry, wait and continue
                if attempt < MAX_RETRIES - 1:
                    self._update_status(model_id, f"Connection lost, retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                else:
                    # Last retry failed, stop polling and handle failure
                    self._stop_progress_polling(model_id)
                    self._handle_failure(model_id, f"{error_msg} (after {MAX_RETRIES} retries)", clean_files=True)

    def _download_single_file(self, model_id: str, model_info) -> None:
        """
        Download single file (enhancement model, with retry mechanism)

        Args:
            model_id: Model ID
            model_info: Model info
        """
        from mediafactory.config import get_config

        config = get_config()
        download_source = config.model.download_source
        endpoint = None if download_source == "https://huggingface.co" else download_source

        # Update status
        self._update_status(model_id, "Downloading model file...")

        # Check if cancelled
        if self._cancel_requested.get(model_id, False):
            self._handle_cancel(model_id)
            return

        # Prepare directory
        models_dir = get_enhancement_models_dir()
        models_dir.mkdir(parents=True, exist_ok=True)

        local_filename = model_info.local_filename or model_info.huggingface_filename
        if not local_filename:
            self._handle_failure(model_id, "No filename specified", clean_files=True)
            return

        log_info(f"Downloading {model_id} from {model_info.huggingface_repo}/{model_info.huggingface_filename}")

        # Start progress polling
        self._start_progress_polling(model_id)

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                # Check if cancelled
                if self._cancel_requested.get(model_id, False):
                    self._stop_progress_polling(model_id)
                    self._handle_cancel(model_id)
                    return

                # Update retry status
                if attempt > 0:
                    self._update_status(model_id, f"Retrying ({attempt + 1}/{MAX_RETRIES})...")
                    log_info(f"Download retry {attempt + 1}/{MAX_RETRIES} for {model_id}")

                # Prepare download parameters
                params = {
                    "mode": "file",
                    "repo_id": model_info.huggingface_repo,
                    "filename": model_info.huggingface_filename,
                    "local_dir": str(models_dir),
                    "endpoint": endpoint,
                    "local_filename": local_filename,
                    "timeout": config.model.download_timeout,
                }

                # Execute download in thread
                success = self._run_download_thread(model_id, params)

                # Stop progress polling
                self._stop_progress_polling(model_id)

                # If cancelled during download
                if self._cancel_requested.get(model_id, False):
                    self._handle_cancel(model_id)
                    return

                if success:
                    # Verify download integrity
                    if is_model_complete(model_id):
                        self._handle_success(model_id)
                    else:
                        self._handle_failure(model_id, "Download completed but verification failed", clean_files=True)
                else:
                    # Download failed, will retry
                    raise Exception("Download failed")
                return

            except Exception as ex:
                last_error = ex
                error_msg = str(ex)[:100]
                log_error(f"Download failed for {model_id} (attempt {attempt + 1}/{MAX_RETRIES}): {error_msg}")

                # Check if cancelled
                if self._cancel_requested.get(model_id, False):
                    self._stop_progress_polling(model_id)
                    self._handle_cancel(model_id)
                    return

                # Not last retry, wait and continue
                if attempt < MAX_RETRIES - 1:
                    self._update_status(model_id, f"Connection lost, retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                else:
                    # Last retry failed, stop polling and handle failure
                    self._stop_progress_polling(model_id)
                    self._handle_failure(model_id, f"{error_msg} (after {MAX_RETRIES} retries)", clean_files=True)

    def _run_download_thread(self, model_id: str, params: Dict) -> bool:
        """
        Run download in a thread (cooperative cancellation)

        Args:
            model_id: Model ID
            params: Download parameters dict

        Returns:
            True if download succeeded
        """
        from mediafactory.gui.flet.download_worker import download_repo_worker, download_file_worker

        # Record download source info
        endpoint = params.get("endpoint")
        download_source = endpoint if endpoint else "https://huggingface.co"
        log_info(f"[Download] Starting {model_id} from {download_source}")

        # Container for download result
        result_container = {"success": False, "error": None}

        def download_task():
            """Execute download in thread"""
            try:
                if params["mode"] == "repo":
                    result_container.update(download_repo_worker(params))
                else:
                    result_container.update(download_file_worker(params))
            except Exception as e:
                result_container["success"] = False
                result_container["error"] = str(e)

        # Start download thread
        self._download_thread = threading.Thread(target=download_task, daemon=True)
        self._download_thread.start()

        # Non-blocking polling loop
        start_time = time.time()

        while self._download_thread.is_alive():
            # Check if cancelled
            if self._cancel_requested.get(model_id, False):
                log_info(f"[Download] Cancel requested for {model_id}, waiting for thread to finish...")
                # Wait for thread to finish (cooperative cancellation)
                self._download_thread.join(timeout=30.0)  # Wait up to 30 seconds
                if self._download_thread.is_alive():
                    log_info(f"[Download] Thread still running for {model_id}, will continue in background")
                return False

            # Check if timeout
            if time.time() - start_time > DOWNLOAD_TIMEOUT:
                log_error(f"Download timeout for {model_id}")
                # Thread will continue in background but we return False
                return False

            # Short interval wait to not block main loop
            self._download_thread.join(timeout=0.5)

        # Download thread finished
        if result_container.get("success"):
            log_info(f"[Download] Completed: {model_id}")
            return True
        else:
            error = result_container.get("error", "Unknown error")
            if error:
                log_error(f"Download failed: {error}")
            return False

    def _update_status(self, model_id: str, message: str, progress: float = None) -> None:
        """Update status and notify callbacks"""
        callback_data = None
        with self._lock:
            self._messages[model_id] = message
            if progress is not None:
                self._progress[model_id] = progress
            callback_data = self._get_callback_data(model_id)
        self._notify_callbacks_unlocked(*callback_data)

    def _handle_success(self, model_id: str) -> None:
        """Handle download success"""
        callback_data = None
        with self._lock:
            self._statuses[model_id] = DownloadStatus.COMPLETED
            self._progress[model_id] = 100.0
            self._messages[model_id] = "Download complete"
            log_info(f"Model {model_id} downloaded successfully")
            callback_data = self._get_callback_data(model_id)
        self._notify_callbacks_unlocked(*callback_data)

        # 下载成功后同步模型列表
        try:
            from mediafactory.config import get_config_manager
            config_manager = get_config_manager()
            config_manager.sync_models()
            log_info("Model list synchronized after download")
        except Exception as e:
            log_error(f"Failed to sync models after download: {e}")

    def _handle_cancel(self, model_id: str) -> None:
        """
        Handle download cancellation

        Args:
            model_id: Cancelled model ID
        """
        # Stop progress polling
        self._stop_progress_polling(model_id)

        # Wait for download thread to finish
        if self._download_thread is not None and self._download_thread.is_alive():
            self._download_thread.join(timeout=5.0)

        # Wait for file handles to be released
        time.sleep(0.5)

        # Clean up incomplete files
        self._cleanup_incomplete_files(model_id)

        callback_data = None
        with self._lock:
            self._statuses[model_id] = DownloadStatus.CANCELLED
            self._progress[model_id] = 0.0
            self._messages[model_id] = "Cancelled"
            log_info(f"Model {model_id} download cancelled")
            callback_data = self._get_callback_data(model_id)
        self._notify_callbacks_unlocked(*callback_data)

    def _handle_failure(self, model_id: str, error_msg: str, clean_files: bool = True) -> None:
        """
        Handle download failure

        Args:
            model_id: Failed model ID
            error_msg: Error message
            clean_files: Whether to clean incomplete files (not cleaned during retries)
        """
        # Only clean files on final failure
        if clean_files:
            # Stop progress polling
            self._stop_progress_polling(model_id)

            # Wait for download thread to finish
            if self._download_thread is not None and self._download_thread.is_alive():
                self._download_thread.join(timeout=5.0)

            # Wait for file handles to be released
            time.sleep(0.5)
            self._cleanup_incomplete_files(model_id)

        callback_data = None
        with self._lock:
            self._statuses[model_id] = DownloadStatus.FAILED
            self._progress[model_id] = 0.0
            # Prompt user to retry
            self._messages[model_id] = f"Failed: {error_msg}. Click Download to retry."
            log_error(f"Model {model_id} download failed: {error_msg}")
            callback_data = self._get_callback_data(model_id)
        self._notify_callbacks_unlocked(*callback_data)

    def _cleanup_incomplete_files(self, model_id: str) -> None:
        """
        Clean up incomplete model files

        Args:
            model_id: Model ID to clean
        """
        model_info = MODEL_REGISTRY.get(model_id)
        if not model_info:
            return

        try:
            if model_info.download_mode == DownloadMode.FILE:
                # Single file model
                filename = model_info.local_filename or model_info.huggingface_filename
                if filename:
                    model_path = get_enhancement_models_dir() / filename
                    if model_path.exists():
                        model_path.unlink()
                        log_info(f"Cleaned up incomplete file for {model_id}")
            else:
                # Repository model
                model_path = get_models_base_dir() / model_id
                if model_path.exists():
                    shutil.rmtree(model_path)
                    log_info(f"Cleaned up incomplete directory for {model_id}")
        except PermissionError as ex:
            # File still in use, retry after a short delay
            log_error(f"Permission denied cleaning {model_id}, retrying after delay: {ex}")
            time.sleep(1.0)
            try:
                if model_info.download_mode == DownloadMode.FILE:
                    filename = model_info.local_filename or model_info.huggingface_filename
                    if filename:
                        model_path = get_enhancement_models_dir() / filename
                        if model_path.exists():
                            model_path.unlink()
                            log_info(f"Cleaned up incomplete file for {model_id} (retry)")
                else:
                    model_path = get_models_base_dir() / model_id
                    if model_path.exists():
                        shutil.rmtree(model_path)
                        log_info(f"Cleaned up incomplete directory for {model_id} (retry)")
            except Exception as retry_ex:
                log_error(f"Failed to cleanup incomplete files for {model_id} after retry: {retry_ex}")
        except Exception as ex:
            log_error(f"Failed to cleanup incomplete files for {model_id}: {ex}")

    def update_progress(self, model_id: str, progress: float, message: str = "") -> None:
        """
        Update download progress (for external calls)

        Args:
            model_id: Model ID
            progress: Progress (0-100)
            message: Status message
        """
        with self._lock:
            if self._current == model_id:
                self._progress[model_id] = progress
                if message:
                    self._messages[model_id] = message
                self._notify_callbacks(model_id)

    def clear_status(self, model_id: str) -> None:
        """
        Clear model status (for retry)

        Args:
            model_id: Model ID
        """
        # Stop progress polling
        self._stop_progress_polling(model_id)

        with self._lock:
            self._statuses.pop(model_id, None)
            self._progress.pop(model_id, None)
            self._messages.pop(model_id, None)
            self._cancel_requested.pop(model_id, None)


# Global singleton access function
def get_download_manager() -> DownloadManager:
    """Get DownloadManager singleton"""
    return DownloadManager()
