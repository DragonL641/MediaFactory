# MediaFactory 构建指南

## 平台支持

MediaFactory 支持 **macOS** 和 **Windows** 平台。Linux 平台暂不支持。

## 前置要求

- Python 3.10 或更高版本
- uv（推荐）或 pip

### macOS 额外要求
- Xcode Command Line Tools

### Windows 额外要求
- Inno Setup 6 或更高版本（可选，用于创建安装程序）

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

**产物**：`dist/MediaFactory-Setup-{version}.exe`（如果安装了 Inno Setup）
或 `dist/MediaFactory.exe`（仅可执行文件）

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
version = "3.2.0"
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
git-cliff --tag v3.3.0 --unreleased --prepend CHANGELOG.md

# 3. 检查生成的 changelog，必要时手动调整

# 4. 提交版本更新和 changelog
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 3.3.0 and update changelog"

# 5. 打 tag
git tag v3.3.0

# 6. 推送提交和 tag
git push && git push origin v3.3.0

# 7. 创建 GitHub Release（可选）
#    tag 已包含完整的发布内容
```

### 常用命令

```bash
# 预览下一个版本的 changelog（不写入文件）
git-cliff --unreleased

# 生成两个 tag 之间的变更
git-cliff v3.2.0..v3.3.0

# 追加到现有 CHANGELOG.md
git-cliff --tag v3.3.0 --prepend CHANGELOG.md

# 仅输出到标准输出
git-cliff --tag v3.3.0 --unreleased
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

## 构建系统架构

```
scripts/
├── build/
│   ├── build_darwin.py      # macOS 构建入口
│   ├── build_win.py          # Windows 构建入口
│   └── build_source.py       # 源码归档
├── pyinstaller/
│   ├── installer_simple.spec # PyInstaller 配置
│   └── hooks/                # PyInstaller 钩子
└── utils/
    ├── build_common.py       # 公共工具函数
    └── build_executor.py     # 构建执行器
```

### 关键模块

- **build_common.py**：项目信息、日志、文件工具等公共函数
- **build_executor.py**：封装 PyInstaller 调用的通用逻辑
- **installer_simple.spec**：PyInstaller 规范文件

## 故障排除

### PyInstaller 找不到模块

如果遇到 "No module named 'xxx'" 错误：

1. 检查 `scripts/pyinstaller/installer_simple.spec` 中的 `hiddenimports` 列表
2. 添加缺失的模块到 `hiddenimports`

### macOS 图标不显示

1. 确保 `src/mediafactory/resources/icon.icns` 存在
2. 检查 `.spec` 文件中的图标路径是否正确

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
