# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

本文件为 Claude Code (claude.ai/code) 在处理本仓库代码时提供指导。

## 项目概述

**MediaFactory**（前身为 VideoDub）是一个多媒体处理平台，用于字幕生成和视频相关任务。提供统一的架构，包括服务层、流水线层和引擎层，用于处理音频提取、语音转文字转录（使用 Faster Whisper）、翻译（本地模型和 LLM API）和字幕生成等任务。

**平台支持**：macOS、Windows（Linux 暂不支持）

**关键架构说明：**
- **Electron + FastAPI 架构**：React + TypeScript 前端通过 HTTP/WebSocket 与 FastAPI 后端通信
- **三层架构**：Frontend (Electron) → API (FastAPI) → Service → Pipeline → Engine
- **单一包**：`mediafactory/` 包含所有后端代码（API、服务、流水线、引擎）
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
│           electron/ (main+preload) + src/ (React)          │
│  main/ (主进程) | preload/ | src/ (React + Ant Design)      │
└──────────────────────────┬────────────────────────────────┘
                           │ HTTP/WebSocket (127.0.0.1:8765)
                           ▼
┌───────────────────────────────────────────────────────────┐
│           API 层 (FastAPI + WebSocket)                     │
│              mediafactory/api/                         │
│  routes/ | schemas.py | websocket.py | task_manager.py     │
│              task_manager.py（含进度适配器）                │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────┴────────────────────────────────┐
│           服务层 (Service Layer)                           │
│     (异步桥接、配置管理、进度适配)                          │
│         mediafactory/services/                         │
│  services/runner.py（RUNNERS 按 TaskType 分发）            │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────┴────────────────────────────────┐
│           流水线层 (Pipeline Layer)                        │
│  (编排 - ProcessingStages)                                 │
│         mediafactory/pipeline/                         │
│  ModelLoading → AudioExtraction →                         │
│  Transcription → PostProcess → Translation → SRT          │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────┴────────────────────────────────┐
│           引擎层 (Engine Layer)                            │
│  AudioEngine, RecognitionEngine, PostProcessEngine,        │
│  TranslationEngine, SRTEngine, ASSEngine,                 │
│  VTTEngine, VideoEnhancementEngine                          │
│         mediafactory/engine/                           │
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
          TaskManager → runner → Pipeline → Stage → Engine
               │
               ▼
          WebSocket → Electron (实时进度更新)
```

### 流水线阶段与进度权重

各 stage 的全局进度区间由 `Pipeline` 按自身 stage 组合对 `STAGE_WEIGHTS`（`pipeline/pipeline.py`）归一化得出——同一 stage 在不同流程中区间不同（如 translation 在字幕全流程约占 68-95%，在翻译-only 流程占 0-83%）：

- `ModelLoadingStage`（权重 5）：加载 Whisper 模型
- `AudioExtractionStage`（权重 10）：从视频提取音频，使用高质量设置（48000Hz，立体声，滤波器）
- `TranscriptionStage`（权重 40）：使用 Faster Whisper 进行语音转文字，带进度跟踪（主要工作）
- `PostProcessStage`（权重 10）：智能分句（stable-ts）
- `TranslationStage`（权重 25）：翻译到目标语言，自动回退
- `SRTGenerationStage`（权重 5）：生成字幕文件（SRT/ASS/VTT）

**注意**：`ModelLoadingStage` 定义在 `stages.py` 中并在 `pipeline.py` 工厂方法里实例化，但未在 `pipeline/__init__.py` 中公开导出（引用需从 `stages` 导入）。音频提取与视频增强为单动作流程，由 runner 直调引擎，不走 Pipeline。模型释放在 Pipeline 的 `finally: context.cleanup()` 统一执行。

## 常用命令

### 开发

MediaFactory 使用 `dependency-groups` + `include-group` 进行依赖分组，层级关系：
`runtime`（基础）→ `bundle`（= runtime）→ `core`（runtime + ML）→ `dev`（工具）

| 组名 | 内容 | 命令 |
|------|------|------|
| **runtime** | 基础运行时（与 `[project.dependencies]` 同步） | — |
| **bundle** | 打包依赖（= runtime，用于 PyInstaller 验证） | `uv sync --group bundle` |
| **core** | 核心依赖（runtime + ML） | `uv sync --group core` |
| **dev** | 开发依赖（开发工具） | `uv sync --group dev` |

```bash
# 开发者：安装所有依赖
uv sync --all-groups

# 清除 Python 缓存（更改导入后很重要）
find mediafactory -name "*.pyc" -delete
find mediafactory -name "__pycache__" -type d -exec rm -rf {} +

# 运行测试（pytest 配置在 pyproject.toml 中）
pytest                              # 运行所有测试
pytest -v                           # 详细输出
pytest -m "unit"                    # 仅运行单元测试
pytest -m "not slow"                # 排除慢速测试
pytest --cov=mediafactory       # 运行并生成覆盖率报告
pytest tests/unit/test_constants.py  # 运行单个测试文件
pytest -k "test_translation"        # 运行匹配名称的测试
# CI 只跑单元测试（跳过默认 addopts 中的覆盖率配置）：
uv run pytest tests/unit/ --override-ini="addopts=" --cov=mediafactory --cov-report=xml

# 清理构建产物和缓存
rm -rf build/ dist/ *.egg-info/ .pytest_cache/ htmlcov/ .coverage

# 代码质量
uv run black mediafactory/ tests/ && uv run isort mediafactory/ tests/    # 格式化代码
uv run flake8 mediafactory/ tests/ && uv run bandit -r mediafactory/      # 运行 lint
uv run mypy mediafactory/                                          # 类型检查
```

### 构建可执行文件

```bash
# Python 后端构建（通过入口脚本，内部调用 PyInstaller）
uv run python scripts/build/build_darwin.py          # macOS
uv run python scripts/build/build_win.py              # Windows

# Electron 前端构建（需要 Node.js ≥20.19.0，package.json 在仓库根目录）
npm run dev          # 启动 Electron 应用（自动拉起 Python 后端）
npm run typecheck    # TS 类型检查（electron/main、preload、src 三份 tsconfig）
npm run lint         # ESLint（仅 electron/）

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

# Electron 前端开发模式（根目录运行；开发模式下 Electron 会 spawn
# .venv/bin/python -m uvicorn mediafactory.api.main:get_app，因此需先 uv sync）
npm run dev
```

## 架构

### 服务层

**服务层**（`mediafactory/services/`，Phase 3 收敛后仅两个模块）：
- `runner.py`：统一任务执行入口——`RUNNERS` 注册表按 TaskType 分发到 `run_subtitle/run_audio/run_transcribe/run_translate/run_enhance`；组装 `ProcessingContext`、选择 Pipeline 工厂或直调引擎（audio/enhance 单动作不走 Pipeline）、LLM 降级链、readiness 前置检查、模块级引擎缓存。**Pipeline 结果原样透传、不重包装**；直调路径异常上抛由 TaskManager 统一捕获
- `models.py`：模型状态聚合（`ModelStatusService.get_readiness`）与 LLM 连接测试

**调用模式**：runner 在 `run_in_executor` 中运行同步 Pipeline：
```python
result = await loop.run_in_executor(None, pipeline.execute, context)
```

### API 层（`mediafactory/api/`）

- `main.py`：FastAPI 应用入口，生命周期管理，WebSocket 端点
- `routes/config.py`：配置管理 API（读取、更新、保存、LLM 预设）
- `routes/models.py`：模型管理 API
- `routes/processing.py`：任务处理 API（字幕、音频、转录、翻译、增强）
- `schemas.py`：Pydantic 数据模型（TaskConfig、TaskProgress、TaskResult 等）
- `websocket.py`：WebSocket 连接管理器，实时进度推送
- `task_manager.py`：后台任务管理器（SQLite 持久队列 + `SimpleProgressAdapter` 进度适配、`get_task_manager` 单例装配 WorkerProcessExecutor；write-through 落库，重启 `recover()` 恢复队列）
- `task_store.py`：SQLite 任务持久层（任务表 CRUD、队列标记 queued_at、崩溃恢复查询）
- `worker.py`：执行器接缝（InlineExecutor 进程内 / WorkerProcessExecutor spawn 子进程）+ 子进程侧任务执行与进度回传
- `download_task.py`：模型下载后台任务（立即执行不进队列，带进度节流）

### 关键模块

**核心框架**（`mediafactory/core/`）：
- `exception_wrapper.py`：自动转换标准 Python 异常（`wrap_exceptions` 上下文管理器）
- `progress_protocol.py`：`ProgressCallback` 协议、`NoOpProgressCallback`
- `error_utils.py`：`sanitize_error()` 异常转用户消息
- `tool.py`：`CancellationToken`（协作式取消）

**流水线**（`mediafactory/pipeline/`）：
- `pipeline.py`：`Pipeline` 编排类，工厂方法：`create_default()`（字幕 6 stage）、`create_transcribe_standalone()`（转录 4 stage）、`create_translation_only()`（字幕翻译 2 stage）
- `context.py`：`ProcessingContext`、`ProcessingResult`
- `stage.py`：`ProcessingStage` 抽象基类
- `stages.py`：具体阶段实现

**引擎层**（`mediafactory/engine/`）：
- `AudioEngine`：ffmpeg 音频提取（48000Hz 立体声，语音增强滤波器）
- `RecognitionEngine`：Faster Whisper 语音识别
- `PostProcessEngine`：stable-ts 智能分句
- `TranslationEngine`：统一翻译引擎，通过 `use_local_models_only` 和 `use_llm_backend` 参数切换本地翻译/LLM API 模式
- `SRTEngine`、`ASSEngine`、`VTTEngine`：字幕文件生成
- `VideoEnhancementEngine`：视频画质增强
- `enhancement/`：`RealESRGANEnhancer`（超分辨率）、`Denoiser`（降噪）、`TemporalSmoother`（时序平滑）

**LLM 翻译**（`mediafactory/llm/`）：
- 统一 OpenAI 兼容后端架构：`TranslationBackend`（ABC）→ `OpenAICompatibleBackend`
- `initialize_llm_backend()`：集中后端初始化
- 预设服务：OpenAI、DeepSeek、GLM、通义千问、Moonshot、自定义
- 翻译方式：批量翻译 + 递归验证 + 本地回退

**其他**：
- `config/`：Pydantic v2 配置系统（TOML 存储，`MF_` 环境变量前缀），包含 `PostProcessConfig`（分句配置）
- `logging/`：统一日志系统（loguru，自动清理过期日志，配置审计）
- `models/`：模型管理（`model_registry` 注册表、`whisper_runtime`/`translation_runtime` 运行时、`model_download` 下载、`local_models` 本地模型发现）
- `i18n.py` + `locales/`：轻量 i18n，后端用户可见消息统一用 `t("key")`，语言偏好读自 config.toml，JSON 字典实现（前端则用 react-i18next + `src/locales/`）
- `core/error_utils.py`：`sanitize_error()` 将异常转为用户友好消息（Service/API 层共用）
- `constants.py`：`BackendConfigMapping`（含 `BASE_URL_PRESETS` LLM 服务预设）、`LANGUAGE_NAMES` 等语言常量
- `resource_manager.py`：`whisper_model()` 上下文管理器（加载/释放 Whisper 模型，无单例）
- `utils/`：语言名称映射（`resources.py`）、prompt 加载器
- `resources/prompts/`：LLM 提示模板（Markdown + `${variable}` 语法）

### 进度系统

**进度协议**（`core/progress_protocol.py`）：层分离的中性接口
- `ProgressCallback`：将引擎与 GUI 特定概念解耦的协议
- `NoOpProgressCallback`：不需要进度时的无操作实现

**进度映射**（在 `pipeline/pipeline.py` 中实现）：
- 阶段范围映射：`model_loading`(0-10%) → `audio_extraction`(10-20%) → `transcription`(20-60%) → `postprocess`(60-70%) → `translation`(70-95%) → `srt_generation`(95-100%)
- WebSocket 实时推送：`TaskManager` 通过 WebSocket 将进度实时推送到前端

### 异常处理（`mediafactory/exceptions.py`）

- `MediaFactoryError`：基类（`message`、`context`）
- 核心类型：`ProcessingError`（默认 RECOVERABLE）、`ConfigurationError`（默认 FATAL）、`OperationCancelledError`（默认 WARNING）
- `exception_wrapper.py`：`wrap_exceptions` 上下文管理器自动转换标准异常

### 配置系统（`mediafactory/config/`）

- Pydantic v2 模型（普通 `BaseModel`，非 `BaseSettings`），TOML 格式存储（`config.toml`）
- `AppConfigManager`：集中管理器，支持嵌套更新（双下划线表示法）
- 配置变更自动记录审计日志，敏感字段脱敏
```python
from mediafactory.config import get_config, update_config, save_config, reload_config

config = get_config()
update_config(whisper__beam_size=7)
save_config()
```

### 日志系统

所有日志写入 `logs/LOG-YYYY-MM-DD-HHMM.log`，基于 loguru：

- **双日志模式（重要约定）**：
  - **API 层**（`api/` 目录）：使用 `logging.getLogger(__name__)`，通过 `InterceptHandler` 自动重定向到 loguru
  - **Service/Engine/Pipeline 层**：使用 `from mediafactory.logging import log_info, log_error` 直接调用 loguru
  - **不要**在 API 层文件中直接导入 loguru，**不要**在 Service/Engine 层使用标准 logging
- **自动初始化**：首次导入时自动初始化
- **日志清理**：每次启动自动清理，保留最近 30 天或最多 20 个文件
- **审计日志**：配置变更自动记录，`api_key`/`password`/`secret`/`token` 等敏感字段自动脱敏

### 模型管理

- 翻译模型文件（2GB+）不捆绑在包中，用户在设置页面自行下载
- 模型从 `./models` 目录加载，启动时自动扫描并写入 `config.toml`
- `whisper_model()`：上下文管理器确保 Whisper 模型正确释放（`resource_manager.py`）
- 硬件自动检测：CUDA (NVIDIA GPU, float16) / CPU (int8 量化)；**Faster Whisper 不支持 MPS**

### 构建系统

**PyInstaller**（`scripts/pyinstaller/installer_simple.spec`）：
- 完整打包所有依赖（含 ML：torch, transformers, faster-whisper 等），开箱即用
- 自定义钩子在 `scripts/pyinstaller/hooks/`

**Electron**（`electron/`）：
- Electron + React + TypeScript + Ant Design
- `electron.vite.config.ts` + `electron-builder.yml`

**FFmpeg**：统一使用 `imageio-ffmpeg`，不依赖系统 FFmpeg

## 测试

- 框架：pytest 带覆盖率
- 结构：`tests/unit/`（按模块分子目录：api、config、core、engine、llm、pipeline、services、utils）+ `tests/integration/`
- 标记：`unit`、`integration`、`slow`、`requires_ml`、`requires_network`（无 `e2e`）
- **契约测试安全网**（共 74 个，Phase 1-3 结构性重构与 Phase 1 持久化/worker 重构的回归防线——**改动 runner/task_manager/task_store/worker/pipeline/download_task 前先确认这些测试全绿**）：`tests/unit/services/test_runner_contract.py`（21 个：5 个 runner 全覆盖、LLM 三分支、字段改名映射、失败透传）、`tests/unit/api/test_task_manager_contract.py`（9 个：状态机/CANCELLED 不变量/串行队列/取消出队）、`tests/unit/api/test_download_task.py`（3 个：成功/失败/节流）、`tests/unit/pipeline/test_progress_mapping.py`（8 个：区间归一化/防叠加/恢复）、`tests/unit/api/test_task_store.py`（11 个：任务 CRUD/白名单更新/队列标记/崩溃恢复）、`tests/unit/api/test_worker_executor.py`（10 个：子进程执行往返/崩溃隔离 respawn/取消 IPC/进度回传）、`tests/unit/api/test_task_manager_persistence.py`（12 个：write-through 落库/重启恢复/生产装配/manager+worker+SQLite 端到端链路）

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
- `scripts/` 仅用于构建和开发者调试，`mediafactory/` 业务代码不应调用 `scripts/` 下的脚本
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
