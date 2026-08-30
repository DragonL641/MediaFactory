"""系统级 API：目录浏览（Web UI 文件选取）与产物定位（reveal）。"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mediafactory.i18n import t

logger = logging.getLogger(__name__)
# API 层使用标准 logging，通过 InterceptHandler 自动重定向到 loguru
# 详见 mediafactory.logging.loguru_logger.setup_logging_intercept

router = APIRouter()


class BrowseEntry(BaseModel):
    name: str
    is_dir: bool


class BrowseResult(BaseModel):
    path: str
    parent: Optional[str]
    entries: List[BrowseEntry]


class RevealRequest(BaseModel):
    path: str


@router.get("/browse", response_model=BrowseResult)
async def browse(path: Optional[str] = None, ext: Optional[str] = None) -> BrowseResult:
    """列出目录内容供 Web UI 文件选取。

    目录始终显示；文件按逗号分隔的扩展名过滤（缺省不过滤）；
    跳过 dotfile（隐藏配置文件，减少列表噪音）。
    """
    # resolve()：手输相对路径（如 Downloads）规范化为绝对路径，不落 daemon CWD
    target = Path(path).expanduser().resolve() if path else Path.home()
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=400, detail=t("error.pathNotAccessible"))

    extensions = (
        {e.strip().lower().lstrip(".") for e in ext.split(",") if e.strip()}
        if ext
        else None
    )

    entries: List[BrowseEntry] = []
    try:
        for item in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            if item.name.startswith("."):
                continue  # 隐藏 dotfile
            try:
                is_dir = item.is_dir()
            except OSError:
                continue  # 无法 stat 的条目（受保护 junction 等）跳过，不炸整个目录
            if is_dir:
                entries.append(BrowseEntry(name=item.name, is_dir=True))
            elif extensions is None or item.suffix.lower().lstrip(".") in extensions:
                entries.append(BrowseEntry(name=item.name, is_dir=False))
    except PermissionError:
        raise HTTPException(status_code=400, detail=t("error.pathNotAccessible"))

    # 目录在前、各自按名排序（sorted 已保证字母序，这里只做分区稳定排序）
    entries.sort(key=lambda e: not e.is_dir)
    parent = str(target.parent) if target.parent != target else None
    return BrowseResult(path=str(target), parent=parent, entries=entries)


@router.post("/reveal", status_code=204)
async def reveal(req: RevealRequest) -> None:
    """在系统文件管理器中定位并选中文件。"""
    target = Path(req.path).expanduser()
    if not target.exists():
        raise HTTPException(status_code=400, detail=t("error.pathNotAccessible"))

    if sys.platform == "darwin":
        cmd = ["open", "-R", str(target)]
    elif sys.platform == "win32":
        cmd = ["explorer", f"/select,{target}"]
    else:
        raise HTTPException(status_code=400, detail=t("error.platformNotSupported"))

    # 列表参数 + 无 shell：无注入面；异步执行避免阻塞事件循环。
    # 便利性操作失败不打断用户（仍 204），但留日志可查。
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    returncode = await proc.wait()
    # explorer.exe 成功时也返回 1——Windows 分支不据此告警
    if returncode != 0 and sys.platform != "win32":
        logger.warning(f"reveal 命令返回非零（忽略）: {cmd}")
