"""LLM 翻译后端基类和数据类型。

此模块定义了翻译后端的抽象接口和请求数据类型。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from mediafactory.core.progress_protocol import ProgressCallback


# ============================================================================
# 辅助函数
# ============================================================================


def prepare_texts(texts: List[str]) -> Tuple[List[str], List[int]]:
    """准备文本：过滤空字符串，记录空字符串位置。

    Args:
        texts: 原始文本列表

    Returns:
        (非空文本列表, 空字符串的索引列表)
    """
    non_empty_texts = []
    empty_indices = []

    for i, text in enumerate(texts):
        if text.strip():
            non_empty_texts.append(text)
        else:
            empty_indices.append(i)

    return non_empty_texts, empty_indices


def restore_result(
    translated_non_empty: List[str], empty_indices: List[int], original_count: int
) -> List[str]:
    """将翻译结果与空字符串合并，恢复原始结构。

    Args:
        translated_non_empty: 非空文本的翻译结果
        empty_indices: 空字符串的原始索引
        original_count: 原始文本总数

    Returns:
        完整的翻译结果列表（包含空字符串）
    """
    result = []
    non_empty_idx = 0

    for i in range(original_count):
        if i in empty_indices:
            result.append("")  # 恢复空字符串
        else:
            result.append(translated_non_empty[non_empty_idx])
            non_empty_idx += 1

    return result


@dataclass
class TranslationRequest:
    """翻译请求数据类。

    Attributes:
        text: 待翻译的文本（单个字符串或文本列表）
        src_lang: 源语言代码（如 "en", "zh", "ja" 等）
        tgt_lang: 目标语言代码
        cancelled_callback: 取消检查回调函数，返回 True 表示已取消
        progress_callback: 进度回调，用于报告翻译进度
    """

    text: str | list[str]
    src_lang: str
    tgt_lang: str
    cancelled_callback: Optional[Callable[[], bool]] = field(default=None, repr=False)
    progress_callback: Optional["ProgressCallback"] = field(default=None, repr=False)


@dataclass
class TranslationResult:
    """翻译结果数据类。

    Attributes:
        translated_text: 翻译后的文本（单个字符串或字符串列表）
        backend_used: 使用的后端名称
        success: 是否成功
        error_message: 错误信息（如果失败）
    """

    translated_text: str | list[str]
    backend_used: str
    success: bool = True
    error_message: str = ""


class TranslationBackend(ABC):
    """翻译后端抽象基类。

    所有翻译后端（本地模型、API 调用等）都必须实现此接口。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """返回后端名称。"""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用（如 API Key 是否配置）。"""

    @abstractmethod
    def translate(self, request: TranslationRequest) -> TranslationResult:
        """执行翻译。

        Args:
            request: 翻译请求对象

        Returns:
            翻译结果对象
        """

    def get_language_name(self, lang_code: str) -> str:
        """获取语言的可读名称。

        Args:
            lang_code: 语言代码

        Returns:
            语言名称（如 "English", "中文" 等）
        """
        # 默认实现，子类可以覆盖以提供更准确的名称
        return lang_code

    def test_connection(self) -> dict:
        """测试 API 连接是否正常。

        发送一个简单的测试请求验证 API Key 是否有效。

        Returns:
            包含测试结果的字典:
            - success: bool - 测试是否成功
            - message: str - 详细消息
            - error: str | None - 错误信息（如果失败）
        """
        # 默认实现：后端未实现连通性测试
        return {
            "success": False,
            "message": f"{self.name} 后端未实现连通性测试",
            "error": "Not implemented",
        }

    # ========================================================================
    # 通用辅助方法（减少子类重复代码）
    # ========================================================================

    def _normalize_texts(self, text: str | list[str]) -> list[str]:
        """统一文本处理逻辑：将 str 转换为 list[str]。

        Args:
            text: 输入文本（字符串或字符串列表）

        Returns:
            字符串列表
        """
        if isinstance(text, str):
            return [text]
        return text

    def _handle_empty_results(
        self, results: list[str], request: TranslationRequest
    ) -> TranslationResult | None:
        """统一空结果处理逻辑。

        Args:
            results: 翻译结果列表
            request: 原始翻译请求

        Returns:
            如果所有结果为空，返回失败的 TranslationResult；否则返回 None
        """
        if all(result.strip() == "" for result in results):
            return TranslationResult(
                translated_text=(
                    request.text if isinstance(request.text, str) else request.text
                ),
                backend_used=self.name,
                success=False,
                error_message="所有翻译结果均为空，请检查配置",
            )
        return None

    def _validate_connection_test_prerequisites(
        self, api_key: str | None, base_url: str | None, package_name: str
    ) -> dict | None:
        """验证连接测试的前提条件（API Key 和 Base URL）。

        Args:
            api_key: API Key
            base_url: API Base URL
            package_name: 需要安装的 Python 包名（用于错误提示）

        Returns:
            如果验证失败，返回错误字典；否则返回 None
        """
        if not api_key:
            return {
                "success": False,
                "message": "API Key is required",
                "error": "API Key is empty",
            }

        if not base_url:
            return {
                "success": False,
                "message": "Base URL is required",
                "error": "Base URL is empty",
            }

        return None

    def _create_translation_result(
        self,
        result: List[str],
        original_texts: List[str],
        success: bool = True,
        error_message: str = "",
    ) -> TranslationResult:
        """创建翻译结果（统一处理单句/多句输出格式）。

        Args:
            result: 翻译结果列表
            original_texts: 原始文本列表
            success: 是否成功
            error_message: 错误信息

        Returns:
            TranslationResult 对象
        """
        if len(original_texts) == 1:
            return TranslationResult(
                translated_text=result[0] if result else original_texts[0],
                backend_used=self.name,
                success=success,
                error_message=error_message,
            )
        else:
            return TranslationResult(
                translated_text=result if success else original_texts,
                backend_used=self.name,
                success=success,
                error_message=error_message,
            )
