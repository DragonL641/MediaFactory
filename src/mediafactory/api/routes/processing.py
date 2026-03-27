"""
处理 API 路由

提供字幕生成、音频提取、转录、翻译、视频增强等端点。
任务创建后不自动执行，用户需手动启动。
"""

import logging

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

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_task_manager():
    """延迟导入以避免循环依赖"""
    from mediafactory.api.main import get_task_manager as _get_tm
    return _get_tm()


@router.post("/subtitle", response_model=TaskResponse)
async def create_subtitle_task(request: SubtitleRequest):
    """创建字幕生成任务（不自动启动）"""
    from mediafactory.api.schemas import TaskConfig, TaskType

    config = TaskConfig(
        task_type=TaskType.SUBTITLE,
        input_path=request.video_path,
        output_path=request.output_path,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        use_llm=request.use_llm,
        llm_preset=request.llm_preset,
        output_format=request.output_format,
        bilingual=request.bilingual,
        bilingual_layout=request.bilingual_layout,
        style_preset=request.style_preset,
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Subtitle: {request.video_path.split('/')[-1]}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task created, waiting to start",
    )


@router.post("/audio", response_model=TaskResponse)
async def create_audio_task(request: AudioRequest):
    """创建音频提取任务（不自动启动）"""
    from mediafactory.api.schemas import TaskConfig, TaskType

    config = TaskConfig(
        task_type=TaskType.AUDIO,
        input_path=request.video_path,
        output_path=request.output_path,
        audio_sample_rate=request.sample_rate,
        audio_channels=request.channels,
        audio_filter_enabled=request.filter_enabled,
        audio_highpass_freq=request.highpass_freq,
        audio_lowpass_freq=request.lowpass_freq,
        audio_volume=request.volume,
        audio_output_format=request.output_format,
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Audio: {request.video_path.split('/')[-1]}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task created, waiting to start",
    )


@router.post("/transcribe", response_model=TaskResponse)
async def create_transcribe_task(request: TranscribeRequest):
    """创建音频转录任务（不自动启动）"""
    from mediafactory.api.schemas import TaskConfig, TaskType

    config = TaskConfig(
        task_type=TaskType.TRANSCRIBE,
        input_path=request.audio_path,
        output_path=request.output_path,
        source_lang=request.language,
        output_format=request.output_format,
        style_preset=request.style_preset,
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Transcribe: {request.audio_path.split('/')[-1]}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task created, waiting to start",
    )


@router.post("/translate", response_model=TaskResponse)
async def create_translate_task(request: TranslateRequest):
    """创建翻译任务（不自动启动）"""
    from mediafactory.api.schemas import TaskConfig, TaskType

    if not request.srt_path and not request.text:
        raise HTTPException(status_code=400, detail="Either srt_path or text is required")

    config = TaskConfig(
        task_type=TaskType.TRANSLATE,
        input_path=request.srt_path or "",
        input_text=request.text,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        use_llm=request.use_llm,
        llm_preset=request.llm_preset,
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Translate: {request.target_lang}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task created, waiting to start",
    )


@router.post("/enhance", response_model=TaskResponse)
async def create_enhance_task(request: EnhanceRequest):
    """创建视频增强任务（不自动启动）"""
    from mediafactory.api.schemas import TaskConfig, TaskType

    config = TaskConfig(
        task_type=TaskType.ENHANCE,
        input_path=request.video_path,
        output_path=request.output_path,
        enhancement_scale=request.scale,
        enhancement_model=request.model_type,
        enhancement_denoise=request.denoise,
        enhancement_temporal=request.temporal,
    )

    task_manager = _get_task_manager()
    task_id = await task_manager.create_task(
        config, name=f"Enhance: {request.video_path.split('/')[-1]}"
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task created, waiting to start",
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
            detail="Cannot start task: task not found, not PENDING, or another task is running",
        )

    return {"task_id": task_id, "status": TaskStatus.RUNNING.value, "message": "Task started"}


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
            "message": f"Task already {current_status}",
        }

    return CancelResponse(
        task_id=task_id,
        status="cancelling",
        message="Cancellation requested",
    )


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    task_manager = _get_task_manager()
    status = await task_manager.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return status


@router.get("/tasks")
async def list_tasks():
    """列出所有任务"""
    task_manager = _get_task_manager()
    return await task_manager.get_all_tasks()


@router.delete("/tasks/{task_id}")
async def remove_task(task_id: str):
    """移除任务"""
    task_manager = _get_task_manager()
    success = await task_manager.remove_task(task_id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot remove a running task")

    return {"success": True}


@router.get("/tasks/{task_id}/config")
async def get_task_config(task_id: str):
    """获取任务配置（用于编辑回显）"""
    task_manager = _get_task_manager()
    config = await task_manager.get_task_config(task_id)

    if not config:
        raise HTTPException(status_code=404, detail="Task not found")

    return config


@router.put("/tasks/{task_id}/config")
async def update_task_config(task_id: str, update: TaskConfigUpdateRequest):
    """更新 PENDING 任务的配置"""
    task_manager = _get_task_manager()

    # 检查任务状态
    status_info = await task_manager.get_task_status(task_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Task not found")

    if status_info["status"] != TaskStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Can only edit PENDING tasks, current status: {status_info['status']}",
        )

    update_data = update.model_dump(exclude_unset=True)
    success = await task_manager.update_task_config(task_id, update_data)

    if not success:
        raise HTTPException(status_code=500, detail="Update failed")

    return {"success": True, "message": "Config updated"}


# ============ 批量操作 ============


@router.post("/batch/start")
async def batch_start_tasks():
    """启动所有 PENDING 任务（串行执行）"""
    task_manager = _get_task_manager()
    count = await task_manager.start_all_pending()
    return {"success": True, "started": count, "message": f"Queued {count} tasks for execution"}


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
