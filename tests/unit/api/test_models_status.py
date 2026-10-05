"""GET /api/models/status 的 face_restoration 节契约"""

import pytest

pytestmark = [pytest.mark.unit]


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from mediafactory.api.main import create_app

    return TestClient(create_app())


class TestModelsStatusFaceRestoration:
    def test_status_contains_face_restoration_section(self, client):
        resp = client.get("/api/models/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "face_restoration" in body
        section = body["face_restoration"]
        assert section["name"] == "CodeFormer"
        ids = [m["id"] for m in section["models"]]
        assert ids == ["CodeFormer", "facexlib-detection", "facexlib-parsing"]
        for m in section["models"]:
            assert {"name", "purpose", "size", "memory", "downloaded", "complete"} <= set(m)
