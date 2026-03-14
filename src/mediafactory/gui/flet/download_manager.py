"""
下载队列管理器

提供串行下载队列，线程安全的状态管理，以及下载失败时的清理功能。
统一支持 HuggingFace 模型和增强模型的下载（全部通过 HuggingFace Hub）。
"""

import shutil
import threading
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from huggingface_hub import hf_hub_download, snapshot_download

from mediafactory.logging import log_error, log_info
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
        下载整个 HuggingFace 仓库

        Args:
            model_id: 模型 ID
            model_info: 模型信息
        """
        from mediafactory.config import get_config

        try:
            config = get_config()
            download_source = config.model.download_source
            endpoint = None if download_source == "https://huggingface.co" else download_source

            # 更新状态
            self._update_status(model_id, "Downloading from HuggingFace...")

            # 检查是否被取消
            if self._cancel_requested.get(model_id, False):
                self._handle_cancel(model_id)
                return

            # 执行下载
            local_path = get_models_base_dir() / model_id
            snapshot_download(
                repo_id=model_info.huggingface_repo,
                local_dir=str(local_path),
                endpoint=endpoint,
            )

            # 检查是否被取消
            if self._cancel_requested.get(model_id, False):
                self._handle_cancel(model_id)
                return

            # 验证下载完整性
            if is_model_complete(model_id):
                self._handle_success(model_id)
            else:
                self._handle_failure(model_id, "Download completed but verification failed")

        except Exception as ex:
            error_msg = str(ex)[:100]
            log_error(f"Download failed for {model_id}: {error_msg}")
            self._handle_failure(model_id, error_msg)

    def _download_single_file(self, model_id: str, model_info) -> None:
        """
        下载单个文件（增强模型）

        Args:
            model_id: 模型 ID
            model_info: 模型信息
        """
        from mediafactory.config import get_config

        try:
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
                self._handle_failure(model_id, "No filename specified")
                return

            log_info(f"Downloading {model_id} from {model_info.huggingface_repo}/{model_info.huggingface_filename}")

            # 使用 hf_hub_download 下载单个文件
            downloaded_path = hf_hub_download(
                repo_id=model_info.huggingface_repo,
                filename=model_info.huggingface_filename,
                local_dir=str(models_dir),
                endpoint=endpoint,
            )

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
                self._handle_failure(model_id, "Download completed but verification failed")

        except Exception as ex:
            error_msg = str(ex)[:100]
            log_error(f"Download failed for {model_id}: {error_msg}")
            self._handle_failure(model_id, error_msg)

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

    def _handle_failure(self, model_id: str, error_msg: str) -> None:
        """
        处理下载失败

        Args:
            model_id: 失败的模型 ID
            error_msg: 错误消息
        """
        # 清理不完整的文件
        self._cleanup_incomplete_files(model_id)

        callback_data = None
        with self._lock:
            self._statuses[model_id] = DownloadStatus.FAILED
            self._progress[model_id] = 0.0
            self._messages[model_id] = f"Failed: {error_msg}"
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
        with self._lock:
            self._statuses.pop(model_id, None)
            self._progress.pop(model_id, None)
            self._messages.pop(model_id, None)
            self._cancel_requested.pop(model_id, None)


# 全局单例访问函数
def get_download_manager() -> DownloadManager:
    """获取 DownloadManager 单例"""
    return DownloadManager()
