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
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

---

## 功能特性

- **高质量音频提取** - 48kHz 立体声，语音增强滤波
- **语音转文字** - Faster Whisper（比 OpenAI Whisper 快 4-6 倍）
- **翻译** - 本地模型（NLLB、M2M）或 LLM API（OpenAI、智谱 GLM）
- **字幕生成** - 完整流程，翻译失败自动回退
- **批量处理** - 高效多文件处理
- **支持 30+ 种语言**的转录和翻译

---

## 安装

MediaFactory 使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理，提供快速且现代的 Python 环境管理。

### 系统要求

- **Python**: 3.10+（推荐 3.12）
- **FFmpeg**: 通过 imageio-ffmpeg 自动包含（无需手动安装）
- **GPU**（可选）: 支持 CUDA 的 NVIDIA GPU 用于加速

### 选择安装方式

#### 方式 1：使用安装程序（推荐）

从 [Releases](https://github.com/Dragon/MediaFactory/releases) 下载安装程序。安装程序会自动下载所有必需的依赖（ML 模型约 350MB）。

#### 方式 2：从源码运行

**基础功能**（GUI + LLM API 翻译，约 150MB）：
```bash
git clone https://github.com/Dragon/MediaFactory.git
cd MediaFactory
uv sync
uv run mediafactory
```

**完整功能**（包含本地 ASR 和翻译，约 350MB）：
```bash
uv sync --extra ml
uv run mediafactory
```

#### 方式 3：开发者安装

安装所有依赖，包括开发工具：
```bash
uv sync --group dev
```

### PyTorch 安装

首次运行时，应用程序会自动检测硬件（CPU/GPU）并引导您完成 PyTorch 安装。无需手动配置。

**高级用户如需预安装 PyTorch：**

| 平台 | 命令 |
|------|------|
| **CPU（所有平台）** | `uv pip install torch --index-url https://download.pytorch.org/whl/cpu` |
| **CUDA 12.4（NVIDIA GPU）** | `uv pip install torch --index-url https://download.pytorch.org/whl/cu124` |
| **CUDA 11.8（旧版 GPU）** | `uv pip install torch --index-url https://download.pytorch.org/whl/cu118` |

**注意**：RTX 50 系列（Blackwell 架构）需要 PyTorch 每夜构建版本和 CUDA 12.8+ 支持。

### 安装 Pre-commit 钩子（贡献者）

如果您计划贡献代码，请安装 pre-commit 钩子以在提交前自动检查代码质量：

```bash
pre-commit install
pre-commit run --all-files
```

### 硬件要求

| 配置 | 内存 | 存储 | 说明 |
|------|------|------|------|
| **CPU 模式** | 4GB RAM | 2GB | 所有平台 |
| **GPU 模式** | 8GB RAM | 5GB | NVIDIA GPU，4GB+ 显存 |

### 下载模型（必需）

```bash
# 列出可用模型
python scripts/utils/download_model.py --list

# 下载推荐模型（如 google/madlad400-3b-mt）
python scripts/utils/download_model.py google/madlad400-3b-mt
```

国内用户使用镜像加速：
```bash
python scripts/utils/download_model.py google/madlad400-3b-mt --source=https://hf-mirror.com
```

---

## 快速开始

### GUI 应用

```bash
python -m mediafactory
```

---

## 开发

### 安装开发依赖

```bash
# 安装完整开发环境（包含所有 ML 依赖和开发工具）
uv sync --group dev
```

### 使用 pip 安装（备选）

```bash
pip install -e ".[ml]" && pip install pytest pytest-cov black flake8 mypy pre-commit build twine
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

支持的 LLM 后端：OpenAI、智谱 GLM。

---

## 构建

MediaFactory 支持多种打包方式，从简单的可执行文件到完整的安装程序。

### PyInstaller 构建

创建完整的独立可执行文件，包含所有依赖：

```bash
# 为当前平台构建
python scripts/pyinstaller/build_installer.py

# 清理构建产物
python scripts/pyinstaller/build_installer.py --clean
```

**输出**: `dist/MediaFactory/` (目录形式)

**体积**: ~500MB-1GB（包含所有依赖）

#### 创建平台安装程序

从 PyInstaller 构建结果创建安装程序：

**macOS (.pkg 安装程序)**:
```bash
bash scripts/build/macos/build_macos_pkg.sh
```
**输出**: `dist/MediaFactory-Installer-3.2.0.pkg`

**Windows (.exe 安装程序)**:
- 要求: [Inno Setup](https://jrsoftware.org/isdl.php) 6.0+
```bash
iscc scripts/build/windows/installer_windows.iss
```
**输出**: `dist/MediaFactory-Setup-3.2.0.exe`
✅ **镜像选择**: 支持国内镜像加速
✅ **完整向导**: 友好的图形化安装向导

### 首次运行流程

当用户首次运行安装程序时：

1. **欢迎页面** - 介绍功能
2. **环境检测** - 自动检测 NVIDIA GPU 和 CUDA 版本
3. **镜像源选择** - 选择下载源（国内镜像/官方源）
4. **配置文件生成** - 基于 `config.toml.example` 生成用户配置
5. **依赖安装** - 使用 uv 快速安装 PyTorch 和其他依赖
6. **模型下载** - 下载 Whisper 和翻译模型

**预计时间**: 5-15 分钟（取决于网络速度）

### 构建配置

编辑构建脚本以自定义：

**`scripts/pyinstaller/build_installer.py`**:
```python
PRODUCT_NAME = "MediaFactory"
PRODUCT_VERSION = "3.2.0"
ENCRYPT_BYTECODE = True  # 加密字节码
COMPRESS_OUTPUT = True   # 压缩输出
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

## 许可证

MIT 许可证
