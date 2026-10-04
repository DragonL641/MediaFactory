"""TaskConfig.terminology 校验测试。"""

import pytest
from pydantic import ValidationError

from mediafactory.api.schemas import TaskConfig, TaskType

pytestmark = [pytest.mark.unit]


def test_terminology_default_none():
    cfg = TaskConfig(task_type=TaskType.SUBTITLE, input_path="v.mp4")
    assert cfg.terminology is None


def test_terminology_valid_dict_accepted():
    cfg = TaskConfig(
        task_type=TaskType.SUBTITLE,
        input_path="v.mp4",
        terminology={"Kubernetes": "K8s"},
    )
    assert cfg.terminology == {"Kubernetes": "K8s"}


def test_terminology_over_200_entries_rejected():
    big = {f"term{i}": f"词{i}" for i in range(201)}
    with pytest.raises(ValidationError):
        TaskConfig(task_type=TaskType.SUBTITLE, input_path="v.mp4", terminology=big)


def test_terminology_overlong_value_rejected():
    with pytest.raises(ValidationError):
        TaskConfig(
            task_type=TaskType.SUBTITLE,
            input_path="v.mp4",
            terminology={"Kubernetes": "字" * 201},
        )
