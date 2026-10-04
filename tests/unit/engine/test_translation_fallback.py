"""TranslationEngine 兜底编排测试（Ollama client 全 mock）。"""

import pytest

from mediafactory.engine.translation import TranslationEngine
from mediafactory.llm.base import (
    DetailedTranslationResult,
    TranslationRequest,
    TranslationResult,
)
from mediafactory.llm.term_memory import TermDict

pytestmark = [pytest.mark.unit]


def _detailed(translations: list[str], failed: list[int], success: bool = True):
    return DetailedTranslationResult(
        result=TranslationResult(
            translated_text=translations, backend_used="fake", success=success
        ),
        failed_indices=failed,
        term_dict=None,
    )


class _FakeBackend:
    """可编程后端：依次返回预置 DetailedTranslationResult。"""

    name = "fake"
    is_available = True

    def __init__(self, results, base_url: str = ""):
        self._results = list(results)
        self.detailed_calls: list[TranslationRequest] = []
        self.detailed_term_dicts: list = []
        self._base_url = base_url

    def get_model_name(self) -> str:
        return "fake-model"

    def translate_detailed(self, request, term_dict=None):
        self.detailed_calls.append(request)
        self.detailed_term_dicts.append(term_dict)
        return self._results.pop(0)

    def translate(self, request):
        return self.translate_detailed(request).result


class _FakeOllamaClient:
    def __init__(self, available: bool = True, installed: bool = True):
        self._available = available
        self._installed = installed
        self.unloaded: list[str] = []

    def is_available_sync(self) -> bool:
        return self._available

    def is_model_installed_sync(self, name: str) -> bool:
        return self._installed

    def unload_model_sync(self, name: str) -> None:
        self.unloaded.append(name)


@pytest.fixture
def patch_ollama(monkeypatch):
    def _patch(client: _FakeOllamaClient):
        monkeypatch.setattr(
            "mediafactory.llm.ollama_client.get_ollama_client", lambda: client
        )
        return client

    return _patch


def _patch_fallback_class(monkeypatch, fallback: _FakeBackend):
    """engine 探测通过后会自行 new OpenAICompatibleBackend——替换为 fake。"""
    monkeypatch.setattr(
        "mediafactory.llm.openai_compatible_backend.OpenAICompatibleBackend",
        lambda **kw: fallback,
    )


def test_fallback_used_on_primary_failure(patch_ollama, monkeypatch):
    ollama = patch_ollama(_FakeOllamaClient())
    primary = _FakeBackend([_detailed(["原文1", "原文2"], failed=[1])])
    fallback = _FakeBackend([_detailed(["译文2"], failed=[])])
    _patch_fallback_class(monkeypatch, fallback)

    engine = TranslationEngine(
        llm_backend=primary, use_llm_backend=True, fallback_model="qwen2.5:7b"
    )
    assert engine._fallback_backend is fallback  # 探测通过后构建

    outcome = engine.translate_texts(["t1", "t2"], "en", "zh")
    assert outcome.translations == ["原文1", "译文2"]
    assert outcome.stats == {"total": 2, "remote": 1, "fallback": 1, "failed": 0}
    assert ollama.unloaded == ["qwen2.5:7b"]


def test_no_fallback_when_not_configured(patch_ollama):
    patch_ollama(_FakeOllamaClient())
    primary = _FakeBackend([_detailed(["原文1"], failed=[0])])
    engine = TranslationEngine(llm_backend=primary, use_llm_backend=True)

    outcome = engine.translate_texts(["t1"], "en", "zh")
    assert outcome.translations == ["原文1"]
    assert outcome.stats == {"total": 1, "remote": 0, "fallback": 0, "failed": 1}


def test_single_direction_no_fallback_for_local_primary(patch_ollama):
    patch_ollama(_FakeOllamaClient())
    primary = _FakeBackend(
        [_detailed(["原文1"], failed=[0])],
        base_url="http://localhost:11434/v1",
    )
    engine = TranslationEngine(
        llm_backend=primary, use_llm_backend=True, fallback_model="qwen2.5:7b"
    )
    assert engine._fallback_backend is None  # 主渠道是 Ollama → 不构建兜底


def test_probe_failure_disables_fallback(patch_ollama):
    patch_ollama(_FakeOllamaClient(available=False))
    primary = _FakeBackend([_detailed(["原文1"], failed=[0])])
    engine = TranslationEngine(
        llm_backend=primary, use_llm_backend=True, fallback_model="qwen2.5:7b"
    )
    assert engine._fallback_backend is None

    outcome = engine.translate_texts(["t1"], "en", "zh")
    assert outcome.translations == ["原文1"]
    assert outcome.stats["failed"] == 1


def test_fallback_failure_keeps_original(patch_ollama, monkeypatch):
    patch_ollama(_FakeOllamaClient())
    primary = _FakeBackend([_detailed(["原文1", "原文2"], failed=[0, 1])])
    # 兜底契约：全长列表，失败位保留原文
    fallback = _FakeBackend([_detailed(["译文1", "原文2"], failed=[1])])
    _patch_fallback_class(monkeypatch, fallback)
    engine = TranslationEngine(
        llm_backend=primary, use_llm_backend=True, fallback_model="qwen2.5:7b"
    )

    outcome = engine.translate_texts(["t1", "t2"], "en", "zh")
    assert outcome.translations == ["译文1", "原文2"]
    assert outcome.stats == {"total": 2, "remote": 0, "fallback": 1, "failed": 1}


def test_fallback_receives_failed_texts_only(patch_ollama, monkeypatch):
    patch_ollama(_FakeOllamaClient())
    primary = _FakeBackend([_detailed(["原文1", "原文2", "原文3"], failed=[1, 2])])
    fallback = _FakeBackend([_detailed(["译文2", "译文3"], failed=[])])
    _patch_fallback_class(monkeypatch, fallback)
    engine = TranslationEngine(
        llm_backend=primary, use_llm_backend=True, fallback_model="qwen2.5:7b"
    )

    outcome = engine.translate_texts(["t1", "t2", "t3"], "en", "zh")
    # 兜底只收失败句的源文（按原序），不收成功句
    assert fallback.detailed_calls[0].text == ["t2", "t3"]
    assert outcome.translations == ["原文1", "译文2", "译文3"]
    assert outcome.stats["fallback"] == 2


def test_term_dict_shared_with_fallback(patch_ollama, monkeypatch):
    shared = TermDict()
    patch_ollama(_FakeOllamaClient())
    primary = _FakeBackend(
        [
            DetailedTranslationResult(
                result=TranslationResult(
                    translated_text=["原文1"], backend_used="fake", success=True
                ),
                failed_indices=[0],
                term_dict=shared,
            )
        ]
    )
    fallback = _FakeBackend([_detailed(["译文1"], failed=[])])
    _patch_fallback_class(monkeypatch, fallback)
    engine = TranslationEngine(
        llm_backend=primary, use_llm_backend=True, fallback_model="qwen2.5:7b"
    )

    engine.translate_texts(["t1"], "en", "zh")
    # 主链学到的 TermDict 原样传给兜底链（术语一致性）
    assert fallback.detailed_term_dicts[0] is shared


def test_primary_hard_failure_raises(patch_ollama):
    patch_ollama(_FakeOllamaClient())
    primary = _FakeBackend([_detailed(["原文1"], failed=[], success=False)])
    engine = TranslationEngine(llm_backend=primary, use_llm_backend=True)

    with pytest.raises(Exception):
        engine.translate_texts(["t1"], "en", "zh")


def test_no_unload_when_local_not_used(patch_ollama):
    ollama = patch_ollama(_FakeOllamaClient())
    primary = _FakeBackend([_detailed(["译文1"], failed=[])])
    engine = TranslationEngine(
        llm_backend=primary, use_llm_backend=True, fallback_model="qwen2.5:7b"
    )

    engine.translate_texts(["t1"], "en", "zh")
    assert ollama.unloaded == []  # 兜底未触发 → 模型从未加载 → 不卸载


def test_single_text_scalar_normalized(patch_ollama):
    """单文本输入 translate_detailed 返回标量 str——必须归一为 list（R2 教训）。"""
    patch_ollama(_FakeOllamaClient())
    primary = _FakeBackend(
        [
            DetailedTranslationResult(
                result=TranslationResult(
                    translated_text="译文1",  # 标量！
                    backend_used="fake",
                    success=True,
                ),
                failed_indices=[],
                term_dict=None,
            )
        ]
    )
    engine = TranslationEngine(llm_backend=primary, use_llm_backend=True)

    outcome = engine.translate_texts(["t1"], "en", "zh")
    assert outcome.translations == ["译文1"]
