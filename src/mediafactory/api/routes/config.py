"""
配置管理 API 路由

提供配置读取、更新、保存等端点。
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mediafactory.config import get_config, reload_config, save_config, update_config
from mediafactory.api.error_handler import sanitize_error
from mediafactory.i18n import t

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""

    config: Dict[str, Any]


class PartialConfigUpdate(BaseModel):
    """部分配置更新"""

    whisper: Optional[Dict[str, Any]] = None
    model: Optional[Dict[str, Any]] = None
    openai_compatible: Optional[Dict[str, Any]] = None
    llm_api: Optional[Dict[str, Any]] = None
    app: Optional[Dict[str, Any]] = None


@router.get("/")
async def get_full_config():
    """
    获取完整配置

    返回所有配置分区的当前值。
    """
    config = get_config()
    return config.to_toml_dict()


@router.get("/{section}")
async def get_config_section(section: str):
    """
    获取配置分区

    支持的分区：whisper, model, openai_compatible, llm_api
    """
    config = get_config()
    config_dict = config.to_toml_dict()

    if section not in config_dict:
        raise HTTPException(status_code=404, detail=t("error.configSectionNotExist", section=section))

    return {section: config_dict[section]}


@router.put("/")
async def update_full_config(request: PartialConfigUpdate):
    """
    更新配置（部分更新）

    只更新请求中包含的字段，其他字段保持不变。
    """
    try:
        config = get_config()

        # 处理各分区的更新
        update_kwargs = {}

        if request.whisper is not None:
            for key, value in request.whisper.items():
                update_kwargs[f"whisper__{key}"] = value

        if request.model is not None:
            for key, value in request.model.items():
                update_kwargs[f"model__{key}"] = value

        if request.openai_compatible is not None:
            for key, value in request.openai_compatible.items():
                update_kwargs[f"openai_compatible__{key}"] = value

        if request.llm_api is not None:
            for key, value in request.llm_api.items():
                update_kwargs[f"llm_api__{key}"] = value

        if request.app is not None:
            for key, value in request.app.items():
                update_kwargs[f"app__{key}"] = value

        if update_kwargs:
            update_config(**update_kwargs)

        # 如果语言发生变化，同步 i18n
        if request.app and "language" in request.app:
            from mediafactory.i18n import set_language
            set_language(request.app["language"])

        # 返回更新后的配置
        config = get_config()
        return config.to_toml_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=t("error.configUpdateFailed"))
    except Exception as e:
        logger.exception(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=t("error.configUpdateFailed"))


@router.post("/save")
async def save_config_to_disk():
    """
    保存配置到磁盘

    将当前内存中的配置写入 config.toml 文件。
    """
    try:
        save_config()
        return {"success": True, "message": t("task.configSaved")}
    except Exception as e:
        logger.exception(f"保存配置失败: {e}")
        raise HTTPException(status_code=500, detail=t("error.configSaveFailed"))


@router.post("/reload")
async def reload_config_from_disk():
    """
    从磁盘重新加载配置

    丢弃内存中的修改，重新读取 config.toml 文件。
    """
    try:
        reload_config()
        config = get_config()
        return {"success": True, "config": config.to_toml_dict()}
    except Exception as e:
        logger.exception(f"重新加载配置失败: {e}")
        raise HTTPException(status_code=500, detail=t("error.configReloadFailed"))


@router.get("/llm/presets")
async def get_llm_presets():
    """
    获取 LLM 预设列表

    返回所有支持的 LLM 服务预设及其配置状态。
    """
    from mediafactory.constants import BackendConfigMapping

    presets = BackendConfigMapping.BASE_URL_PRESETS
    config = get_config()

    result = {}
    for preset_id, preset_info in presets.items():
        preset_config = getattr(config.openai_compatible, preset_id, None)
        has_key = preset_config.api_key != "" if preset_config else False
        has_base_url = bool(preset_config.base_url) if preset_config else False
        # custom 预设：有 base_url 即视为已配置
        is_configured = (
            (has_base_url or bool(preset_config.model))
            if preset_id == "custom"
            else (has_key or bool(preset_config.model))
        )
        result[preset_id] = {
            "display_name": preset_info["display_name"],
            "base_url": preset_config.base_url or preset_info["base_url"],
            "model": preset_config.model,
            "model_examples": preset_info["model_examples"],
            "configured": is_configured,
            "has_api_key": has_key,
            "connection_available": preset_config.connection_available,
        }

    return result


class LLMPresetUpdateRequest(BaseModel):
    """LLM 预设更新请求（JSON body）"""

    api_key: Optional[str] = ""
    base_url: Optional[str] = None
    model: Optional[str] = None


class SetCurrentPresetRequest(BaseModel):
    """设置当前预设请求"""

    preset: str


@router.put("/llm/preset/{preset_id}")
async def update_llm_preset(preset_id: str, request: LLMPresetUpdateRequest):
    """
    更新 LLM 预设配置

    使用 JSON body 传递配置，避免 API Key 暴露在 URL 中。
    """
    from mediafactory.constants import BackendConfigMapping

    if preset_id not in BackendConfigMapping.BASE_URL_PRESETS:
        raise HTTPException(status_code=404, detail=t("error.unknownPreset", preset=preset_id))

    try:
        # 构建更新参数
        update_kwargs = {f"openai_compatible__{preset_id}__api_key": request.api_key}

        if request.base_url is not None:
            update_kwargs[f"openai_compatible__{preset_id}__base_url"] = request.base_url

        if request.model is not None:
            update_kwargs[f"openai_compatible__{preset_id}__model"] = request.model

        update_config(**update_kwargs)

        return {"success": True, "message": t("task.presetUpdated", preset=preset_id)}

    except Exception as e:
        logger.exception(f"更新预设失败: {e}")
        raise HTTPException(status_code=500, detail=t("error.presetUpdateFailed", error=sanitize_error(e)))


@router.delete("/llm/preset/{preset_id}")
async def delete_llm_preset(preset_id: str):
    """
    删除 LLM 预设配置

    清空指定预设的 API Key 和 Model，保留 base_url。
    """
    from mediafactory.constants import BackendConfigMapping

    if preset_id not in BackendConfigMapping.BASE_URL_PRESETS:
        raise HTTPException(status_code=404, detail=t("error.unknownPreset", preset=preset_id))

    try:
        update_kwargs = {
            f"openai_compatible__{preset_id}__api_key": "",
            f"openai_compatible__{preset_id}__model": "",
        }
        update_config(**update_kwargs)

        return {"success": True, "message": t("task.presetDeleted", preset=preset_id)}

    except Exception as e:
        logger.exception(f"删除预设失败: {e}")
        raise HTTPException(status_code=500, detail=t("error.presetDeleteFailed", error=sanitize_error(e)))


@router.put("/llm/current-preset")
async def set_current_llm_preset(request: SetCurrentPresetRequest):
    """
    设置当前使用的 LLM 预设
    """
    from mediafactory.constants import BackendConfigMapping

    if request.preset not in BackendConfigMapping.BASE_URL_PRESETS:
        raise HTTPException(status_code=404, detail=t("error.unknownPreset", preset=request.preset))

    try:
        update_config(openai_compatible__current_preset=request.preset)
        return {"success": True, "current_preset": request.preset}
    except Exception as e:
        logger.exception(f"设置当前预设失败: {e}")
        raise HTTPException(status_code=500, detail=t("error.setCurrentPresetFailed", error=sanitize_error(e)))
