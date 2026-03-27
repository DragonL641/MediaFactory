# MediaFactory 构建指南

## 平台支持

MediaFactory 支持 **macOS** 和 **Windows** 平台。Linux 平台暂不支持。

## 前置要求

- Python 3.11、3.12 或 3.13（推荐 3.12）
- uv（推荐）或 pip
- Node.js >= 18

### macOS 额外要求
- Xcode Command Line Tools

### Windows 额外要求
- 无额外要求

## 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

## 构建命令

### macOS 构建

```bash
python scripts/build/build_darwin.py
```

**产物**：`dist/MediaFactory-{version}.app.zip`

### Windows 构建

```bash
python scripts/build/build_win.py
```

**产物**：`dist/MediaFactory-{version}-win64.zip`

### 源码归档

```bash
# 构建 tar.gz 和 zip
python scripts/build/build_source.py

# 仅构建 zip（用于 GitHub Releases）
python scripts/build/build_source.py --zip-only
```

**产物**：`release/MediaFactory-{version}.source.zip`

### 清理构建产物

```bash
# macOS
python scripts/build/build_darwin.py --clean

# Windows
python scripts/build/build_win.py --clean
```

## 版本管理

版本号在 `pyproject.toml` 中定义，这是单一真相源：

```toml
[project]
version = "0.2.0"
```

构建脚本会自动读取此版本号。

## Changelog 自动生成

MediaFactory 使用 [git-cliff](https://git-cliff.org/) 自动生成 CHANGELOG.md。

### 安装 git-cliff

**macOS:**
```bash
brew install git-cliff
```

**Windows:**
```powershell
# 使用 scoop
scoop install git-cliff

# 或从 GitHub Releases 下载
# https://github.com/orhun/git-cliff/releases
```

**Linux:**
```bash
# Arch Linux
pacman -S git-cliff

# 或使用 cargo
cargo install git-cliff
```

### 发布工作流

> **重要**: Changelog 必须在打 git tag **之前**生成，确保 tag 包含完整的发布内容。

```bash
# 1. 更新版本号 (pyproject.toml)
#    编辑 project.version 字段

# 2. 生成 changelog（在打 tag 之前）
git-cliff --tag v0.2.0 --unreleased --prepend CHANGELOG.md

# 3. 检查生成的 changelog，必要时手动调整

# 4. 提交版本更新和 changelog
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.2.0 and update changelog"

# 5. 打 tag
git tag v0.2.0

# 6. 推送提交和 tag
git push && git push origin v0.2.0

# 7. 创建 GitHub Release（可选）
#    tag 已包含完整的发布内容
```

### 常用命令

```bash
# 预览下一个版本的 changelog（不写入文件）
git-cliff --unreleased

# 生成两个 tag 之间的变更
git-cliff v0.1.0..v0.2.0

# 追加到现有 CHANGELOG.md
git-cliff --tag v0.2.0 --prepend CHANGELOG.md

# 仅输出到标准输出
git-cliff --tag v0.2.0 --unreleased
```

### Commit 规范

git-cliff 依赖 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

| Commit 类型 | Changelog 分类 |
|-------------|----------------|
| `feat` | Added |
| `fix` | Fixed |
| `refactor` | Changed |
| `perf` | Performance |
| `docs` | Documentation |
| `test` | Testing |
| `chore`, `style`, `ci` | *跳过* |

**示例 commit message:**
```
feat(gui): 添加双语字幕支持
fix(audio): 修复音频提取时的崩溃问题
refactor(core): 重构进度跟踪系统
docs: 更新安装文档
```

## Electron 前端构建

MediaFactory 使用 Electron + React + TypeScript + Ant Design 作为前端。

### 开发模式

```bash
# 终端 1: 启动 Python 后端（API 服务器）
uv sync --group core
python -m mediafactory

# 终端 2: 启动 Electron 开发服务器（热更新）
cd src/electron
npm install
npm run dev
```

### 前端构建

```bash
cd src/electron
npm run build
```

构建产物位于 `dist/electron/` 目录：
- `dist/electron/main/` — Electron 主进程
- `dist/electron/preload/` — Preload 脚本
- `dist/electron/renderer/` — React 前端

### 完整桌面应用打包

```bash
# 1. 构建 Python 后端
pyinstaller scripts/pyinstaller/installer_simple.spec

# 2. 构建前端并打包桌面应用
cd src/electron
npm run build
npx electron-builder --mac    # macOS
npx electron-builder --win    # Windows
```

### 前端技术栈

- **框架**: React 18 + TypeScript
- **UI 库**: Ant Design 5
- **状态管理**: @tanstack/react-query
- **HTTP 客户端**: Axios
- **实时通信**: WebSocket
- **构建工具**: electron-vite

## 直接使用 PyInstaller

```bash
pyinstaller scripts/pyinstaller/installer_simple.spec
```

## 构建系统架构

```
scripts/
├── pyinstaller/              # PyInstaller 构建脚本和配置
│   ├── installer_simple.spec  # PyInstaller spec 配置文件
│   ├── hooks/                 # PyInstaller 自定义 hooks
│   │   ├── hook-mediafactory.py    # MediaFactory 包收集
│   │   ├── hook-uvicorn.py         # Uvicorn 服务器支持
│   │   └── hook-pkg_resources.py   # pkg_resources 模块
│   └── README_PYINSTALLER.md   # 本文件
├── build/                     # 平台构建脚本
│   ├── build_darwin.py        # macOS 构建入口
│   ├── build_win.py           # Windows 构建入口
│   └── build_source.py        # 源码 ZIP 构建脚本
└── utils/                     # 工具脚本
    ├── build_common.py        # 构建通用模块
    ├── build_executor.py      # 构建执行器
    ├── check_gpu.py           # GPU 检测脚本
    ├── download_model.py      # 模型下载脚本
    ├── sync_version.py        # 版本同步脚本
    └── init_models_in_installation.py # 模型初始化脚本
```

### 关键模块

- **build_common.py**：项目信息、日志、文件工具等公共函数
- **build_executor.py**：封装 PyInstaller 调用的通用逻辑
- **installer_simple.spec**：PyInstaller 规范文件

## 构建产物

构建完成后，产物位于 `dist/` 目录：

```
dist/
├── MediaFactory/                      # 产物文件夹
│   ├── MediaFactory                   # 可执行文件 (Linux/macOS)
│   ├── MediaFactory.exe               # 可执行文件 (Windows)
│   ├── config.toml                    # 用户配置文件（可编辑）
│   ├── NOTICE.txt                     # 第三方许可声明
│   ├── README.txt                     # 模型下载指南
│   ├── models/                        # 模型目录（需用户下载）
│   │   └── README.txt                 # 模型目录说明
│   └── _internal/                     # 依赖文件
└── MediaFactory-0.2.0-{platform}.zip  # 压缩产物（自动生成）
```

## 图标文件

- **Windows**: 使用 `.png` 格式，放置在 `src/mediafactory/resources/icon.png`（PyInstaller + Pillow 自动转换为 ICO）
- **macOS**: 需要 `.icns` 格式，放置在 `src/mediafactory/resources/icon.icns`
- **Linux**: 通常不需要图标文件

如果没有对应的图标文件，构建会自动跳过图标设置。

## 体积优化

PyInstaller 通过以下方式减小产物体积：

1. **排除不必要的模块**：测试框架、开发工具、未使用的 ML 子模块
2. **去除符号表**：`--strip` 选项（macOS 除外）
3. **不使用 UPX**：避免某些环境兼容性问题
4. **仅包含必要的隐式导入**：减少未使用的依赖

## Transformers 缓存配置

在冻结环境中，transformers 缓存被重定向：
- `src/mediafactory/utils/transformers_config.py`：将缓存目录设置为 `./cache` 文件夹
- 使用 `HF_HOME` 而非已弃用的 `TRANSFORMERS_CACHE`（transformers v5+）

## 故障排除

### PyInstaller 找不到模块

如果遇到 "No module named 'xxx'" 错误：

1. 检查 `scripts/pyinstaller/installer_simple.spec` 中的 `hiddenimports` 列表
2. 添加缺失的模块到 `hiddenimports`

### 构建后程序无法运行

检查 `scripts/pyinstaller/installer_simple.spec` 中的：
1. `datas` 列表是否包含所有必要文件
2. `hiddenimports` 是否包含所有动态导入的模块
3. 运行程序时查看详细错误信息

### faster-whisper 数据文件缺失

如果提示找不到 `faster_whisper/assets`，确保 `installer_simple.spec` 中包含：
```python
datas += collect_data_files('faster_whisper')
```

### macOS 图标不显示

1. 确保 `src/mediafactory/resources/icon.icns` 存在
2. 检查 `.spec` 文件中的图标路径是否正确
3. macOS 不支持 UPX，确保未启用

### Windows SmartScreen 警告

由于未进行代码签名，Windows 可能会显示 SmartScreen 警告。用户需要：
1. 点击"更多信息"
2. 选择"仍要运行"

### 版本解析失败

构建脚本使用 `tomli` 库解析 `pyproject.toml`。如果解析失败：

1. 确保 `tomli` 已安装：`pip install tomli`
2. 检查 `pyproject.toml` 中的版本格式是否正确（应为 `X.Y.Z` 格式）

## 开发者资源

- **构建工具模块**：`scripts/utils/build_common.py`
- **构建执行器**：`scripts/utils/build_executor.py`
- **PyInstaller 配置**：`scripts/pyinstaller/installer_simple.spec`
- **CI/CD 配置**：`.github/workflows/release.yml`
