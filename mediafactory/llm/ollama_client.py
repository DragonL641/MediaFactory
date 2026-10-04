"""Ollama 本地服务客户端。

daemon 内唯一与 Ollama REST API 交互的模块。
async 方法供 API 路由（事件循环）使用；sync 方法供 engine/runner
（worker 同步上下文）使用。

API 行为要点（Ollama 0.17.5 冒烟实测）：
- GET /api/tags        已安装模型（name/size/details.*）
- GET /api/ps          已加载模型（含 expires_at）
- POST /api/pull       NDJSON 流式进度，终止行 {"status": "success"} 或 {"error": ...}
- POST /api/generate   keep_alive=0 请求卸载（异步生效）
- DELETE /api/delete   删除模型（成功无响应体）

卸载必须先查 /api/ps：对未加载的模型直接发 generate 会触发
"先加载再卸载"，造成无谓的内存峰值。
"""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from ..constants import OLLAMA_BASE_URL
from ..logging import log_debug, log_warning


@dataclass
class OllamaModelInfo:
    """已安装模型信息。"""

    name: str
    size: int
    parameter_size: str
    quantization_level: str
    modified_at: str


class OllamaError(Exception):
    """Ollama 协议或 HTTP 错误。"""


def _parse_model(raw: dict) -> OllamaModelInfo:
    details = raw.get("details") or {}
    return OllamaModelInfo(
        name=raw.get("name", ""),
        size=int(raw.get("size", 0)),
        parameter_size=details.get("parameter_size", ""),
        quantization_level=details.get("quantization_level", ""),
        modified_at=raw.get("modified_at", ""),
    )


class OllamaClient:
    """Ollama REST 客户端。transport 参数供测试注入 httpx.MockTransport。"""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        timeout: float = 2.0,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    # ---------- async（路由层） ----------

    def _async_client(self, read_timeout: float | None = None) -> httpx.AsyncClient:
        timeout = httpx.Timeout(read_timeout, connect=self._timeout)
        return httpx.AsyncClient(
            base_url=self._base_url, timeout=timeout, transport=self._transport
        )

    async def is_available(self) -> bool:
        try:
            async with self._async_client() as client:
                return (await client.get("/api/tags")).status_code == 200
        except Exception:
            return False

    async def is_model_installed(self, name: str) -> bool:
        try:
            async with self._async_client() as client:
                resp = await client.get("/api/tags")
                resp.raise_for_status()
        except Exception:
            return False
        return any(m.get("name") == name for m in resp.json().get("models", []))

    async def list_installed(self) -> list[OllamaModelInfo]:
        async with self._async_client() as client:
            resp = await client.get("/api/tags")
            resp.raise_for_status()
            return [_parse_model(m) for m in resp.json().get("models", [])]

    async def pull_stream(self, name: str) -> AsyncIterator[dict]:
        """逐行产出 /api/pull 的 NDJSON 事件；error 行抛 OllamaError。

        断开流（离开 async with）即取消拉取，Ollama 保留已下载分片。
        """
        async with self._async_client(read_timeout=None) as client:
            async with client.stream("POST", "/api/pull", json={"name": name}) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if "error" in event:
                        raise OllamaError(event["error"])
                    yield event

    async def delete_model(self, name: str) -> None:
        async with self._async_client() as client:
            resp = await client.request("DELETE", "/api/delete", json={"name": name})
            resp.raise_for_status()

    async def unload_model(self, name: str) -> None:
        if name not in await self._loaded_names():
            return
        async with self._async_client() as client:
            await client.post("/api/generate", json={"model": name, "keep_alive": 0})

    async def _loaded_names(self) -> set[str]:
        async with self._async_client() as client:
            resp = await client.get("/api/ps")
            resp.raise_for_status()
        return {m.get("name", "") for m in resp.json().get("models", [])}

    # ---------- sync（engine / runner） ----------

    def _sync_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url, timeout=self._timeout, transport=self._transport
        )

    def is_available_sync(self) -> bool:
        try:
            with self._sync_client() as client:
                return client.get("/api/tags").status_code == 200
        except Exception:
            return False

    def is_model_installed_sync(self, name: str) -> bool:
        try:
            with self._sync_client() as client:
                resp = client.get("/api/tags")
                resp.raise_for_status()
        except Exception:
            return False
        return any(m.get("name") == name for m in resp.json().get("models", []))

    def unload_model_sync(self, name: str) -> None:
        """请求卸载模型（若已加载）。短超时、吞异常——供引擎 finally 调用。"""
        try:
            with self._sync_client() as client:
                resp = client.get("/api/ps")
                resp.raise_for_status()
                loaded = {m.get("name", "") for m in resp.json().get("models", [])}
                if name not in loaded:
                    return
                client.post("/api/generate", json={"model": name, "keep_alive": 0})
                log_debug(f"[Ollama] Unload requested for {name}")
        except Exception as e:
            log_warning(f"[Ollama] Unload {name} failed (ignored): {e}")


_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    """进程级单例。"""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
