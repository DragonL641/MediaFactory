# Changelog

All notable changes to MediaFactory will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

**pipeline:** stage 内取消异常必须立即传播，不再被当作警告继续执行

**tests:** 修复预存的 prompt_loader 测试失败（translate/single.md 已随 batch-only 翻译迁移删除，改为断言 translate/batch 等价覆盖）

**tests:** 修复预存的 logging 测试失败（移除对已删除 log_stage 的引用，保留 log_step/log_success 断言）

### Removed

**cleanup:** Phase 1 死代码清理，累计删除约 1900 行：死引擎 video_composer、FFmpegConfig 与 [ffmpeg] 配置节、零引用的 launcher/memory_detection/resource_protocol/resource_management/file_utils/transformers_config、FileConstants/ModelTokenLimits 死块及孤儿导出、Flet 时代 gui_observers 遗留与 service 层死取消机制

**cleanup:** 删除 13 个零引用 i18n key、THIRD_PARTY_LICENSES.txt 中不存在的 flet 条目、HEAD 上已损坏的调试脚本（whisper_debug.py、local_model_debug.py）

### Changed

**refactor:** 模型下载执行逻辑下沉至 api/download_task 模块，routes/models.py 只做参数解析；exception_wrapper 测试重写并恢复测试基线（0 failed, 259 passed）

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
