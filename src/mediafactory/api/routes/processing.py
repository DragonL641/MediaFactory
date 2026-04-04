"""
处理 API 路由

提供字幕生成、音频提取、转录、翻译、视频增强等端点。
任务创建后不自动执行，用户需手动启动。
"""

import logging
import os

from fastapi import APIRouter, HTTPException

from mediafactory.api.schemas import (
    AudioRequest,
    CancelResponse,
    EnhanceRequest,
    SubtitleRequest,
    TaskConfigUpdateRequest,
    TaskResponse,
    TaskStatus,
    TranscribeRequest,
    TranslateRequest,
)
from mediafactory.i18n import t

logger = logging.getLogger(__name__)
# API 层使用标准 logging，通过 InterceptHandler 自动重定向到 loguru
# 详见 mediafactory.logging.loguru_logger.setup_logging_intercept

router = APIRouter()


def _get_task_manager():
    """延迟导入以避免循环依赖"""
    from mediafactory.api.main import get_task_manager as _get_tm
    return _get_tm()


@router.post("/subtitle", response_model=TaskResponse)
async def create_subtitle_task(request: SubtitleRequest):
    """创建字幕生成任务（不自动启动）"""
    from mediafactory.api.schemas import SubtitleConfig, TaskConfig, TaskType

    config = TaskConfig(
        task_type=TaskType.SUBTITLE,
        input_path=request.video_path,
        output_path=request.output_path,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        use_llm=request.use_llm,
        llm_preset=request.llm_preset,
        subtitle_config=SubtitleConfig(
            output_format=request.output_format,
            bilingual=request.bilingual,
            bilingual_layout=request.bilingual_layout,
            style_preset=request.style_preset,
            diarization_enabled=request.diarization_enabled,
        ),
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Subtitle: {os.path.basename(request.video_path)}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message=t("task.createdWaiting"),
    )


@router.post("/audio", response_model=TaskResponse)
async def create_audio_task(request: AudioRequest):
    """创建音频提取任务（不自动启动）"""
    from mediafactory.api.schemas import AudioConfig, TaskConfig, TaskType

    config = TaskConfig(
        task_type=TaskType.AUDIO,
        input_path=request.video_path,
        output_path=request.output_path,
        audio_config=AudioConfig(
            sample_rate=request.sample_rate,
            channels=request.channels,
            filter_enabled=request.filter_enabled,
            highpass_freq=request.highpass_freq,
            lowpass_freq=request.lowpass_freq,
            volume=request.volume,
            output_format=request.output_format,
        ),
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Audio: {os.path.basename(request.video_path)}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message=t("task.createdWaiting"),
    )


@router.post("/transcribe", response_model=TaskResponse)
async def create_transcribe_task(request: TranscribeRequest):
    """创建音频转录任务（不自动启动）"""
    from mediafactory.api.schemas import SubtitleConfig, TaskConfig, TaskType

    config = TaskConfig(
        task_type=TaskType.TRANSCRIBE,
        input_path=request.audio_path,
        output_path=request.output_path,
        source_lang=request.source_lang,
        subtitle_config=SubtitleConfig(
            output_format=request.output_format,
            style_preset=request.style_preset,
            diarization_enabled=request.diarization_enabled,
        ),
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Transcribe: {os.path.basename(request.audio_path)}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message=t("task.createdWaiting"),
    )


@router.post("/translate", response_model=TaskResponse)
async def create_translate_task(request: TranslateRequest):
    """创建翻译任务（不自动启动）"""
    from mediafactory.api.schemas import TaskConfig, TaskType

    if not request.srt_path and not request.text:
        raise HTTPException(status_code=400, detail=t("error.eitherSrtOrTextRequired"))

    config = TaskConfig(
        task_type=TaskType.TRANSLATE,
        input_path=request.srt_path or "",
        input_text=request.text,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        use_llm=request.use_llm,
        llm_preset=request.llm_preset,
        output_format=request.output_format,
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Translate: {request.target_lang}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message=t("task.createdWaiting"),
    )


@router.post("/enhance", response_model=TaskResponse)
async def create_enhance_task(request: EnhanceRequest):
    """创建视频增强任务（不自动启动）"""
    from mediafactory.api.schemas import EnhancementConfig, TaskConfig, TaskType

    config = TaskConfig(
        task_type=TaskType.ENHANCE,
        input_path=request.video_path,
        output_path=request.output_path,
        enhancement_config=EnhancementConfig(
            scale=request.scale,
            model=request.model_type,
            denoise=request.denoise,
            temporal=request.temporal,
        ),
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Enhance: {os.path.basename(request.video_path)}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message=t("task.createdWaiting"),
    )


# ============ 任务控制 ============


@router.post("/start/{task_id}")
async def start_task(task_id: str):
    """启动单个 PENDING 任务"""
    task_manager = _get_task_manager()
    success = await task_manager.start_single_task(task_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=t("error.cannotStartTask"),
        )

    return {"task_id": task_id, "status": TaskStatus.RUNNING.value, "message": t("task.started")}


@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    task_manager = _get_task_manager()
    success = await task_manager.cancel_task(task_id)

    if not success:
        # 任务可能已完成/失败，返回当前状态而非 404
        status = await task_manager.get_task_status(task_id)
        current_status = status["status"] if status else "unknown"
        return {
            "task_id": task_id,
            "status": current_status,
            "message": t("task.alreadyInStatus", status=current_status),
        }

    return CancelResponse(
        task_id=task_id,
        status="cancelling",
        message=t("task.cancellationRequested"),
    )


@router.post("/retry/{task_id}")
async def retry_task(task_id: str):
    """重试失败/取消的任务（创建同配置新任务）"""
    task_manager = _get_task_manager()

    # 获取原任务配置
    config_dict = await task_manager.get_task_config(task_id)
    if not config_dict:
        raise HTTPException(status_code=404, detail=t("error.taskNotFound"))

    # 检查原任务状态
    status_info = await task_manager.get_task_status(task_id)
    if not status_info:
        raise HTTPException(status_code=404, detail=t("error.taskNotFound"))

    if status_info["status"] not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=400, detail=t("error.canOnlyRetryFailed")
        )

    # 用相同配置创建新任务
    from mediafactory.api.schemas import TaskConfig

    new_config = TaskConfig(**config_dict)
    new_task_id = await task_manager.create_task(
        new_config, name=status_info.get("name", f"Retry: {task_id}")
    )

    return TaskResponse(
        task_id=new_task_id,
        status=TaskStatus.PENDING,
        message=t("task.retried"),
    )


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    task_manager = _get_task_manager()
    status = await task_manager.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail=t("error.taskNotFound"))

    return status


@router.get("/tasks")
async def list_tasks():
    """列出所有任务（排除下载任务）"""
    from mediafactory.api.schemas import TaskType

    task_manager = _get_task_manager()
    return await task_manager.get_all_tasks(exclude_types=[TaskType.DOWNLOAD])


@router.delete("/tasks/{task_id}")
async def remove_task(task_id: str):
    """移除任务"""
    task_manager = _get_task_manager()
    success = await task_manager.remove_task(task_id)

    if not success:
        raise HTTPException(status_code=400, detail=t("error.cannotRemoveRunningTask"))

    return {"success": True}


@router.get("/tasks/{task_id}/config")
async def get_task_config(task_id: str):
    """获取任务配置（用于编辑回显）"""
    task_manager = _get_task_manager()
    config = await task_manager.get_task_config(task_id)

    if not config:
        raise HTTPException(status_code=404, detail=t("error.taskNotFound"))

    return config


@router.put("/tasks/{task_id}/config")
async def update_task_config(task_id: str, update: TaskConfigUpdateRequest):
    """更新 PENDING 任务的配置"""
    task_manager = _get_task_manager()

    # 检查任务状态
    status_info = await task_manager.get_task_status(task_id)
    if not status_info:
        raise HTTPException(status_code=404, detail=t("error.taskNotFound"))

    if status_info["status"] != TaskStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=t("error.canOnlyEditPending", status=status_info['status']),
        )

    update_data = update.model_dump(exclude_unset=True)
    success = await task_manager.update_task_config(task_id, update_data)

    if not success:
        raise HTTPException(status_code=500, detail=t("error.updateFailed"))

    return {"success": True, "message": t("task.configUpdated")}


# ============ 批量操作 ============


@router.post("/batch/start")
async def batch_start_tasks():
    """启动所有 PENDING 任务（串行执行）"""
    task_manager = _get_task_manager()
    count = await task_manager.start_all_pending()
    return {"success": True, "started": count, "message": t("task.queuedForExecution", count=count)}


@router.post("/batch/cancel")
async def batch_cancel_tasks():
    """取消所有运行中的任务"""
    task_manager = _get_task_manager()
    tasks = await task_manager.get_all_tasks()

    cancelled = 0
    for task_info in tasks:
        if task_info["status"] == TaskStatus.RUNNING.value:
            try:
                await task_manager.cancel_task(task_info["id"])
                cancelled += 1
            except Exception:
                pass

    return {"success": True, "cancelled": cancelled}


@router.delete("/batch/clear")
async def batch_clear_tasks():
    """清除所有已完成/失败/已取消的任务"""
    task_manager = _get_task_manager()
    tasks = await task_manager.get_all_tasks()

    cleared = 0
    for task_info in tasks:
        if task_info["status"] in (
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        ):
            try:
                await task_manager.remove_task(task_info["id"])
                cleared += 1
            except Exception:
                pass

    return {"success": True, "cleared": cleared}
