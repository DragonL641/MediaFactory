"""FACE_RESTORATION 注册表条目契约"""

import inspect

import pytest

pytestmark = [pytest.mark.unit]


class TestFaceRestorationRegistry:
    def test_three_entries_registered(self):
        from mediafactory.models.model_registry import (
            FACE_MODEL_IDS,
            MODEL_REGISTRY,
            DownloadMode,
            ModelType,
        )

        assert len(FACE_MODEL_IDS) == 3
        for mid in FACE_MODEL_IDS:
            info = MODEL_REGISTRY[mid]
            assert info.model_type == ModelType.FACE_RESTORATION
            assert info.download_mode == DownloadMode.FILE
            assert info.huggingface_filename
            assert info.model_size_mb > 0

    def test_codeformer_license_is_s_lab(self):
        from mediafactory.models.model_registry import MODEL_REGISTRY, LicenseType

        assert MODEL_REGISTRY["CodeFormer"].license == LicenseType.S_LAB_1_0

    def test_facexlib_entries_license_commercial_ok(self):
        """facexlib（Apache-2.0）条目不得挂 S-Lab——许可追踪是注册表的存在目的"""
        from mediafactory.models.model_registry import (
            MODEL_REGISTRY,
            LicenseType,
        )

        assert MODEL_REGISTRY["facexlib-detection"].license != LicenseType.S_LAB_1_0
        assert MODEL_REGISTRY["facexlib-parsing"].license != LicenseType.S_LAB_1_0

    def test_weights_match_spike_verified_sources(self):
        """条目的 repo/filename 与 spike 实测下载源一致"""
        from mediafactory.models.model_registry import MODEL_REGISTRY

        assert (
            MODEL_REGISTRY["CodeFormer"].huggingface_repo == "ziixzz/codeformer-v0.1.0.pth"
        )
        assert MODEL_REGISTRY["CodeFormer"].huggingface_filename == "codeformer-v0.1.0.pth"
        assert MODEL_REGISTRY["facexlib-detection"].huggingface_repo == "leonelhs/facexlib"
        assert (
            MODEL_REGISTRY["facexlib-detection"].huggingface_filename
            == "detection_Resnet50_Final.pth"
        )
        assert MODEL_REGISTRY["facexlib-parsing"].huggingface_repo == "leonelhs/facexlib"
        assert (
            MODEL_REGISTRY["facexlib-parsing"].huggingface_filename == "parsing_parsenet.pth"
        )

    def test_not_in_enhancement_gate_types(self):
        """FACE_RESTORATION 不得混入 enhancement_ready 的全量必装集合"""
        from mediafactory.services.models import ModelStatusService

        src = inspect.getsource(ModelStatusService.get_readiness)
        assert "FACE_RESTORATION" not in src
