"""
下载队列管理器

提供串行下载队列，线程安全的状态管理，以及下载失败时的清理功能。
统一支持 HuggingFace 模型和增强模型的下载（全部通过 HuggingFace Hub）。
"""

import shutil
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from huggingface_hub import hf_hub_download, snapshot_download

from mediafactory.logging import log_error, log_info

# 重试配置
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试间隔（秒）
from mediafactory.models.model_registry import (
    MODEL_REGISTRY,
    DownloadMode,
    get_enhancement_models_dir,
    get_models_base_dir,
    is_model_complete,
)


class DownloadStatus(Enum):
    """下载状态枚举"""

    IDLE = "idle"  # 空闲，未下载
    WAITING = "waiting"  # 排队中
    DOWNLOADING = "downloading"  # 下载中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    DELETING = "deleting"  # 删除中


class DownloadManager:
    """
    串行下载队列管理器（单例）

    负责管理模型下载队列，提供线程安全的状态访问。
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 避免重复初始化
        if DownloadManager._initialized:
            return
        DownloadManager._initialized = True

        self._lock = threading.Lock()
        self._queue: List[str] = []  # 排队中的 model_id 列表
        self._current: Optional[str] = None  # 当前正在下载的 model_id
        self._statuses: Dict[str, DownloadStatus] = {}  # {model_id: status}
        self._progress: Dict[str, float] = {}  # {model_id: progress_percent}
        self._messages: Dict[str, str] = {}  # {model_id: status message}
        self._callbacks: List[Callable[[str, DownloadStatus, float, str], None]] = []
        self._cancel_requested: Dict[str, bool] = {}  # {model_id: cancel_flag}
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

        # 轮询线程管理
        self._poll_threads: Dict[str, threading.Thread] = {}
        self._poll_stop_events: Dict[str, threading.Event] = {}

    def enqueue(self, model_id: str) -> bool:
        """
        将模型加入下载队列

        Args:
            model_id: 模型 ID

        Returns:
            True 如果成功加入队列
        """
        callback_data = None
        
        with self._lock:
            # 检查是否已在队列中或正在下载
            if model_id in self._queue:
                log_info(f"Model {model_id} already in queue")
                return False
            if self._current == model_id:
                log_info(f"Model {model_id} already downloading")
                return False

            # 设置状态
            if self._current is None:
                # 队列为空，直接开始下载
                self._current = model_id
                self._statuses[model_id] = DownloadStatus.DOWNLOADING
                self._progress[model_id] = 0.0
                self._messages[model_id] = "Starting download..."
                self._cancel_requested[model_id] = False
                # 启动工作线程
                self._start_worker()
            else:
                # 加入队列
                self._queue.append(model_id)
                self._statuses[model_id] = DownloadStatus.WAITING
                self._progress[model_id] = 0.0
                self._messages[model_id] = "Waiting in queue..."

            log_info(f"Model {model_id} enqueued, status: {self._statuses[model_id]}")
            # 准备回调数据（在锁内）
            callback_data = self._get_callback_data(model_id)
        
        # 在锁外调用回调
        if callback_data:
            self._notify_callbacks_unlocked(*callback_data)
        return True

    def cancel(self, model_id: str) -> bool:
        """
        取消下载（排队中或下载中）

        Args:
            model_id: 模型 ID

        Returns:
            True 如果成功取消
        """
        callback_data = None
        success = False

        with self._lock:
            # 检查是否在队列中
            if model_id in self._queue:
                self._queue.remove(model_id)
                # 清除状态，恢复到 IDLE（排队中没有文件被下载）
                self._statuses.pop(model_id, None)
                self._progress.pop(model_id, None)
                self._messages.pop(model_id, None)
                log_info(f"Model {model_id} cancelled from queue, status cleared")
                callback_data = (model_id, DownloadStatus.IDLE, 0.0, "")
                success = True
            # 检查是否正在下载
            elif self._current == model_id:
                self._cancel_requested[model_id] = True
                self._messages[model_id] = "Cancelling..."
                log_info(f"Model {model_id} cancel requested")
                callback_data = self._get_callback_data(model_id)
                success = True

        # 停止进度轮询
        if success:
            self._stop_progress_polling(model_id)

        # 在锁外通知 UI
        if callback_data:
            self._notify_callbacks_unlocked(*callback_data)
        return success

    def get_status(self, model_id: str) -> DownloadStatus:
        """
        获取模型下载状态

        Args:
            model_id: HuggingFace 模型 ID

        Returns:
            当前下载状态
        """
        with self._lock:
            return self._statuses.get(model_id, DownloadStatus.IDLE)

    def get_progress(self, model_id: str) -> float:
        """
        获取模型下载进度

        Args:
            model_id: HuggingFace 模型 ID

        Returns:
            下载进度 (0-100)
        """
        with self._lock:
            return self._progress.get(model_id, 0.0)

    def get_message(self, model_id: str) -> str:
        """
        获取模型下载状态消息

        Args:
            model_id: HuggingFace 模型 ID

        Returns:
            状态消息
        """
        with self._lock:
            return self._messages.get(model_id, "")

    def is_in_queue(self, model_id: str) -> bool:
        """
        检查模型是否在队列中或正在下载

        Args:
            model_id: HuggingFace 模型 ID

        Returns:
            True 如果在队列中或正在下载
        """
        with self._lock:
            return model_id in self._queue or self._current == model_id

    def register_callback(
        self, callback: Callable[[str, DownloadStatus, float, str], None]
    ) -> None:
        """
        注册状态变化回调函数

        Args:
            callback: 回调函数，接收 (model_id, status, progress, message)
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def unregister_callback(
        self, callback: Callable[[str, DownloadStatus, float, str], None]
    ) -> None:
        """
        注销状态变化回调函数

        Args:
            callback: 要注销的回调函数
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _notify_callbacks(self, model_id: str) -> None:
        """
        通知所有回调函数状态变化（在锁内调用，会释放锁后调用回调）

        Args:
            model_id: 状态变化的模型 ID
        """
        # 获取回调数据（在锁内）
        callback_data = self._get_callback_data(model_id)
        callbacks = list(self._callbacks)
        
        # 在锁外调用回调
        for callback in callbacks:
            try:
                callback(*callback_data)
            except Exception as e:
                log_error(f"Callback error: {e}")

    def _get_callback_data(self, model_id: str) -> Tuple[str, DownloadStatus, float, str]:
        """
        获取回调所需数据（在锁内调用）

        Args:
            model_id: 模型 ID

        Returns:
            (model_id, status, progress, message)
        """
        status = self._statuses.get(model_id, DownloadStatus.IDLE)
        progress = self._progress.get(model_id, 0.0)
        message = self._messages.get(model_id, "")
        return (model_id, status, progress, message)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _start_progress_polling(self, model_id: str) -> None:
        """启动进度轮询线程"""
        stop_event = threading.Event()
        self._poll_stop_events[model_id] = stop_event

        def poll_progress():
            """轮询下载进度"""
            from mediafactory.models.model_download import get_downloaded_size, get_models_dir

            # 获取模型总大小（从注册表）
            model_info = MODEL_REGISTRY.get(model_id)
            if not model_info:
                return

            total_size = model_info.model_size_mb * 1024 * 1024  # 转换为字节

            while not stop_event.is_set():
                try:
                    # 根据下载模式确定路径
                    if model_info.download_mode == DownloadMode.FILE:
                        # 单文件模式
                        filename = model_info.local_filename or model_info.huggingface_filename
                        if filename:
                            model_path = get_enhancement_models_dir() / filename
                        else:
                            model_path = get_enhancement_models_dir()
                    else:
                        # 仓库模式
                        model_path = get_models_dir() / model_id

                    downloaded = get_downloaded_size(model_path) if model_path.is_dir() else (
                        model_path.stat().st_size if model_path.exists() else 0
                    )

                    if total_size > 0:
                        progress = min(100, int(downloaded / total_size * 100))
                        message = f"{progress}% ({self._format_size(downloaded)} / {self._format_size(total_size)})"

                        # 更新状态
                        callback_data = None
                        with self._lock:
                            if model_id in self._statuses:
                                self._progress[model_id] = float(progress)
                                self._messages[model_id] = message
                                callback_data = self._get_callback_data(model_id)

                        # 在锁外通知观察者
                        if callback_data:
                            self._notify_callbacks_unlocked(*callback_data)

                except Exception as e:
                    log_info(f"Poll progress error: {e}")

                # 等待 1 秒
                stop_event.wait(1.0)

        thread = threading.Thread(target=poll_progress, daemon=True)
        self._poll_threads[model_id] = thread
        thread.start()

    def _stop_progress_polling(self, model_id: str) -> None:
        """停止进度轮询线程"""
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
        在锁外安全地通知所有回调

        Args:
            model_id: 模型 ID
            status: 下载状态
            progress: 进度
            message: 状态消息
        """
        with self._lock:
            callbacks = list(self._callbacks)
        
        for callback in callbacks:
            try:
                callback(model_id, status, progress, message)
            except Exception as e:
                log_error(f"Callback error: {e}")

    def _start_worker(self) -> None:
        """启动工作线程"""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return

        self._running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def _process_queue(self) -> None:
        """处理下载队列的工作线程"""
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

            # 执行下载
            self._download_model(model_id)

            # 检查是否还有下一个任务
            with self._lock:
                self._current = None
                if len(self._queue) == 0:
                    self._running = False
                    break

    def _download_model(self, model_id: str) -> None:
        """
        下载单个模型（统一入口）

        根据模型的 download_mode 决定下载方式：
        - REPO: 使用 snapshot_download 下载整个仓库
        - FILE: 使用 hf_hub_download 下载单个文件

        Args:
            model_id: 模型 ID
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
        下载整个 HuggingFace 仓库（带重试机制）

        Args:
            model_id: 模型 ID
            model_info: 模型信息
        """
        from mediafactory.config import get_config

        config = get_config()
        download_source = config.model.download_source
        endpoint = None if download_source == "https://huggingface.co" else download_source
        local_path = get_models_base_dir() / model_id

        # 更新状态
        self._update_status(model_id, "Downloading from HuggingFace...")

        # 检查是否被取消
        if self._cancel_requested.get(model_id, False):
            self._handle_cancel(model_id)
            return

        # 启动进度轮询
        self._start_progress_polling(model_id)

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                # 检查是否被取消
                if self._cancel_requested.get(model_id, False):
                    self._stop_progress_polling(model_id)
                    self._handle_cancel(model_id)
                    return

                # 更新重试状态
                if attempt > 0:
                    self._update_status(model_id, f"Retrying ({attempt + 1}/{MAX_RETRIES})...")
                    log_info(f"Download retry {attempt + 1}/{MAX_RETRIES} for {model_id}")

                # 执行下载（huggingface_hub 默认支持断点续传）
                snapshot_download(
                    repo_id=model_info.huggingface_repo,
                    local_dir=str(local_path),
                    endpoint=endpoint,
                )

                # 停止进度轮询
                self._stop_progress_polling(model_id)

                # 检查是否被取消
                if self._cancel_requested.get(model_id, False):
                    self._handle_cancel(model_id)
                    return

                # 验证下载完整性
                if is_model_complete(model_id):
                    self._handle_success(model_id)
                else:
                    self._handle_failure(model_id, "Download completed but verification failed")
                return

            except Exception as ex:
                last_error = ex
                error_msg = str(ex)[:100]
                log_error(f"Download failed for {model_id} (attempt {attempt + 1}/{MAX_RETRIES}): {error_msg}")

                # 检查是否被取消
                if self._cancel_requested.get(model_id, False):
                    self._stop_progress_polling(model_id)
                    self._handle_cancel(model_id)
                    return

                # 非最后一次重试，等待后继续
                if attempt < MAX_RETRIES - 1:
                    self._update_status(model_id, f"Connection lost, retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                else:
                    # 最后一次重试失败，停止进度轮询并处理失败
                    self._stop_progress_polling(model_id)
                    self._handle_failure(model_id, f"{error_msg} (after {MAX_RETRIES} retries)", clean_files=True)

    def _download_single_file(self, model_id: str, model_info) -> None:
        """
        下载单个文件（增强模型，带重试机制）

        Args:
            model_id: 模型 ID
            model_info: 模型信息
        """
        from mediafactory.config import get_config

        config = get_config()
        download_source = config.model.download_source
        endpoint = None if download_source == "https://huggingface.co" else download_source

        # 更新状态
        self._update_status(model_id, "Downloading model file...")

        # 检查是否被取消
        if self._cancel_requested.get(model_id, False):
            self._handle_cancel(model_id)
            return

        # 准备目录
        models_dir = get_enhancement_models_dir()
        models_dir.mkdir(parents=True, exist_ok=True)

        local_filename = model_info.local_filename or model_info.huggingface_filename
        if not local_filename:
            self._handle_failure(model_id, "No filename specified", clean_files=True)
            return

        log_info(f"Downloading {model_id} from {model_info.huggingface_repo}/{model_info.huggingface_filename}")

        # 启动进度轮询
        self._start_progress_polling(model_id)

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                # 检查是否被取消
                if self._cancel_requested.get(model_id, False):
                    self._stop_progress_polling(model_id)
                    self._handle_cancel(model_id)
                    return

                # 更新重试状态
                if attempt > 0:
                    self._update_status(model_id, f"Retrying ({attempt + 1}/{MAX_RETRIES})...")
                    log_info(f"Download retry {attempt + 1}/{MAX_RETRIES} for {model_id}")

                # 使用 hf_hub_download 下载单个文件（默认支持断点续传）
                downloaded_path = hf_hub_download(
                    repo_id=model_info.huggingface_repo,
                    filename=model_info.huggingface_filename,
                    local_dir=str(models_dir),
                    endpoint=endpoint,
                )

                # 停止进度轮询
                self._stop_progress_polling(model_id)

                # 检查是否被取消
                if self._cancel_requested.get(model_id, False):
                    self._handle_cancel(model_id)
                    return

                # 如果 local_filename 与 huggingface_filename 不同，需要重命名
                downloaded_file = Path(downloaded_path)
                target_file = models_dir / local_filename

                if downloaded_file.exists() and downloaded_file != target_file:
                    # 如果下载的文件在子目录中，移动到 enhancement 目录
                    if target_file.exists():
                        target_file.unlink()
                    shutil.move(str(downloaded_file), str(target_file))
                    log_info(f"Moved {downloaded_file} to {target_file}")

                # 验证下载完整性
                if is_model_complete(model_id):
                    self._handle_success(model_id)
                else:
                    self._handle_failure(model_id, "Download completed but verification failed", clean_files=True)
                return

            except Exception as ex:
                last_error = ex
                error_msg = str(ex)[:100]
                log_error(f"Download failed for {model_id} (attempt {attempt + 1}/{MAX_RETRIES}): {error_msg}")

                # 检查是否被取消
                if self._cancel_requested.get(model_id, False):
                    self._stop_progress_polling(model_id)
                    self._handle_cancel(model_id)
                    return

                # 非最后一次重试，等待后继续
                if attempt < MAX_RETRIES - 1:
                    self._update_status(model_id, f"Connection lost, retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                else:
                    # 最后一次重试失败，停止进度轮询并处理失败
                    self._stop_progress_polling(model_id)
                    self._handle_failure(model_id, f"{error_msg} (after {MAX_RETRIES} retries)", clean_files=True)

    def _update_status(self, model_id: str, message: str, progress: float = None) -> None:
        """更新状态并通知回调"""
        callback_data = None
        with self._lock:
            self._messages[model_id] = message
            if progress is not None:
                self._progress[model_id] = progress
            callback_data = self._get_callback_data(model_id)
        self._notify_callbacks_unlocked(*callback_data)

    def _handle_success(self, model_id: str) -> None:
        """处理下载成功"""
        callback_data = None
        with self._lock:
            self._statuses[model_id] = DownloadStatus.COMPLETED
            self._progress[model_id] = 100.0
            self._messages[model_id] = "Download complete"
            log_info(f"Model {model_id} downloaded successfully")
            callback_data = self._get_callback_data(model_id)
        self._notify_callbacks_unlocked(*callback_data)

    def _handle_cancel(self, model_id: str) -> None:
        """
        处理取消下载

        Args:
            model_id: 被取消的模型 ID
        """
        # 清理不完整的文件
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
        处理下载失败

        Args:
            model_id: 失败的模型 ID
            error_msg: 错误消息
            clean_files: 是否清理不完整的文件（重试期间不清理）
        """
        # 只在最终失败时清理文件
        if clean_files:
            self._cleanup_incomplete_files(model_id)

        callback_data = None
        with self._lock:
            self._statuses[model_id] = DownloadStatus.FAILED
            self._progress[model_id] = 0.0
            # 提示用户可以重试
            self._messages[model_id] = f"Failed: {error_msg}. Click Download to retry."
            log_error(f"Model {model_id} download failed: {error_msg}")
            callback_data = self._get_callback_data(model_id)
        self._notify_callbacks_unlocked(*callback_data)

    def _cleanup_incomplete_files(self, model_id: str) -> None:
        """
        清理不完整的模型文件

        Args:
            model_id: 要清理的模型 ID
        """
        model_info = MODEL_REGISTRY.get(model_id)
        if not model_info:
            return
        
        try:
            if model_info.download_mode == DownloadMode.FILE:
                # 单文件模型
                filename = model_info.local_filename or model_info.huggingface_filename
                if filename:
                    model_path = get_enhancement_models_dir() / filename
                    if model_path.exists():
                        model_path.unlink()
                        log_info(f"Cleaned up incomplete file for {model_id}")
            else:
                # 仓库模型
                model_path = get_models_base_dir() / model_id
                if model_path.exists():
                    shutil.rmtree(model_path)
                    log_info(f"Cleaned up incomplete directory for {model_id}")
        except Exception as ex:
            log_error(f"Failed to cleanup incomplete files for {model_id}: {ex}")

    def update_progress(self, model_id: str, progress: float, message: str = "") -> None:
        """
        更新下载进度（供外部调用）

        Args:
            model_id: 模型 ID
            progress: 进度 (0-100)
            message: 状态消息
        """
        with self._lock:
            if self._current == model_id:
                self._progress[model_id] = progress
                if message:
                    self._messages[model_id] = message
                self._notify_callbacks(model_id)

    def clear_status(self, model_id: str) -> None:
        """
        清除模型状态（用于重试）

        Args:
            model_id: 模型 ID
        """
        # 停止进度轮询
        self._stop_progress_polling(model_id)

        with self._lock:
            self._statuses.pop(model_id, None)
            self._progress.pop(model_id, None)
            self._messages.pop(model_id, None)
            self._cancel_requested.pop(model_id, None)


# 全局单例访问函数
def get_download_manager() -> DownloadManager:
    """获取 DownloadManager 单例"""
    return DownloadManager()
