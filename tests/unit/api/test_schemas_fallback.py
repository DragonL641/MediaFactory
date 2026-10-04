"""fallback_model 校验测试。"""

import pytest
from pydantic import ValidationError

from mediafactory.api.schemas import TaskConfig, TaskType, TranslateRequest

pytestmark = [pytest.mark.unit]


def test_task_config_fallback_model_default_none():
    config = TaskConfig(task_type=TaskType.TRANSLATE, input_path="a.srt")
    assert config.fallback_model is None


def test_task_config_fallback_model_accepts_name():
    config = TaskConfig(
        task_type=TaskType.TRANSLATE, input_path="a.srt", fallback_model="qwen2.5:7b"
    )
    assert config.fallback_model == "qwen2.5:7b"


@pytest.mark.parametrize("bad", ["", "   ", "x" * 201])
def test_task_config_fallback_model_rejects_blank_and_overlong(bad):
    with pytest.raises(ValidationError):
        TaskConfig(task_type=TaskType.TRANSLATE, input_path="a.srt", fallback_model=bad)


def test_translate_request_fallback_model():
    # 前端提交 snake_case（与 terminology/use_llm 同风格）
    request = TranslateRequest(text="hi", use_llm=True, fallback_model="qwen2.5:7b")
    assert request.fallback_model == "qwen2.5:7b"
