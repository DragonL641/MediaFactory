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

## 构建概览

MediaFactory 的构建分为三个阶段：

| 阶段 | 说明 | 产物 |
|------|------|------|
| **后端构建** | PyInstaller 打包 Python FastAPI 后端 | `dist/MediaFactory.app` + `dist/python/` |
| **前端构建** | electron-vite 编译 React + TypeScript | `dist/electron/` |
| **应用打包** | electron-builder 打包为安装包 | `release/{version}/MediaFactory-{version}-{arch}.dmg` |

### 快速开始（完整构建）

```bash
# 1. 后端构建
uv run python scripts/build/build_darwin.py     # macOS
uv run python scripts/build/build_win.py         # Windows

# 2. 前端构建（在项目根目录执行，根 package.json 已配置 electron-vite 命令）
npm run build

# 3. 应用打包
npx electron-builder --mac                        # macOS DMG
npx electron-builder --win                        # Windows NSIS
```

---

## 阶段一：后端构建（Python）

### macOS

```bash
uv run python scripts/build/build_darwin.py
```

**产物**：
- `dist/MediaFactory.app` — 独立 macOS 应用包
- `dist/MediaFactory-{version}.app.zip` — 压缩分发包
- `dist/python/` — PyInstaller COLLECT 产物（用于 Electron 打包）

### Windows

```bash
uv run python scripts/build/build_win.py
```

**产物**：`dist/MediaFactory-{version}-win64.zip`

### 清理构建产物

```bash
uv run python scripts/build/build_darwin.py --clean   # macOS
uv run python scripts/build/build_win.py --clean       # Windows
```

> **注意**：后端构建会自动将 PyInstaller 产物复制到 `dist/python/`，供阶段三的 Electron 打包使用。

---

## 阶段二：前端构建（Electron）

MediaFactory 使用 Electron + React + TypeScript + Ant Design 作为前端，`electron-vite` 作为构建工具。

### 开发模式

```bash
# 终端 1: 启动 Python 后端
uv sync --group core
uv run python -m mediafactory

# 终端 2: 启动 Electron 开发服务器（热更新）
npm run dev
```

### 生产构建

```bash
npm run build
```

构建产物位于 `dist/electron/` 目录：
- `dist/electron/main/` — Electron 主进程
- `dist/electron/preload/` — Preload 脚本
- `dist/electron/renderer/` — React 前端

### 前端技术栈

- **框架**: React 18 + TypeScript
- **UI 库**: Ant Design 5
- **状态管理**: @tanstack/react-query
- **HTTP 客户端**: Axios
- **实时通信**: WebSocket
- **构建工具**: electron-vite

---

## 阶段三：应用打包（DMG / NSIS）

将后端和前端整合打包为用户可安装的桌面应用。

### 前置条件

确保已完成阶段一和阶段二，以下目录存在：
- `dist/python/` — PyInstaller 后端产物
- `dist/electron/` — 前端编译产物

### macOS DMG

```bash
# 仅当前架构（arm64）
npx electron-builder --mac --arm64

# 仅 x64
npx electron-builder --mac --x64

# 同时构建两个架构
npx electron-builder --mac
```

**产物**：`release/{version}/MediaFactory-{version}-arm64.dmg`、`MediaFactory-{version}-x64.dmg`

### Windows NSIS

```bash
npx electron-builder --win
```

**产物**：`release/{version}/MediaFactory-{version}-x64-setup.exe`

### 注意事项

- **模型不打包**：采用"无模型"构建策略，用户通过 Setup Wizard 下载模型
- **代码签名**：本地开发跳过签名，正式发布需 Apple Developer / Windows 代码签名证书
- **macOS Gatekeeper**：未签名应用会被 Gatekeeper 阻止，用户需右键 → 打开来绕过

---

## 源码归档

```bash
# 构建 tar.gz 和 zip
python scripts/build/build_source.py

# 仅构建 zip（用于 GitHub Releases）
python scripts/build/build_source.py --zip-only
```

**产物**：`release/MediaFactory-{version}.source.zip`

## 版本管理

版本号在 `pyproject.toml` 中定义，这是单一真相源：

```toml
[project]
version = "0.3.0"
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
git-cliff --tag v0.3.0 --unreleased --prepend CHANGELOG.md

# 3. 检查生成的 changelog，必要时手动调整

# 4. 提交版本更新和 changelog
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.3.0 and update changelog"

# 5. 打 tag
git tag v0.3.0

# 6. 推送提交和 tag
git push && git push origin v0.3.0

# 7. 创建 GitHub Release（可选）
#    tag 已包含完整的发布内容
```

### 常用命令

```bash
# 预览下一个版本的 changelog（不写入文件）
git-cliff --unreleased

# 生成两个 tag 之间的变更
git-cliff v0.1.0..v0.3.0

# 追加到现有 CHANGELOG.md
git-cliff --tag v0.3.0 --prepend CHANGELOG.md

# 仅输出到标准输出
git-cliff --tag v0.3.0 --unreleased
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

> 已整合到上方「阶段二：前端构建」章节。

## 直接使用 PyInstaller

```bash
uv run python -m PyInstaller scripts/pyinstaller/installer_simple.spec --clean --noconfirm
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

### 后端产物（`dist/`）

```
dist/
├── MediaFactory/                      # PyInstaller COLLECT 目录
│   ├── MediaFactory                   # 可执行文件
│   └── _internal/                     # 依赖文件
├── MediaFactory.app/                  # macOS .app 包
├── MediaFactory-{version}.app.zip     # macOS 压缩包
├── python/                            # 用于 Electron 打包的副本
└── electron/                          # 前端编译产物
    ├── main/                          # Electron 主进程
    ├── preload/                       # Preload 脚本
    └── renderer/                      # React 前端
```

### 最终安装包（`release/{version}/`）

```
release/{version}/
├── MediaFactory-{version}-arm64.dmg   # macOS ARM DMG
├── MediaFactory-{version}-x64.dmg     # macOS x64 DMG
└── MediaFactory-{version}-x64-setup.exe  # Windows 安装包
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
