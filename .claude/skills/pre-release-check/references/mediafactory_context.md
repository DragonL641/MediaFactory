# MediaFactory 项目上下文

本文档提供 MediaFactory 项目的架构、设计和约定信息，用于代码审查时理解项目上下文。

---

## 项目定位

**MediaFactory**（前身为 VideoDub）是一个专业的多媒体处理工具，主要运行场景是用户的本地设备。

### 核心定位原则

1. **轻量化工具**: 避免过度设计，优先功能正确性
2. **本地优先**: 主要功能在本地执行，不依赖云端
3. **高可维护性**: 代码简洁清晰，易于理解和修改
4. **模块化设计**: 支持横向扩展，新功能易于添加

### 质量优先级

```
功能正确性 > 代码可维护性 > 性能优化
```

---

## 架构层次

MediaFactory 采用 5 层架构：

```
┌─────────────────────────────────────────────┐
│           表现层 (Presentation Layer)       │
│         (GUI - customtkinter)                │
│              src/mediafactory/gui/           │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┴──────────────────────────┐
│           服务层 (Service Layer)            │
│     (业务逻辑，GUI → Tool 桥接)              │
│       src/mediafactory/gui/services/         │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┴──────────────────────────┐
│           工具层 (Tool Layer - Application)  │
│  ┌─────────────────────────────────────┐   │
│  │  组合工具 (Composite Tools)         │   │
│  │  SubtitleGeneratorTool (v2.0)      │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  原子工具 (Atomic Tools)            │   │
│  │  AudioExtractorTool                 │   │
│  │  SpeechToTextTool                   │   │
│  │  TranslatorTool                     │   │
│  └─────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┴──────────────────────────┐
│           流水线层 (Pipeline Layer)          │
│  (编排 - ProcessingStages)                   │
│       src/mediafactory/pipeline/             │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┴──────────────────────────┐
│           引擎层 (Engine Layer - Infrastructure)│
│  AudioEngine, RecognitionEngine,             │
│  TranslationEngine, SRTEngine                │
│         src/mediafactory/engine/             │
└─────────────────────────────────────────────┘
```

### 层次职责

| 层次 | 职责 | 不应做的事 |
|------|------|------------|
| **表现层** | 用户交互、显示更新 | 直接调用 Engine、处理业务逻辑 |
| **服务层** | 业务逻辑编排、GUI-Tool 桥接 | 处理 UI 细节、直接操作资源 |
| **工具层** | 功能组合、原子操作 | 直接 UI 操作、底层计算 |
| **流水线层** | 阶段编排、进度跟踪 | 业务逻辑、资源管理 |
| **引擎层** | 底层计算、资源操作 | 业务规则、UI 交互 |

---

## 核心设计模式

### 1. 工具模式 (Tool Pattern)

**位置**: `src/mediafactory/core/tool.py`

所有处理工具继承 `Tool` 抽象基类：

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @abstractmethod
    def execute(self, context: ToolContext) -> ToolOutput: ...
```

**内置工具**:
- `AudioExtractorTool`: 音频提取（原子工具）
- `SpeechToTextTool`: 语音转文字（原子工具）
- `TranslatorTool`: 翻译（原子工具）
- `SubtitleGeneratorTool`: 字幕生成（组合工具，使用 Pipeline）

### 2. 流水线模式 (Pipeline Pattern)

**位置**: `src/mediafactory/pipeline/`

流水线由多个 `ProcessingStage` 组成：

```python
pipeline = Pipeline.create_default(
    audio_engine=AudioEngine(),
    recognition_engine=RecognitionEngine(),
    translation_engine=TranslationEngine(),
    srt_engine=SRTEngine(),
)

result = pipeline.execute(context)
```

**流水线阶段**（v3.0+ 进度范围）:
- `ModelLoadingStage` (0-10%): 加载 Whisper 模型
- `AudioExtractionStage` (10-20%): 提取音频
- `TranscriptionStage` (20-70%): 语音转文字（主要工作）
- `TranslationStage` (70-95%): 翻译
- `SRTGenerationStage` (95-100%): 生成 SRT
- `ModelCleanupStage`: 清理模型资源

### 3. 事件总线模式 (Event Bus Pattern)

**位置**: `src/mediafactory/core/events.py`

```python
event_bus = get_event_bus()
event_bus.publish(Event(
    type=EventType.TOOL_EXECUTION_START,
    source=self.name,
    data={"input_path": input_path}
))
```

**标准事件类型**:
- `TOOL_EXECUTION_START`: 工具开始执行
- `TOOL_EXECUTION_PROGRESS`: 进度更新
- `TOOL_EXECUTION_COMPLETE`: 工具执行完成
- `TOOL_EXECUTION_ERROR`: 工具执行错误
- `TOOL_EXECUTION_CANCELLED`: 工具执行取消

### 4. 插件注册模式 (Plugin Registry Pattern)

**位置**: `src/mediafactory/core/plugin.py`

```python
@get_plugin_registry().register
class MyCustomTool(Tool):
    name = "my_custom_tool"
    # ...
```

---

## 关键约定

### 1. 配置管理

**配置系统**:
- **格式**: TOML (`config.toml`)
- **库**: Pydantic v2
- **环境变量**: `MF_` 前缀（如 `MF_WHISPER_BEAM_SIZE=7`）

**配置访问**:
```python
# 新方式（推荐）
from mediafactory.config import get_config, update_config

config = get_config()
beam_size = config.whisper.beam_size
update_config(whisper__beam_size=7)

# 遗留方式（服务层）
from mediafactory.gui.services import ConfigurationService

config = ConfigurationService.get_instance()
backend = config.get("backend", "openai")
```

### 2. 进度跟踪

**新协议** (v3.0+):
```python
from mediafactory.core.progress_protocol import ProgressCallback

def process(progress: ProgressCallback = NO_OP_PROGRESS):
    progress.update(50, "处理中...")
    if progress.is_cancelled():
        return
```

**GUI 进度桥**:
```python
from mediafactory.progress.bridge import create_gui_progress_bridge

progress_bridge = create_gui_progress_bridge(
    gui_observers=gui_observers,
    current_file_index=1,
    total_files=3,
)
```

### 3. 异常处理

**结构化异常层次**:
```python
from mediafactory.exceptions import (
    MediaFactoryError,        # 基类
    EngineError,              # 引擎层错误
    PipelineError,            # 流水线错误
    ToolError,                # 工具层错误
    ServiceError,             # 服务层错误
)

# 所有异常包含：
# - context: 错误上下文字典
# - suggestion: 修复建议
# - severity: 严重性级别
```

**异常包装器**:
```python
from mediafactory.core.exception_wrapper import wrap_exceptions

with wrap_exceptions(context={"file": path}, operation="process"):
    # 代码 - 异常自动转换为 MediaFactory 类型
    risky_operation()
```

### 4. 日志系统

**统一日志**:
```python
from mediafactory.logging import log_info, log_warning, log_error, log_error_with_context

log_info("处理开始")
log_error_with_context(
    "操作失败",
    exception_object,
    context={"file_path": path}
)
```

所有日志写入单个文件：`mediafactory_YYYYMMDD_HHMMSS.log`

### 5. 相对导入规则

**服务层导入工具**:
```python
# 正确（3个点）
from ...tools.audio_extractor import AudioExtractorTool

# 错误（4个点）
from ....tools.audio_extractor import AudioExtractorTool
```

---

## 特殊技术选型

### Faster Whisper (而非 OpenAI Whisper)

- **速度**: 快 4-6 倍
- **内存**: 更低的内存占用
- **MPS**: 不支持 Apple Silicon GPU（回退到 CPU）

### 无模型构建策略

- 翻译模型（2GB+）不捆绑在包中
- 模型必须通过 `scripts/download_model.py` 下载
- 模型位置: `./models` 目录

### 音频质量规范

- **采样率**: 48000Hz
- **声道**: 立体声 (2)
- **滤波器**: 高通 200Hz，低通 3000Hz

### TOML 配置系统

- **格式**: TOML
- **验证**: Pydantic v2
- **更新**: 双下划线表示法 (`update_config(whisper__beam_size=7)`)

---

## 关键文件位置

### 核心框架
- `src/mediafactory/core/tool.py`: Tool 抽象基类
- `src/mediafactory/core/engine.py`: Engine 抽象基类
- `src/mediafactory/core/events.py`: EventBus
- `src/mediafactory/core/plugin.py`: PluginRegistry

### 流水线
- `src/mediafactory/pipeline/pipeline.py`: Pipeline 类
- `src/mediafactory/pipeline/context.py`: ProcessingContext
- `src/mediafactory/pipeline/stages.py`: ProcessingStages

### 工具
- `src/mediafactory/tools/audio_extractor.py`: 音频提取工具
- `src/mediafactory/tools/speech_to_text.py`: 语音转文字工具
- `src/mediafactory/tools/translator.py`: 翻译工具
- `src/mediafactory/tools/subtitle_generator.py`: 字幕生成工具

### 引擎
- `src/mediafactory/engine/audio.py`: 音频处理引擎
- `src/mediafactory/engine/recognition.py`: 语音识别引擎
- `src/mediafactory/engine/translation.py`: 翻译引擎
- `src/mediafactory/engine/srt.py`: SRT 生成引擎

### GUI
- `src/mediafactory/gui/main_window.py`: 主窗口
- `src/mediafactory/gui/services/`: 服务层
- `src/mediafactory/gui/tabs/`: 选项卡面板
- `src/mediafactory/gui/widgets/`: 可重用组件

---

## 代码审查关注点

### MediaFactory 特定检查

1. **资源清理**: Pipeline 执行后是否调用 ModelCleanupStage
2. **层次分离**: GUI 是否直接调用 Engine（应通过 Service）
3. **配置刷新**: 跨服务配置是否正确 reload()
4. **进度跟踪**: 是否使用 GUIProgressBridge
5. **异常处理**: 是否使用 MediaFactoryError 层次
6. **日志记录**: 是否使用统一日志系统
7. **相对导入**: 服务层是否使用 3 个点导入
8. **组件生命周期**: GUI 组件 destroy 后是否正确处理

### 避免的反模式

1. ❌ GUI 直接调用 Engine
2. ❌ 硬编码配置值
3. ❌ 裸 except 块
4. ❌ 全局状态共享
5. ❌ 过度自研（可用现成库替代）
6. ❌ 4 个点的相对导入
7. ❌ 未验证的用户输入

---

## 性能考量

### 批处理优化

- LLM 翻译支持批处理（`llm_translation.batch_size` 配置）
- 批处理间添加 5 秒延迟避免速率限制

### GPU 加速

- CUDA: 使用 float16
- CPU: 使用 int8 量化
- MPS: 不支持（Faster Whisper 限制）

---

## 测试策略

### 测试覆盖重点

1. 核心工具（SubtitleGeneratorTool）
2. 回退机制（翻译失败回退）
3. 并发场景（多线程配置访问）
4. 边界条件（空文件、损坏文件）

### 测试标记

- `unit`: 单元测试
- `integration`: 集成测试
- `e2e`: 端到端测试
- `slow`: 慢速测试
- `requires_network`: 需要网络
