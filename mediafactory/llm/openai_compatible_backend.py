"""统一的 OpenAI 兼容翻译后端。

支持所有提供 OpenAI 兼容 API 的服务：
- OpenAI (官方)
- DeepSeek
- 智谱 GLM
- 通义千问
- Moonshot
- Ollama 本地
- 其他兼容服务

特性：
- 使用 OpenAI SDK 进行统一调用（SDK 内置重试）
- 批量翻译 + 二分降级策略
- 验证失败时：二分（递归至 split_threshold）→ 记录失败位置
- API 异常时：content filter 二分递归，其他异常记录失败位置
- 失败位置保留原文，结束日志汇总
- 支持可中断的翻译操作
- Prompt 外置管理
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..constants import LANGUAGE_NAMES
from ..core.progress_protocol import ProgressCallback
from ..exceptions import OperationCancelledError
from ..logging import (
    log_debug,
    log_error,
    log_info,
    log_llm_request,
    log_llm_response,
    log_warning,
)
from .base import (
    DetailedTranslationResult,
    TranslationBackend,
    TranslationRequest,
    TranslationResult,
    prepare_texts,
)
from .term_memory import TermDict


@dataclass
class BatchResult:
    """单批次翻译结果。

    Attributes:
        translations: 翻译结果列表（成功的有译文，失败的保留原文）
        failed_indices: 失败位置索引（相对于本批次的局部索引）
    """

    translations: list[str]
    failed_indices: list[int] = field(default_factory=list)


class OpenAICompatibleBackend(TranslationBackend):
    """统一的 OpenAI 兼容后端。

    支持 OpenAI、DeepSeek、GLM、通义千问、Moonshot 等服务。
    只需配置 base_url + api_key + model 即可使用。

    降级策略：
    批量翻译 → 二分（递归至最小批次）→ 记录失败位置（保留原文）
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        timeout: int = 30,
        max_retries: int = 3,
        batch_size: int = 40,
        split_threshold: int = 10,
        **kwargs,
    ):
        """初始化 OpenAI 兼容后端。

        Args:
            api_key: API Key
            base_url: API 基础 URL（如 https://api.openai.com/v1）
            model: 使用的模型名称
            temperature: 生成温度（翻译建议 0.1-0.3）
            timeout: 请求超时时间（秒）
            max_retries: SDK 最大重试次数
            batch_size: 批量翻译的批次大小
            split_threshold: 低于此数量不进行二分降级
            **kwargs: 其他参数
        """
        self._api_key = api_key or ""
        self._base_url = base_url or ""
        self._model = model or "gpt-4o-mini"
        self._temperature = temperature
        self._timeout = timeout
        self._max_retries = max_retries
        self._batch_size = batch_size
        self._split_threshold = split_threshold
        self._client = None
        self._kwargs = kwargs

        try:
            self._init_client()
        except ImportError:
            pass

    def _init_client(self) -> None:
        """初始化 OpenAI 客户端。

        本地 LLM（如 Ollama）不需要 API Key，使用占位符 "not-needed"。
        仅在 base_url 缺失时跳过初始化。
        """
        try:
            from openai import OpenAI
        except ImportError:
            return

        if not self._base_url:
            return

        # 本地 LLM 不需要 API Key，使用占位值
        api_key = self._api_key if self._api_key else "not-needed"

        self._client = OpenAI(
            api_key=api_key,
            base_url=self._base_url,
            timeout=self._timeout,
            max_retries=self._max_retries,
        )
        log_debug(f"[OpenAI-Compatible] 客户端初始化成功: base_url={self._base_url}")

    @property
    def name(self) -> str:
        """返回后端名称。"""
        return "openai_compatible"

    @property
    def is_available(self) -> bool:
        """检查后端是否可用。

        本地 LLM 只需要 base_url 即可使用，不需要 api_key。
        """
        if not self._base_url:
            return False

        if self._client is None:
            try:
                self._init_client()
            except Exception:
                return False

        return self._client is not None

    @property
    def get_model_name(self) -> str:
        """返回模型名称。"""
        return self._model

    # ==================== 连接测试 ====================

    def test_connection(self) -> dict:
        """测试 API 连接是否正常。"""
        # 使用基类的前提条件验证
        error_result = self._validate_connection_test_prerequisites(
            self._api_key, self._base_url, "openai"
        )
        if error_result:
            return error_result

        if self._client is None:
            try:
                self._init_client()
            except ImportError:
                return {
                    "success": False,
                    "message": "openai 包未安装，请运行: pip install openai",
                    "error": "ImportError: openai package not found",
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"初始化客户端失败: {str(e)}",
                    "error": str(e),
                }

        try:
            log_debug(f"[OpenAI-Compatible] 测试连接 - 模型: {self._model}")

            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "user", "content": "Hello, please respond with 'OK'."}
                ],
                max_tokens=10,
            )

            if response and hasattr(response, "choices") and len(response.choices) > 0:
                log_info(f"[OpenAI-Compatible] 连接成功！模型: {self._model}")
                return {
                    "success": True,
                    "message": f"连接成功！模型: {self._model}",
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "message": "API 返回了无效的响应",
                    "error": "Invalid response from API",
                }

        except Exception as e:
            error_str = str(e)
            log_error(f"[OpenAI-Compatible] 连接失败: {error_str}")
            error_msg = self._parse_error_message(error_str)

            return {
                "success": False,
                "message": error_msg,
                "error": error_str,
            }

    def _parse_error_message(self, error_str: str) -> str:
        """解析错误消息，返回用户友好的提示。"""
        error_lower = error_str.lower()

        if (
            "401" in error_str
            or "unauthorized" in error_lower
            or "invalid api key" in error_lower
        ):
            return "API Key 无效或已过期"
        elif (
            "429" in error_str or "rate limit" in error_lower or "quota" in error_lower
        ):
            return "API 配额已用尽或请求频率超限"
        elif "timeout" in error_lower or "timed out" in error_lower:
            return "请求超时，请检查网络连接"
        elif "connection" in error_lower or "network" in error_lower:
            return "网络连接失败，请检查网络"
        elif "model" in error_lower and (
            "not found" in error_lower or "does not exist" in error_lower
        ):
            return "模型不存在，请检查模型名称"
        else:
            return f"请求失败: {error_str}"

    # ==================== 主翻译入口 ====================

    def translate(self, request: TranslationRequest) -> TranslationResult:
        """执行翻译。translate_detailed 的薄包装，行为与旧版一致。"""
        return self.translate_detailed(request).result

    def translate_detailed(
        self,
        request: TranslationRequest,
        term_dict: TermDict | None = None,
    ) -> DetailedTranslationResult:
        """执行翻译并暴露失败位置与术语记忆。

        Args:
            request: 翻译请求
            term_dict: 可传入既有 TermDict（兜底链复用主链学到的词条）；
                None 时新建并从 request.user_terms 注册种子

        Returns:
            DetailedTranslationResult（failed_indices 相对最终输出列表）
        """
        if not self.is_available:
            return DetailedTranslationResult(
                result=TranslationResult(
                    translated_text=request.text,
                    backend_used=self.name,
                    success=False,
                    error_message="OpenAI 兼容 API 未配置或不可用",
                ),
            )

        texts = self._normalize_texts(request.text)
        if term_dict is None:
            term_dict = TermDict()
            if request.user_terms:
                term_dict.register_user(request.user_terms)

        try:
            translated, failed_indices = self._translate_all_texts(
                texts=texts,
                src_lang=request.src_lang,
                tgt_lang=request.tgt_lang,
                cancelled_callback=request.cancelled_callback,
                progress_callback=request.progress_callback,
                term_dict=term_dict,
            )
            result = TranslationResult(
                translated_text=translated[0] if len(texts) == 1 else translated,
                backend_used=self.name,
                success=True,
            )
            return DetailedTranslationResult(
                result=result, failed_indices=failed_indices, term_dict=term_dict
            )
        except OperationCancelledError:
            raise
        except Exception as e:
            error_msg = str(e)
            log_error(f"[OpenAI-Compatible] 翻译失败: {error_msg}")
            return DetailedTranslationResult(
                result=TranslationResult(
                    translated_text=texts if len(texts) > 1 else texts[0],
                    backend_used=self.name,
                    success=False,
                    error_message=error_msg,
                ),
            )

    # ==================== 核心翻译逻辑 ====================

    def _translate_all_texts(
        self,
        texts: list[str],
        src_lang: str,
        tgt_lang: str,
        cancelled_callback: Callable | None = None,
        progress_callback: ProgressCallback | None = None,
        term_dict: TermDict | None = None,
    ) -> tuple[list[str], list[int]]:
        """翻译所有文本（分批处理 + 统一失败收集）。

        Args:
            texts: 待翻译的文本列表
            src_lang: 源语言代码
            tgt_lang: 目标语言代码
            cancelled_callback: 取消检查回调
            progress_callback: 进度回调
            term_dict: 术语记忆实例（None 时创建空的）

        Returns:
            (翻译结果列表, 失败索引列表)——失败索引相对最终输出列表
            （已把非空空间的失败位映射回含空字符串的原空间）
        """
        term_dict = term_dict or TermDict()
        tgt_name = self.get_language_name(tgt_lang)
        src_name = self.get_language_name(src_lang)

        # 准备文本：分离空字符串
        non_empty_texts, empty_indices = prepare_texts(texts)

        # 如果全是空字符串，直接返回
        if not non_empty_texts:
            if progress_callback:
                progress_callback.update(100, "Translation completed")
            return texts, []

        # Log LLM request
        log_llm_request(
            backend="openai_compatible",
            model=self._model,
            text_length=sum(len(t) for t in non_empty_texts),
            src_lang=src_name,
            tgt_lang=tgt_name,
            batch_size=len(non_empty_texts),
        )

        log_info(
            f"[OpenAI-Compatible] 开始翻译: {len(non_empty_texts)} 行, "
            f"目标语言={tgt_name}, 批次大小={self._batch_size}"
        )

        if progress_callback:
            progress_callback.update(5, "Starting translation...")

        # 分批翻译 + 收集失败位置
        all_translated = list(non_empty_texts)  # 预填原文
        failed_global_indices: list[int] = []
        total_batches = (
            len(non_empty_texts) + self._batch_size - 1
        ) // self._batch_size

        for batch_idx in range(total_batches):
            # 检查是否已取消
            if cancelled_callback and cancelled_callback():
                raise OperationCancelledError("翻译已取消")

            global_start = batch_idx * self._batch_size
            global_end = min(global_start + self._batch_size, len(non_empty_texts))
            batch = non_empty_texts[global_start:global_end]

            log_debug(
                f"[OpenAI-Compatible] 翻译批次 {batch_idx + 1}/{total_batches}: "
                f"行 {global_start + 1}-{global_end}"
            )

            try:
                result = self._translate_batch(
                    batch,
                    tgt_lang,
                    cancelled_callback,
                    allow_split=True,
                    src_lang=src_lang,
                    term_dict=term_dict,
                )
                # 术语滚动记忆：学习本批候选并执行冲突替换
                result.translations = self._learn_and_fix(
                    term_dict, batch, result.translations, cancelled_callback
                )
                # 填入翻译结果
                for i, text in enumerate(result.translations):
                    all_translated[global_start + i] = text
                # 记录失败位置（转为全局索引）
                failed_global_indices.extend(
                    global_start + i for i in result.failed_indices
                )
            except OperationCancelledError:
                raise
            except Exception as e:
                if self._is_content_filter_error(e):
                    # contentFilter: 二分递归，尽量保留 LLM 翻译
                    log_warning(
                        f"[OpenAI-Compatible] 批次 {batch_idx + 1}/{total_batches} "
                        f"触发内容过滤，开始二分处理..."
                    )
                    result = self._translate_batch_with_content_filter_split(
                        batch,
                        tgt_lang,
                        cancelled_callback,
                        src_lang=src_lang,
                        term_dict=term_dict,
                    )
                    # 术语滚动记忆：降级批产物与正常批同权（提取 + 冲突替换）
                    result.translations = self._learn_and_fix(
                        term_dict, batch, result.translations, cancelled_callback
                    )
                    for i, text in enumerate(result.translations):
                        all_translated[global_start + i] = text
                    failed_global_indices.extend(
                        global_start + i for i in result.failed_indices
                    )
                else:
                    # 非 contentFilter 错误：整批失败
                    log_warning(
                        f"[OpenAI-Compatible] 批次 {batch_idx + 1}/{total_batches} "
                        f"API 调用失败: {e}，记录失败位置"
                    )
                    failed_global_indices.extend(range(global_start, global_end))

            # 报告进度（5-95% 范围）
            if progress_callback:
                progress = 5 + ((batch_idx + 1) / total_batches) * 90
                progress_callback.update(
                    progress,
                    f"Translating batch {batch_idx + 1}/{total_batches}",
                )

        # 汇总失败位置（保留原文）
        if failed_global_indices:
            log_warning(
                f"[OpenAI-Compatible] {len(failed_global_indices)} 句翻译失败，"
                f"保留原文输出"
            )

        # 恢复空字符串，并把失败索引从非空空间映射回最终列表空间
        result = []
        failed_set = set(failed_global_indices)
        failed_final: list[int] = []
        non_empty_idx = 0
        empty_set = set(empty_indices)
        for i in range(len(texts)):
            if i in empty_set:
                result.append("")
            else:
                result.append(all_translated[non_empty_idx])
                if non_empty_idx in failed_set:
                    failed_final.append(i)
                non_empty_idx += 1

        # 报告完成
        if progress_callback:
            progress_callback.update(100, "Translation completed")

        log_info(
            f"[OpenAI-Compatible] 翻译完成: {len(non_empty_texts)} 行"
            + (
                f"，其中 {len(failed_global_indices)} 句保留原文"
                if failed_global_indices
                else ""
            )
        )
        if term_dict.dump():
            log_info(
                f"[TermDict] 术语记忆 {len(term_dict.dump())} 条: {term_dict.dump()}"
            )

        log_llm_response(
            "openai_compatible",
            success=not failed_global_indices,
            output_length=sum(len(t) for t in result),
            error=(
                f"{len(failed_global_indices)} sentence(s) failed, kept original"
                if failed_global_indices
                else None
            ),
        )

        return result, failed_final

    def _translate_batch(
        self,
        batch: list[str],
        tgt_lang: str,
        cancelled_callback: Callable | None = None,
        allow_split: bool = True,
        src_lang: str = "",
        term_dict: TermDict | None = None,
    ) -> BatchResult:
        """单批次翻译，包含降级逻辑。

        降级策略：
        1. 尝试批量翻译
        2. 验证失败 → 二分（当 allow_split 且数量 >= split_threshold）
        3. 不再二分 → 记录失败位置

        API 异常直接抛出，由 _translate_all_texts 统一处理。
        """
        tgt_name = self.get_language_name(tgt_lang)
        src_name = self.get_language_name(src_lang) if src_lang else ""

        # 术语注入：命中当前批的词条渲染进 prompt
        hits = term_dict.hits(batch) if term_dict else {}
        custom_instructions = term_dict.render(hits) if term_dict else ""

        # 1. 尝试批量翻译
        response = self._call_llm_batch(
            batch,
            tgt_name,
            cancelled_callback,
            src_name=src_name,
            custom_instructions=custom_instructions,
        )
        result = self._parse_json_response(response)

        if result and self._validate_keys(result, batch):
            # 类型安全提取：确保所有值都是字符串
            translations = [
                str(result.get(str(i), batch[i])) for i in range(len(batch))
            ]
            return BatchResult(translations=translations)

        # 2. 验证失败，尝试二分
        if allow_split and len(batch) >= self._split_threshold:
            half = len(batch) // 2
            log_warning(
                f"[OpenAI-Compatible] 批次验证失败（{len(batch)} 句），二分处理: "
                f"{half} + {len(batch) - half}"
            )

            first = self._translate_batch(
                batch[:half],
                tgt_lang,
                cancelled_callback,
                allow_split=True,
                src_lang=src_lang,
                term_dict=term_dict,
            )
            second = self._translate_batch(
                batch[half:],
                tgt_lang,
                cancelled_callback,
                allow_split=True,
                src_lang=src_lang,
                term_dict=term_dict,
            )

            return BatchResult(
                translations=first.translations + second.translations,
                failed_indices=(
                    first.failed_indices + [half + i for i in second.failed_indices]
                ),
            )

        # 3. 不再二分，记录失败
        log_warning(f"[OpenAI-Compatible] 批次 {len(batch)} 句无法翻译，记录失败位置")
        return BatchResult(
            translations=list(batch),
            failed_indices=list(range(len(batch))),
        )

    # ==================== 术语滚动记忆 ====================

    _EXTRACT_MAX_TERMS = 5

    def _cap_candidates(self, candidates: dict[str, str]) -> dict[str, str]:
        """裁剪提取候选至硬上限。"""
        return dict(list(candidates.items())[: self._EXTRACT_MAX_TERMS])

    def _extract_terms(
        self,
        batch: list[str],
        translations: list[str],
        cancelled_callback: Callable | None = None,
    ) -> dict[str, str]:
        """从本批源文-译文对照提取候选词条。任何失败静默返回空 dict。"""
        try:
            from ..utils.prompt_loader import get_prompt

            prompt = get_prompt(
                "translate/extract_terms", max_terms=str(self._EXTRACT_MAX_TERMS)
            )
            user_content = json.dumps(
                {"source": batch, "translation": translations},
                ensure_ascii=False,
            )
            response = self._call_llm(prompt, user_content, cancelled_callback)
            parsed = self._parse_json_response(response)
            raw_terms: Any = parsed.get("terms") if parsed else None
            if not isinstance(raw_terms, dict):
                return {}
            terms = {
                str(k): str(v).strip()
                for k, v in raw_terms.items()
                if str(k).strip() and str(v).strip()
            }
            return self._cap_candidates(terms)
        except Exception as e:
            log_debug(f"[TermDict] 词条提取失败（忽略）: {e}")
            return {}

    def _learn_and_fix(
        self,
        term_dict: TermDict,
        batch: list[str],
        translations: list[str],
        cancelled_callback: Callable | None = None,
    ) -> list[str]:
        """学习本批候选并执行冲突替换。"""
        candidates = self._extract_terms(batch, translations, cancelled_callback)
        if not candidates:
            return translations
        wrong_map: dict[str, str] = {}
        for word, translation in candidates.items():
            key = word.strip().lower()
            if term_dict.learn(word, translation) == "conflict":
                wrong_map[key] = translation
                if term_dict.source_of(key) == "user":
                    log_warning(
                        f"[TermDict] 模型未遵守用户术语表，已替换: {key!r}"
                        f" → {term_dict.dump().get(key, {}).get('translation')!r}"
                    )
                else:
                    log_debug(f"[TermDict] auto 词条译法冲突，已按首译统一: {key!r}")
        if wrong_map:
            translations = term_dict.apply_conflict_fixes(translations, wrong_map)
        return translations

    # ==================== contentFilter 二分递归 ====================

    @staticmethod
    def _is_content_filter_error(error: Exception) -> bool:
        """检测是否为 LLM 内容过滤错误（如 GLM code 1301）"""
        error_str = str(error).lower()
        return any(
            keyword in error_str
            for keyword in ("1301", "contentfilter", "不安全", "敏感内容")
        )

    def _translate_batch_with_content_filter_split(
        self,
        batch: list[str],
        tgt_lang: str,
        cancelled_callback: Callable | None = None,
        src_lang: str = "",
        term_dict: TermDict | None = None,
    ) -> BatchResult:
        """contentFilter 错误的二分递归处理。

        策略：二分 → 两半分别重试 → 成功的保留 LLM 翻译 →
        失败的继续二分 → 达到最小批次回退本地模型。
        """
        if cancelled_callback and cancelled_callback():
            raise OperationCancelledError("翻译已取消")

        try:
            return self._translate_batch(
                batch,
                tgt_lang,
                cancelled_callback,
                allow_split=True,
                src_lang=src_lang,
                term_dict=term_dict,
            )
        except OperationCancelledError:
            raise
        except Exception as e:
            # 非 contentFilter 错误直接抛出
            if not self._is_content_filter_error(e):
                raise

            # 达到最小批次，标记整批失败（由 _translate_all_texts 统一本地回退）
            if len(batch) < self._split_threshold:
                log_warning(
                    f"[OpenAI-Compatible] 批次降至 {len(batch)} 句仍触发内容过滤，"
                    f"回退本地模型"
                )
                return BatchResult(
                    translations=list(batch),
                    failed_indices=list(range(len(batch))),
                )

            # 二分重试
            half = len(batch) // 2
            log_info(
                f"[OpenAI-Compatible] 内容过滤触发二分: "
                f"{len(batch)} → {half} + {len(batch) - half}"
            )
            first = self._translate_batch_with_content_filter_split(
                batch[:half],
                tgt_lang,
                cancelled_callback,
                src_lang=src_lang,
                term_dict=term_dict,
            )
            second = self._translate_batch_with_content_filter_split(
                batch[half:],
                tgt_lang,
                cancelled_callback,
                src_lang=src_lang,
                term_dict=term_dict,
            )
            return BatchResult(
                translations=first.translations + second.translations,
                failed_indices=(
                    first.failed_indices + [half + i for i in second.failed_indices]
                ),
            )

    # ==================== 底层 API 调用 ====================

    def _call_llm(
        self,
        system_prompt: str,
        user_content: str,
        cancelled_callback: Callable | None = None,
    ) -> str:
        """底层 API 调用（无应用层重试，依赖 SDK 内置重试）。

        Args:
            system_prompt: 系统提示词
            user_content: 用户内容
            cancelled_callback: 取消检查回调

        Returns:
            LLM 响应文本

        Raises:
            OperationCancelledError: 翻译已取消
            Exception: API 调用失败（SDK 已重试耗尽）
        """
        if cancelled_callback and cancelled_callback():
            raise OperationCancelledError("翻译已取消")

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=self._temperature,
        )

        content = response.choices[0].message.content
        return content.strip() if content else ""

    def _call_llm_batch(
        self,
        batch: list[str],
        tgt_name: str,
        cancelled_callback: Callable | None = None,
        src_name: str = "",
        custom_instructions: str = "",
    ) -> str:
        """批量翻译 API 调用。

        Args:
            batch: 待翻译的文本批次
            tgt_name: 目标语言名称
            cancelled_callback: 取消检查回调
            src_name: 源语言名称
            custom_instructions: 术语注入文本（空串表示无）

        Returns:
            LLM 响应文本
        """
        prompt = self._get_batch_prompt(tgt_name, src_name, custom_instructions)
        input_json = json.dumps(
            {str(i): t for i, t in enumerate(batch)}, ensure_ascii=False
        )
        src_hint = f"（从{src_name}）" if src_name else ""
        user_content = f"请将以下{src_hint}内容翻译为{tgt_name}：\n{input_json}"
        return self._call_llm(prompt, user_content, cancelled_callback)

    # ==================== 辅助方法 ====================

    def _parse_json_response(self, response_text: str) -> dict[str, str] | None:
        """解析 JSON 响应。

        依次尝试：1. 直接解析 2. 提取 markdown 代码块 3. 提取 JSON 对象

        Args:
            response_text: LLM 返回的文本

        Returns:
            解析后的字典，如果解析失败返回 None
        """
        if not response_text:
            return None

        # 收集候选 JSON 文本
        candidates = [response_text]

        # 尝试提取 markdown 代码块
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            candidates.append(json_match.group(1))

        # 尝试提取 JSON 对象
        brace_start = response_text.find("{")
        brace_end = response_text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            candidates.append(response_text[brace_start : brace_end + 1])

        for candidate in candidates:
            try:
                result = json.loads(candidate)
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, TypeError):
                continue

        return None

    def _validate_keys(self, result: dict[str, str], batch: list[str]) -> bool:
        """验证结果键是否包含所有期望的键。

        宽容匹配：LLM 可能返回额外的键，只要包含所有期望键即可。

        Args:
            result: 解析后的结果字典
            batch: 原始输入批次

        Returns:
            True 如果包含所有期望键，False 否则
        """
        expected_keys = {str(i) for i in range(len(batch))}
        result_keys = set(result.keys())
        return expected_keys.issubset(result_keys)

    def _get_batch_prompt(
        self,
        target_language: str,
        source_language: str = "",
        custom_instructions: str = "",
    ) -> str:
        """获取批量翻译 prompt。"""
        from ..utils.prompt_loader import get_prompt

        return get_prompt(
            "translate/batch",
            target_language=target_language,
            source_language=source_language,
            custom_instructions=custom_instructions,
        )

    def get_language_name(self, lang_code: str) -> str:
        """获取语言的可读名称。"""
        return LANGUAGE_NAMES.get(lang_code, lang_code)
