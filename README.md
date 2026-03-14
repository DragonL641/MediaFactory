# MediaFactory

<div align="center">
  <h1>🎬 MediaFactory</h1>
  <p><i>Professional Multimedia Processing Platform</i></p>
  <p>
    <a href="#features">Features</a> •
    <a href="#installation">Installation</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#configuration">Configuration</a> •
    <a href="#building">Building</a> •
    <a href="#troubleshooting">Troubleshooting</a>
  </p>
</div>

A professional multimedia processing platform for subtitle generation and video-related tasks.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

---

## Features

- **High-Quality Audio Extraction** - 48kHz stereo with voice enhancement filters
- **Speech-to-Text** - Faster Whisper (4-6x faster than OpenAI Whisper)
- **Translation** - Local models (NLLB, M2M) or LLM APIs (OpenAI, GLM)
- **Subtitle Generation** - Complete pipeline with automatic translation fallback
- **Batch Processing** - Efficient multi-file processing
- **30+ Languages** supported for transcription and translation
- **Unified Progress Tracking** - Stage-aware progress updates with GUI bridge
- **Self-Contained Deployment** - All data in installation directory for clean uninstall
- **Setup Wizard** - First-run configuration with hardware detection

---

### Competitive Comparison

| Feature | MediaFactory | pyVideoTrans | VideoCaptioner | SubtitleEdit |
|---------|:------------:|:------------:|:--------------:|:------------:|
| **Core Focus** | Multimedia Platform | Video Translation | LLM Subtitle Assistant | Subtitle Editor |
| **License** | MIT | GPL-3.0 | GPL-3.0 | GPL/LGPL |
| **Platform** | Cross-platform | Cross-platform | Cross-platform | Windows |
| | | | | |
| **Speech Recognition** | ✅ Faster Whisper | ✅ Multiple | ✅ Multiple | ✅ Whisper |
| **VAD Filtering** | ✅ Silero VAD | ✅ | ✅ | ❌ |
| **Translation** | ✅ Local + LLM | ✅ Multiple | ✅ LLM-focused | ✅ Google/DeepL |
| **Batch Translation** | ✅ Recursive Validation | ✅ | ✅ | ❌ |
| | | | | |
| **SRT Format** | ✅ | ✅ | ✅ | ✅ |
| **ASS Format** | ✅ 5 Style Templates | ✅ | ✅ Multiple | ✅ Full Editor |
| **Bilingual Subtitles** | ✅ 4 Layouts | ✅ | ✅ | ❌ |
| **Soft Subtitle Embed** | ✅ mov_text | ✅ | ✅ | ✅ |
| **Hard Subtitle Burn** | ✅ | ✅ | ✅ | ✅ |
| | | | | |
| **TTS Dubbing** | ❌ | ✅ Multiple TTS | ❌ | ✅ Azure/ElevenLabs |
| **Voice Cloning** | ❌ | ✅ F5-TTS | ❌ | ❌ |
| **Subtitle Editing** | ❌ | ❌ | ❌ | ✅ Full Editor |
| **Waveform Editor** | ❌ | ❌ | ❌ | ✅ Visual Sync |
| **300+ Formats** | ❌ | ❌ | ❌ | ✅ |
| | | | | |
| **GUI** | ✅ Flet | ✅ PySide6 | ✅ Qt | ✅ WinForms |
| **CLI Mode** | ✅ | ❌ | ❌ | ✅ |
| **Pipeline Orchestration** | ✅ Core Feature | ✅ | ❌ | ❌ |
| **Event System** | ✅ EventBus | ❌ | ❌ | ❌ |
| **Config System** | ✅ TOML + Pydantic | ❌ | JSON | XML |
| **Batch Processing** | ✅ | ✅ | ✅ | ✅ |

### Why MediaFactory?

**Architecture Advantages**:
- **3-Layer Architecture** - GUI → Service → Pipeline → Engine
- **Pipeline Architecture** - ProcessingStage pattern for composable workflows
- **Event System** - EventBus for decoupled components
- **Type-Safe Config** - TOML + Pydantic v2 with hot reload

**Key Features**:
- 🚀 **Faster Whisper** - 4-6x faster than OpenAI Whisper
- 🎯 **VAD Filtering** - Built-in Silero VAD reduces hallucinations
- 🌐 **Unified LLM Backend** - OpenAI-compatible API supports all major services
- 📝 **Batch Translation** - Recursive validation with auto-repair
- 🎨 **ASS Styling** - 5 preset templates + custom style files
- 🔀 **Bilingual Support** - 4 layout options for dual-language subtitles
- 📦 **Self-Contained** - All data in installation directory

**What MediaFactory is NOT**:
- Not a full subtitle editor (use SubtitleEdit for manual editing)
- Not a video dubbing tool (use pyVideoTrans for TTS/voice cloning)
- Not an online service (fully local processing)

---

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Dragon/MediaFactory.git
cd MediaFactory
```

2. Run the setup script:
```bash
python scripts/setup_env.py
```

The interactive script will:
- Detect your hardware (GPU, CUDA version)
- Ask if you're a user or developer
- Install the appropriate dependencies
- Optionally download AI models

### Requirements

- **Python**: 3.10+ (3.12 recommended)
- **FFmpeg**: Included via imageio-ffmpeg (no manual installation needed)
- **GPU** (optional): NVIDIA GPU with CUDA support for acceleration

### Hardware Requirements

| Configuration | Memory | Storage | Notes |
|---------------|--------|---------|-------|
| **CPU Mode** | 4GB RAM | 2GB | All platforms |
| **GPU Mode** | 8GB RAM | 5GB | NVIDIA GPU with 4GB+ VRAM |

### Install Pre-commit Hooks (For Contributors)

If you plan to contribute code, install pre-commit hooks:

```bash
pre-commit install
pre-commit run --all-files
```

---

## Quick Start

### GUI

```bash
# Method 1: Using console script
uv run mediafactory

# Method 2: Using Python module
uv run python -m mediafactory

# Method 3: Using Python API
uv run python -c "from mediafactory import launch_gui; launch_gui()"
```

---

## Configuration

Edit `config.toml`:

```toml
[whisper]
beam_size = 5

[model]
local_model_path = "models"

[api_translation]
backend = "openai"

[openai]
api_key = "YOUR_API_KEY"
model = "gpt-4o-mini"

[llm_translation]
enable_batch = true
batch_size = 100
```

Supported LLM backends: OpenAI, GLM (智谱AI).

---

## Building

MediaFactory supports multiple packaging methods, from standalone executables to full installers.

### PyInstaller Build

Create standalone executables with all dependencies:

```bash
# Build for current platform
python scripts/pyinstaller/build_installer.py

# Clean build artifacts
python scripts/pyinstaller/build_installer.py --clean
```

**Output**: `dist/MediaFactory.exe` (Windows) or `dist/MediaFactory.app` (macOS)

**Size**: ~200-500MB (without ML dependencies)

### Platform Installers

**macOS (.dmg disk image):**
```bash
python scripts/build/macos/create_dmg.py
```
**Output**: `dist/MediaFactory-3.2.0.dmg`

**Windows (.exe installer):**
- Requires: [Inno Setup](https://jrsoftware.org/isdl.php) 6.0+
```bash
python scripts/build/windows/package_windows.py
# Or use Inno Setup directly
iscc scripts/build/windows/installer_windows.iss
```
**Output**: `dist/MediaFactory-Setup-3.2.0.exe`

### Setup Wizard

When users run the GUI for the first time, the Setup Wizard starts automatically:

**Features:**
- Fast installation (uv downloads dependencies 10-100x faster than pip)
- Auto-detection of GPU and recommended PyTorch version
- Mirror selection for users in China
- User-friendly graphical wizard

**Setup Steps:**
1. Welcome page - Introduction
2. Hardware detection - Auto-detect NVIDIA GPU and CUDA version
3. Mirror selection - Choose download source (China mirror / official)
4. Config generation - Create user config from `config.toml.example`
5. Dependency installation - Install PyTorch and other dependencies
6. Model download - Download Whisper and translation models

**Estimated time**: 5-15 minutes (depending on network speed)

### Build Configuration

Edit build scripts to customize:

**`scripts/pyinstaller/build_installer.py`**:
```python
PRODUCT_NAME = "MediaFactory"
PRODUCT_VERSION = "3.2.0"
ENCRYPT_BYTECODE = True
COMPRESS_OUTPUT = True
```

**`scripts/build/windows/installer_windows.iss`**:
```iss
#define AppVersion "3.2.0"
#define AppPublisher "Your Name"
```

### Release Checklist

Before release, ensure:

- [ ] Update version numbers in all build scripts
- [ ] Test installer on clean systems
- [ ] Verify first-run wizard works correctly
- [ ] Test GPU/CPU auto-detection
- [ ] Verify model download functionality
- [ ] Check config file generation

**Note**: Translation models (2GB+) are NOT bundled. Users must download separately via the setup wizard or manually.

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **FFmpeg not found** | MediaFactory uses built-in imageio-ffmpeg, no manual installation needed |
| **Out of memory (OOM)** | Use smaller Whisper model (small instead of large-v3), or force CPU mode |
| **Poor accuracy** | Try `large-v3` model; ensure audio source is clear; check source language setting |
| **Missing translation model** | Run `uv run python scripts/utils/download_model.py --list` to see available models |
| **macOS GPU not used** | Faster Whisper doesn't support MPS; CPU is used automatically |
| **API translation fails** | Check API key in config.toml; verify network connection and quota |
| **Progress stuck at 0%** | Ensure v3.0+; check GUI callbacks; see log file for errors |

### Log Files

All logs are written to: `mediafactory_YYYYMMDD_HHMMSS.log` (in application root directory)

---

## License

MIT License
