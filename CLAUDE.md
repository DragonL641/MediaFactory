# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

本文件为 Claude Code (claude.ai/code) 在处理本仓库代码时提供指导。

## 项目概述

**MediaFactory**（前身为 VideoDub）是一个多媒体处理平台，用于字幕生成和视频相关任务。提供统一的架构，包括服务层、流水线层和引擎层，用于处理音频提取、语音转文字转录（使用 Faster Whisper）、翻译（本地模型和 LLM API）和字幕生成等任务。

**平台支持**：macOS、Windows（Linux 暂不支持）

**关键架构说明：**
- **Electron + FastAPI 架构**：React + TypeScript 前端通过 HTTP/WebSocket 与 FastAPI 后端通信
- **三层架构**：Frontend (Electron) → API (FastAPI) → Service → Pipeline → Engine
- **单一包**：`src/mediafactory/` 包含所有后端代码（API、服务、流水线、引擎）
- 使用 **Faster Whisper** 而非 OpenAI Whisper，转录速度快 4-6 倍
- LLM 翻译使用**逐句顺序翻译**，每句添加上下文参考以提高翻译质量
- 构建产物**包含所有 ML 依赖**（torch, transformers, faster-whisper 等），开箱即用
- 翻译模型文件（2GB+）不捆绑在包中，用户在设置页面自行下载
- **基于 TOML 的配置**，使用 Pydantic v2 模型
- **模型按需下载**：用户在设置页面自行下载所需模型（语音识别、翻译模型等）

### 架构层次

```
┌───────────────────────────────────────────────────────────┐
│         前端层 (Electron + React + TypeScript)             │
│                    src/electron/                          │
│  main/ (主进程) | preload/ | renderer/ (React + Ant Design)│
└──────────────────────────┬────────────────────────────────┘
                           │ HTTP/WebSocket (127.0.0.1:8765)
                           ▼
┌───────────────────────────────────────────────────────────┐
│           API 层 (FastAPI + WebSocket)                     │
│              src/mediafactory/api/                         │
│  routes/ | schemas.py | websocket.py | task_manager.py     │
│              task_executor.py                              │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────┴────────────────────────────────┐
│           服务层 (Service Layer)                           │
│     (异步桥接、配置管理、进度适配)                          │
│         src/mediafactory/services/                         │
│  SubtitleService | AudioService | TranslationService | ... │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────┴────────────────────────────────┐
│           流水线层 (Pipeline Layer)                        │
│  (编排 - ProcessingStages)                                 │
│         src/mediafactory/pipeline/                         │
│  ModelLoading → AudioExtraction →                         │
│  Transcription → Translation → SRT                        │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────┴────────────────────────────────┐
│           引擎层 (Engine Layer)                            │
│  AudioEngine, RecognitionEngine,                           │
│  TranslationEngine, SRTEngine, ASSEngine,                 │
│  VideoComposer, VideoEnhancementEngine                     │
│         src/mediafactory/engine/                           │
└───────────────────────────────────────────────────────────┘
```

### 事件流

```
用户操作 → Electron (React)
               │
               ▼ HTTP/WS
          FastAPI Server
               │
               ▼
          TaskExecutor → Service → Pipeline → Stage → Engine
               │
               ▼
          WebSocket → Electron (实时进度更新)
```

### 流水线阶段（v3.0+ 进度范围）

- `ModelLoadingStage` (0-10%)：加载 Whisper 模型
- `AudioExtractionStage` (10-20%)：从视频提取音频，使用高质量设置（48000Hz，立体声，滤波器）
- `TranscriptionStage` (20-70%)：使用 Faster Whisper 进行语音转文字，带进度跟踪（主要工作）
- `TranslationStage` (70-95%)：翻译到目标语言，自动回退
- `SRTGenerationStage` (95-100%)：生成字幕文件
- `ModelCleanupStage`：释放模型资源

**注意**：`ModelLoadingStage` 和 `ModelCleanupStage` 定义在 `stages.py` 中，但未在 `pipeline/__init__.py` 中公开导出。

## 常用命令

### 开发

MediaFactory 使用 `dependency-groups` 进行依赖分组：

| 组名 | 内容 | 命令 |
|------|------|------|
| **bundle** | 打包依赖（含 ML，开箱即用） | `uv sync --group bundle` |
| **core** | 核心依赖（所有功能，含 ML） | `uv sync --group core` |
| **dev** | 开发依赖（开发工具） | `uv sync --group dev` |

```bash
# 开发者：安装所有依赖
uv sync --all-groups

# 清除 Python 缓存（更改导入后很重要）
find src/mediafactory -name "*.pyc" -delete
find src/mediafactory -name "__pycache__" -type d -exec rm -rf {} +

# 运行测试（pytest 配置在 pyproject.toml 中）
pytest                              # 运行所有测试
pytest -v                           # 详细输出
pytest -m "unit"                    # 仅运行单元测试
pytest -m "not slow"                # 排除慢速测试
pytest --cov=src/mediafactory       # 运行并生成覆盖率报告
pytest tests/test_basic_flow.py     # 运行单个测试文件
pytest -k "test_translation"        # 运行匹配名称的测试

# 清理构建产物和缓存
rm -rf build/ dist/ *.egg-info/ .pytest_cache/ htmlcov/ .coverage

# 代码质量
uv run black src/ tests/ && uv run isort src/ tests/    # 格式化代码
uv run flake8 src/ tests/ && uv run bandit -r src/      # 运行 lint
uv run mypy src/                                          # 类型检查
```

### 构建可执行文件

```bash
# Python 后端构建（通过入口脚本，内部调用 PyInstaller）
uv run python scripts/build/build_darwin.py          # macOS
uv run python scripts/build/build_win.py              # Windows

# Electron 前端构建（需要 Node.js）
cd src/electron && npm run build

# 清理所有构建产物
rm -rf build/ dist/ release/
```

### 版本管理

项目使用 **pyproject.toml 作为单一真相源** 管理版本号：
- **版本定义**：`pyproject.toml` 中的 `project.version`
- **统一读取**：`_version.py` 是唯一的版本读取器（支持 tomli/tomllib 解析 + importlib.metadata 回退 + 简单解析器 fallback）
- **所有消费者**通过 `_version.py` 获取版本：`from mediafactory._version import get_version`
- **跨栈同步**：`sync_version.py` 将版本同步到 `package.json` 和 `BUILD.md`

```bash
python scripts/utils/sync_version.py --check     # 检查版本一致性
python scripts/utils/sync_version.py 0.3.0       # 更新所有文件版本号
```

### 模型管理（运行前必需）
```bash
python scripts/utils/download_model.py --list                    # 列出已下载模型
python scripts/utils/download_model.py facebook/m2m100_1.2B     # 下载模型
python scripts/utils/download_model.py facebook/m2m100_1.2B --delete  # 删除模型
python scripts/utils/download_model.py facebook/m2m100_1.2B --source=https://hf-mirror.com  # 中国镜像
```

### 运行应用程序
```bash
# 启动 API 服务器（为 Electron 前端提供后端）
python -m mediafactory          # 直接运行模块（推荐）
mediafactory                    # 使用 console script

# Electron 前端开发模式
cd src/electron && npm run dev
```

## 架构

### 服务层

**服务层**（`src/mediafactory/services/`）：API 层与处理逻辑之间的桥梁

- `SubtitleService`：完整字幕生成流程（音频 → 转录 → 翻译 → SRT）
- `AudioService`：音频提取
- `TranscriptionService`：语音转文字
- `TranslationService`：翻译（文本/SRT，本地 + LLM API）
- `VideoEnhancementService`：视频画质增强

**调用模式**：Service 创建 Pipeline 并执行，在 `run_in_executor` 中运行以避免阻塞 async 事件循环：
```python
result = await loop.run_in_executor(None, pipeline.execute, context)
```

### API 层（`src/mediafactory/api/`）

- `main.py`：FastAPI 应用入口，生命周期管理，WebSocket 端点
- `routes/config.py`：配置管理 API（读取、更新、保存、LLM 预设）
- `routes/models.py`：模型管理 API
- `routes/processing.py`：任务处理 API（字幕、音频、转录、翻译、增强）
- `schemas.py`：Pydantic 数据模型（TaskConfig、TaskProgress、TaskResult 等）
- `websocket.py`：WebSocket 连接管理器，实时进度推送
- `task_manager.py`：后台任务管理器（任务队列、状态跟踪、自动清理）
- `task_executor.py`：任务执行器，桥接 API 层和 Service 层

### 关键模块

**核心框架**（`src/mediafactory/core/`）：
- `exception_wrapper.py`：自动转换标准 Python 异常（`wrap_exceptions` 上下文管理器）
- `progress_protocol.py`：`ProgressCallback` 协议、`SimpleProgressCallback`、`NoOpProgressCallback`
- `resource_protocol.py`：`ResourceCleanupProtocol` 资源清理协议
- `tool.py`：`CancellationToken`（协作式取消）

**流水线**（`src/mediafactory/pipeline/`）：
- `pipeline.py`：`Pipeline` 编排类，`create_default()`、`create_transcription_only()` 等
- `context.py`：`ProcessingContext`、`ProcessingResult`
- `stage.py`：`ProcessingStage` 抽象基类
- `stages.py`：具体阶段实现

**引擎层**（`src/mediafactory/engine/`）：
- `AudioEngine`：ffmpeg 音频提取（48000Hz 立体声，语音增强滤波器）
- `RecognitionEngine`：Faster Whisper 语音识别
- `TranslationEngine`（基类）、`LocalTranslationEngine`、`LLMTranslationEngine`
- `SRTEngine`、`ASSEngine`：字幕文件生成
- `VideoComposer`：视频合成
- `VideoEnhancementEngine`：视频画质增强
- `enhancement/`：`RealESRGANEnhancer`（超分辨率）、`Denoiser`（降噪）、`TemporalSmoother`（时序平滑）

**LLM 翻译**（`src/mediafactory/llm/`）：
- 统一 OpenAI 兼容后端架构：`TranslationBackend`（ABC）→ `OpenAICompatibleBackend`
- `initialize_llm_backend()`：集中后端初始化
- 预设服务：OpenAI、DeepSeek、GLM、通义千问、Moonshot、自定义
- 翻译方式：批量翻译 + 递归验证 + 本地回退

**其他**：
- `config/`：Pydantic v2 配置系统（TOML 存储，`MF_` 环境变量前缀）
- `logging/`：统一日志系统（loguru，自动清理过期日志，配置审计）
- `models/`：Faster Whisper 模型选择和本地翻译模型发现
- `constants.py`：`BackendConfigMapping`、`ToolConstants` 等
- `resource_manager.py`：Whisper 模型资源管理（单例，上下文管理器）
- `utils/`：transformers 配置、视频扫描器、prompt 加载器
- `resources/prompts/`：LLM 提示模板（Markdown + `${variable}` 语法）
- `batch.py`：`BatchProcessor` 批处理

### 进度系统

**进度协议**（`core/progress_protocol.py`）：层分离的中性接口
- `ProgressCallback`：将引擎与 GUI 特定概念解耦的协议
- `NoOpProgressCallback`：不需要进度时的无操作实现

**进度映射**（在 `pipeline/stages.py` 中实现）：
- 阶段范围映射：`model_loading`(0-10%) → `audio_extraction`(10-20%) → `transcription`(20-70%) → `translation`(70-95%) → `srt_generation`(95-100%)
- WebSocket 实时推送：`TaskManager` 通过 WebSocket 将进度实时推送到前端

### 异常处理（`src/mediafactory/exceptions.py`）

- `MediaFactoryError`：基类（`message`、`context`、`severity`）
  - `ErrorSeverity`：FATAL、RECOVERABLE、WARNING
- 核心类型：`ProcessingError`、`ConfigurationError`、`ValidationError`、`ModelError`、`APIError`、`NetworkError`、`AuthenticationError`、`RateLimitError`、`OperationCancelledError`
- `exception_wrapper.py`：`wrap_exceptions` 上下文管理器自动转换标准异常

### 配置系统（`src/mediafactory/config/`）

- Pydantic v2 模型，TOML 格式存储（`config.toml`）
- `AppConfigManager`：集中管理器，支持嵌套更新（双下划线表示法）
- 环境变量覆盖：`MF_` 前缀（例如 `MF_WHISPER_BEAM_SIZE=7`）
- 配置变更自动记录审计日志，敏感字段脱敏
```python
from mediafactory.config import get_config, update_config, save_config, reload_config

config = get_config()
update_config(whisper__beam_size=7)
save_config()
```

### 日志系统

所有日志写入 `logs/LOG-YYYY-MM-DD-HHMM.log`，基于 loguru：
- **统一导入**：`from mediafactory.logging import log_info, log_error, log_error_with_context`
- **自动初始化**：首次导入时自动初始化
- **日志清理**：每次启动自动清理，保留最近 30 天或最多 20 个文件
- **API 日志桥接**：`setup_logging_intercept()` 将 API 层标准 logging 重定向到 loguru
- **审计日志**：配置变更自动记录，`api_key`/`password`/`secret`/`token` 等敏感字段自动脱敏

### 模型管理

- 翻译模型文件（2GB+）不捆绑在包中，用户在设置页面自行下载
- 模型从 `./models` 目录加载，启动时自动扫描并写入 `config.toml`
- `ModelResourceManager`：单例模式，`whisper_model()` 上下文管理器确保正确释放
- 硬件自动检测：CUDA (NVIDIA GPU, float16) / CPU (int8 量化)；**Faster Whisper 不支持 MPS**

### 构建系统

**PyInstaller**（`scripts/pyinstaller/installer_simple.spec`）：
- 完整打包所有依赖（含 ML：torch, transformers, faster-whisper 等），开箱即用
- 自定义钩子在 `scripts/pyinstaller/hooks/`

**Electron**（`src/electron/`）：
- Electron + React + TypeScript + Ant Design
- `electron.vite.config.ts` + `electron-builder.yml`

**FFmpeg**：统一使用 `imageio-ffmpeg`，不依赖系统 FFmpeg

## 测试

- 框架：pytest 带覆盖率
- 标记：`unit`、`integration`、`e2e`、`slow`、`requires_network`
- 关键测试：`test_basic_flow.py`、`test_translation_accuracy.py`、`test_local_models.py`、`test_engine_robustness.py`、`test_logging.py`

## 重要实现细节

### Faster Whisper 迭代器消费
`model.transcribe()` 返回 `(segments_generator, info)`，生成器**必须被消费**：
```python
segments_generator, info = model.transcribe(audio_path, **kwargs)
segments_list = list(segments_generator)  # 必须消费
```

### 添加新的 LLM 服务预设
无需创建新的后端类，只需在 `constants.py` 的 `BackendConfigMapping.BASE_URL_PRESETS` 添加预设：
```python
"my_service": {
    "display_name": "我的服务",
    "base_url": "https://api.myservice.com/v1",
    "model_examples": ["model-1", "model-2"],
},
```

### 进度回调使用模式
```python
from mediafactory.core.progress_protocol import ProgressCallback, NO_OP_PROGRESS

def process_with_progress(data: str, progress: ProgressCallback = NO_OP_PROGRESS) -> str:
    progress.update(0, "启动中...")
    for i, item in enumerate(data):
        if progress.is_cancelled():
            return ""
        progress.update((i + 1) / len(data) * 100, f"处理中 {i+1}/{len(data)}")
    return result
```

### 线程安全取消模式
使用 `CancellationToken`（`core/tool.py`），而不是 `threading.Event()`。

## 重要说明

- 该项目仍处于原型开发阶段，**不需要考虑向后兼容性**
- 以功能性、可维护性优先，**避免过度设计**，优先使用现成开源库
- 技术架构选项必须用户审示并同意
- 不考虑 API 密钥明文存储等安全风险（本地工具）
- `scripts/` 仅用于构建和开发者调试，`src/` 业务代码不应调用 `scripts/` 下的脚本
- 代码注释使用中文，力求简单
- README.md 和 README_zh.md 必须同时更新
- 项目的包结构不能轻易变动，增包或减包需先知会开发者

## 开发规范

### 语言要求

**用户界面文本**：必须使用英文（按钮、标签、提示、错误消息等）
**代码注释和文档**：可使用中文
**日志消息**：可使用中文或英文

### 命名约定

- 变量/方法：英文 `snake_case`
- 类：英文 `PascalCase`
- 常量：英文 `UPPER_SNAKE_CASE`

### 配置刷新模式
当需要最新配置时，调用 `config.reload()` 获取最新的 `config.toml`。
