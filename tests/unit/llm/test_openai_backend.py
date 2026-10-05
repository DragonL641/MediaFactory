"""OpenAICompatibleBackend 术语记忆集成测试（mock LLM client）。"""

import pytest

from mediafactory.llm import OpenAICompatibleBackend
from mediafactory.llm.base import TranslationRequest

pytestmark = [pytest.mark.unit]


class FakeResponse:
    def __init__(self, content: str):
        self.choices = [
            type("C", (), {"message": type("M", (), {"content": content})()})()
        ]


class FakeClient:
    """按顺序返回预设响应，并记录全部请求。"""

    def __init__(self, contents: list[str]):
        self._contents = list(contents)
        self.calls: list[dict] = []
        self.chat = type("Chat", (), {})()
        self.chat.completions = type("Completions", (), {})()
        self.chat.completions.create = self._create

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self._contents.pop(0) if self._contents else "{}"
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item)


def make_backend(contents: list[str]) -> tuple[OpenAICompatibleBackend, FakeClient]:
    backend = OpenAICompatibleBackend(
        api_key="test", base_url="https://api.test.com/v1", model="m", batch_size=40
    )
    client = FakeClient(contents)
    backend._client = client
    return backend, client


def _msg_content(call: dict) -> str:
    return "\n".join(m["content"] for m in call["messages"])


class TestNullValueValidation:
    def test_null_value_never_reaches_translations(self):
        """M9 回归：JSON null 值不得以字面量 None 进译文，应走降级链。

        批 1 返回 {"0": "你好", "1": null} → 验证失败 → 二分为单句重试；
        单句再给 null → 该句按失败处理（保留原文，由上层 failed 通道接管）。
        """
        backend, client = make_backend(['{"0": "你好", "1": null}', '{"0": "世界好"}'])
        request = TranslationRequest(
            text=["Hello", "World"],
            src_lang="en",
            tgt_lang="zh",
        )
        result = backend.translate(request)
        texts = result.translated_text
        joined = "".join(texts) if isinstance(texts, list) else str(texts)
        assert "None" not in joined  # 字面量 None 绝不出现

    def test_numeric_value_never_reaches_translations(self):
        """数字值同样不进译文（走失败链保留原文或重试）"""
        backend, client = make_backend(['{"0": 123}'])
        request = TranslationRequest(
            text=["Hello"],
            src_lang="en",
            tgt_lang="zh",
        )
        result = backend.translate(request)
        texts = result.translated_text
        joined = "".join(texts) if isinstance(texts, list) else str(texts)
        assert "None" not in joined


class TestInjection:
    def test_user_terms_injected_into_translation_prompt(self):
        backend, client = make_backend(['{"0": "你好 K8s 世界"}'])
        request = TranslationRequest(
            text=["Hello Kubernetes world"],
            src_lang="en",
            tgt_lang="zh",
            user_terms={"Kubernetes": "K8s"},
        )
        backend.translate(request)
        assert "# Terminology (must follow)" in _msg_content(client.calls[0])
        assert "- kubernetes → K8s" in _msg_content(client.calls[0])

    def test_no_terms_no_injection(self):
        backend, client = make_backend(['{"0": "你好"}'])
        request = TranslationRequest(text=["Hello"], src_lang="en", tgt_lang="zh")
        backend.translate(request)
        assert "# Terminology" not in _msg_content(client.calls[0])


class TestExtractionAndConflict:
    def _two_batch_setup(self, contents: list[str]):
        backend, client = make_backend(contents)
        backend._batch_size = 1  # 强制两批
        request = TranslationRequest(
            text=["Hello Kubernetes world", "Kubernetes is great"],
            src_lang="en",
            tgt_lang="zh",
        )
        return backend, client, request

    def test_cross_batch_consistency(self):
        # 序列：批1翻译 → 批1提取 → 批2翻译 → 批2提取
        contents = [
            '{"0": "你好 K8s 世界"}',  # 批1翻译
            '{"terms": {"Kubernetes": "K8s"}}',  # 批1提取
            '{"0": "K8s 很棒"}',  # 批2翻译（带注入）
            '{"terms": {}}',  # 批2提取
        ]
        backend, client, request = self._two_batch_setup(contents)
        result = backend.translate(request)
        assert result.success
        # 第二次翻译请求必须包含批1学到的术语注入
        assert "# Terminology (must follow)" in _msg_content(client.calls[2])
        assert "- kubernetes → K8s" in _msg_content(client.calls[2])

    def test_conflict_replaced_with_dict_translation(self):
        # user 种子 K8s；批1模型无视注入翻成"库伯内提斯"，提取暴露冲突 → 替换
        contents = [
            '{"0": "这是 库伯内提斯"}',  # 批1翻译
            '{"terms": {"Kubernetes": "库伯内提斯"}}',  # 批1提取暴露冲突
        ]
        backend, client = make_backend(contents)
        request = TranslationRequest(
            text=["This is Kubernetes"],
            src_lang="en",
            tgt_lang="zh",
            user_terms={"Kubernetes": "K8s"},
        )
        result = backend.translate(request)
        assert result.success
        assert (
            result.translated_text == "这是 K8s"
        )  # 已被替换回 dict 译法（单句返回 str）

    def test_extraction_failure_is_silent(self):
        contents = [
            '{"0": "你好"}',  # 翻译成功
            "not valid json at all",  # 提取返回垃圾
        ]
        backend, client = make_backend(contents)
        request = TranslationRequest(text=["Hello"], src_lang="en", tgt_lang="zh")
        result = backend.translate(request)
        assert result.success
        assert result.translated_text == "你好"

    def test_extraction_candidates_capped_at_five(self):
        import json as _json

        many = {f"term{i}": f"词{i}" for i in range(10)}
        contents = [
            '{"0": "你好"}',
            _json.dumps({"terms": many}),
        ]
        backend, client = make_backend(contents)
        request = TranslationRequest(text=["Hello"], src_lang="en", tgt_lang="zh")
        backend.translate(request)
        assert len(backend._cap_candidates(many)) == 5


class TestContentFilterRecursiveInjection:
    def test_term_dict_survives_content_filter_bisect(self):
        """评审 Important：content-filter 二分递归的子批必须带术语注入。"""
        err = Exception("Error code: 1301 - content filter triggered")
        contents = [
            err,  # 批1翻译触发 content filter
            err,  # content-filter split 首层重试再次触发 → 进入递归二分
            '{"0": "子批1"}',  # 递归子批1翻译（此处必须带术语注入）
            '{"terms": {}}',  # 子批1提取
            '{"0": "子批2"}',  # 子批2翻译
            '{"terms": {}}',  # 子批2提取
        ]
        backend, client = make_backend(contents)
        backend._batch_size = 4
        backend._split_threshold = 2
        request = TranslationRequest(
            text=["Kubernetes a", "Kubernetes b", "Kubernetes c", "Kubernetes d"],
            src_lang="en",
            tgt_lang="zh",
            user_terms={"Kubernetes": "K8s"},
        )
        result = backend.translate(request)
        assert result.success
        # calls[0]=主批（抛错），calls[1]=split 首层重试（抛错），
        # calls[2]/calls[3]=递归子批的翻译与提取——必须带术语注入
        assert "# Terminology (must follow)" in _msg_content(client.calls[2])
        assert "# Terminology (must follow)" in _msg_content(client.calls[3])


class TestContentFilterLearnAndFix:
    def test_split_path_runs_learn_and_fix(self):
        """content-filter 降级批产物必须与正常批同权：过术语提取+冲突替换。"""
        err = Exception("Error code: 1301 - content filter triggered")
        contents = [
            err,  # 主批(2句)触发 content filter
            '{"0": "K8s 集群"}',  # split 重试整批(2句)：缺 "1" → 校验失败 → 内部二分
            '{"0": "K8s 集群"}',  # 左(1句)成功（模型未守用户术语）
            '{"nothing": 1}',  # 右(1句)校验失败 → 保留原文
            # 降级批的提取调用：走 _learn_and_fix 则学到冲突并替换回 "K8s"
            '{"terms": {"Kubernetes": "K8s 集群"}}',
        ]
        backend, client = make_backend(contents)
        backend._batch_size = 4
        backend._split_threshold = 2
        request = TranslationRequest(
            text=["Kubernetes a", "Kubernetes b"],
            src_lang="en",
            tgt_lang="zh",
            user_terms={"Kubernetes": "K8s"},
        )
        result = backend.translate(request)
        # 用户术语 K8s 的译法在降级批被模型写成 "K8s 集群"：
        # 走了 _learn_and_fix 就会冲突替换回 "K8s"
        assert "K8s 集群" not in result.translated_text
