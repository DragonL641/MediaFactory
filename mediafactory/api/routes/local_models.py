"""本地（Ollama）模型管理路由。

独立于 models.py 的原因：models.py 的 DELETE /{model_id:path} 是全捕获
路由，本路由必须先于它注册才能让 /local/* 优先匹配（见 api/main.py）。
"""

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from mediafactory.api.local_pull_task import active_pulls, start_pull
from mediafactory.i18n import t
from mediafactory.llm.ollama_client import OllamaError, get_ollama_client

router = APIRouter()

# Ollama 模型名：字母数字开头，可含 . : / _ -（如 qwen2.5:7b、library/model:tag）
_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.:/_-]{0,199}$")


class LocalPullRequest(BaseModel):
    """拉取请求"""

    name: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        v = v.strip()
        if not _MODEL_NAME_RE.match(v):
            raise ValueError("invalid Ollama model name")
        return v


@router.get("/local")
async def get_local_models() -> dict:
    """Ollama 可用性与已安装模型列表。"""
    client = get_ollama_client()
    if not await client.is_available():
        return {"available": False, "models": []}
    models = await client.list_installed()
    return {
        "available": True,
        "models": [
            {
                "name": m.name,
                "size": m.size,
                "parameterSize": m.parameter_size,
                "quantizationLevel": m.quantization_level,
                "modifiedAt": m.modified_at,
            }
            for m in models
        ],
    }


@router.post("/local/pull")
async def pull_local_model(request: LocalPullRequest):
    """启动 Ollama 模型拉取（后台任务 + WS 进度）。"""
    name = request.name
    if name in active_pulls():
        raise HTTPException(
            status_code=409,
            detail=t("task.downloadAlreadyInProgress", modelId=name),
        )
    client = get_ollama_client()
    if not await client.is_available():
        raise HTTPException(status_code=503, detail="Ollama is not running")

    task_id = await start_pull(name)
    return {"task_id": task_id, "status": "pending"}


@router.delete("/local/{name:path}")
async def delete_local_model(name: str):
    """删除已安装的本地模型。"""
    if name in active_pulls():
        raise HTTPException(status_code=409, detail="model is being pulled")
    client = get_ollama_client()
    if not await client.is_available():
        raise HTTPException(status_code=503, detail="Ollama is not running")
    try:
        await client.delete_model(name)
    except OllamaError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"success": True}
