"""translate_detailed：失败位置暴露、空串映射、TermDict 传递。"""

import json

import pytest

from mediafactory.llm.base import TranslationRequest
from mediafactory.llm.openai_compatible_backend import OpenAICompatibleBackend
from mediafactory.llm.term_memory import TermDict

pytestmark = [pytest.mark.unit]


class _FakeClient:
    """按顺序返回预设响应。"""

    def __init__(self, contents: list[str]):
        self._contents = list(contents)
        self.calls: list[dict] = []
        self.chat = type("Chat", (), {})()
        self.chat.completions = type("Completions", (), {})()
        self.chat.completions.create = self._create

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        content = self._contents.pop(0) if self._contents else ""
        message = type("M", (), {"content": content})()
        choice = type("C", (), {"message": message})()
        return type("Resp", (), {"choices": [choice]})()


def _backend(responses: list[str], **kwargs) -> OpenAICompatibleBackend:
    backend = OpenAICompatibleBackend(
        base_url="http://x/v1", api_key="k", model="m", **kwargs
    )
    backend._client = _FakeClient(responses)
    return backend


def _request(texts: list[str]) -> TranslationRequest:
    return TranslationRequest(text=texts, src_lang="en", tgt_lang="zh")


def test_failed_indices_exposed_on_unparseable_batch():
    # split_threshold 必须 >1：阈值为 1 且批大小为 1 时二分会无限递归（half=0）
    backend = _backend(["not json at all"], batch_size=1, split_threshold=2)
    detailed = backend.translate_detailed(_request(["hello"]))
    assert detailed.result.success is True
    assert detailed.failed_indices == [0]
    # 单文本输入保持旧契约：translated_text 为标量 str
    assert detailed.result.translated_text == "hello"


def test_multi_batch_partial_failure():
    ok = json.dumps({"0": "译B"}, ensure_ascii=False)
    # 每个成功批次会额外触发一次 _extract_terms 调用（R2 行为），需多备响应
    backend = _backend(["bad json", ok, ok, ok], batch_size=1, split_threshold=2)
    detailed = backend.translate_detailed(_request(["A", "B"]))
    assert detailed.failed_indices == [0]
    assert detailed.result.translated_text == ["A", "译B"]


def test_failed_indices_map_through_empty_strings():
    bad = "bad json"
    backend = _backend([bad, bad], batch_size=1, split_threshold=2)
    detailed = backend.translate_detailed(_request(["hello", "", "world"]))
    # 非空空间失败 [0,1] → 最终空间 [0,2]（跳过空串位 1）
    assert detailed.failed_indices == [0, 2]
    assert detailed.result.translated_text == ["hello", "", "world"]


def test_term_dict_passed_in_is_returned_same_instance():
    backend = _backend([json.dumps({"0": "你好"}, ensure_ascii=False)])
    td = TermDict()
    td.register_user({"hello": "你好"})
    detailed = backend.translate_detailed(_request(["hello"]), term_dict=td)
    assert detailed.term_dict is td


def test_term_dict_created_from_user_terms_when_absent():
    backend = _backend([json.dumps({"0": "你好"}, ensure_ascii=False)])
    detailed = backend.translate_detailed(
        TranslationRequest(
            text=["hello"], src_lang="en", tgt_lang="zh", user_terms={"hello": "你好"}
        )
    )
    assert detailed.term_dict is not None
    assert "hello" in detailed.term_dict.dump()


def test_translate_wrapper_unchanged():
    backend = _backend([json.dumps({"0": "你好"}, ensure_ascii=False)])
    result = backend.translate(_request(["hello"]))
    assert result.success is True
    assert result.translated_text == "你好"


def test_llm_response_log_reflects_real_success():
    """全部批次失败时日志不得打 SUCCESS（冒烟 00:32:45 假 SUCCESS 的教训）。"""
    from loguru import logger

    records: list = []
    sink_id = logger.add(lambda m: records.append(m), level="INFO")
    try:
        backend = _backend(["not json at all"], batch_size=1, split_threshold=2)
        backend.translate_detailed(_request(["hello"]))
    finally:
        logger.remove(sink_id)

    responses = [
        r for r in records if "LLM Response" in (r.record["message"] if hasattr(r, "record") else str(r))
    ]
    assert responses, "expected an LLM Response log line"
    assert "FAILED" in str(responses[-1])


def test_llm_response_log_success_on_clean_run():
    from loguru import logger

    ok = json.dumps({"0": "译"}, ensure_ascii=False)
    records: list = []
    sink_id = logger.add(lambda m: records.append(m), level="INFO")
    try:
        backend = _backend([ok, ok], batch_size=1, split_threshold=2)
        backend.translate_detailed(_request(["hello"]))
    finally:
        logger.remove(sink_id)

    responses = [
        r for r in records if "LLM Response" in (r.record["message"] if hasattr(r, "record") else str(r))
    ]
    assert responses, "expected an LLM Response log line"
    assert "SUCCESS" in str(responses[-1])
