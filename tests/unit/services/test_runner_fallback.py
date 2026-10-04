"""runner 的 fallback_model 透传测试。"""

import pytest

from mediafactory.api.schemas import TaskConfig, TaskType
from mediafactory.services import runner

pytestmark = [pytest.mark.unit]


def test_select_translation_engine_passes_fallback_model(monkeypatch):
    captured: dict = {}

    class _FakeBackend:
        is_available = True

    def _fake_engine(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "mediafactory.services.runner.initialize_llm_backend",
        lambda *a, **k: _FakeBackend(),
    )
    monkeypatch.setattr("mediafactory.services.runner.TranslationEngine", _fake_engine)

    config = TaskConfig(
        task_type=TaskType.TRANSLATE,
        input_path="a.txt",
        input_text="hi",
        use_llm=True,
        fallback_model="qwen2.5:7b",
    )
    runner._select_translation_engine(config)
    assert captured["fallback_model"] == "qwen2.5:7b"
    assert captured["user_terms"] is None
