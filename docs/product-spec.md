# MediaFactory 现状规格（product-spec）

> **本文件是产品现状的 source of truth**——描述"现在是什么"。要做什么在 `docs/roadmap.md`，怎么做的设计在 `docs/superpowers/specs/`，本文件只管现状。
>
> 锚点：`c03f6ff`（最近一次回填/校对时的 commit）· 最近校对：2026-10-04
> 校对方式：diff 引导（`git log <锚点>..HEAD` + 下方可机检断言对账）

## 稳定层 — 为什么（产品级决策才动）

### 定位
本地优先的多媒体处理平台（字幕生成、转录、翻译、视频增强），FastAPI daemon 同源伺服 React SPA + Tauri 2 桌面壳交付。个人求职作品集项目，工程质量（分层架构、契约测试、CI）是核心叙事。

### 原则与口径
- 原型阶段，不考虑向后兼容；避免过度设计，优先成熟开源方案
- 单一后端包 `mediafactory/`，顶层包结构增减需开发者知会
- Tauri 壳只做进程生命周期，无业务逻辑；改业务去 SPA 或 daemon
- UI 文本英文，代码注释可中文；README.md 与 README_zh.md 双语同步
- 版本单一真相源：`pyproject.toml` 的 `project.version`，`sync_version.py` 同步下游
- 日志双模式：API 层标准 logging（InterceptHandler 转 loguru），Service/Engine/Pipeline 层直用 loguru 封装
- 翻译只有两条腿：云端 LLM API 与本地 LLM（Ollama），同一个 OpenAI 兼容后端（本地占位 key）；云端 MT 翻译 API（Azure/腾讯云/阿里云）2026-10-04 整体裁剪不再接入。降级链 LLM 批量→二分→内容过滤递归，失败句保留原文并在日志汇总（可按任务开本地兜底，见「本地模型与本地兜底」节）；本地翻译模型（M2M100）已于 2026-10-04 裁剪（commit 23cf627），翻译任务必须启用 LLM

### 非功能约束
- 平台仅 macOS / Windows（Linux 不支持）
- 本地工具，不考虑 API key 明文存储风险
- 桌面安装包捆绑全部 ML 依赖（torch/faster-whisper/stable-ts 等），翻译不再捆绑本地模型，仅依赖 LLM API 配置
- FFmpeg 统一走 imageio-ffmpeg，不依赖系统安装

## 结构层 — 有什么（ship 回填生长）

### 模块地图
| 模块 | 一句话 | 真源 |
|---|---|---|
| `mediafactory/api/` | FastAPI 路由、task_manager（SQLite 持久队列）、worker 子进程、daemon 锁、SPA 伺服 | `mediafactory/api/` |
| `mediafactory/services/` | runner（RUNNERS 按 TaskType 分发）+ 模型状态聚合 | `mediafactory/services/runner.py` |
| `mediafactory/pipeline/` | stage 编排：字幕 6-stage / 转录 4-stage / 翻译-only 2-stage 工厂 | `mediafactory/pipeline/pipeline.py` |
| `mediafactory/engine/` | Audio/Recognition(Faster Whisper)/PostProcess(stable-ts)/Translation/SRT/ASS/VTT/VideoEnhancement 引擎 | `mediafactory/engine/` |
| `mediafactory/llm/` | TranslationBackend ABC：OpenAI 兼容后端（批量+二分降级+contentFilter 递归+术语记忆）+ OllamaClient（Ollama REST 唯一封装） | `mediafactory/llm/` |
| `mediafactory/config/` | Pydantic v2 + TOML 配置，MF_ 环境变量，frozen 数据目录 | `mediafactory/config/` |
| `mediafactory/models/` | 模型注册表、whisper 运行时、模型下载任务 | `mediafactory/models/` |
| `mediafactory/persistence/` | 任务历史 SQLite（db/orm/repository） | `mediafactory/persistence/` |
| `src/` | React SPA（TypeScript + Ant Design 6 + vite），构建产物 webui/ 由 daemon 同源伺服 | `src/` |
| `src-tauri/` | Tauri 2 壳（约 250 行 Rust，仅进程生命周期） | `src-tauri/` |
| `tests/` | unit（按模块分子目录）+ integration；契约测试防线 | `tests/unit/` |
| `scripts/` | 构建/调试工具，业务代码不得调用 | `scripts/build/` |

### 功能
#### 术语表（2026-10-04，R2）
翻译任务可选 JSON 术语表（`TaskConfig.terminology`，≤200 条、单条 ≤200 字符，超限 422）。`TermDict`（`mediafactory/llm/term_memory.py`）first-wins 语义：key 小写归一化、最小 2 字符；用户种子先于翻译加载（时序保证优先，文件永不写回）；每批翻译后 LLM 自判提取「值得记」候选（≤5 条/批，提取调用不带历史 dict）滚动入典（source=auto）；命中词条经 `batch.md` 的 `${custom_instructions}` 槽位注入；译法冲突按术语表替换译文，日志按来源分级（user=warning 注入失效信号 / auto=debug 常态波动）。链路：`SubtitleRequest`/`TranslateRequest.terminology` → 路由透传 → `TranslationEngine(user_terms=)` → `TranslationRequest.user_terms` → `OpenAICompatibleBackend`。前端：字幕与翻译表单共享 `TerminologyFileField` 上传控件（hidden Form.Item 承载值）。

#### 本地模型与本地兜底（2026-10-04，R3）
**模型管理**：Settings「Local Models (Ollama)」卡片。状态与已装列表 `GET /api/models/local`；拉取 `POST /api/models/local/pull`（DOWNLOAD 类型任务 + WS 进度节流 0.5s；取消=任务置 CANCELLED 后协程停止消费流，断流即中止，终态写入前复查防覆盖取消态）；删除 `DELETE /api/models/local/{name}`（拉取中 409、Ollama 不可达 503）。Ollama 地址为常量 `OLLAMA_BASE_URL`（`constants.py`），不做用户配置。LLM 预设含 `ollama`（base_url `http://localhost:11434/v1`，免 key；ProviderDialog 的 model 字段在选中该预设时切换为已装模型下拉）。

**本地兜底**：任务级显式开启。`TaskConfig.fallback_model`（None=不兜底；≤200 字符）经 `SubtitleRequest`/`TranslateRequest` 透传。表单「Local Fallback」开关打开条件：Ollama 可用且有已装模型，且主渠道非 ollama preset（单向：本地主渠道不兜底）。编排点 `TranslationEngine.translate_texts`：主链 `translate_detailed()` 的失败句（空串映射后的最终空间索引）按源文转投兜底 backend（同一 `OpenAICompatibleBackend` 指向 Ollama `/v1`），`TermDict` 跨主/兜底共享；兜底再失败保留原文（R1 终态），不二次兜底。四计数 `translation_stats {total, remote, fallback, failed}` 随 `ProcessingResult.metadata` 入历史表 metadata_json，History「Translation Stats」列展示；句级明细只进日志。生命周期：随用随载（Ollama 原生行为）+ 翻译步骤结束卸载（keep_alive 0，先查 `/api/ps` 未加载不触发；卸载异步生效）。backend 层 `translate_detailed()` 返回 `DetailedTranslationResult`（translations + failed_indices + term_dict），`translate()` 为其薄包装；`_translate_all_texts` 返回 `(译文, 失败索引)` 二元组，失败索引已从非空空间映射回含空串的最终空间。

（ship 时按 ADDED/MODIFIED/REMOVED 增量生长；五种任务类型：音频提取、转录、字幕生成、字幕翻译、视频增强——audio/enhance 单动作直调引擎不走 Pipeline）

## 派生层 — 指针（永不手写）

| 内容 | 真源 | 版本锚 |
|---|---|---|
| 架构细节与实现约定 | CLAUDE.md | 完整内嵌版 |
| 契约测试清单（115 个） | CLAUDE.md「测试」节 | 115 |
| 打包链 | BUILD.md | — |
| API 文档 | docs/api.md | — |
| 版本号 | pyproject.toml `project.version` | 0.4.0 |

## 可机检断言

- [ ] `pyproject.toml` 的 project.version == package.json 的 version == src-tauri/Cargo.toml 的 version（`uv run python scripts/utils/sync_version.py --check`）
- [ ] `mediafactory/persistence/` 存在且含 db.py/orm.py/repository.py
- [ ] daemon 端口 8765（`mediafactory/api/` 内常量）
- [ ] `uv run pytest -m "unit"` 全绿
