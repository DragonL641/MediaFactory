# PyInstaller Build System

MediaFactory 使用 PyInstaller 进行打包，将 Python 代码编译为独立的可执行文件。

## 目录结构

```
scripts/
├── pyinstaller/              # PyInstaller 构建脚本和配置
│   ├── build_installer.py   # PyInstaller 构建脚本
│   ├── installer_simple.spec  # PyInstaller spec 配置文件
│   ├── hooks/              # PyInstaller 自定义 hooks
│   │   ├── hook-mediafactory.py    # MediaFactory 包收集
│   │   ├── hook-flet.py            # Flet 框架文件
│   │   ├── hook-transformers.py    # transformers 缓存配置
│   │   └── hook-pkg_resources.py   # pkg_resources 模块
│   └── README_PYINSTALLER.md   # 本文件
├── build/                   # 平台安装程序构建脚本
│   ├── build_darwin.py     # macOS 构建入口
│   ├── build_win.py        # Windows 构建入口
│   ├── build_source.py     # 源码 ZIP 构建脚本
│   ├── macos/              # macOS 构建脚本
│   │   ├── build_macos.sh   # macOS .pkg 构建脚本
│   │   ├── build_macos_pkg.sh # macOS .pkg 构建脚本
│   │   └── create_dmg.py    # DMG 创建脚本
│   └── windows/            # Windows 构建脚本
│       ├── build_windows.py        # Windows 构建脚本
│       ├── build_windows_installer.bat # Windows .bat 构建脚本
│       ├── installer_windows.iss   # Inno Setup 配置
│       └── package_windows.py     # Windows 打包脚本
└── utils/                   # 工具脚本
    ├── build_common.py       # 构建通用模块
    ├── check_gpu.py          # GPU 检测脚本
    ├── download_model.py     # 模型下载脚本
    ├── install_dependencies.py # 依赖安装脚本
    └── init_models_in_installation.py # 模型初始化脚本
```

## 使用方法

### 通过主构建脚本

```bash
# 为当前平台构建（PyInstaller）
python scripts/pyinstaller/build_installer.py

# 清理构建产物
python scripts/pyinstaller/build_installer.py --clean
```

### 直接使用 PyInstaller

```bash
# 使用 spec 文件构建
pyinstaller scripts/pyinstaller/installer_simple.spec
```

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

## 配置

构建配置直接在 `build_installer.py` 中硬编码：

```python
# Build configuration (hardcoded)
PRODUCT_NAME = "MediaFactory"
PRODUCT_VERSION = "0.2.0"
ENCRYPT_BYTECODE = True
ENCRYPTION_KEY = None  # Uses default "mediafactory-2026-secure" if None
COMPRESS_OUTPUT = True
CONFIG_FILES_TO_INCLUDE = ["config.toml", "NOTICE.txt", "README.txt"]
SPEC_FILE = "installer_simple.spec"
```

## 字节码加密

PyInstaller 支持加密 Python 字节码以降低源码泄漏风险。

### 默认加密
默认使用内置密钥加密：
```python
ENCRYPT_BYTECODE = True
ENCRYPTION_KEY = None  # Uses default key
```

### 自定义加密
修改 `build_pyinstaller.py`：
```python
ENCRYPT_BYTECODE = True
ENCRYPTION_KEY = "your-secret-key-here"
```

### 禁用加密
```python
ENCRYPT_BYTECODE = False
```

**注意**：PyInstaller 加密需要额外的加密模块。如果没有安装，构建会自动跳过加密（不会报错）。

## 创建平台安装程序

从 PyInstaller 构建结果创建安装程序：

**macOS (.pkg 安装程序)**:
```bash
python scripts/build/build_darwin.py
```
**输出**: `dist/MediaFactory-Installer-0.2.0.pkg`

**Windows (.exe 安装程序)**:
- 要求: [Inno Setup](https://jrsoftware.org/isdl.php) 6.0+
```bash
python scripts/build/build_win.py
```
**输出**: `dist/MediaFactory-Setup-0.2.0.exe`

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
- 运行时钩子设置环境变量：`HF_HOME`、`HF_HUB_CACHE`、`HUGGINGFACE_HUB_CACHE`

## 故障排除

### ImportError: No module named 'xxx'

在 `installer_simple.spec` 的 `hiddenimports` 中添加缺失的模块。

### 构建后程序无法运行

检查 `scripts/pyinstaller/installer_simple.spec` 中的：
1. `datas` 列表是否包含所有必要文件
2. `hiddenimports` 是否包含所有动态导入的模块
3. 运行程序时查看详细错误信息

### macOS 上无法运行

确保：
1. Python 版本兼容（3.11、3.12、3.13）
2. 所有依赖正确安装
3. 没有使用 UPX（macOS 不支持）

### faster-whisper 数据文件缺失

如果提示找不到 `faster_whisper/assets`，确保 `pyinstaller.spec` 中包含：
```python
datas += collect_data_files('faster_whisper')
```

## 许可证

MIT License - 与 MediaFactory 主项目相同。
