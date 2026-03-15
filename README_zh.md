# MediaFactory

<div align="center">
  <h1>🎬 MediaFactory</h1>
  <p><i>专业级多媒体处理平台</i></p>
  <p>
    <a href="#功能特性">功能特性</a> •
    <a href="#安装">安装</a> •
    <a href="#快速开始">快速开始</a> •
    <a href="#配置">配置</a> •
    <a href="#构建">构建</a>
  </p>
</div>

专业级多媒体处理平台，专注于字幕生成和视频相关任务。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)

---

## 功能特性

- **高质量音频提取** - 48kHz 立体声，语音增强滤波
- **语音转文字** - Faster Whisper（比 OpenAI Whisper 快 4-6 倍）
- **翻译** - 本地模型（MADLAD400）或 LLM API（OpenAI、DeepSeek、智谱 GLM 等）
- **字幕生成** - 完整流程，翻译失败自动回退
- **视频增强** - 画质提升、人脸增强、降噪处理
- **批量处理** - 高效多文件处理，递归验证
- **30+ 语言支持** - 转录和翻译
- **统一进度跟踪** - 分阶段进度更新，GUI 桥接支持
- **自包含部署** - 所有数据在安装目录，干净卸载
- **安装向导** - 首次运行配置，硬件自动检测

---

### 竞品对比

| 功能 | MediaFactory | pyVideoTrans | VideoCaptioner | SubtitleEdit |
|------|:------------:|:------------:|:--------------:|:------------:|
| **核心定位** | 多媒体平台 | 视频翻译 | LLM 字幕助手 | 字幕编辑器 |
| **许可证** | MIT | GPL-3.0 | GPL-3.0 | GPL/LGPL |
| **平台** | 跨平台 | 跨平台 | 跨平台 | Windows |
| | | | | |
| **语音识别** | ✅ Faster Whisper | ✅ 多种 | ✅ 多种 | ✅ Whisper |
| **VAD 过滤** | ✅ Silero VAD | ✅ | ✅ | ❌ |
| **翻译** | ✅ 本地 + LLM | ✅ 多种 | ✅ 多种 | ✅ Google/DeepL |
| **批量翻译** | ✅ 递归验证 | ✅ | ✅ | ❌ |
| | | | | |
| **SRT 格式** | ✅ | ✅ | ✅ | ✅ |
| **ASS 格式** | ✅ 5 种样式模板 | ✅ | ✅ 多种 | ✅ 完整编辑器 |
| **双语字幕** | ✅ 4 种布局 | ✅ | ✅ | ❌ |
| **软字幕嵌入** | ✅ mov_text | ✅ | ✅ | ✅ |
| **硬字幕烧录** | ✅ | ✅ | ✅ | ✅ |
| | | | | |
| **TTS 配音** | ❌ | ✅ 多种 TTS | ❌ | ✅ Azure/ElevenLabs |
| **声音克隆** | ❌ | ✅ F5-TTS | ❌ | ❌ |
| **字幕编辑** | ❌ | ❌ | ❌ | ✅ 完整编辑器 |
| **波形编辑器** | ❌ | ❌ | ❌ | ✅ 可视化同步 |
| **300+ 格式** | ❌ | ❌ | ❌ | ✅ |
| | | | | |
| **GUI** | ✅ Flet | ✅ PySide6 | ✅ Qt | ✅ WinForms |
| **CLI 模式** | ✅ | ❌ | ❌ | ✅ |
| **Pipeline 编排** | ✅ 核心特性 | ✅ | ❌ | ❌ |
| **事件系统** | ✅ EventBus | ❌ | ❌ | ❌ |
| **配置系统** | ✅ TOML + Pydantic | ❌ | JSON | XML |
| **批量处理** | ✅ | ✅ | ✅ | ✅ |

### 为什么选择 MediaFactory？

**架构优势**：
- **三层架构** - GUI → Service → Pipeline → Engine
- **Pipeline 架构** - ProcessingStage 模式，可组合工作流
- **事件系统** - EventBus 解耦组件
- **类型安全配置** - TOML + Pydantic v2，支持热重载

**核心特性**：
- 🚀 **Faster Whisper** - 比 OpenAI Whisper 快 4-6 倍
- 🎯 **VAD 过滤** - 内置 Silero VAD，减少幻觉
- 🌐 **统一 LLM 后端** - OpenAI 兼容 API，支持所有主流服务
- 📝 **批量翻译** - 递归验证，自动修复
- 🎨 **ASS 样式** - 5 种预设模板 + 自定义样式文件
- 🔀 **双语支持** - 4 种布局选项
- 📦 **自包含** - 所有数据在安装目录

**MediaFactory 不是**：
- 不是完整的字幕编辑器（手动编辑请使用 SubtitleEdit）
- 不是视频配音工具（TTS/声音克隆请使用 pyVideoTrans）
- 不是在线服务（完全本地处理）

---

## 安装

### 用户安装

1. 克隆仓库：
```bash
git clone https://github.com/Dragon/MediaFactory.git
cd MediaFactory
```

2. 安装依赖：
```bash
uv sync --group core
```

此命令会从 PyTorch 官方源下载带 CUDA 12.4 支持的 PyTorch。

3. 运行应用：
```bash
uv run mediafactory
```

> **说明**: PyTorch 从 `download.pytorch.org`（而非 PyPI）下载，以确保 CUDA 支持。
> CUDA 12.4 向后兼容所有 CUDA 12.x 驱动（NVIDIA 驱动 ≥ 525.60.13）。

### 开发者安装

1. 克隆并安装所有依赖：
```bash
git clone https://github.com/Dragon/MediaFactory.git
cd MediaFactory
uv sync --all-groups
```

2. 安装 pre-commit 钩子：
```bash
pre-commit install
pre-commit run --all-files
```

### 系统要求

- **Python**: 3.11、3.12 或 3.13（推荐 3.12）
- **uv**: 现代 Python 包管理器（[安装 uv](https://docs.astral.sh/uv/)）
- **FFmpeg**: 通过 imageio-ffmpeg 自动包含（无需手动安装）
- **GPU**（可选）: 支持 CUDA 12.x 的 NVIDIA GPU（驱动 ≥ 525.60.13）

### 硬件要求

| 配置 | 内存 | 存储 | 说明 |
|------|------|------|------|
| **CPU 模式** | 4GB RAM | 2GB | 所有平台 |
| **GPU 模式** | 8GB RAM | 15GB | NVIDIA GPU，4GB+ 显存，驱动 ≥ 525.60.13 |

### 安装 Pre-commit 钩子（贡献者）

如果您计划贡献代码，请安装 pre-commit 钩子：

```bash
pre-commit install
pre-commit run --all-files
```

---

## 快速开始

### GUI 应用

```bash
# 方式 1: 使用 console script
uv run mediafactory

# 方式 2: 使用 Python 模块
uv run python -m mediafactory

# 方式 3: 使用 Python API
uv run python -c "from mediafactory import launch_gui; launch_gui()"
```

---

## 配置

编辑 `config.toml`：

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

支持的 LLM 后端：OpenAI、DeepSeek、智谱 GLM、通义千问、Moonshot。

---

## 构建

MediaFactory 支持多种打包方式，从独立可执行文件到完整安装程序。

### PyInstaller 构建

创建包含所有依赖的独立可执行文件：

```bash
# 为当前平台构建
python scripts/pyinstaller/build_installer.py

# 清理构建产物
python scripts/pyinstaller/build_installer.py --clean
```

**输出**: `dist/MediaFactory.exe` (Windows) 或 `dist/MediaFactory.app` (macOS)

**体积**: ~200-500MB（不含 ML 依赖）

### 平台安装程序

**macOS (.dmg 磁盘镜像)**:
```bash
python scripts/build/macos/create_dmg.py
```
**输出**: `dist/MediaFactory-3.2.0.dmg`

**Windows (.exe 安装程序)**:
- 要求: [Inno Setup](https://jrsoftware.org/isdl.php) 6.0+
```bash
python scripts/build/windows/package_windows.py
# 或直接使用 Inno Setup
iscc scripts/build/windows/installer_windows.iss
```
**输出**: `dist/MediaFactory-Setup-3.2.0.exe`

### 安装向导

用户首次运行 GUI 时，安装向导自动启动：

**功能**：
- 快速安装（uv 下载依赖比 pip 快 10-100 倍）
- 自动检测 GPU 和推荐 PyTorch 版本
- 国内用户镜像选择
- 友好的图形化向导

**安装步骤**：
1. 欢迎页面 - 介绍
2. 硬件检测 - 自动检测 NVIDIA GPU 和 CUDA 版本
3. 镜像选择 - 选择下载源（国内镜像/官方源）
4. 配置生成 - 基于 `config.toml.example` 生成用户配置
5. 依赖安装 - 安装 PyTorch 和其他依赖
6. 模型下载 - 下载 Whisper 和翻译模型

**预计时间**: 5-15 分钟（取决于网络速度）

### 构建配置

编辑构建脚本以自定义：

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

### 发布清单

发布前确保：

- [ ] 更新版本号（所有构建脚本）
- [ ] 测试安装程序在干净系统上运行
- [ ] 验证首次运行向导正常工作
- [ ] 测试 GPU/CPU 自动检测
- [ ] 验证模型下载功能
- [ ] 检查配置文件生成

**注意**: 翻译模型（2GB+）不打包在安装程序中，用户需通过安装向导或手动下载。

---

## 故障排除

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| **FFmpeg 未找到** | MediaFactory 使用内置 imageio-ffmpeg，无需手动安装 |
| **内存不足 (OOM)** | 使用更小的 Whisper 模型（small 而非 large-v3），或强制 CPU 模式 |
| **识别准确率低** | 尝试 `large-v3` 模型；确保音频源清晰；检查源语言设置 |
| **翻译模型缺失** | 运行 `uv run python scripts/utils/download_model.py --list` 查看可用模型 |
| **macOS GPU 未使用** | Faster Whisper 不支持 MPS；自动使用 CPU |
| **API 翻译失败** | 检查 config.toml 中的 API key；验证网络连接和配额 |
| **进度卡在 0%** | 确保使用 v3.0+；检查 GUI 回调；查看日志文件错误 |

### 日志文件

所有日志写入：`mediafactory_YYYYMMDD_HHMMSS.log`（在应用根目录）

---

## 许可证

MIT 许可证
