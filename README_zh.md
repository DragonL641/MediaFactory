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

### 系统要求

- Python 3.10+
- FFmpeg（包含在 imageio-ffmpeg 中，无需手动安装）
- PyTorch（默认安装 CPU 版本）

### 安装

```bash
git clone https://github.com/Dragon/MediaFactory.git
cd MediaFactory
pip install -e .
```

### GPU 加速（可选，仅限 Windows/Linux）

**注意**：默认安装使用仅 CPU 的 PyTorch 以确保最大兼容性。

#### RTX 50 系列 GPU（RTX 5070/5090，Blackwell 架构）

RTX 50 系列 GPU 需要使用 PyTorch 每夜构建版本和 CUDA 12.8 支持：

```bash
# 卸载现有 PyTorch
pip uninstall torch torchaudio -y

# 安装 PyTorch 每夜构建版本（CUDA 12.8，支持 sm_120）
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# 验证安装
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Compute capability:', torch.cuda.get_device_capability(0) if torch.cuda.is_available() else 'N/A')"
```

**预期输出**：`CUDA available: True`，`Compute capability: (12, 0)`

**重要提示**：每夜构建版本可能存在稳定性问题。

#### 旧版 NVIDIA GPU（RTX 40 系列及以下）

如需在 Windows 或 Linux 上使用旧版 NVIDIA GPU 加速：

```bash
# 卸载 CPU 版本
pip uninstall torch torchaudio -y

# 安装 CUDA 12.4 版本（推荐）
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# 或 CUDA 11.8（如果 12.4 不兼容）
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# 验证 CUDA 是否可用
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

**预期输出**：`CUDA available: True`

**macOS 用户**：不支持 GPU 加速（Faster Whisper 不支持 MPS）。

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
# 基础开发环境（GUI 和基本功能）
uv sync --group dev

# 完整开发环境（包含 ML 依赖 - 本地 ASR 和翻译）
uv sync --group dev --extra ml
```

**依赖说明**：
- `uv sync` - 仅核心依赖（GUI + LLM API 翻译）
- `--group dev` - 开发工具（pytest、black、flake8 等）
- `--extra ml` - ML 依赖（faster-whisper、transformers 等）

### 使用 pip 安装（备选）

```bash
pip install -e ".[cpu]" && pip install pytest pytest-cov black flake8 mypy pre-commit build twine
```

### 安装 Pre-commit 钩子

项目使用 pre-commit 进行代码质量检查。如果您计划贡献代码，请安装 Git 钩子：

```bash
# 安装 pre-commit Git 钩子
pre-commit install

# 手动运行检查
pre-commit run --all-files
```

代码质量检查工具包括：
- **Black** - 代码格式化
- **Flake8** - 代码检查
- **Bandit** - 安全检查

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
