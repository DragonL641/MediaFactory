# Changelog

All notable changes to MediaFactory will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0]


### Added

**api:** TaskStore SQLite 持久层——schema/insert/get/get_all


**api:** TaskStore 支持 update 白名单/delete/队列标记


**api:** TaskStore 崩溃恢复——RUNNING 残留标 FAILED，队列保留


**api:** Worker 子进程侧——_WorkerProgress 进度协议与任务结果投影


**api:** TaskExecutor 接缝——InlineExecutor 与 WorkerProcessExecutor（spawn 子进程 IPC）


**api:** TaskManager write-through 落库与执行器接缝（_execute_task 双路径）


**api:** TaskManager 队列/取消/重试/删除/配置更新 write-through 持久化


**api:** 生产装配——WorkerProcessExecutor + data/tasks.db + lifespan 重启恢复


**api:** DaemonLock PID 实例锁——杜绝 daemon 双开


**api:** Daemon 双入口接实例锁——双开时明确报错退出


**api:** System 路由——browse 目录浏览与 reveal 定位产物


**api:** Daemon 同源伺服 Web UI——SPA 路由 + StaticFiles + 缺目录降级


**web:** 前端 API 基址同源化——相对路径 + location 推导 WS


**web:** 移除 Electron 自定义标题栏——浏览器原生窗口栏


**web:** 文件选取与产物定位去 Electron 化——PathInput/服务端浏览/reveal API


Frozen 可变数据迁平台用户目录——get_data_root_dir 与只读资产根分离


POST /api/system/shutdown 优雅停机端点，入口手动构造 uvicorn Server


Tauri 2 桌面壳——拉起 daemon/就绪显示/退出优雅停机/崩溃提示的完整胶水


**persistence:** Task history store + /api/history routes + terminal hooks


**ui:** History page with first antd Table


**llm:** Add TermDict core (first-wins term memory with conflict fix)


**llm:** Inject hit terms into batch translation prompt via custom_instructions


**llm:** Rolling term learning with conflict replacement in batch loop


**api:** Terminology field with schema limits, passthrough to translation engine


**ui:** Terminology file upload on subtitle and translate task forms


**llm:** Add Ollama REST client with sync/async APIs


**api:** Local model management routes (Ollama status/pull/delete)


**config:** Add ollama LLM preset (local base_url, no api key)


**api:** Per-task fallback_model field with validation and passthrough


**llm:** Expose failed_indices and TermDict via translate_detailed


**engine:** Local fallback orchestration with stats and auto-unload


**runner:** Wire fallback_model through engine; stats into task metadata


**ui:** Local model types and query hooks


**ui:** Local Models (Ollama) settings card


**ui:** Model dropdown from installed Ollama models in ProviderDialog


**ui:** Per-task local fallback switch with model selection


**ui:** Translation stats column in history


**ui:** Merge task history into task queue, drop History page


**enhancement:** Vendor CodeFormer/VQAutoEncoder (basicsr-free) + facexlib dep + spike


**registry:** Add FACE_RESTORATION model type with CodeFormer weight entries


**api:** Expose face_restoration section in model status


**ui:** Face Restoration model cards in Settings


**enhance:** Face_restore/film_grain config plumbing + task-level weight gate


**enhancement:** Film grain via FFmpeg noise filter on final merge


**enhancement:** Auto deinterlace detection + bwdif pre-pass


**enhancement:** FaceRestoreManager with MPS->CPU fallback


**enhance:** Orchestrate deinterlace pre-pass and face restore into enhance()


**ui:** Face restore and film grain switches in enhance form


**translate:** Real .ass parsing in SRTEngine (H3)


**queue:** Allow editing FAILED/CANCELLED tasks for configured retry


**queue:** Per-task log sink in worker (append with attempt separators)


**api:** Task logs endpoint + cleanup on task removal


**ui:** Icon-only action buttons with tooltips + task log modal


**queue:** CreatedAt in payload + result summary into task log


**ui:** Task table utilities + filters i18n


**ui:** Replace task cards with filterable table


**ui:** Log level filter in LogModal


**ui:** Merge batch actions into filter toolbar as icon-only buttons


**ui:** Icon-only table column headers with tooltips


**ui:** Retry opens edit dialog first; drop standalone edit for failed tasks


**ui:** Unified datetime format in created column (YYYY-MM-DD HH:mm)


**ui:** Dedicated Log column before Actions


**ui:** Icon-only status tags with tooltip


**ui:** Cap Name column at 320px with built-in ellipsis tooltip


**ui:** Keep table skeleton on empty task list


**ui:** Show stage message in progress tooltip


**ui:** Drop Add Task button from table empty state


**ui:** Merge progress into status column as ring — drop Progress column


**ui:** Paginate task table, default 10 per page



### Changed

**core:** 优化配置检查与异常处理机制


**project-structure:** 重构项目目录路径为根目录的 mediafactory 结构


**src:** 迁移电前端及相关配置至 src 目录


**core:** 将异常处理函数提取到独立模块并统一导入


**core:** 将异常处理函数提取到独立模块并统一导入


**api:** 模型下载执行逻辑下沉至 download_task 模块，路由只做参数解析


**exceptions:** 删除零运行时价值的 ErrorSeverity 分级与 pipeline 死分支


**api:** Get_task_manager 迁入 task_manager.py，消除下载链路的延迟导入


**pipeline:** 删除 SkipableStage/on_error/ModelCleanupStage/VideoEnhancementStage 死结构，resource_manager 收敛为纯上下文管理器


**pipeline,api:** 进度区间映射移入 Pipeline 按组合归一化，修翻译-only 从 70% 起跳


**core:** 统一任务执行入口 runner，删除 task_executor 与五个 service 类，错误通道拉直


LLM 预设名单单一真相源，清空 models 门面，清理死参数/孤儿 i18n key/幽灵文档引用


**api:** 移除 _load_from_store 冗余局部导入


移除 Electron 壳——开发形态切换为 daemon + 浏览器


**translation:** Remove M2M100 local translation pipeline


**api:** Remove backend task history stack


**ui:** Drop use_llm switches; normalize single-direction gate


**cleanup:** Remove dead code — schemas, endpoints, config, scripts, m2m100 doc residue


**ui:** Drop Download Timeout field — frontend half of deleted dead config field


**cleanup:** Dead code sweep, second batch (L11)


**enhancement:** Batch F — collapse duplicated logic (L12)


**queue:** Address deferred review minors



### Documentation

**api:** Download_task 模块注明下载任务不支持取消/重试的契约限制


**build:** 移除对已删除的 transformers_config.py 的悬空引用


**interview-qa:** 修正对已删除 ResourceCleanupProtocol 的三处失实描述


**interview-qa:** Q17 改写为运行时模型选择逻辑，移除对已删函数的引用


**changelog:** 追加 Phase 1 精简摘要（3 个 bug 修复、约 1900 行死代码删除、测试基线恢复）


同步 CLAUDE.md 至 Phase 1 后状态，修正 FFmpeg 角色描述与 CHANGELOG 格式


CLAUDE.md 登记 Phase 2 契约测试安全网


CLAUDE.md 同步 Phase 3 已删除的 pipeline 结构（ModelCleanupStage/单 stage 工厂/资源单例）


**pipeline:** 补权重意图注释、修正测试反事实数值、同步 CLAUDE.md 进度章节


CLAUDE.md 架构章节同步 runner 三层收敛（服务层/API 层/事件流）


Phase 3 收尾——CLAUDE.md 安全网清单与 CHANGELOG 三阶段战果


修终审指出的架构图 VideoComposer 幽灵引用与 resource_manager 重复条目


修正重启续跑措辞与 worker 边界描述（Phase 1 收尾）


Phase 2 收尾——开发工作流与架构描述同步 daemon+浏览器形态


修正契约安全网计数——persistence 14 个共 105


BUILD.md 标注 Electron 链移除；收尾注释与锁文件权限清理


Phase 3 收尾——BUILD.md 按 Tauri 形态重写，README/CLAUDEMD/CHANGELOG 同步


Wiki GUI 框架章节由 Electron 刷新为 Tauri 壳架构


修正 Windows NSIS 产物名为 _x64-setup（审查笔误）


已知限制补 frozen worker 首次实跑关注点（终审 Minor）


**workflow:** Add dev-helm files, backfill R1 removal


**roadmap:** R2 term memory kickoff (doing)


**spec:** Backfill R2 term memory (ADDED semantics), clear roadmap R2


**roadmap:** Kick off R3 local model management + fallback


**readme:** Local models (Ollama) usage and fallback


**roadmap:** Video enhancement repositioned for personal use; P0-P2 packages into Later


**spec:** Backfill R3 local models + fallback (ADDED), clear roadmap R3


**roadmap:** Drop R4 LLM semantic segmentation (scope cut)


**spec:** Ship history-stack removal + provider dialog polish


Re-audit CLAUDE.md/AGENTS.md against c03f6ff..HEAD drift


**roadmap:** Intake pull-reliability batch (Next) + hygiene batch (Later); drop length-control


**readme:** Clarify local translation row means Ollama LLM; drop roadmap item


**roadmap:** Pull-reliability + hygiene batch into Now (bounded)


**spec:** Ship pull reliability + hygiene batch (anchor 62434d8)


**roadmap:** Clear shipped pull-reliability + hygiene batch


**roadmap:** Remove leftover corpse of shipped Next entry


**spec:** Anchor to dead-code cleanup (60602fe); contract count 170


Move video-enhancement positioning decisions into product-spec stable layer


**roadmap:** Defer spandrel/community-model freedom out of P0


**roadmap:** Queue enhancement P0/P1/P2 into Next; spandrel + observation stay in Later


Contract list recount (170->182) + P0 feature description; drop spike script


Contract list recount (182->194) + api.md stub for removed status endpoint


Contract list recount (194->206) for task queue batch


Contract recount (206->211) for table batch


Backfill task queue spec, sync counts, refresh README



### Fixed

**models:** 优化模型完整性校验及重试通知机制


**pipeline:** Stage 内取消异常必须立即传播，不得当作警告继续执行


**tests:** 修复预存的 prompt_loader/logging 测试失败，恢复套件全绿


**pipeline:** 中间 WAV 不再消费字幕输出路径；补 LLM 成功分支契约测试；spec 同步 runner


**api:** Worker 测试桩满足 put 契约；子进程异常 traceback 落统一日志


**api:** WorkerProcessExecutor cancel 按 task_id 守卫；shutdown 复用显式报错；队列资源回收与 reader 加固


**api:** Shutdown 落库 CANCELLED 确定终态；补 retry/update_task_status 落库测试


**api:** Tasks.db 锚定 get_app_root_dir；恢复日志补全与测试卫生


**api:** 启动恢复逐行容错；lifespan 接线冒烟测试；Windows 测试兼容与 docstring 清理


**api:** DaemonLock 存活探测平台分支——Windows 禁用 os.kill 改 ctypes


**api:** Browse 条目级容错与路径规范化；reveal 异步化留痕；跳过 dotfile


**web:** 占位符文案对齐手输+浏览；扩展名常量化；浏览按钮 Tooltip


Config.toml 迁数据根——补 Task 1 遗漏的 get_config_path 迁移


Path.home 改 patch 注入保证跨平台测试；import os 归位与 dev config 断言


壳运行时风险修复——双启动交接宽限/shutdown 超时/退出竞态消除


双启动改退出码特征码判别（42=锁让位），删除宽限机制并修转复用不可达


冒烟发现的两处集成缺陷——frozen 入口缺日志初始化、壳漏挂 RunEvent::Exit


**llm:** Narrow terms type for mypy in _extract_terms


**llm,api,ui:** Address review findings - terminology reaches end-to-end


**api,engine:** Address review findings - pull cancel protection, error detail preserved


**api:** Hold strong refs to running Ollama pull tasks


**ui:** Hide API Key field for Ollama provider in ProviderDialog


**pull:** Watchdog, post-completion verification, in-card progress


**llm:** Truthful LLM Response log; content-filter batches run learn-and-fix


**enhancement:** Review findings C1+C2+I1+I2+I3


**enhancement:** Address all 8 review minors


**enhancement:** Batch A+B — cancellable ffmpeg, temp leak, cleanup, guards


Batch D — i18n bare keys, LLM null-value validation, watchdog grace


**ui:** Stop log polling on terminal task state (review I1) + enum canEdit + pending-editable regression


**ui:** Review findings — level regex, per-row loading, crash-path summary, terminal fetch


**ui:** Filter labels + missing columns.status i18n key


**ui:** Unfix Log column


**ci:** Unblock test suite and lint gate


**engine:** Restore TimeEstimator.get_video_duration — L11 dead-code sweep误删活方法


**api:** Default use_llm=true — UI 开关移除后 payload 不再携带该字段


**ui:** Edit dialog never closed after save — bare close() resolved to window.close



### Testing

**core:** 重写 exception_wrapper 测试，移除对已删符号的引用，恢复测试基线


**services:** 补 audio/subtitle/translation 契约测试，锁定编排行为


**api:** 补 task_manager 状态机/串行队列/取消/进度映射契约测试


**api:** 补 download_task 契约测试（成功/失败/节流）


**services,api:** 补 transcription/enhance 契约测试与 executor 注册完备性断言


**runner:** 补 run_enhance 契约与 Pipeline 失败透传断言，去重注册表测试


**api:** Worker 崩溃隔离契约——SIGKILL 子进程只失败当前任务并自动重启


**api:** 崩溃隔离测试断言补全与轮询加上限


**api:** 锁定重启恢复契约——RUNNING 标 FAILED、队列按 queued_at 重建


**api:** 锁定恢复错误消息的回读路径


**api:** Manager+worker+SQLite 端到端链路；docs 同步 Phase 1 架构变化


**api:** 补 DaemonLock release 的 PID 比较分支覆盖


**api:** 入口接线补 happy-path 并清理局部导入


**api:** Chmod 回归测试 Windows 跳过；reveal 告警豁免 explorer 退出码


**api:** SPA 伺服补 ws 连接断言；路由支持 HEAD；降级 warning 加指引


钉住 __main__ 生产路径 server 注册；server_ref 类型打磨


Align unit test collection between local gate and CI



## [Unreleased]

### Added

**desktop:** Tauri 2 桌面壳（src-tauri/）——拉起 daemon → 端口就绪显示窗口 → 退出优雅停机（15s 超时硬杀兜底）→ 崩溃提示；一键构建产出 macOS dmg（ad-hoc 签名）

**config:** frozen 可变数据迁平台用户目录（macOS ~/Library/Application Support/MediaFactory、Windows %APPDATA%\MediaFactory），安装目录只留只读资产

**api:** POST /api/system/shutdown 优雅停机端点（uvicorn should_exit → lifespan 收尾，RUNNING 任务落 CANCELLED）

### Fixed

**pipeline:** stage 内取消异常必须立即传播，不再被当作警告继续执行

**tests:** 修复预存的 prompt_loader 测试失败（translate/single.md 已随 batch-only 翻译迁移删除，改为断言 translate/batch 等价覆盖）

**tests:** 修复预存的 logging 测试失败（移除对已删除 log_stage 的引用，保留 log_step/log_success 断言）

### Removed

**cleanup:** Phase 1 死代码清理，累计删除约 1900 行：死引擎 video_composer、FFmpegConfig 与 [ffmpeg] 配置节、零引用的 launcher/memory_detection/resource_protocol/resource_management/file_utils/transformers_config、FileConstants/ModelTokenLimits 死块及孤儿导出、Flet 时代 gui_observers 遗留与 service 层死取消机制

**cleanup:** 删除 13 个零引用 i18n key、THIRD_PARTY_LICENSES.txt 中不存在的 flet 条目、HEAD 上已损坏的调试脚本（whisper_debug.py、local_model_debug.py）

### Changed

**refactor:** 模型下载执行逻辑下沉至 api/download_task 模块，routes/models.py 只做参数解析；exception_wrapper 测试重写并恢复测试基线（0 failed, 259 passed）

**refactor:** Phase 3 结构性收敛——五层调用链收敛为 routes → task_manager → runner → pipeline/engine：新建 services/runner.py 统一任务入口（RUNNERS 注册表、引擎缓存、LLM 降级链、readiness 门），删除 api/task_executor.py 与五个 service 类；ProcessingResult 从 Pipeline 直达 TaskManager 不再重包装（error_type/error_context/metadata 不再丢失）

**refactor:** 进度区间映射从 task_manager 全局硬编码表移入 Pipeline（STAGE_WEIGHTS 按组合归一化），修复翻译-only 任务从 70% 起跳与音频监视线程取消后误报 100% 的问题

**refactor:** 删除 ErrorSeverity 分级、SkipableStage/on_error/ModelCleanupStage 死结构；resource_manager 收敛为纯 whisper_model 上下文管理器（163→33 行）；ProcessingContext 类型化（config 携带 pydantic 子配置、新增 requested_output_path/output_format 字段）；LLM 预设名单收敛为 constants.PRESET_NAMES 单一真相源；models 包门面清空

**tests:** 契约测试安全网增至 41 个（runner 21 / task_manager 9 / download 3 / 进度映射 8），全部经变异验证锁定不变量；mypy 错误 115 → 92；后端 16,559 → 13,954 行（-15.7%）

**api:** 任务队列落 SQLite 持久化（data/tasks.db），任务执行移入独立 worker 子进程：ML 崩溃不再拖垮服务，daemon 重启后任务记录与排队队列不丢（恢复为待执行）、中断任务标记失败

**build:** 开发形态切换为 daemon + 浏览器——移除 Electron 壳，daemon 同源伺服 Web UI（vite 产物 webui/）

**api:** daemon 实例锁（data/daemon.lock）杜绝双开；新增 system 路由（目录浏览 / 产物定位）

**web:** 文件选取改为手动输入 + 服务端目录浏览（PathInput/BrowseModal），打开产物改为后端 reveal

## [0.4.0]

### Added

**ui:** Add WebVTT to output format options

**ui:** Enable bilingual subtitle option for WebVTT format

**api:** Add VTT format support in backend schemas and pipeline

**pipeline:** Add PostProcessEngine and PostProcessStage for intelligent sentence segmentation

**models:** 添加模型前置条件就绪状态支持

### Changed

**translation:** 改进本地翻译错误处理机制

### Documentation

**readme:** 更新模型管理和任务类型展示内容

Update all documentation and bump version to v0.4.0

### Fixed

**transcription:** Pass output_format through to pipeline instead of hardcoding SRT

**translation:** Support configurable output format instead of hardcoding SRT

Add VTT i18n keys, HuggingFace token config, and download error display

**download:** Improve gated repo error message with actionable steps

**models:** Support config.yaml and pipeline-only repos in completeness check

**tasks:** Remove invalid Alert styles prop causing TS error

Resolve ESLint errors in electron frontend code

**pre-commit:** Use npm run typecheck instead of chained npx tsc commands

**pre-commit:** Use files regex for ESLint hook to match ts and tsx

### Testing

**tests:** 重构测试体系，新增集成准确率和错误处理测试

Add VTT format generation and parsing tests

## [0.3.0]

### Added

**i18n:** 添加多语言支持及相关国际化功能

**api:** 支持字幕与翻译任务的LLM预设及双语样式配置

### Changed

优化构建系统和延迟加载 ML 依赖

**core:** 迁移默认翻译模型到 M2M100-1.2B

**build:** 重构构建脚本和公共工具模块

### Fixed

**download:** 修复 GUI 模式下 huggingface_hub 进度条导致的下载失败

**download_worker:** 确保Windows下stdout和stderr有效避免崩溃

**pyinstaller:** 修复跨平台 site-packages 路径处理及多进程支持

## [0.2.1] - 2026-03-17

### Added

- 自动硬件检测（GPU/CPU）功能
- 添加版本管理架构文档说明

### Changed

- 优化构建系统，延迟加载 ML 依赖，减少启动时间
- 统一日志系统，全部使用 loguru 替代标准库 logging
- 重构翻译模块降级策略并修复本地回退 bug
- 优化下载进度条显示和模型卡片布局

### Fixed

- 修复 GUI 模式下 huggingface_hub 进度条导致的下载失败
- 添加 CUDA 兼容性检查和超时保护
- 修复 MADLAD400 模型加载问题

### Documentation

- 重构 Wiki 文档结构并新增远端 LLM 调用章节

## [0.1.0] - 2025-03-01

### Added
- Initial release of MediaFactory
- Multimedia processing platform with subtitle generation
- Support for audio extraction using FFmpeg
- Speech recognition using Faster Whisper
- Translation support (local MADLAD400 model and LLM API)
- Flet-based GUI with Material Design 3
- Batch processing support
- Multiple subtitle formats (SRT, ASS)
- Video composition with embedded subtitles

### Architecture
- **3-Layer Architecture** - GUI → Service → Engine separation
- **Pipeline Pattern** - Composable processing stages
- **Event System** - EventBus for decoupled components
- **Type-Safe Config** - TOML + Pydantic v2 with hot reload

### Engines
- **AudioEngine** - Audio extraction with voice enhancement
- **RecognitionEngine** - Faster Whisper with VAD support
- **TranslationEngine** - Local models + LLM API backends
- **SRTEngine** - SRT subtitle generation
- **ASSEngine** - ASS subtitle with 5 style templates
- **VideoComposer** - Subtitle embedding
- **VideoEnhancementEngine** - Video quality enhancement

### Features
- High-quality audio extraction (48kHz stereo)
- Faster Whisper (4-6x faster than OpenAI Whisper)
- 30+ languages for transcription and translation
- Bilingual subtitles (4 layout options)
- Batch processing with recursive validation
- Unified progress tracking with GUI bridge
- Self-contained deployment

### LLM Backends
- OpenAI
- DeepSeek
- ZhipuAI GLM
- Tongyi Qianwen
- Moonshot
- Custom OpenAI-compatible endpoints

[0.1.0]: https://github.com/DragonL641/MediaFactory/releases/tag/v0.1.0
[0.2.1]: https://github.com/DragonL641/MediaFactory/releases/tag/v0.2.1
