# MediaFactory

<div align="center">
  <h1>🎬 MediaFactory</h1>
  <p><i>Professional Multimedia Processing Platform</i></p>
  <p>
    <a href="#features">Features</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#why-mediafactory">Why MediaFactory</a> •
    <a href="#requirements">Requirements</a>
  </p>
</div>

A professional multimedia processing platform for subtitle generation and video-related tasks.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-%3E%3D18.0.0-green.svg)](https://nodejs.org/)

---

## Features

### 🎯 Multiple Task Types

Support for 5 task types: Audio Extraction, Speech-to-Text, Subtitle Generation, Subtitle Translation, and Video Enhancement. Each task card shows status, progress, and estimated time remaining.

<p align="center">
  <img src="docs/images/TaskTypes.png" alt="Task Types" width="500"/>
</p>

### 📦 Batch Add Tasks

Drag and drop multiple files or entire folders. Set source/target languages and LLM settings once, then process all files in one go.

<p align="center">
  <img src="docs/images/TaskBatchAdd.png" alt="Batch Add Tasks" width="500"/>
</p>

### 🤖 Unified Model Management

Manage all models in one place — the Settings page. Download and configure local models (Whisper, M2M100) for fully offline processing, or connect to 6+ LLM providers (OpenAI, DeepSeek, GLM, Qwen, Moonshot, or custom endpoints) for cloud-based translation. Your choice, your privacy.

<p align="center">
  <img src="docs/images/ModelConfig.png" alt="Model Configuration" width="500"/>
</p>

---

## Quick Start

**Prerequisites**: Python 3.11+ and [uv](https://docs.astral.sh/uv/)

```bash
# 1. Clone the repository
git clone https://github.com/DragonL641/MediaFactory.git
cd MediaFactory

# 2. Install dependencies (includes PyTorch with CUDA 12.8)
uv sync --group core

# 3. Download models (required before first run)
uv run python scripts/utils/download_model.py facebook/m2m100_1.2B

# 4. Run the application
uv run mediafactory
```

> **Note**: PyTorch is downloaded from `download.pytorch.org` (not PyPI) to ensure CUDA support.
> CUDA 12.8 supports Blackwell (RTX 50 series) and earlier architectures.

---

## Why MediaFactory?

AI video tools often force you to choose between quality and speed, or between cloud convenience and privacy. MediaFactory gives you both.

- **Fast and accurate** — Faster Whisper delivers 4-6x speedup without sacrificing quality
- **Local or cloud** — Use local models for privacy, or LLM APIs for convenience — your choice
- **Batch processing done right** — Real progress tracking, not a black box
- **Clean uninstall** — All data stays in one folder, delete it and it's gone

### How we compare

**vs. pyVideoTrans** — Great for TTS dubbing, but GPL-licensed and focused on translation workflows. MediaFactory is MIT-licensed with a cleaner architecture for extensibility.

**vs. VideoCaptioner** — LLM-focused subtitle assistant with GPL license. MediaFactory offers both local and cloud options with a more permissive license.

**vs. SubtitleEdit** — The gold standard for manual subtitle editing with 300+ format support. MediaFactory is for automated generation, not manual editing — use both together.

| Feature | MediaFactory | pyVideoTrans | VideoCaptioner | SubtitleEdit |
|---------|:------------:|:------------:|:--------------:|:------------:|
| **Core Focus** | Auto Generation | Video Translation | LLM Subtitles | Manual Editing |
| **License** | MIT | GPL-3.0 | GPL-3.0 | GPL/LGPL |
| **Speech Recognition** | ✅ Faster Whisper | ✅ Multiple | ✅ Multiple | ✅ Whisper |
| **Local Translation** | ✅ | ✅ | ❌ | ❌ |
| **LLM Translation** | ✅ 6+ Providers | ✅ | ✅ | ✅ Google/DeepL |
| **Batch Processing** | ✅ | ✅ | ✅ | ✅ |
| **Subtitle Editing** | ❌ | ❌ | ❌ | ✅ Full Editor |
| **TTS Dubbing** | ❌ | ✅ | ❌ | ✅ |

---

## Requirements

### Hardware

| Mode | RAM | Storage | Notes |
|------|-----|---------|-------|
| **CPU** | 4GB | 2GB | Works on any platform |
| **GPU** | 8GB | 15GB | NVIDIA GPU with 4GB+ VRAM, Driver ≥ 525.60.13 |

> **macOS users**: Faster Whisper doesn't support Metal (MPS). CPU mode is used automatically.

### Software

- **Python**: 3.11, 3.12, or 3.13 (3.12 recommended)
- **uv**: Modern Python package manager ([install uv](https://docs.astral.sh/uv/))
- **Node.js**: ≥20.19.0 (for Electron GUI development)
- **FFmpeg**: Included via imageio-ffmpeg (no manual installation needed)
- **macOS**: 12.0 (Monterey) or later

---

## Usage Notes

**Model selection**: Uses `faster-whisper-large-v3` for speech recognition. GPU recommended for best performance.

**Translation quality**: LLM translation generally produces more natural results than local models. Use local models when privacy is critical.

**Model download**: Download translation model before first run:

```bash
# List available models
uv run python scripts/utils/download_model.py --list

# Download translation model
uv run python scripts/utils/download_model.py facebook/m2m100_1.2B
```

**Log files**: All logs are written to `logs/LOG-YYYY-MM-DD-HHMM.log` in the application directory.

---

## What MediaFactory is NOT

- **Not a subtitle editor** — For manual timing adjustments, use [SubtitleEdit](https://github.com/SubtitleEdit/subtitleedit)
- **Not a dubbing tool** — For TTS and voice cloning, use [pyVideoTrans](https://github.com/jianchang512/pyvideotrans)
- **Not an online platform** — Core processing (speech recognition, audio extraction) runs locally. Only translation can optionally use cloud LLM APIs.

---

## License

MIT License
