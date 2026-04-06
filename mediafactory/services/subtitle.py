"""
字幕生成服务
"""

import asyncio
from pathlib import Path
from typing import Optional

from mediafactory.config import get_config
from mediafactory.engine.audio import AudioEngine
from mediafactory.engine.recognition import RecognitionEngine
from mediafactory.engine.translation import TranslationEngine
from mediafactory.engine.srt import SRTEngine
from mediafactory.llm import initialize_llm_backend
from mediafactory.pipeline import Pipeline
from mediafactory.pipeline.context import ProcessingContext, ProcessingResult
from mediafactory.logging import log_info, log_error, log_error_with_context
from mediafactory.core.progress_protocol import ProgressCallback, NO_OP_PROGRESS
from mediafactory.core.error_utils import sanitize_error


class SubtitleService:
    """
    字幕生成服务

    委托给 Pipeline 进行字幕生成，统一工作流和进度报告。
    """

    def __init__(self):
        self.config = get_config()
        self._audio_engine = None
        self._recognition_engine = None
        self._srt_engine = None

    async def generate_subtitle(
        self,
        video_path: str,
        source_lang: str = "auto",
        target_lang: str = "zh",
        use_llm: bool = False,
        llm_preset: Optional[str] = None,
        output_format: str = "srt",
        bilingual: bool = False,
        bilingual_layout: str = "translate_on_top",
        style_preset: str = "default",
        progress: ProgressCallback = NO_OP_PROGRESS,
    ) -> ProcessingResult:
        """
        生成字幕

        Args:
            video_path: 视频文件路径
            source_lang: 源语言（auto 表示自动检测）
            target_lang: 目标语言
            use_llm: 是否使用 LLM API 进行翻译
            output_format: 输出格式（srt/ass/txt）
            progress: 进度回调

        Returns:
            ProcessingResult: 处理结果
        """
        video_path = Path(video_path)

        try:
            progress.update(0, "Starting subtitle generation...")
            log_info(f"Starting subtitle generation for: {video_path}")

            # 初始化翻译引擎
            if use_llm:
                backend = initialize_llm_backend(self.config, preset=llm_preset)
                if backend and backend.is_available:
                    translation_engine = TranslationEngine(
                        llm_backend=backend,
                        use_llm_backend=True,
                    )
                else:
                    log_error(
                        "LLM backend initialization failed, falling back to local model"
                    )
                    translation_engine = TranslationEngine()
            else:
                translation_engine = TranslationEngine()

            # 创建 Pipeline 上下文
            context = ProcessingContext(
                video_path=str(video_path),
                src_lang=source_lang,
                tgt_lang=target_lang,
                progress_callback=progress,
                bilingual=bilingual,
                bilingual_layout=bilingual_layout,
                style_preset=style_preset,
                config={
                    "output_format_type": output_format,
                    "output_format": output_format,
                },
            )

            # 创建并执行 Pipeline（传入所有引擎，延迟初始化）
            if self._audio_engine is None:
                self._audio_engine = AudioEngine()
            if self._recognition_engine is None:
                self._recognition_engine = RecognitionEngine()
            if self._srt_engine is None:
                self._srt_engine = SRTEngine()

            pipeline = Pipeline.create_default(
                self._audio_engine,
                self._recognition_engine,
                translation_engine,
                self._srt_engine,
            )

            # 在线程池中执行 Pipeline（因为它是同步的）
            loop = asyncio.get_running_loop()

            def run_pipeline():
                return pipeline.execute(context)

            result: ProcessingResult = await loop.run_in_executor(None, run_pipeline)

            if not result.success:
                return ProcessingResult(
                    success=False,
                    error_message=result.error_message or "Pipeline execution failed",
                    error_type=result.error_type,
                )

            progress.update(100, "Subtitle generation completed")
            log_info(f"Subtitle generated: {result.output_path}")

            return ProcessingResult(
                success=True,
                output_path=result.output_path,
                metadata={
                    "video_path": str(video_path),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "output_format": output_format,
                },
            )

        except Exception as e:
            log_error_with_context(
                "Subtitle generation failed",
                e,
                context={"video_path": str(video_path)},
            )
            return ProcessingResult(
                success=False,
                error_message=sanitize_error(e),
                error_type=type(e).__name__,
            )
