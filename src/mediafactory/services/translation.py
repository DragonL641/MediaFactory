"""
翻译服务
"""

import asyncio
from pathlib import Path
from typing import Optional

from mediafactory.config import get_config
from mediafactory.engine.translation import TranslationEngine
from mediafactory.engine.srt import SRTEngine
from mediafactory.llm import initialize_llm_backend
from mediafactory.pipeline import Pipeline
from mediafactory.pipeline.context import ProcessingContext, ProcessingResult
from mediafactory.logging import log_info, log_error, log_error_with_context
from mediafactory.core.progress_protocol import ProgressCallback, NO_OP_PROGRESS


class TranslationService:
    """
    翻译服务

    SRT 翻译委托给 Pipeline 执行，纯文本翻译保持直接调用。
    """

    def __init__(self):
        self.config = get_config()
        self._local_engine: Optional[TranslationEngine] = None

    @property
    def local_engine(self) -> TranslationEngine:
        if self._local_engine is None:
            self._local_engine = TranslationEngine()
        return self._local_engine

    async def translate_text(
        self,
        text: str,
        target_lang: str,
        use_llm: bool = False,
        llm_preset: Optional[str] = None,
        progress: ProgressCallback = NO_OP_PROGRESS,
    ) -> ProcessingResult:
        """
        翻译文本（纯文本，不走 Pipeline）

        Args:
            text: 要翻译的文本
            target_lang: 目标语言
            use_llm: 是否使用 LLM API
            progress: 进度回调

        Returns:
            ProcessingResult: 翻译结果
        """
        try:
            progress.update(0, "Starting translation...")

            if use_llm:
                backend = initialize_llm_backend(self.config, preset=llm_preset)
                if backend and backend.is_available:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: backend.translate(text, target_lang)
                    )
                    translated_text = result.translated_text
                else:
                    log_error("LLM backend 不可用，回退到本地模型")
                    loop = asyncio.get_event_loop()
                    translated_text = await loop.run_in_executor(
                        None, lambda: self.local_engine.translate(text, target_lang)
                    )
            else:
                loop = asyncio.get_event_loop()
                translated_text = await loop.run_in_executor(
                    None, lambda: self.local_engine.translate(text, target_lang)
                )

            progress.update(100, "Translation completed")

            return ProcessingResult(
                success=True,
                metadata={
                    "original_text": text,
                    "translated_text": translated_text,
                    "target_lang": target_lang,
                },
            )

        except Exception as e:
            log_error_with_context(
                "Translation failed",
                e,
                context={"target_lang": target_lang},
            )
            return ProcessingResult(
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
            )

    async def translate_srt(
        self,
        srt_path: str,
        target_lang: str,
        use_llm: bool = False,
        llm_preset: Optional[str] = None,
        progress: ProgressCallback = NO_OP_PROGRESS,
    ) -> ProcessingResult:
        """
        翻译 SRT 字幕文件（通过 Pipeline 执行）

        Args:
            srt_path: SRT 文件路径
            target_lang: 目标语言
            use_llm: 是否使用 LLM API
            progress: 进度回调

        Returns:
            ProcessingResult: 翻译结果（包含输出路径）
        """
        srt_path = Path(srt_path)

        try:
            progress.update(0, "Reading SRT file...")
            log_info(f"Starting SRT translation for: {srt_path}")

            # 读取 SRT 文件为 segments 格式
            srt_engine = SRTEngine()
            segments = srt_engine.parse(str(srt_path))

            if not segments:
                return ProcessingResult(
                    success=False,
                    error_message="No segments found in SRT file",
                    error_type="ValidationError",
                )

            # 创建 Pipeline 上下文
            context = ProcessingContext(
                src_lang="auto",
                tgt_lang=target_lang,
                progress_callback=progress,
                config={
                    "output_path": str(srt_path.with_suffix(f".{target_lang}.srt")),
                    "output_format_type": "srt",
                },
            )
            context.transcription_result = {"segments": segments}

            # 确定翻译引擎
            if use_llm:
                backend = initialize_llm_backend(self.config, preset=llm_preset)
                if backend and backend.is_available:
                    translation_engine = TranslationEngine(
                        llm_backend=backend,
                        use_llm_backend=True,
                    )
                else:
                    log_error("LLM backend initialization failed, falling back to local model")
                    translation_engine = self.local_engine
            else:
                translation_engine = self.local_engine

            # 创建并执行 Pipeline（Translation → SRT Generation）
            pipeline = Pipeline.create_translation_only(translation_engine, srt_engine)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, pipeline.execute, context)

            if not result.success:
                return ProcessingResult(
                    success=False,
                    error_message=result.error_message or "Pipeline execution failed",
                    error_type=result.error_type,
                )

            progress.update(100, "SRT translation completed")
            log_info(f"SRT translated: {result.output_path}")

            return ProcessingResult(
                success=True,
                output_path=result.output_path,
                metadata={"output_path": result.output_path},
            )

        except Exception as e:
            log_error_with_context(
                "SRT translation failed",
                e,
                context={"srt_path": str(srt_path)},
            )
            return ProcessingResult(
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
            )
