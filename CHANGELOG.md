# Changelog

All notable changes to MediaFactory will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1]


### Documentation

**version:** 添加版本管理架构文档说明



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
