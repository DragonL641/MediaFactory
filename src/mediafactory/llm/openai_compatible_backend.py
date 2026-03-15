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
- 使用 OpenAI SDK 进行统一调用
- 批量翻译 + 智能降级策略
- 行数不匹配时：纠正 → 分批 → 逐句 → 本地模型
- 支持可中断的翻译操作
- Prompt 外置管理
"""

import json
import time
from typing import Optional, List, Dict, Callable

from .base import (
    TranslationBackend,
    TranslationRequest,
    TranslationResult,
    prepare_texts,
    restore_result,
)
from .local_fallback import LocalModelFallback
from ..constants import LANGUAGE_NAMES
from ..core.progress_protocol import ProgressCallback
from ..exceptions import ProcessingError
from ..logging import (
    log_debug,
    log_info,
    log_warning,
    log_error,
    log_llm_request,
    log_llm_response,
    log_llm_retry,
)

# 批量翻译配置
DEFAULT_BATCH_SIZE = 20  # 默认批量大小


class OpenAICompatibleBackend(TranslationBackend):
    """统一的 OpenAI 兼容后端。

    支持 OpenAI、DeepSeek、GLM、通义千问、Moonshot 等服务。
    只需配置 base_url + api_key + model 即可使用。

    降级策略：
    批量翻译 (20句) → 纠正 → 分成两小批 → 逐句 → 本地模型
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        timeout: int = 30,
        max_retries: int = 3,
        batch_size: int = DEFAULT_BATCH_SIZE,
        **kwargs,
    ):
        """初始化 OpenAI 兼容后端。

        Args:
            api_key: API Key
            base_url: API 基础 URL（如 https://api.openai.com/v1）
            model: 使用的模型名称
            temperature: 生成温度（翻译建议 0.1-0.3）
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            batch_size: 批量翻译的批次大小
            **kwargs: 其他参数
        """
        self._api_key = api_key or ""
        self._base_url = base_url or ""
        self._model = model or "gpt-4o-mini"
        self._temperature = temperature
        self._timeout = timeout
        self._max_retries = max_retries
        self._batch_size = batch_size
        self._client = None
        self._kwargs = kwargs
        self._local_fallback: Optional[LocalModelFallback] = None

        try:
            self._init_client()
        except ImportError:
            pass

    def _init_client(self) -> None:
        """初始化 OpenAI 客户端。"""
        try:
            from openai import OpenAI
        except ImportError:
            return

        if not self._api_key or not self._base_url:
            return

        self._client = OpenAI(
            api_key=self._api_key,
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
        """检查后端是否可用。"""
        if not self._api_key or not self._base_url:
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
        """执行翻译。

        Args:
            request: 翻译请求对象

        Returns:
            翻译结果对象
        """
        if not self.is_available:
            return TranslationResult(
                translated_text=(
                    request.text if isinstance(request.text, str) else request.text
                ),
                backend_used=self.name,
                success=False,
                error_message="OpenAI 兼容 API 未配置或不可用",
            )

        # 使用基类的文本标准化方法
        texts = self._normalize_texts(request.text)

        # 初始化本地回退（但不加载）
        self._local_fallback = LocalModelFallback()

        try:
            translated = self._translate_all_texts(
                texts=texts,
                src_lang=request.src_lang,
                tgt_lang=request.tgt_lang,
                cancelled_callback=request.cancelled_callback,
                progress_callback=request.progress_callback,
            )

            # 返回结果
            if len(texts) == 1:
                return TranslationResult(
                    translated_text=translated[0],
                    backend_used=self.name,
                    success=True,
                )
            else:
                return TranslationResult(
                    translated_text=translated,
                    backend_used=self.name,
                    success=True,
                )

        except Exception as e:
            error_msg = str(e)
            log_error(f"[OpenAI-Compatible] 翻译失败: {error_msg}")
            return TranslationResult(
                translated_text=texts if len(texts) > 1 else texts[0],
                backend_used=self.name,
                success=False,
                error_message=error_msg,
            )

        finally:
            # 翻译完成后释放本地模型
            if self._local_fallback:
                self._local_fallback.release()
                self._local_fallback = None

    # ==================== 核心翻译逻辑 ====================

    def _translate_all_texts(
        self,
        texts: List[str],
        src_lang: str,
        tgt_lang: str,
        cancelled_callback: Optional[Callable] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[str]:
        """翻译所有文本（分批处理）。

        Args:
            texts: 待翻译的文本列表
            src_lang: 源语言代码
            tgt_lang: 目标语言代码
            cancelled_callback: 取消检查回调
            progress_callback: 进度回调

        Returns:
            翻译结果列表
        """
        tgt_name = self.get_language_name(tgt_lang)
        src_name = self.get_language_name(src_lang)

        # 准备文本：分离空字符串
        non_empty_texts, empty_indices = prepare_texts(texts)

        # 如果全是空字符串，直接返回
        if not non_empty_texts:
            if progress_callback:
                progress_callback.update(100, "Translation completed")
            return texts

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
            f"目标语言={tgt_name}"
        )

        if progress_callback:
            progress_callback.update(5, "Starting translation...")

        # 分批翻译
        all_translated = []
        total_batches = (
            len(non_empty_texts) + self._batch_size - 1
        ) // self._batch_size

        for batch_idx in range(total_batches):
            # 检查是否已取消
            if cancelled_callback and cancelled_callback():
                log_warning("[OpenAI-Compatible] 翻译被取消")
                raise RuntimeError("翻译已被取消")

            start = batch_idx * self._batch_size
            end = min(start + self._batch_size, len(non_empty_texts))
            batch = non_empty_texts[start:end]

            log_debug(
                f"[OpenAI-Compatible] 翻译批次 {batch_idx + 1}/{total_batches}: 行 {start + 1}-{end}"
            )

            translated_batch = self._translate_batch(
                batch, tgt_lang, cancelled_callback
            )
            all_translated.extend(translated_batch)

            # 报告进度（5-95% 范围）
            if progress_callback:
                progress = 5 + ((batch_idx + 1) / total_batches) * 90
                progress_callback.update(
                    progress,
                    f"Translating batch {batch_idx + 1}/{total_batches}",
                )

        # 恢复空字符串
        result = restore_result(all_translated, empty_indices, len(texts))

        # 报告完成
        if progress_callback:
            progress_callback.update(100, "Translation completed")

        log_info(f"[OpenAI-Compatible] 翻译完成: {len(non_empty_texts)} 行")
        log_llm_response(
            "openai_compatible",
            success=True,
            output_length=sum(len(t) for t in result),
        )

        return result

    def _translate_batch(
        self,
        batch: List[str],
        tgt_lang: str,
        cancelled_callback: Optional[Callable] = None,
    ) -> List[str]:
        """单批次翻译，包含完整降级逻辑。

        降级策略：
        1. 尝试批量翻译
        2. 行数不匹配 → 单次纠正
        3. 纠正失败 → 分成两小批
        4. 小批次失败 → 逐句翻译
        5. 单句失败 → 本地模型

        Args:
            batch: 待翻译的文本批次
            tgt_lang: 目标语言代码
            cancelled_callback: 取消检查回调

        Returns:
            翻译结果列表
        """
        tgt_name = self.get_language_name(tgt_lang)

        # 1. 尝试批量翻译
        response = self._call_llm_batch(batch, tgt_name, cancelled_callback)
        result = self._parse_json_response(response)

        if result and self._validate_keys(result, batch):
            return [result[str(i)] for i in range(len(batch))]  # ✅ 成功

        # 2. 行数不匹配，尝试纠正
        log_warning(
            f"[OpenAI-Compatible] 批次验证失败，尝试纠正..."
        )
        corrected = self._call_llm_batch(
            batch, tgt_name, cancelled_callback,
            error_hint=f"上次返回行数不正确，期望{len(batch)}行，请严格按JSON格式返回"
        )
        result = self._parse_json_response(corrected)

        if result and self._validate_keys(result, batch):
            return [result[str(i)] for i in range(len(batch))]  # ✅ 纠正成功

        # 3. 纠正失败，分成两小批
        log_warning(
            f"[OpenAI-Compatible] 纠正失败，分批处理: {len(batch)} → 2 批"
        )

        half = len(batch) // 2
        first_half = self._translate_batch_small(
            batch[:half], tgt_lang, cancelled_callback
        )
        second_half = self._translate_batch_small(
            batch[half:], tgt_lang, cancelled_callback
        )

        return first_half + second_half

    def _translate_batch_small(
        self,
        batch: List[str],
        tgt_lang: str,
        cancelled_callback: Optional[Callable] = None,
    ) -> List[str]:
        """小批次翻译（不再分批，失败直接转单句）。

        Args:
            batch: 待翻译的文本批次（通常 ≤10 句）
            tgt_lang: 目标语言代码
            cancelled_callback: 取消检查回调

        Returns:
            翻译结果列表
        """
        tgt_name = self.get_language_name(tgt_lang)

        # 尝试批量翻译
        response = self._call_llm_batch(batch, tgt_name, cancelled_callback)
        result = self._parse_json_response(response)

        if result and self._validate_keys(result, batch):
            return [result[str(i)] for i in range(len(batch))]  # ✅ 成功

        # 小批次也失败，转单句翻译
        log_warning(
            f"[OpenAI-Compatible] 小批次验证失败，转逐句翻译: {len(batch)} 句"
        )
        return self._translate_individually(batch, tgt_lang, cancelled_callback)

    def _translate_individually(
        self,
        texts: List[str],
        tgt_lang: str,
        cancelled_callback: Optional[Callable] = None,
    ) -> List[str]:
        """逐句翻译，单句失败时回退到本地模型。

        Args:
            texts: 待翻译的文本列表
            tgt_lang: 目标语言代码
            cancelled_callback: 取消检查回调

        Returns:
            翻译结果列表
        """
        tgt_name = self.get_language_name(tgt_lang)
        results = []

        for i, text in enumerate(texts):
            if cancelled_callback and cancelled_callback():
                raise RuntimeError("翻译已取消")

            try:
                # 尝试 LLM 单句翻译
                translated = self._translate_single_llm(
                    text, tgt_name, cancelled_callback
                )
                results.append(translated)
                log_debug(f"[OpenAI-Compatible] 单句 {i+1}/{len(texts)} LLM 翻译成功")

            except Exception as e:
                # LLM 单句失败，回退到本地模型
                log_warning(
                    f"[OpenAI-Compatible] 单句 {i+1} LLM 翻译失败: {e}，回退到本地模型"
                )
                translated = self._local_fallback.translate_single(
                    text, tgt_lang
                )
                results.append(translated)

        return results

    # ==================== 底层 API 调用 ====================

    def _call_llm(
        self,
        system_prompt: str,
        user_content: str,
        cancelled_callback: Optional[Callable] = None,
    ) -> str:
        """底层 API 调用，包含重试逻辑。

        Args:
            system_prompt: 系统提示词
            user_content: 用户内容
            cancelled_callback: 取消检查回调

        Returns:
            LLM 响应文本

        Raises:
            RuntimeError: API 调用失败或被取消
        """
        for attempt in range(self._max_retries):
            if cancelled_callback and cancelled_callback():
                raise RuntimeError("翻译已取消")

            try:
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

            except Exception as e:
                error_str = str(e)

                # 检查是否为不可重试错误
                if self._is_non_retryable_error(error_str):
                    raise

                log_llm_retry(
                    "openai_compatible", attempt + 1, self._max_retries, error_str
                )

                if attempt < self._max_retries - 1:
                    wait_time = min(2**attempt, 60)
                    log_debug(f"[OpenAI-Compatible] 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(
                        f"{self._parse_error_message(error_str)} (经过 {self._max_retries} 次重试)"
                    )

        return ""

    def _call_llm_batch(
        self,
        batch: List[str],
        tgt_name: str,
        cancelled_callback: Optional[Callable] = None,
        error_hint: Optional[str] = None,
    ) -> str:
        """批量翻译 API 调用。

        Args:
            batch: 待翻译的文本批次
            tgt_name: 目标语言名称
            cancelled_callback: 取消检查回调
            error_hint: 错误提示（用于纠正场景）

        Returns:
            LLM 响应文本
        """
        prompt = self._get_batch_prompt(tgt_name, error_hint)
        input_json = json.dumps(
            {str(i): t for i, t in enumerate(batch)},
            ensure_ascii=False
        )
        return self._call_llm(prompt, input_json, cancelled_callback)

    def _translate_single_llm(
        self,
        text: str,
        tgt_name: str,
        cancelled_callback: Optional[Callable] = None,
    ) -> str:
        """单句 LLM 翻译（共用 _call_llm 的重试逻辑）。

        Args:
            text: 待翻译文本
            tgt_name: 目标语言名称
            cancelled_callback: 取消检查回调

        Returns:
            翻译结果文本
        """
        prompt = self._get_single_prompt(tgt_name)
        response = self._call_llm(prompt, text, cancelled_callback)
        return response.strip() if response else text

    def _is_non_retryable_error(self, error_str: str) -> bool:
        """检查是否为不可重试的错误。"""
        error_lower = error_str.lower()

        # 鉴权错误
        if any(
            kw in error_lower
            for kw in ["401", "unauthorized", "invalid api key", "api key", "expired"]
        ):
            return True

        # 模型不存在
        if any(
            kw in error_lower
            for kw in ["model not found", "does not exist", "invalid model"]
        ):
            return True

        # 配额用尽
        if any(kw in error_lower for kw in ["insufficient_quota", "quota"]):
            return True

        return False

    # ==================== 辅助方法 ====================

    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, str]]:
        """解析 JSON 响应。

        Args:
            response_text: LLM 返回的文本

        Returns:
            解析后的字典，如果解析失败返回 None
        """
        if not response_text:
            return None

        # 尝试直接解析
        try:
            result = json.loads(response_text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 代码块
        import re

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        # 尝试找到 JSON 对象
        brace_start = response_text.find("{")
        brace_end = response_text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            try:
                result = json.loads(response_text[brace_start : brace_end + 1])
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        return None

    def _validate_keys(self, result: Dict[str, str], batch: List[str]) -> bool:
        """验证结果键是否与输入匹配。

        Args:
            result: 解析后的结果字典
            batch: 原始输入批次

        Returns:
            True 如果键完全匹配，False 否则
        """
        expected_keys = {str(i) for i in range(len(batch))}
        result_keys = set(result.keys())
        return expected_keys == result_keys

    def _get_batch_prompt(self, target_language: str, error_hint: Optional[str] = None) -> str:
        """获取批量翻译 prompt。"""
        from ..utils.prompt_loader import get_prompt

        custom_instructions = error_hint if error_hint else ""

        return get_prompt(
            "translate/batch",
            target_language=target_language,
            custom_instructions=custom_instructions,
        )

    def _get_single_prompt(self, target_language: str) -> str:
        """获取单句翻译 prompt。"""
        from ..utils.prompt_loader import get_prompt

        return get_prompt(
            "translate/single",
            source_language="自动检测",
            target_language=target_language,
            prev_text="（无）",
            current_text="（待翻译）",
            next_text="（无）",
            custom_instructions="",
        )

    def get_language_name(self, lang_code: str) -> str:
        """获取语言的可读名称。"""
        return LANGUAGE_NAMES.get(lang_code, lang_code)
