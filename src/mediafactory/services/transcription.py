"""
转录服务
"""

import asyncio
from pathlib import Path
from typing import Optional

from mediafactory.config import get_config
from mediafactory.engine.recognition import RecognitionEngine
from mediafactory.engine.srt import SRTEngine
from mediafactory.pipeline import Pipeline
from mediafactory.pipeline.context import ProcessingContext, ProcessingResult
from mediafactory.logging import log_info, log_error, log_error_with_context
from mediafactory.core.progress_protocol import ProgressCallback, NO_OP_PROGRESS
from mediafactory.api.error_handler import sanitize_error


class TranscriptionService:
    """
    语音转文字服务

    使用 Faster Whisper 进行语音识别，委托给 Pipeline 执行。
    """

    def __init__(self):
        self.config = get_config()
        self._recognition_engine: Optional[RecognitionEngine] = None

    @property
    def recognition_engine(self) -> RecognitionEngine:
        if self._recognition_engine is None:
            self._recognition_engine = RecognitionEngine()
        return self._recognition_engine

    async def transcribe(
        self,
        audio_path: str,
        language: str = "auto",
        progress: ProgressCallback = NO_OP_PROGRESS,
        output_format: str = "srt",
    ) -> ProcessingResult:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径
            language: 语言代码（auto 表示自动检测）
            progress: 进度回调

        Returns:
            ProcessingResult: 转录结果
        """
        audio_path = Path(audio_path)

        try:
            progress.update(0, "Starting transcription...")
            log_info(f"Starting transcription for: {audio_path}")

            # 创建 Pipeline 上下文
            context = ProcessingContext(
                audio_path=str(audio_path),
                src_lang=language if language != "auto" else None,
                progress_callback=progress,
                config={
                    "output_format_type": output_format,
                },
            )

            # 创建并执行 Pipeline（ModelLoading → Transcription → SRT → Cleanup）
            pipeline = Pipeline.create_transcribe_standalone(
                self.recognition_engine,
                SRTEngine(),
            )

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, pipeline.execute, context)

            if not result.success:
                return ProcessingResult(
                    success=False,
                    error_message=result.error_message or "Pipeline execution failed",
                    error_type=result.error_type,
                )

            progress.update(100, "Transcription completed")
            log_info(f"Transcribed: {audio_path}")

            # 提取 metadata
            metadata = {"audio_path": str(audio_path)}
            if result.context:
                metadata["segments"] = result.context.transcription_result.get("segments", [])
                metadata["language"] = result.context.transcription_result.get("language")

            return ProcessingResult(
                success=True,
                output_path=result.output_path,
                metadata=metadata,
            )

        except Exception as e:
            log_error_with_context(
                "Transcription failed",
                e,
                context={"audio_path": str(audio_path)},
            )
            return ProcessingResult(
                success=False,
                error_message=sanitize_error(e),
                error_type=type(e).__name__,
            )
