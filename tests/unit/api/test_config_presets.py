"""ollama preset 暴露与可配置性测试。"""

import pytest
from fastapi.testclient import TestClient

from mediafactory.api.main import get_app

pytestmark = [pytest.mark.unit]


@pytest.fixture
def client():
    return TestClient(get_app())


def test_presets_include_ollama(client):
    presets = client.get("/api/config/llm/presets").json()
    assert "ollama" in presets
    assert presets["ollama"]["display_name"] == "Ollama (Local)"
    assert presets["ollama"]["base_url"] == "http://localhost:11434/v1"
