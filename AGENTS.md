# AGENTS.md

**MediaFactory**：多媒体处理平台（字幕生成、转录、翻译、视频增强）。FastAPI daemon（127.0.0.1:8765，同源伺服 React SPA）+ Tauri 2 桌面壳；平台仅 macOS / Windows。深度参考：**CLAUDE.md**（完整架构、契约测试清单、实现细节）、BUILD.md（打包链）。

## 目录

- `mediafactory/` — 全部后端，单一包。分层：`api/`（FastAPI 路由、task_manager、worker）→ `services/runner.py`（RUNNERS 按 TaskType 分发）→ `pipeline/`（stage 编排）→ `engine/`；另有 `llm/`、`config/`、`models/`
- `src/` — React SPA（TypeScript + Ant Design + vite），构建产物输出 `webui/`
- `src-tauri/` — Tauri 壳（约 250 行 Rust，只做进程生命周期：拉起 daemon / 优雅停机，**无业务逻辑**；改业务去 SPA 或 daemon）
- `tests/` — `unit/`（按模块分子目录）+ `integration/`
- `scripts/` — 仅构建与调试工具，`mediafactory/` 业务代码**不得**调用
- `docs/roadmap.md` — 需求池（以后做什么的唯一登记处）；`docs/product-spec.md` — 现状规格（现在是什么，ship 时回填）

## 常用命令

```bash
# 开发（两个终端）：daemon 启动时固化 webui/ 伺服，前端重新 build 后需重启 daemon
uv run python -m mediafactory     # daemon（8765）
npm run dev                       # vite（5173，代理 /api 与 /ws）

uv sync --all-groups              # 开发者安装（core 组含 ML 依赖）
pytest -m "unit"                  # 测试（pytest 配置在 pyproject.toml）
uv run ruff format mediafactory/ tests/ && uv run ruff check mediafactory/
uv run mypy mediafactory/         # 类型检查
npm run typecheck                 # 前端 TS 检查；npx eslint src/ 为 lint

uv run python scripts/build/build_darwin.py   # macOS 安装包全链（需 Rust ≥1.77.2）
```

## 硬性规则

- **日志双模式**：API 层用 `logging.getLogger(__name__)`（经 InterceptHandler 转 loguru）；Service/Engine/Pipeline 层用 `from mediafactory.logging import log_info, log_error`。两层互不混用。
- **UI 文本必须英文**（按钮、标签、错误消息）；代码注释可中文。
- **版本单一真相源**：`pyproject.toml` 的 `project.version`，用 `scripts/utils/sync_version.py` 同步到 package.json / Cargo.toml / BUILD.md。
- README.md 与 README_zh.md 必须同时更新；顶层包结构增减需先知会开发者。
- 原型阶段，不考虑向后兼容；避免过度设计。

## Gotchas

- **契约测试防线**：改 runner / task_manager / task_store / worker / pipeline / download_task / daemon_lock / system 路由 / SPA 伺服 / config 数据目录前，先确认对应契约测试全绿（清单见 CLAUDE.md「测试」节，共 213 个）。
- `ModelLoadingStage` 未在 `pipeline/__init__.py` 导出，需从 `stages` 导入。
- audio / enhance 为单动作流程，runner 直调引擎，不走 Pipeline。
- Faster Whisper：`transcribe()` 返回的生成器必须消费（`list(...)`）；不支持 MPS（macOS 走 CPU int8）。
- FFmpeg 统一用 `imageio-ffmpeg`，不依赖系统 FFmpeg。
- 全新 clone 后直接 `cd src-tauri && cargo build` 会报 resources 缺失——`python-backend/` 由构建脚本组装、不入库，先跑一键构建。
- 新增 LLM 预设只需改 `constants.py` 的 `BASE_URL_PRESETS`，不写新后端类。
- daemon 单实例锁：双开第二个以 `SystemExit(42)` 让位退出（Tauri 壳据此区分双启动与崩溃）。
