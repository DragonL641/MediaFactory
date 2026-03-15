"""MediaFactory Batch Processing Module.

Provides batch processing functionality for video files with:
- Model sharing (avoid reloading models between files)
- Error isolation (single file failure doesn't affect others)
- Progress tracking and result reporting
- Pipeline-based architecture
"""

import logging
import os
import time
import threading
import traceback
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)

from .config import get_config_manager
from .engine import AudioEngine, RecognitionEngine, TranslationEngine, SRTEngine
from .models.whisper_runtime import select_device
from .models.model_registry import WHISPER_MODEL_ID
from .pipeline import Pipeline, ProcessingContext
from .pipeline.stages import (
    AudioExtractionStage,
    TranscriptionStage,
    TranslationStage,
    SRTGenerationStage,
)
from .utils.video_scanner import (
    resolve_input_path,
    get_file_size_info,
)
from .logging import (
    log_processing_start,
    log_processing_end,
    log_info,
    log_warning,
    log_error,
    log_step,
    log_success,
)
from .exceptions import MediaFactoryError, OperationCancelledError
from .core.exception_wrapper import convert_exception
from .core.tool import CancellationToken


class ProcessingStatus(Enum):
    """Processing status enumeration."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FileProcessingResult:
    """Result of processing a single file."""

    video_path: str
    status: ProcessingStatus
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None  # NEW: Exception type name
    error_context: Optional[dict] = None  # NEW: Error context from exception
    error_severity: Optional[str] = None  # NEW: Error severity level
    is_fatal: bool = True  # NEW: Whether error should stop batch processing
    processing_time: float = 0.0


@dataclass
class BatchProcessingReport:
    """Batch processing result summary report."""

    total_files: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_time: float = 0.0
    results: List[FileProcessingResult] = field(default_factory=list)

    def add_result(self, result: FileProcessingResult) -> None:
        """Add a single file processing result."""
        self.results.append(result)
        if result.status == ProcessingStatus.SUCCESS:
            self.success_count += 1
        elif result.status == ProcessingStatus.FAILED:
            self.failed_count += 1
        elif result.status == ProcessingStatus.SKIPPED:
            self.skipped_count += 1

    def get_summary(self) -> str:
        """Generate summary report string."""
        lines = [
            "",
            "=" * 60,
            "Batch Processing Complete - Summary",
            "=" * 60,
            f"Total files: {self.total_files}",
            f"Success: {self.success_count}",
            f"Failed: {self.failed_count}",
            f"Skipped: {self.skipped_count}",
            f"Total time: {self.total_time:.1f} seconds",
            "",
        ]

        # List successful files
        success_results = [
            r for r in self.results if r.status == ProcessingStatus.SUCCESS
        ]
        if success_results:
            lines.append("Successful files:")
            for result in success_results:
                lines.append(f"   {Path(result.video_path).name}")
                lines.append(f"      → {result.output_path}")
            lines.append("")

        # List failed files with details
        failed_results = [
            r for r in self.results if r.status == ProcessingStatus.FAILED
        ]
        if failed_results:
            lines.append("Failed files:")
            for result in failed_results:
                lines.append(f"   {result.video_path}")
                lines.append(f"      Error: {result.error_message}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


class SharedModelContext:
    """Shared model context manager for batch processing.

    Loads models once at the start of batch processing and shares them
    across all video files to avoid reloading.
    """

    def __init__(
        self,
        use_local_models_only: bool = False,
        translation_model: Optional[str] = None,  # 使用自动选择
        config=None,
        api_backend: Optional[str] = None,
    ):
        self.use_local_models_only = use_local_models_only
        self.translation_model = translation_model
        self.config = config if config is not None else get_config_manager().config
        self.api_backend = api_backend

        # Device selection
        self.device: Optional[str] = None
        self._model_context: Optional[Any] = None
        self._whisper_model: Optional[Any] = None  # Store loaded model instance

        # LLM backend
        self.llm_backend: Optional[Any] = None

        # Engines (shared across files)
        self.audio_engine: Optional[AudioEngine] = None
        self.recognition_engine: Optional[RecognitionEngine] = None
        self.translation_engine: Optional[TranslationEngine] = None
        self.srt_engine: Optional[SRTEngine] = None

        # Thread lock for model access
        self._lock = threading.Lock()

    def load_models(
        self,
        gui_observers: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Load all required models.

        Ensures proper cleanup on failure using try-except.
        """
        log_step("Initializing batch processing models")

        try:
            # 1. Select device (model is fixed to Large V3)
            self.device = select_device()
            log_step(f"Whisper model: {WHISPER_MODEL_ID}")
            log_step(f"Device: {self.device}")

            # Update GUI progress
            if gui_observers and "recognition_progress_func" in gui_observers:
                gui_observers["recognition_progress_func"](
                    0.0, f"Loading {WHISPER_MODEL_ID} model..."
                )

            # 2. Load Whisper model using context manager
            from .resource_manager import whisper_model

            self._model_context = whisper_model(WHISPER_MODEL_ID, self.device)
            self._whisper_model = self._model_context.__enter__()

            log_success(f"Faster Whisper model {WHISPER_MODEL_ID} loaded")

            if gui_observers and "recognition_progress_func" in gui_observers:
                gui_observers["recognition_progress_func"](
                    10.0, f"Model {WHISPER_MODEL_ID} loaded"
                )

            # 3. Initialize LLM backend if configured
            self._init_llm_backend()

            # 4. Initialize engines
            self.audio_engine = AudioEngine()
            self.recognition_engine = RecognitionEngine()
            self.translation_engine = self._create_translation_engine()
            self.srt_engine = SRTEngine()

            log_success("Batch processing engines initialized")

        except Exception as e:
            # Ensure model context is cleaned up on failure
            if self._model_context is not None:
                try:
                    self._model_context.__exit__(None, None, None)
                except Exception:
                    pass  # Ignore cleanup errors
                finally:
                    self._model_context = None
                    self._whisper_model = None
            raise  # Re-raise the original exception

    def _init_llm_backend(self) -> None:
        """Initialize LLM backend for remote translation."""
        # Use api_backend from GUI selection, or default to openai_compatible
        backend_to_use = self.api_backend or "openai_compatible"

        try:
            from .llm import initialize_llm_backend

            self.llm_backend = initialize_llm_backend(self.config, backend_to_use)

            if self.llm_backend and self.llm_backend.is_available:
                log_success(f"LLM translation backend {backend_to_use} enabled")
            else:
                log_warning(
                    f"LLM backend {backend_to_use} incomplete, using local models"
                )
                self.llm_backend = None
        except Exception as e:
            log_warning(f"Failed to initialize LLM backend: {e}")
            self.llm_backend = None

    def _create_translation_engine(self) -> TranslationEngine:
        """Create translation engine instance."""
        use_llm_backend = self.llm_backend is not None and self.api_backend is not None

        return TranslationEngine(
            use_local_models_only=self.use_local_models_only,
            model_type=self.translation_model,
            device=self.device or "cpu",
            llm_backend=self.llm_backend,
            use_llm_backend=use_llm_backend,
        )

    def create_pipeline(self) -> Pipeline:
        """Create a pipeline for processing a single file."""
        return Pipeline(
            [
                AudioExtractionStage(self.audio_engine),
                TranscriptionStage(self.recognition_engine),
                TranslationStage(self.translation_engine),
                SRTGenerationStage(self.srt_engine),
            ]
        )

    def get_whisper_model(self) -> Any:
        """Get the loaded Whisper model instance (thread-safe)."""
        with self._lock:
            if not self._whisper_model:
                raise RuntimeError("Model not loaded. Call load_models() first.")
            return self._whisper_model

    def release(self) -> None:
        """Release model resources."""
        log_step("Releasing model resources")

        # Release Whisper model context
        if self._model_context is not None:
            try:
                self._model_context.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error releasing model context: {e}")
            self._model_context = None

        with self._lock:
            self._whisper_model = None  # Clear model reference

        # Clear engine references
        self.audio_engine = None
        self.recognition_engine = None
        self.translation_engine = None
        self.srt_engine = None

        # Force garbage collection
        import gc

        gc.collect()

        # Clear CUDA cache if available
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as e:
            logger.debug(f"Error clearing CUDA cache: {e}")

        log_success("Model resources released")


class BatchProcessor:
    """Batch video processor using pipeline architecture."""

    def __init__(
        self,
        src_lang: Optional[str] = None,
        tgt_lang: str = "zh",
        use_local_models_only: bool = False,
        translation_model: Optional[str] = None,  # 使用自动选择
        config=None,
        api_backend: Optional[str] = None,
    ):
        self.config = config if config is not None else get_config_manager().config
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.use_local_models_only = use_local_models_only
        self.translation_model = translation_model
        self.api_backend = api_backend

        # Cancellation token (unified pattern)
        self._cancelled = CancellationToken()

        # Shared model context
        self._model_context: Optional[SharedModelContext] = None

    def cancel(self) -> None:
        """Cancel batch processing."""
        self._cancelled.cancel("Batch processing cancelled by user")

    def is_cancelled(self) -> bool:
        """Check if cancelled."""
        return self._cancelled.is_cancelled()

    def preview_files(
        self,
        input_path: str,
        wait_seconds: Optional[int] = None,
        on_countdown: Optional[Callable[[int], None]] = None,
    ) -> List[str]:
        """Preview files to process and wait for confirmation.

        Args:
            input_path: Input path (file or directory)
            wait_seconds: Wait seconds, None uses default min(file_count, 10)
            on_countdown: Countdown callback with remaining seconds

        Returns:
            List of video file paths
        """
        # Parse input path
        path_type, video_files = resolve_input_path(input_path)

        # Show file list (logged only, no console output for file list)
        log_step("File Preview")
        file_count, total_size_gb = get_file_size_info(video_files)

        log_info(f"Path type: {'Single file' if path_type == 'file' else 'Directory'}")
        log_info(f"File count: {file_count}")
        log_info(f"Total size: {total_size_gb:.2f} GB")

        # No wait for single file
        if path_type == "file":
            return video_files

        # Calculate wait time
        if wait_seconds is None:
            wait_seconds = min(file_count, 10)

        # Countdown
        log_info(f"Starting processing in {wait_seconds} seconds...")
        log_info("Press Ctrl+C to cancel")

        try:
            for remaining in range(wait_seconds, 0, -1):
                if self.is_cancelled():
                    raise KeyboardInterrupt("Operation cancelled by user")

                # Use callback for GUI display (no console progress bar)
                if on_countdown:
                    on_countdown(remaining)
                time.sleep(1)
        except KeyboardInterrupt:
            log_warning("Operation cancelled by user")
            raise

        return video_files

    def process_batch(
        self,
        video_files: List[str],
        gui_observers: Optional[Dict[str, Any]] = None,
        on_file_start: Optional[Callable[[int, int, str], None]] = None,
        on_file_complete: Optional[
            Callable[[int, int, FileProcessingResult], None]
        ] = None,
    ) -> BatchProcessingReport:
        """Batch process video files.

        Args:
            video_files: List of video file paths
            gui_observers: GUI observer dictionary
            on_file_start: File start callback (current_index, total, file_path)
            on_file_complete: File complete callback (current_index, total, result)

        Returns:
            Batch processing report
        """
        report = BatchProcessingReport(total_files=len(video_files))
        start_time = time.time()

        # Create shared model context
        self._model_context = SharedModelContext(
            use_local_models_only=self.use_local_models_only,
            translation_model=self.translation_model,
            config=self.config,
            api_backend=self.api_backend,
        )

        # Create progress bridge for batch processing
        from .core.progress_bridge import create_gui_progress_bridge

        progress_bridge = create_gui_progress_bridge(
            gui_observers=gui_observers,
            current_file_index=1,
            total_files=len(video_files),
        )

        try:
            # Load models
            self._model_context.load_models(gui_observers)

            # Get shared Whisper model
            whisper_model = self._model_context.get_whisper_model()

            # Create pipeline (without model loading stage for batch)
            pipeline = self._model_context.create_pipeline()

            # Process each file
            for i, video_path in enumerate(video_files, 1):
                if self.is_cancelled():
                    # Mark remaining files as skipped
                    for remaining_path in video_files[i - 1 :]:
                        result = FileProcessingResult(
                            video_path=remaining_path,
                            status=ProcessingStatus.SKIPPED,
                            error_message="Operation cancelled by user",
                        )
                        report.add_result(result)
                    break

                # Notify file start
                if on_file_start:
                    on_file_start(i, len(video_files), video_path)

                # Process single file
                result = self._process_single_file(
                    video_path,
                    i,
                    len(video_files),
                    gui_observers,
                    pipeline,
                    whisper_model,
                    progress_bridge,
                )
                report.add_result(result)

                # Notify file complete
                if on_file_complete:
                    on_file_complete(i, len(video_files), result)

        finally:
            # Release model resources
            if self._model_context:
                self._model_context.release()
                self._model_context = None

        report.total_time = time.time() - start_time
        return report

    def _process_single_file(
        self,
        video_path: str,
        current_index: int,
        total_files: int,
        gui_observers: Optional[Dict[str, Any]] = None,
        pipeline: Optional[Pipeline] = None,
        whisper_model: Any = None,
        progress_bridge=None,
    ) -> FileProcessingResult:
        """Process a single video file with error isolation."""
        file_start_time = time.time()

        # Log processing start
        log_processing_start(
            process_type=f"Video Processing [{current_index}/{total_files}]",
            video_path=video_path,
            context={
                "src_lang": self.src_lang,
                "tgt_lang": self.tgt_lang,
                "whisper_model": (
                    self._model_context.model_size if self._model_context else "unknown"
                ),
                "device": (
                    self._model_context.device if self._model_context else "unknown"
                ),
                "translation_model": self.translation_model,
            },
        )

        # Check file exists
        if not os.path.exists(video_path):
            log_processing_end(
                process_type="Video Processing",
                success=False,
                duration_sec=0,
                error=f"File not found: {video_path}",
            )
            return FileProcessingResult(
                video_path=video_path,
                status=ProcessingStatus.FAILED,
                error_message=f"File not found: {video_path}",
                error_type="ProcessingError",
                error_context={"video_path": video_path},
                error_severity="fatal",
                is_fatal=True,
            )

        # Ensure model context is initialized
        if self._model_context is None:
            raise RuntimeError("Model context not initialized")

        try:
            # Check cancellation
            def check_cancelled():
                if self.is_cancelled():
                    raise KeyboardInterrupt("Operation cancelled by user")
                if gui_observers and "cancelled" in gui_observers:
                    if gui_observers["cancelled"]():
                        raise KeyboardInterrupt("Operation cancelled by user")

            check_cancelled()

            # Create progress bridge for this file
            from .core.progress_bridge import create_gui_progress_bridge

            if progress_bridge is None:
                progress_bridge = create_gui_progress_bridge(
                    gui_observers=gui_observers,
                    current_file_index=current_index,
                    total_files=total_files,
                )
            else:
                # Update file index for existing bridge
                progress_bridge.set_file_index(current_index)

            # Create processing context
            context = ProcessingContext(
                video_path=video_path,
                src_lang=self.src_lang,
                tgt_lang=self.tgt_lang,
                whisper_model=self._model_context.model_size,
                whisper_device=self._model_context.device,
                translation_model=self.translation_model,
                use_local_models_only=self.use_local_models_only,
                llm_backend=self._model_context.llm_backend,
                gui_observers=gui_observers,
                progress_callback=progress_bridge,
            )

            # Pre-set the loaded model (skip model loading stage)
            context.whisper_model_instance = whisper_model

            # Execute pipeline
            result = pipeline.execute(context)

            if not result.success:
                raise Exception(result.error_message or "Processing failed")

            # Handle audio cleanup - delete on success
            if result.success:
                if context.audio_path and os.path.exists(context.audio_path):
                    try:
                        os.remove(context.audio_path)
                    except Exception:
                        pass

            processing_time = time.time() - file_start_time

            # Log processing end (success)
            log_processing_end(
                process_type="Video Processing",
                success=True,
                duration_sec=processing_time,
                output_path=result.output_path,
            )

            return FileProcessingResult(
                video_path=video_path,
                status=ProcessingStatus.SUCCESS,
                output_path=result.output_path,
                processing_time=processing_time,
            )

        except KeyboardInterrupt:
            self._cancelled.cancel("User cancelled during file processing")
            processing_time = time.time() - file_start_time
            log_processing_end(
                process_type="Video Processing",
                success=False,
                duration_sec=processing_time,
                error="Operation cancelled by user",
            )
            return FileProcessingResult(
                video_path=video_path,
                status=ProcessingStatus.SKIPPED,
                error_message="Operation cancelled by user",
                error_type="OperationCancelledError",
                error_severity="warning",
                is_fatal=False,
                processing_time=processing_time,
            )
        except MediaFactoryError as e:
            # Handle structured exceptions
            processing_time = time.time() - file_start_time
            log_processing_end(
                process_type="Video Processing",
                success=False,
                duration_sec=processing_time,
                error=f"{type(e).__name__}: {e.message}",
            )

            # Determine if error is fatal (should stop batch)
            is_fatal = e.severity in ("fatal",)

            return FileProcessingResult(
                video_path=video_path,
                status=ProcessingStatus.FAILED,
                error_message=e.message,
                error_type=type(e).__name__,
                error_context=e.context,
                error_severity=e.severity,
                is_fatal=is_fatal,
                processing_time=processing_time,
            )
        except Exception as e:
            # Wrap generic exceptions
            wrapped = convert_exception(
                e,
                context={"video_path": video_path},
            )

            processing_time = time.time() - file_start_time
            log_processing_end(
                process_type="Video Processing",
                success=False,
                duration_sec=processing_time,
                error=f"{type(wrapped).__name__}: {wrapped.message}",
            )

            # Determine if error is fatal
            is_fatal = wrapped.severity in ("fatal",)

            return FileProcessingResult(
                video_path=video_path,
                status=ProcessingStatus.FAILED,
                error_message=wrapped.message,
                error_type=type(wrapped).__name__,
                error_context=wrapped.context,
                error_severity=wrapped.severity,
                is_fatal=is_fatal,
                processing_time=processing_time,
            )

    def process(
        self,
        input_path: str,
        gui_observers: Optional[Dict[str, Any]] = None,
        skip_preview: bool = False,
        on_file_start: Optional[Callable[[int, int, str], None]] = None,
        on_file_complete: Optional[
            Callable[[int, int, FileProcessingResult], None]
        ] = None,
    ) -> BatchProcessingReport:
        """Process input path (file or directory).

        This is the main entry point for batch processing.

        Args:
            input_path: Input path (file or directory)
            gui_observers: GUI observer dictionary
            skip_preview: Skip preview confirmation (for GUI mode)
            on_file_start: File start callback
            on_file_complete: File complete callback

        Returns:
            Batch processing report
        """
        self._cancelled.reset()  # Reset cancellation token

        try:
            # Preview files
            if skip_preview:
                _, video_files = resolve_input_path(input_path)
            else:
                video_files = self.preview_files(input_path)

            # Batch process
            report = self.process_batch(
                video_files,
                gui_observers,
                on_file_start,
                on_file_complete,
            )

            # Output summary report (use logging for consistency)
            log_info(report.get_summary())

            return report

        except OperationCancelledError:
            log_warning("Batch processing cancelled")
            return BatchProcessingReport()
        except MediaFactoryError as e:
            # Handle structured exceptions
            if e.severity == "fatal":
                log_error(f"Fatal error: {e.message}")
            else:
                log_warning(f"Error: {e.message}")
            return BatchProcessingReport()
        except (FileNotFoundError, ValueError) as e:
            wrapped = convert_exception(e)
            log_error(str(wrapped.message))
            return BatchProcessingReport()
        except Exception as e:
            wrapped = convert_exception(e)
            log_error(f"Unexpected error: {wrapped.message}")
            return BatchProcessingReport()


def process_batch(
    input_path: str,
    src_lang: Optional[str] = None,
    tgt_lang: str = "zh",
    gui_observers: Optional[Dict[str, Any]] = None,
    use_local_models_only: bool = False,
    translation_model: Optional[str] = None,  # 使用自动选择
    skip_preview: bool = False,
) -> BatchProcessingReport:
    """Batch process video files (convenience function).

    Args:
        input_path: Input path (file or directory)
        src_lang: Source language code (None for auto-detection)
        tgt_lang: Target language code (default: 'zh')
        gui_observers: Optional GUI progress observer callbacks
        use_local_models_only: Whether to use only local translation models
        translation_model: Translation model type to use
        skip_preview: Skip preview confirmation

    Returns:
        Batch processing report
    """
    processor = BatchProcessor(
        src_lang=src_lang,
        tgt_lang=tgt_lang,
        use_local_models_only=use_local_models_only,
        translation_model=translation_model,
    )
    return processor.process(
        input_path,
        gui_observers,
        skip_preview,
    )
