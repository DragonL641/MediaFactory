"""
模型管理 API 路由

提供模型状态查询、下载、删除等端点。
"""

import asyncio
import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mediafactory.services.models import ModelStatusService

logger = logging.getLogger(__name__)

router = APIRouter()

# 复用现有服务
_status_service = ModelStatusService()

# 模型状态缓存（60 秒）
_models_status_cache: Dict[str, Any] = None
_models_status_cache_time: float = 0
_MODELS_STATUS_CACHE_TTL = 60


def _invalidate_models_status_cache():
    """清除模型状态缓存"""
    global _models_status_cache, _models_status_cache_time
    _models_status_cache = None
    _models_status_cache_time = 0


class DownloadRequest(BaseModel):
    """下载请求"""
    source: str = "official"  # official, mirror


class LLMTestRequest(BaseModel):
    """LLM 测试请求"""
    preset: str = "openai"


@router.get("/status")
async def get_models_status() -> Dict[str, Any]:
    """
    获取所有模型状态

    返回 Whisper、翻译模型、LLM、增强模型、降噪模型的状态信息。
    使用 60 秒缓存减少文件系统检查。
    """
    global _models_status_cache, _models_status_cache_time

    # 检查缓存
    if _models_status_cache and (time.time() - _models_status_cache_time) < _MODELS_STATUS_CACHE_TTL:
        return _models_status_cache

    whisper_status = _status_service.get_whisper_status()
    translation_status = _status_service.get_translation_status()
    llm_status = _status_service.get_llm_status()

    # 获取翻译模型详情
    translation_models = _status_service.get_translation_model_statuses()

    # 一次性获取 config，传递给子函数
    from mediafactory.config import get_config
    config = get_config()

    enhancement_models = _get_enhancement_model_statuses(config)
    denoise_models = _get_denoise_model_statuses(config)

    # 获取 Whisper 模型详情列表
    whisper_models = _get_whisper_model_statuses()

    result = {
        "whisper": {
            "name": whisper_status.name,
            "loaded": whisper_status.loaded,
            "available": whisper_status.available,
            "enabled": whisper_status.enabled,
            "models": whisper_models,
        },
        "translation": {
            "name": translation_status.name,
            "loaded": translation_status.loaded,
            "available": translation_status.available,
            "enabled": translation_status.enabled,
            "models": translation_models,
        },
        "llm": {
            "name": llm_status.name,
            "loaded": llm_status.loaded,
            "available": llm_status.available,
            "enabled": llm_status.enabled,
            "config": _status_service.get_llm_config(),
        },
        "enhancement": {
            "name": "Real-ESRGAN",
            "models": enhancement_models,
        },
        "denoise": {
            "name": "NAFNet",
            "models": denoise_models,
        },
    }

    # 更新缓存
    _models_status_cache = result
    _models_status_cache_time = time.time()

    return result


def _get_whisper_model_statuses() -> List[Dict[str, Any]]:
    """获取 Whisper 模型状态列表"""
    from mediafactory.models.model_registry import is_model_downloaded, is_model_complete

    whisper_models = [
        {
            "id": "Systran/faster-whisper-large-v3",
            "name": "Whisper Large V3",
            "size": "~3 GB",
            "memory": "~6 GB",
            "description": "Best quality for speech recognition",
            "downloaded": False,
            "complete": False,
        },
    ]

    for model in whisper_models:
        model["downloaded"] = is_model_downloaded(model["id"])
        if model["downloaded"]:
            model["complete"] = is_model_complete(model["id"])

    return whisper_models


def _get_enhancement_model_statuses(config) -> List[Dict[str, Any]]:
    """获取 Real-ESRGAN 增强模型状态"""
    from mediafactory.models.model_registry import is_model_downloaded, is_model_complete

    enhancement_models = [
        {
            "id": "RealESRGAN_x2plus",
            "name": "Real-ESRGAN x2plus",
            "size": "~64 MB",
            "memory": "~1.2 GB",
            "description": "2x general super resolution",
            "downloaded": False,
            "complete": False,
        },
        {
            "id": "RealESRGAN_x4plus",
            "name": "Real-ESRGAN x4plus",
            "size": "~67 MB",
            "memory": "~2.4 GB",
            "description": "4x general super resolution",
            "downloaded": False,
            "complete": False,
        },
        {
            "id": "RealESRGAN_x4plus_anime_6B",
            "name": "Real-ESRGAN x4plus Anime",
            "size": "~18 MB",
            "memory": "~2.4 GB",
            "description": "4x anime super resolution",
            "downloaded": False,
            "complete": False,
        },
    ]

    for model in enhancement_models:
        model["downloaded"] = is_model_downloaded(model["id"])
        if model["downloaded"]:
            model["complete"] = is_model_complete(model["id"])

    return enhancement_models


def _get_denoise_model_statuses(config) -> List[Dict[str, Any]]:
    """获取 NAFNet 降噪模型状态"""
    from mediafactory.models.model_registry import is_model_downloaded, is_model_complete

    denoise_models = [
        {
            "id": "NAFNet-GoPro-width64",
            "name": "NAFNet Width64",
            "size": "~260 MB",
            "memory": "~1.5 GB",
            "description": "Real image denoising",
            "downloaded": False,
            "complete": False,
        },
    ]

    for model in denoise_models:
        model["downloaded"] = is_model_downloaded(model["id"])
        if model["downloaded"]:
            model["complete"] = is_model_complete(model["id"])

    return denoise_models


@router.get("/whisper")
async def get_whisper_status() -> Dict[str, Any]:
    """获取 Whisper 模型状态"""
    status = _status_service.get_whisper_status()
    return {
        "name": status.name,
        "loaded": status.loaded,
        "available": status.available,
        "enabled": status.enabled,
    }


@router.get("/translation")
async def get_translation_status() -> Dict[str, Any]:
    """获取翻译模型状态"""
    status = _status_service.get_translation_status()
    models = _status_service.get_translation_model_statuses()
    return {
        "name": status.name,
        "loaded": status.loaded,
        "available": status.available,
        "enabled": status.enabled,
        "models": models,
    }


@router.get("/llm")
async def get_llm_status() -> Dict[str, Any]:
    """获取 LLM 状态"""
    status = _status_service.get_llm_status()
    config = _status_service.get_llm_config()
    return {
        "name": status.name,
        "loaded": status.loaded,
        "available": status.available,
        "enabled": status.enabled,
        "config": config,
    }


@router.post("/download/{model_id}")
async def start_model_download(
    model_id: str,
    request: DownloadRequest = DownloadRequest(),
):
    """
    启动模型下载

    支持通过镜像源下载。
    """
    from mediafactory.api.main import get_task_manager
    from mediafactory.api.schemas import TaskConfig, TaskType
    from mediafactory.api.websocket import manager as ws_manager

    # 选择下载源
    endpoint = None
    if request.source == "mirror":
        endpoint = "https://hf-mirror.com"

    # 启动下载任务
    task_manager = get_task_manager()

    config = TaskConfig(
        task_type=TaskType.DOWNLOAD,
        input_path=model_id,
    )

    task_id = await task_manager.create_task(
        config, name=f"下载模型: {model_id}"
    )

    # 后台执行下载
    async def _execute_download_task():
        """执行模型下载任务"""
        from mediafactory.models.model_download import download_model

        async def _progress_callback(progress: float, msg: str = ""):
            await ws_manager.broadcast_progress(
                task_id=task_id,
                status="downloading",
                progress=progress * 100,
                message=msg,
                stage="download",
            )

        try:
            def sync_progress(p: float, m: str = ""):
                asyncio.run(_progress_callback(p, m))

            download_model(
                model_id,
                download_source=endpoint,
                progress_callback=sync_progress,
            )

            _invalidate_models_status_cache()

            await ws_manager.broadcast_task_complete(
                task_id=task_id,
                success=True,
                output_path=f"models/{model_id}",
            )

        except Exception as e:
            logger.exception(f"Download failed: {e}")
            await ws_manager.broadcast_task_complete(
                task_id=task_id,
                success=False,
                error=str(e),
            )

    # 启动后台任务
    asyncio.create_task(_execute_download_task())

    return {
        "task_id": task_id,
        "status": "pending",
        "message": f"下载任务已创建: {model_id}",
    }


@router.delete("/{model_id}")
async def delete_model(model_id: str):
    """删除模型"""
    from mediafactory.models.model_download import delete_model as delete_model_func

    success, error = delete_model_func(model_id)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    _invalidate_models_status_cache()
    return {"success": True, "message": f"模型已删除: {model_id}"}


@router.post("/llm/test")
async def test_llm_connection(request: LLMTestRequest):
    """
    测试 LLM 连接

    发送测试请求到指定的 LLM 预设。
    """
    result = await _status_service.test_llm_connection(request.preset)
    return result


@router.post("/llm/test-all")
async def test_all_llm_connections():
    """测试所有 LLM 预设连接"""
    results = await _status_service.test_all_llm_connections()
    return results
