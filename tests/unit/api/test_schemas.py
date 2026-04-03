"""API schemas 数据模型测试

覆盖枚举值、模型创建、默认值和验证逻辑。
"""

import pytest
from pydantic import ValidationError

from mediafactory.api.schemas import (
    TaskConfig,
    TaskProgress,
    TaskResult,
    TaskStatus,
    TaskType,
    ProcessingStage,
)

pytestmark = [pytest.mark.unit]


# ============================================================================
# 1. TaskType 枚举
# ============================================================================


class TestTaskType:
    """TaskType 枚举值测试"""

    def test_subtitle(self):
        assert TaskType.SUBTITLE == "subtitle"

    def test_audio(self):
        assert TaskType.AUDIO == "audio"

    def test_transcribe(self):
        assert TaskType.TRANSCRIBE == "transcribe"

    def test_translate(self):
        assert TaskType.TRANSLATE == "translate"

    def test_enhance(self):
        assert TaskType.ENHANCE == "enhance"

    def test_download(self):
        assert TaskType.DOWNLOAD == "download"

    def test_all_members_count(self):
        assert len(TaskType) == 6

    def test_is_str_enum(self):
        """TaskType 继承 str，可以直接当字符串使用"""
        assert isinstance(TaskType.SUBTITLE, str)
        assert TaskType.SUBTITLE == "subtitle"


# ============================================================================
# 2. TaskStatus 枚举
# ============================================================================


class TestTaskStatus:
    """TaskStatus 枚举值测试"""

    def test_pending(self):
        assert TaskStatus.PENDING == "pending"

    def test_running(self):
        assert TaskStatus.RUNNING == "running"

    def test_completed(self):
        assert TaskStatus.COMPLETED == "completed"

    def test_failed(self):
        assert TaskStatus.FAILED == "failed"

    def test_cancelled(self):
        assert TaskStatus.CANCELLED == "cancelled"

    def test_all_members_count(self):
        assert len(TaskStatus) == 5


# ============================================================================
# 3. ProcessingStage 枚举
# ============================================================================


class TestProcessingStage:
    """ProcessingStage 枚举值测试"""

    def test_model_loading(self):
        assert ProcessingStage.MODEL_LOADING == "model_loading"

    def test_audio_extraction(self):
        assert ProcessingStage.AUDIO_EXTRACTION == "audio_extraction"

    def test_transcription(self):
        assert ProcessingStage.TRANSCRIPTION == "transcription"

    def test_translation(self):
        assert ProcessingStage.TRANSLATION == "translation"

    def test_srt_generation(self):
        assert ProcessingStage.SRT_GENERATION == "srt_generation"

    def test_video_enhancement(self):
        assert ProcessingStage.VIDEO_ENHANCEMENT == "video_enhancement"

    def test_all_members_count(self):
        assert len(ProcessingStage) == 6


# ============================================================================
# 4. TaskConfig 创建与默认值
# ============================================================================


class TestTaskConfig:
    """TaskConfig 模型创建与验证测试"""

    def test_create_with_required_fields(self):
        config = TaskConfig(task_type=TaskType.SUBTITLE, input_path="/video.mp4")
        assert config.task_type == TaskType.SUBTITLE
        assert config.input_path == "/video.mp4"

    def test_default_values(self):
        config = TaskConfig(task_type=TaskType.SUBTITLE, input_path="/video.mp4")
        assert config.source_lang == "auto"
        assert config.target_lang == "zh"
        assert config.use_llm is False
        assert config.llm_preset == "openai"
        assert config.input_text is None
        assert config.output_path is None
        assert config.audio_config is None
        assert config.subtitle_config is None
        assert config.enhancement_config is None

    def test_custom_values(self):
        config = TaskConfig(
            task_type=TaskType.TRANSLATE,
            input_path="/video.mp4",
            source_lang="en",
            target_lang="ja",
            use_llm=True,
            llm_preset="deepseek",
        )
        assert config.source_lang == "en"
        assert config.target_lang == "ja"
        assert config.use_llm is True
        assert config.llm_preset == "deepseek"

    def test_missing_task_type_raises(self):
        with pytest.raises(ValidationError):
            TaskConfig(input_path="/video.mp4")  # type: ignore[call-arg]

    def test_missing_input_path_raises(self):
        with pytest.raises(ValidationError):
            TaskConfig(task_type=TaskType.SUBTITLE)  # type: ignore[call-arg]

    def test_string_task_type_accepted(self):
        """str enum 支持字符串作为值传入"""
        config = TaskConfig(task_type="subtitle", input_path="/video.mp4")  # type: ignore[arg-type]
        assert config.task_type == TaskType.SUBTITLE

    def test_invalid_task_type_raises(self):
        with pytest.raises(ValidationError):
            TaskConfig(task_type="invalid_type", input_path="/video.mp4")  # type: ignore[arg-type]


# ============================================================================
# 5. TaskProgress 创建
# ============================================================================


class TestTaskProgress:
    """TaskProgress 模型测试"""

    def test_create_with_required_fields(self):
        progress = TaskProgress(
            task_id="task-1",
            status=TaskStatus.RUNNING,
            progress=50.0,
        )
        assert progress.task_id == "task-1"
        assert progress.status == TaskStatus.RUNNING
        assert progress.progress == 50.0

    def test_default_values(self):
        progress = TaskProgress(
            task_id="task-1",
            status=TaskStatus.PENDING,
            progress=0.0,
        )
        assert progress.message == ""
        assert progress.stage is None
        assert progress.file_index == 0
        assert progress.total_files == 1

    def test_with_all_fields(self):
        progress = TaskProgress(
            task_id="task-2",
            status=TaskStatus.RUNNING,
            progress=75.5,
            message="Transcribing...",
            stage=ProcessingStage.TRANSCRIPTION,
            file_index=2,
            total_files=5,
        )
        assert progress.message == "Transcribing..."
        assert progress.stage == ProcessingStage.TRANSCRIPTION
        assert progress.file_index == 2
        assert progress.total_files == 5

    def test_progress_boundary_zero(self):
        progress = TaskProgress(task_id="t", status=TaskStatus.RUNNING, progress=0.0)
        assert progress.progress == 0.0

    def test_progress_boundary_hundred(self):
        progress = TaskProgress(task_id="t", status=TaskStatus.COMPLETED, progress=100.0)
        assert progress.progress == 100.0

    def test_progress_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            TaskProgress(task_id="t", status=TaskStatus.RUNNING, progress=101.0)

    def test_progress_negative_raises(self):
        with pytest.raises(ValidationError):
            TaskProgress(task_id="t", status=TaskStatus.RUNNING, progress=-1.0)


# ============================================================================
# 6. TaskResult 创建
# ============================================================================


class TestTaskResult:
    """TaskResult 模型测试"""

    def test_success_result(self):
        result = TaskResult(
            task_id="task-1",
            success=True,
            output_path="/output/subtitle.srt",
        )
        assert result.task_id == "task-1"
        assert result.success is True
        assert result.output_path == "/output/subtitle.srt"
        assert result.error is None
        assert result.error_type is None
        assert result.metadata == {}

    def test_failure_result(self):
        result = TaskResult(
            task_id="task-2",
            success=False,
            error="Transcription failed",
            error_type="ProcessingError",
        )
        assert result.success is False
        assert result.error == "Transcription failed"
        assert result.error_type == "ProcessingError"
        assert result.output_path is None

    def test_metadata_default_empty(self):
        result = TaskResult(task_id="t", success=True)
        assert result.metadata == {}

    def test_metadata_custom(self):
        result = TaskResult(
            task_id="t",
            success=True,
            metadata={"duration": 120, "segments": 45},
        )
        assert result.metadata["duration"] == 120
        assert result.metadata["segments"] == 45
