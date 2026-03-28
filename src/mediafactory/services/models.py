"""
模型状态服务

提供模型状态查询和管理功能。
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mediafactory.config import get_config
from mediafactory.logging import log_info, log_error
from mediafactory.api.error_handler import sanitize_error


@dataclass
class ModelStatusInfo:
    """模型状态信息"""
    name: str
    loaded: bool = False
    available: bool = False
    enabled: bool = True


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    tier: str  # light, standard, heavy
    memory: str
    downloaded: bool = False
    loading: bool = False
    progress: float = 0.0


class ModelStatusService:
    """
    模型状态服务

    提供模型状态查询和管理功能。
    """

    def __init__(self):
        self.config = get_config()

    def get_whisper_status(self) -> ModelStatusInfo:
        """获取 Whisper 模型状态"""
        try:
            from mediafactory.models.model_download import is_model_downloaded

            available = is_model_downloaded("Systran/faster-whisper-large-v3")

            return ModelStatusInfo(
                name="faster-whisper-large-v3",
                loaded=available,
                available=available,
                enabled=True,
            )
        except Exception as e:
            log_error(f"Failed to get Whisper status: {e}")
            return ModelStatusInfo(
                name="faster-whisper-large-v3",
                loaded=False,
                available=False,
                enabled=True,
            )

    def get_translation_status(self) -> ModelStatusInfo:
        """获取翻译模型状态"""
        try:
            from mediafactory.models.model_registry import (
                get_all_translation_models,
                is_model_downloaded,
            )

            available = any(
                is_model_downloaded(m.huggingface_id)
                for m in get_all_translation_models()
            )

            return ModelStatusInfo(
                name="MADLAD-400",
                loaded=available,
                available=available,
                enabled=True,
            )
        except Exception as e:
            log_error(f"Failed to get translation status: {e}")
            return ModelStatusInfo(
                name="MADLAD-400",
                loaded=False,
                available=False,
                enabled=True,
            )

    def get_translation_model_statuses(self) -> List[Dict[str, Any]]:
        """获取所有翻译模型的状态列表"""
        from mediafactory.models.model_registry import (
            is_model_downloaded,
            is_model_complete,
            get_all_translation_models,
        )

        models = []

        for info in get_all_translation_models():
            model_id = info.huggingface_id
            downloaded = is_model_downloaded(model_id)
            complete = is_model_complete(model_id) if downloaded else False

            # 从 runtime_memory_gb 推断 tier
            memory_gb = info.runtime_memory_gb
            if memory_gb >= 16:
                tier = "heavy"
            elif memory_gb >= 6:
                tier = "standard"
            else:
                tier = "light"

            models.append({
                "id": model_id,
                "name": info.display_name,
                "tier": tier,
                "memory": f"~{info.runtime_memory_gb:.0f}GB",
                "size": f"~{info.model_size_mb // 1024} GB",
                "downloaded": downloaded,
                "complete": complete,
            })

        return models

    def get_llm_status(self) -> ModelStatusInfo:
        """获取 LLM API 状态"""
        try:
            oa_config = getattr(self.config, 'openai_compatible', None)
            current_preset = oa_config.current_preset if oa_config else None

            # 检查是否配置了 API key
            available = False
            if current_preset and oa_config:
                preset_config = oa_config.get_preset_config(current_preset)
                api_key = getattr(preset_config, 'api_key', '')
                available = bool(api_key and api_key != "sk-xxx")

            return ModelStatusInfo(
                name=current_preset or "LLM API",
                loaded=available,
                available=available,
                enabled=True,
            )
        except Exception as e:
            log_error(f"Failed to get LLM status: {e}")
            return ModelStatusInfo(
                name="LLM API",
                loaded=False,
                available=False,
                enabled=True,
            )

    def get_llm_config(self) -> Optional[Dict[str, Any]]:
        """获取 LLM 配置"""
        try:
            oa_config = getattr(self.config, 'openai_compatible', None)
            llm_config = getattr(self.config, 'llm_api', None)
            if not oa_config:
                return None

            return {
                "current_preset": oa_config.current_preset,
                "timeout": llm_config.timeout if llm_config else 30,
                "max_retries": llm_config.max_retries if llm_config else 3,
            }
        except Exception:
            return None

    async def test_llm_connection(self, preset: str) -> Dict[str, Any]:
        """
        测试 LLM 连接

        Args:
            preset: 预设名称

        Returns:
            测试结果
        """
        try:
            from mediafactory.llm import initialize_llm_backend

            # 跳过可用性检查，允许测试未完全配置的后端
            backend = initialize_llm_backend(
                self.config, preset=preset, skip_availability_check=True
            )

            if backend is None:
                return {
                    "success": False,
                    "error": "Failed to initialize LLM backend",
                }

            start_time = time.time()
            result = backend.test_connection()
            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "success": result.get("success", False),
                "latency_ms": latency_ms,
                "message": result.get("message", ""),
                "error": result.get("error"),
            }
        except Exception as e:
            return {
                "success": False,
                "error": sanitize_error(e),
            }

    async def test_all_llm_connections(self) -> Dict[str, Dict[str, Any]]:
        """测试所有 LLM 预设连接"""
        results = {}

        try:
            llm_config = getattr(self.config, 'llm_api', None)
            if not llm_config:
                return {"error": "LLM config not found"}

            presets = llm_config.presets or {}
            for preset_name in presets.keys():
                results[preset_name] = await self.test_llm_connection(preset_name)

        except Exception as e:
            log_error(f"Failed to test all LLM connections: {e}")
            results["error"] = sanitize_error(e)

        return results
