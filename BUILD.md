# MediaFactory 构建指南

**平台支持**：macOS / Windows（Linux 暂不支持）。macOS 产物已本地全链验证；Windows 为 CI 出包（`release.yml`），未真机验证。

## 前置要求

- Python 3.11、3.12 或 3.13（推荐 3.12）
- uv（推荐）或 pip
- Node.js >= 20.19.0（npm；前端构建与桌面打包都需要）
- Rust >= 1.77.2（rustup 安装；仅桌面打包需要，源码运行不需要。Windows 需 MSVC 工具链——Visual Studio Installer 勾选 "Desktop development with C++"）
- macOS：Xcode Command Line Tools（`xcode-select --install`）

### 安装依赖

MediaFactory 使用 `dependency-groups` 进行依赖分组（详见 `pyproject.toml`）：

| 用途 | 命令 |
|------|------|
| 开发者（所有依赖） | `uv sync --all-groups` |
| 桌面打包（含 ML 依赖） | `uv sync --group core` |
| 打包验证 | `uv sync --group bundle` |
| 基础运行时 | `uv sync` |

## 一键构建（桌面安装包）

```bash
uv run python scripts/build/build_darwin.py    # macOS → release/MediaFactory_<version>_aarch64.dmg
uv run python scripts/build/build_win.py       # Windows → release/MediaFactory_<version>_x64-setup.exe
```

前提：`webui/` 已存在（`npm run build` 产物）——组装步骤依赖它，缺失时脚本会提示先构建前端。支持 `--version` 参数覆盖版本号（默认读 `pyproject.toml`）。

内部流程（`scripts/utils/build_executor.py` 的 `build_desktop` 编排，四步）：

1. **PyInstaller**（`installer_simple.spec`，onedir）：ML 依赖全量打包，产出 `dist/MediaFactory/`
2. **组装 `src-tauri/python-backend/`**：COLLECT 产物 + `webui/` 复制到 exe 同级——daemon 在 frozen 下从 exe 旁找 webui（`get_app_root_dir`），故不打进 spec datas
3. **`npm run tauri build`**：Rust 壳编译 + bundle（macOS .app/.dmg ad-hoc 签名；Windows NSIS）
4. **安装包复制到 `release/`**

## 分步构建 / 开发调试

```bash
npm run build                          # 仅前端（产物 webui/，daemon 同源伺服）
uv run python -m mediafactory          # 源码跑 daemon（开发形态，可变数据仍在项目根）
npm run tauri dev                      # 壳开发模式（debug 构建不 spawn 打包产物）
npx tauri icon mediafactory/resources/icon.png -o src-tauri/icons   # 由源图重新生成 Tauri 图标集
```

- `npm run tauri dev`：debug 构建的壳**不会拉起打包产物**，需手动另起 `uv run python -m mediafactory`，壳等端口就绪后显示窗口加载 `http://127.0.0.1:8765`
- 图标有两套、相互独立：Tauri 图标集在 `src-tauri/icons/`（上面的命令重新生成）；PyInstaller 可执行文件图标取 `mediafactory/resources/icon.icns`（macOS）/ `icon.ico`（Windows）
- **注意**：全新 clone 后直接 `cd src-tauri && cargo build` 会报 resources 目录不存在——`python-backend/` 由构建脚本组装（`.gitignore` 排除）。先跑一键构建，或 `mkdir src-tauri/python-backend`

## 桌面应用行为（Tauri 壳）

`src-tauri/`（约 250 行 Rust 胶水，唯一职责是进程生命周期管理，无业务逻辑）：

- **启动**：壳 spawn `python-backend` 内 daemon → TCP 轮询 8765 就绪（uvicorn lifespan 完成后才开始 accept，连通 = API 完全就绪；超时 120s）→ 显示窗口加载 `http://127.0.0.1:8765`
- **数据目录**：frozen 可变数据（tasks.db、daemon.lock、config.toml、logs、models）落平台用户目录（macOS `~/Library/Application Support/MediaFactory`，Windows `%APPDATA%\MediaFactory`）；安装目录只留只读资产
- **退出**：优雅链 `POST /api/system/shutdown` → daemon lifespan 收尾（RUNNING 任务落 CANCELLED）→ atexit 释放实例锁；15s 超时硬杀进程树（unix `killpg` / Windows `taskkill /T /F`，含 worker 子进程）
- **双开**：第二个实例的 daemon 撞实例锁以 exit 42 让位，壳转复用模式直连已有 daemon（退出时不杀不属于它的 daemon）
- **崩溃**：daemon 意外退出（非让位、非主动关闭）→ 弹窗提示后退出壳；任务状态下次启动 `recover()` 恢复

## 签名说明（macOS）

ad-hoc 签名（`tauri.conf.json` `signingIdentity: "-"`）：本地构建可直接运行；分发他人时对方首次打开需右键 → 打开（或 `xattr -dr com.apple.quarantine <app>`）放行。未做 Developer ID 签名与公证（Windows 同样未签名，SmartScreen 会警告）。

## 已知限制

- `kill -TERM` 直接杀壳不走 Tauri 事件流，会留孤儿 daemon——由实例锁陈锁接管 + 重启 recover 自愈兜底；正常退出（关窗/Cmd+Q）不受影响
- tauri-bundler 的 `bundle_dmg.sh` 对上次构建残留的 attached 镜像敏感：构建报 `failed to run bundle_dmg.sh` 时，`hdiutil detach` 挂载点 + 删除 `src-tauri/target/release/bundle/dmg/rw.*.dmg` 后重跑
- identifier `com.mediafactory.app` 以 `.app` 结尾会触发 tauri 构建 warning（cosmetic，产物正常；未来改 identifier 会重置 webview 本地存储）
- Windows 产物未真机验证（无本地环境，CI 出包）

## 构建产物

### 最终安装包（`release/`）

```
release/
├── MediaFactory_<version>_aarch64.dmg      # macOS（本机构架）安装包
├── MediaFactory_<version>_x64-setup.exe    # Windows NSIS 安装包（CI 产出）
└── MediaFactory-<version>.source.zip       # 源码归档（build_source.py）
```

### 中间产物（不入库，`.gitignore` 排除）

```
dist/MediaFactory/                          # PyInstaller COLLECT 产物
src-tauri/python-backend/                   # 组装出的 Tauri resources（COLLECT + webui）
src-tauri/target/                           # cargo / tauri-bundler 输出
webui/                                      # vite 前端产物
```

## 版本管理

版本号在 `pyproject.toml` 中定义，这是单一真相源：

```toml
[project]
version = "0.4.0"
```

构建脚本会自动读取此版本号。`scripts/utils/sync_version.py` 负责跨栈同步，覆盖 `package.json`、`src-tauri/Cargo.toml` 与 `BUILD.md`（含本文件的 git-cliff 命令示例）。

```bash
python scripts/utils/sync_version.py --check     # 检查版本一致性
python scripts/utils/sync_version.py 0.4.0       # 更新所有文件版本号
```

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
git-cliff --tag v0.4.0 --unreleased --prepend CHANGELOG.md

# 3. 检查生成的 changelog，必要时手动调整

# 4. 提交版本更新和 changelog
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.4.0 and update changelog"

# 5. 打 tag
git tag v0.4.0

# 6. 推送提交和 tag
git push && git push origin v0.4.0

# 7. 创建 GitHub Release（可选）
#    tag 已包含完整的发布内容
```

### 常用命令

```bash
# 预览下一个版本的 changelog（不写入文件）
git-cliff --unreleased

# 生成两个 tag 之间的变更
git-cliff v0.1.0..v0.4.0

# 追加到现有 CHANGELOG.md
git-cliff --tag v0.4.0 --prepend CHANGELOG.md

# 仅输出到标准输出
git-cliff --tag v0.4.0 --unreleased
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

## 源码归档

```bash
# 构建 tar.gz 和 zip
python scripts/build/build_source.py

# 仅构建 zip（用于 GitHub Releases）
python scripts/build/build_source.py --zip-only
```

**产物**：`release/MediaFactory-{version}.source.zip`

## 直接使用 PyInstaller

```bash
uv run python -m PyInstaller scripts/pyinstaller/installer_simple.spec --clean --noconfirm
```

产出 `dist/MediaFactory/`（onedir COLLECT 产物）。注意这只完成四步链的第一步——桌面安装包还需组装 `src-tauri/python-backend/` 并跑 `tauri build`（直接用一键构建即可）。

## 构建系统架构

```
scripts/
├── pyinstaller/              # PyInstaller 构建脚本和配置
│   ├── installer_simple.spec  # PyInstaller spec 配置文件
│   ├── hooks/                 # PyInstaller 自定义 hooks
│   │   ├── hook-mediafactory.py    # MediaFactory 包收集
│   │   ├── hook-uvicorn.py         # Uvicorn 服务器支持
│   │   └── hook-pkg_resources.py   # pkg_resources 模块
├── build/                     # 平台构建脚本
│   ├── build_darwin.py        # macOS 构建入口（→ build_desktop）
│   ├── build_win.py           # Windows 构建入口（→ build_desktop）
│   └── build_source.py        # 源码 ZIP 构建脚本
└── utils/                     # 工具脚本
    ├── build_common.py        # 构建通用模块
    ├── build_executor.py      # 构建执行器（桌面打包全链编排）
    ├── check_gpu.py           # GPU 检测脚本
    ├── download_model.py      # 模型下载脚本
    ├── sync_version.py        # 版本同步脚本
    └── init_models_in_installation.py # 模型初始化脚本

src-tauri/                     # Tauri 2 桌面壳（Rust）
├── src/main.rs                # 壳唯一源文件（daemon 生命周期管理）
├── tauri.conf.json            # 窗口 / bundle / resources 配置
├── Cargo.toml                 # Rust 依赖（版本随 sync_version 同步）
├── icons/                     # 图标集（tauri icon 生成，入库）
└── python-backend/            # 构建脚本组装（不入库）
```

### 关键模块

- **build_common.py**：项目信息、日志、文件工具等公共函数
- **build_executor.py**：桌面打包全链编排（`build_desktop`：PyInstaller → 组装 python-backend → tauri build → 收集安装包）
- **installer_simple.spec**：PyInstaller 规范文件

## 体积优化

PyInstaller 通过以下方式减小产物体积：

1. **排除不必要的模块**：测试框架、开发工具、未使用的 ML 子模块（见 `EXCLUDES` 列表）
2. **不使用 UPX**：避免某些环境兼容性问题
3. **仅包含必要的隐式导入**：减少未使用的依赖

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

1. 确保 `mediafactory/resources/icon.icns` 存在
2. 检查 `.spec` 文件中的图标路径是否正确
3. macOS 不支持 UPX，确保未启用

### Windows SmartScreen 警告

由于未进行代码签名，Windows 可能会显示 SmartScreen 警告。用户需要：
1. 点击"更多信息"
2. 选择"仍要运行"

### 端口 8765 被占用

壳检测到端口已通会直接复用已有 daemon（双开让位 exit 42 也走此路径），不是错误；源码形态下报地址占用说明已有 daemon 在跑，别起第二个即可。

### 全新 clone 后 cargo build 报 resources 缺失

`src-tauri/python-backend/` 由构建脚本组装、不在仓库中——先跑一键构建（或 `mkdir src-tauri/python-backend`）再 `cargo build`。

### bundle_dmg.sh 失败

见「已知限制」中的处理方法：`hdiutil detach` 挂载点 + 删除 `rw.*.dmg` 残留后重跑。

### 版本解析失败

构建脚本通过 `mediafactory._version.get_version()` 获取版本号，支持多层回退（`importlib.metadata` → `tomli` 解析 → 简单文本解析）。如果解析失败：

1. 确保 `pyproject.toml` 中的版本格式正确（应为 `X.Y.Z` 格式）
2. 确保包已安装：`uv sync --group core`

## 开发者资源

- **构建工具模块**：`scripts/utils/build_common.py`
- **构建执行器**：`scripts/utils/build_executor.py`
- **PyInstaller 配置**：`scripts/pyinstaller/installer_simple.spec`
- **Tauri 壳源码与配置**：`src-tauri/src/main.rs`、`src-tauri/tauri.conf.json`
- **CI/CD 配置**：`.github/workflows/release.yml`
