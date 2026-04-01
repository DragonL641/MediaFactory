# MediaFactory 项目面试 Q&A

> 基于项目代码、git 历史、OpenSpec 变更记录整理

---

## 目录

- [项目简介（技术角度）](#项目简介技术角度)
- [零、从零理解本项目需要的技术栈（学习路线）](#零从零理解本项目需要的技术栈学习路线)
- [一、项目概述与动机](#一项目概述与动机)
- [二、架构设计](#二架构设计)
- [三、核心技术决策](#三核心技术决策)
- [四、工程实践](#四工程实践)
- [五、性能与优化](#五性能与优化)
- [六、异常处理与可靠性](#六异常处理与可靠性)
- [七、过度设计的反思](#七过度设计的反思)
- [八、扩展性](#八扩展性)
- [九、构建与部署](#九构建与部署)
- [十、技术细节快问快答](#十技术细节快问快答)

---

## 项目简介（技术角度）

**MediaFactory** 是一个跨平台（macOS / Windows）多媒体处理桌面应用，采用 **Electron + FastAPI 混合架构**，将 Python ML 生态与 Web 前端技术结合，提供视频字幕生成、语音转录、翻译和视频增强等功能。

### 技术栈一览

| 层次 | 技术 | 职责 |
|------|------|------|
| **前端** | Electron + React 18 + TypeScript + Ant Design | 桌面壳、UI 渲染、用户交互 |
| **通信** | HTTP REST + WebSocket (127.0.0.1:8765) | 请求/响应 + 实时进度推送 |
| **后端** | FastAPI + Uvicorn | API 服务、任务调度、WebSocket 管理 |
| **服务层** | Python async + ThreadPoolExecutor | 异步桥接、进度适配 |
| **编排层** | Pipeline (自研) | 阶段式任务编排、进度范围映射 |
| **引擎层** | Faster Whisper / OpenAI API / FFmpeg / RealESRGAN | 实际计算（转录、翻译、音视频处理） |
| **配置** | TOML + Pydantic v2 | 声明式配置、校验、环境变量覆盖 |
| **打包** | PyInstaller (后端) + electron-builder (前端) | 双步打包为桌面安装包 |

### 架构一句话总结

```
Electron (React)  ──HTTP/WS──▶  FastAPI  ──▶  Service  ──▶  Pipeline  ──▶  Engine
    前端 UI                    API 层        桥接层        编排层         计算层
```

### 核心处理流程（以字幕生成为例）

```
视频文件
  → AudioEngine (FFmpeg 提取音频, 10-20%)
  → RecognitionEngine (Faster Whisper 转录, 20-70%)
  → TranslationEngine (LLM API / 本地模型翻译, 70-95%)
  → SRTEngine (生成 SRT/ASS 字幕, 95-100%)
```

### 项目规模

- **~90 个 Python 文件**（后端）+ **~30 个 TypeScript/React 文件**（前端）
- **~15 个测试文件**
- **30+ OpenSpec 规范**，**40+ 已归档变更记录**

---

## 零、从零理解本项目需要的技术栈（学习路线）

按依赖关系从底到顶排列，每层是理解下一层的前提。

### 第一阶段：语言基础

| 技术点 | 为什么要学 | 学到什么程度 |
|--------|-----------|-------------|
| **Python 3.11+** | 项目后端语言 | dataclass、Protocol、ABC、context manager、asyncio、`__init__.py` 包机制、typing |
| **TypeScript** | 前端语言 | 类型系统、interface/enum、泛型、模块导入 |
| **React 18** | 前端 UI 框架 | 函数组件、Hooks（useState/useEffect/useMemo）、条件渲染 |

### 第二阶段：后端核心框架

| 技术点 | 在项目中的角色 | 学到什么程度 |
|--------|---------------|-------------|
| **FastAPI** | Web 服务框架，暴露 REST API + WebSocket | 路由定义、依赖注入、lifespan 生命周期、Pydantic 模型校验 |
| **Pydantic v2** | 数据校验与序列化，贯穿后端所有层 | BaseModel 定义、Field 校验、`model_validator`、`model_dump` |
| **Uvicorn** | ASGI 服务器，运行 FastAPI | 基本启动即可，理解 `python -m mediafactory` 最终调用了 `uvicorn.run()` |
| **TOML** | 配置文件格式 | `[section]` 语法、`[[array]]`、Python `tomllib` 读写 |

### 第三阶段：前端技术栈

| 技术点 | 在项目中的角色 | 学到什么程度 |
|--------|---------------|-------------|
| **Electron** | 桌面应用壳，管理窗口和子进程 | 主进程 vs 渲染进程、IPC 通信、BrowserWindow、app 生命周期 |
| **Ant Design** | UI 组件库 | Table/Card/Modal/Form/Select 等常用组件、ConfigProvider 主题 |
| **React Router** | 前端路由 | `<Routes>/<Route>` 声明式路由、`useNavigate` |
| **Axios** | HTTP 客户端 | 实例创建、拦截器、请求/响应处理 |
| **React Query (TanStack Query)** | 服务端状态管理 | `useQuery`/`useMutation`、缓存策略（staleTime）、`queryClient.invalidateQueries` |
| **WebSocket** | 实时进度推送 | `new WebSocket()`、`onmessage`、重连机制、订阅/发布模式 |

### 第四阶段：AI/ML 基础

| 技术点 | 在项目中的角色 | 学到什么程度 |
|--------|---------------|-------------|
| **Faster Whisper (CTranslate2)** | 语音转文字引擎 | `model.transcribe()` API、segment 数据结构、VAD、beam_size、量化(int8/float16) |
| **HuggingFace Hub** | 模型下载与管理 | `snapshot_download()`、模型缓存机制、进度回调 |
| **OpenAI 兼容 API** | LLM 翻译后端 | `/v1/chat/completions` 接口格式、API Key 认证、role/content/message 结构 |
| **Torch (PyTorch)** | ML 推理后端 | `torch.cuda.empty_cache()`、CUDA/MPS/CPU 设备管理、显存释放（不需要训练知识） |
| **RealESRGAN** | 视频超分辨率增强 | 基本概念即可，项目通过封装的 `VideoEnhancementEngine` 调用 |

### 第五阶段：工程化与工具链

| 技术点 | 在项目中的角色 | 学到什么程度 |
|--------|---------------|-------------|
| **FFmpeg (imageio-ffmpeg)** | 音频提取、视频合成、字幕嵌入 | subprocess 调用、常用参数（`-i`, `-vn`, `-ar`, `-ac`, `-f`） |
| **PyInstaller** | Python 后端打包为可执行文件 | `.spec` 文件配置、hidden imports、hooks 机制 |
| **electron-builder** | Electron 前端打包 | `electron-builder.yml` 配置、macOS/Windows 打包流程 |
| **Vite** | 前端构建工具 | 基本概念即可，项目配置已就绪 |
| **pytest** | 测试框架 | fixture、marker（`@pytest.mark.unit`）、`conftest.py`、coverage |
| **Git / Conventional Commits** | 版本管理 | commit message 规范（feat/fix/refactor）、branch 策略 |

### 第六阶段：本项目核心设计模式

理解上述技术后，需要掌握项目中使用的架构模式：

| 模式 | 项目体现 | 理解重点 |
|------|---------|---------|
| **Pipeline 编排** | `ProcessingStage` → `Pipeline.execute()` | 阶段拆分、顺序执行、进度范围映射 |
| **Protocol 接口** | `ProgressCallback`、`ResourceCleanupProtocol` | Python Protocol vs ABC、依赖倒置 |
| **桥接模式** | `GUIProgressBridge`（Engine 进度 → 总体进度） | 范围映射、批处理进度 |
| **单例模式** | `ModelResourceManager`、`AppConfigManager` | 线程安全双重检查锁、`__new__` |
| **策略模式** | LLM 翻译 vs 本地翻译 | 统一接口、运行时切换 |
| **发布-订阅** | WebSocket `ConnectionManager` | 连接管理、任务订阅、广播 |
| **上下文管理器** | `whisper_model()`、`wrap_exceptions()` | `__enter__`/`__exit__`、资源释放保证 |
| **观察者模式（已移除）** | 配置变更通知 | 作为反面教材：过度设计 → 删除 |

### 学习建议

- **最小可运行路径**：Python + FastAPI + Faster Whisper → 先跑通后端 API，再理解前端
- **不需要一次全学**：按需学习，比如只看转录功能时不需要理解视频增强
- **重点理解分层**：API → Service → Pipeline → Engine 是理解项目的关键主线

---

## 一、项目概述与动机

### Q1: 请介绍一下你的项目，它解决了什么问题？

**A:** MediaFactory 是一个面向个人的多媒体处理桌面工具，核心解决的是视频字幕生成流程中的多个痛点：

1. **语音转文字**：使用 Faster Whisper 进行本地转录，比 OpenAI Whisper 快 4-6 倍
2. **翻译**：支持 LLM API（OpenAI、DeepSeek、GLM 等 6+ 服务）和本地模型（M2M100），并提供智能降级策略
3. **字幕生成**：生成 SRT/ASS/TXT 等多种格式，支持双语字幕
4. **视频增强**：RealESRGAN 超分辨率、降噪、时序平滑

本质上就是把"从视频提取字幕"这个多步骤流程自动化，并提供一个可视化界面让非技术用户也能使用。

> **技术细节：** 本项目的 5 种任务类型——字幕生成（Subtitle）、音频提取（Audio）、语音转录（Transcribe）、文本翻译（Translate）、视频增强（Enhance）——对应 5 种不同的 Pipeline 组合。字幕生成是最复杂的，包含全部 6 个 Stage；而音频提取只需要 1 个 Stage。这种设计使得共用引擎层代码的同时，能灵活组合出不同的任务流程。

### Q2: 目标用户是谁？为什么不做一个 Web 服务？

**A:** 目标用户是个人用户，主要场景是给视频加字幕。选择本地桌面应用有几个原因：

- **隐私**：视频内容不需要上传到服务器
- **无服务器成本**：作为个人工具，不需要维护后端基础设施
- **模型常驻内存**：Whisper 模型加载一次后可以反复使用，本地运行效率更高
- **离线可用**：本地模型支持完全离线转录和翻译

> **技术细节：** 桌面应用 vs Web 应用的选型本质是**计算发生在哪里**。本项目需要加载 3GB+ 的 Whisper 模型和 3.7-34GB 的翻译模型到内存/GPU，这些模型一旦加载就应该常驻（避免重复加载的 10-30 秒延迟）。Web 应用意味着模型在服务器上，要么自建服务器（成本高），要么每次调用远程 API（延迟高、隐私风险）。本地桌面应用让模型直接运行在用户硬件上，是最自然的选择。

---

## 二、架构设计

### Q3: 介绍一下整体架构？

**A:** 采用 Electron + FastAPI 的混合架构，分四层：

```
前端层 (Electron + React + Ant Design)
    ↓ HTTP/WebSocket (127.0.0.1:8765)
API 层 (FastAPI + WebSocket)
    ↓
服务层 (Service: 异步桥接、进度适配)
    ↓
流水线层 (Pipeline: 阶段编排)
    ↓
引擎层 (Engine: 实际计算)
```

- **Electron 主进程**负责管理 Python 子进程的生命周期
- **FastAPI**作为后端服务，暴露 REST API 和 WebSocket
- **Service 层**是 API 和 Pipeline 之间的桥梁，处理异步到同步的转换
- **Pipeline 层**用编排模式将处理流程拆分为独立的 Stage
- **Engine 层**是实际干活的，每个 Engine 对应一个具体能力

> **技术细节：** 分层架构的核心思想是**关注点分离**（Separation of Concerns）。每一层只负责一件事：API 层处理 HTTP 协议，Service 层处理异步/同步转换，Pipeline 层处理流程编排，Engine 层处理具体算法。这样改动一层不影响其他层——实际验证了这一点：从 Flet 迁移到 Electron 时，Service/Pipeline/Engine 三层几乎零改动。关键源码路径：`src/mediafactory/api/`（API 层）→ `src/mediafactory/services/`（Service 层）→ `src/mediafactory/pipeline/`（Pipeline 层）→ `src/mediafactory/engine/`（Engine 层）。

### Q4: 为什么选择 Electron + FastAPI 而不是纯 Electron 或纯 Python GUI？

**A:** 这其实是一个**架构迁移**的决策。项目最初用的是 **Flet**（Python GUI 框架），后来迁移到了 Electron。

迁移的原因：
1. **Flet 稳定性差**：首次启动需要下载约 1GB 的 Flutter SDK，用户体验很差
2. **社区规模小**：Flet 社区相对小，遇到问题很难找到解决方案
3. **PyInstaller 兼容性**：Flet + PyInstaller 打包非常复杂，经常出问题
4. **模型常驻需求**：需要一个独立的后端进程来管理模型的生命周期

也考虑过 **python-shell**（Electron 直接 spawn Python 进程），但这种方式无法让模型常驻内存——每次调用都要重新加载模型，太慢了。

最终选择 Electron + FastAPI：
- FastAPI 独立进程管理模型生命周期
- HTTP/WebSocket 通信简单可靠
- 前端可以用成熟的 React 生态
- PyInstaller 只打包后端，electron-builder 打包前端，职责清晰

> **技术细节：** Electron 应用有两种常见的 Python 集成方式：(1) **python-shell**：每次调用都 spawn 一个新的 Python 进程，简单但模型无法常驻；(2) **独立后端服务**（本项目采用）：Python 作为独立进程运行 FastAPI，通过 HTTP 通信。方式 (2) 的优势在于 Python 进程是持久的，模型加载一次后可被多次请求复用。项目中 Electron 主进程通过 `pythonManager.ts` 管理 Python 子进程的启动、健康检测和退出。FastAPI 监听 `127.0.0.1:8765`，仅接受本地连接（CORS 限制为 localhost）。

### Q5: 为什么用 WebSocket 而不是纯 HTTP 轮询？

**A:** 处理一个视频任务可能需要几分钟到几十分钟，需要实时推送进度。

- **HTTP 轮询**：需要客户端不断发请求，浪费资源，延迟高
- **WebSocket**：服务端主动推送，实时性好，连接管理也简单

实现上用了发布-订阅模式：客户端连接 WebSocket 后订阅特定 task_id，服务端只向订阅了该任务的客户端广播进度。

> **技术细节：** WebSocket 是全双工通信协议，建立连接后客户端和服务端可以随时互发消息。与 HTTP 的请求-响应模式不同，WebSocket 连接一旦建立就不需要重复握手。本项目在 `api/websocket.py` 中实现了 `ConnectionManager`，维护一个 `{task_id: set[WebSocket]}` 的映射表。客户端发送 `{"type": "subscribe", "task_id": "xxx"}` 消息来订阅，服务端调用 `broadcast_progress(task_id, progress_data)` 只推送给订阅了该任务的客户端。这种设计避免了不相关的任务进度干扰前端 UI。

### Q6: Pipeline 模式是怎么设计的？为什么不直接在一个函数里顺序调用？

**A:** Pipeline 模式把处理流程拆分成独立的 `ProcessingStage`，每个阶段有：
- `should_execute()`：是否需要执行
- `execute()`：实际执行
- `validate()`：执行后验证
- `on_error()`：错误处理

好处：
1. **灵活性**：可以组合不同的 Pipeline（`create_default()`, `create_transcription_only()`, `create_audio_only()` 等），同一套代码支持多种任务类型
2. **可测试性**：每个 Stage 可以独立测试
3. **进度追踪**：每个 Stage 有明确的进度范围（如 Transcription 20-70%），进度报告很自然
4. **可扩展**：新增功能只需加一个新的 Stage，不影响已有逻辑

如果写在一个大函数里，这些都会变成 if-else，随着功能增加越来越难维护。

> **技术细节：** Pipeline 模式是**责任链模式**（Chain of Responsibility）的变体。每个 `ProcessingStage` 定义在 `pipeline/stage.py` 中，是一个 ABC，包含 `should_execute(ctx) -> bool`、`execute(ctx)`、`validate(ctx)`、`on_error(ctx, error)` 四个生命周期方法。`Pipeline.execute()` 按顺序遍历所有 Stage，调用 `should_execute()` 判断是否跳过，`execute()` 执行具体逻辑，出错时调用 `on_error()`。每个 Stage 的进度范围通过 `ctx.set_stage("transcription", 20, 70)` 设置，`ProcessingContext` 据此将引擎层的局部进度映射为全局 0-100% 进度。工厂方法 `Pipeline.create_default()` 返回完整的 6 阶段 Pipeline，`create_transcription_only()` 只返回模型加载+转录两个阶段。

---

## 三、核心技术决策

### Q7: 为什么选 Faster Whisper 而不是 OpenAI Whisper？

**A:** 核心原因是**性能**。Faster Whisper 基于 CTranslate2 量化推理，在相同精度下：
- 速度提升 4-6 倍（相同硬件）
- 内存占用降低约 50%（int8 量化）
- 支持 CPU 和 CUDA

OpenAI Whisper 的 Python 实现比较重，推理效率低。对于需要频繁转录的桌面工具来说，这个性能差距是决定性的。

> **技术细节：** Faster Whisper 和 OpenAI Whisper 使用的是**同一个模型权重**（如 `large-v3`），区别在于推理引擎。OpenAI Whisper 使用 PyTorch 原生推理，而 Faster Whisper 使用 CTranslate2 引擎。CTranslate2 通过 INT8 量化（将 float32 权重压缩为 int8）和优化的 CUDA kernel 实现加速。int8 量化的精度损失极小（通常 < 1% WER 差异），但速度提升显著。项目中固定使用 `Systran/faster-whisper-large-v3` 模型，通过 `resource_manager.py` 的 `whisper_model()` 上下文管理器加载，确保使用完毕后正确释放 GPU 显存。

### Q8: LLM 翻译的降级策略是怎么设计的？

**A:** 这是一个逐步降级的设计，解决的是 LLM API 不可靠的问题（内容审核拦截、网络超时、API 限流等）：

```
批量翻译（20行/批）
    ↓ 失败（行数不匹配）
纠正：重新翻译不匹配的行
    ↓ 仍然失败
拆分：分成 2 个小批次
    ↓ 仍然失败
逐句翻译（每句独立请求）
    ↓ 仍然失败
本地模型回退（M2M100-418M）
    ↓ 仍然失败
报错
```

每一步都是上一步失败后的更保守策略。批量翻译效率最高但最脆弱，逐句翻译最慢但最可靠，本地模型是最后兜底。

实现上还有一个细节：本地模型采用**懒加载 + 任务期间保留**策略——只有 LLM 失败时才加载本地模型，且加载后在整个任务期间保留，避免重复加载。

> **技术细节：** 批量翻译的核心挑战是**行数一致性**——发给 LLM 20 行，必须返回恰好 20 行翻译，否则字幕时间轴会错位。项目中使用 JSON 格式输出（`{"1": "翻译1", "2": "翻译2", ...}`）来保证结构化。当返回行数不匹配时，"纠正"步骤会找出缺失/多余的行号，只重新翻译这些行。"逐句翻译"使用 `resources/prompts/translate/single.md` 模板，包含上一句、当前句、下一句作为上下文，牺牲速度换取翻译质量。本地回退使用 `M2M100-418M` 模型（3.7GB），通过 `llm/local_fallback.py` 中的 `LocalModelFallback` 类实现，支持 100+ 语言，在 CPU 上每句翻译约 0.5-1 秒。

### Q9: 翻译引擎为什么从 3 个类合并成 1 个类？

**A:** 早期设计了 `TranslationEngine` 基类 + `LocalTranslationEngine` + `LLMTranslationEngine` 两个子类。实际开发中发现：

1. **80% 代码重复**：两个子类的翻译流程几乎一样，只有"调用 LLM"和"调用本地模型"这几行不同
2. **切换逻辑复杂**：用户选择 LLM 但失败时要回退到本地，跨两个类的调用很别扭
3. **基类没有真正的多态价值**：不需要在运行时切换引擎类型

合并后用一个类内部通过 `if use_llm` 分支处理，代码量减少很多，降级逻辑也更自然。

这其实是一个**过度设计的教训**——一开始就设计了继承体系，但实际需求并没有那么复杂。

> **技术细节：** 这是经典的**"三个类派生自一个基类"反模式**（Three-derivative anti-pattern）。当基类只有一个或两个子类，且子类之间逻辑高度相似时，继承带来的多态价值远不及其复杂度成本。更好的做法是：先用一个类实现完整功能，当出现第 3 个真正不同的变体时，再考虑提取基类。Go 语言的名言"一点一点地抽象，不要过早"（A little copying is better than a little dependency）说的就是这个道理。项目中合并后的 `TranslationEngine` 在 `engine/translation.py` 中，通过 `self._llm_backend` 是否为 None 来判断使用 LLM 还是本地模型。

### Q10: 进度系统是怎么跨层传递的？

**A:** 这是项目中比较有趣的设计。问题是：Engine 层只知道自己完成了多少（比如转录了 50/100 段），但前端需要的是 0-100% 的总体进度。

解决方案是 **`GUIProgressBridge`**（进度桥接器）：

```
Engine 报告: "转录进度 50/100 段"
    ↓
GUIProgressBridge 映射:
  TranscriptionStage 的范围是 20%-70%
  所以 50/100 映射到 20% + (50/100) * 50% = 45%
    ↓
通过 ProgressCallback 回调到 Service 层
    ↓
Service 层通过 WebSocket 推送到前端
```

每个 Stage 有一个预定义的进度范围：
- ModelLoading: 0-10%
- AudioExtraction: 10-20%
- Transcription: 20-70%（主要耗时）
- Translation: 70-95%
- SRTGeneration: 95-100%

这样不管内部怎么变，前端拿到的始终是 0-100 的连续进度。

> **技术细节：** 进度桥接的数学原理是**线性映射**。假设当前 Stage 的全局范围是 `[stage_start, stage_end]`，引擎报告局部进度 `local_progress`（0-100），则全局进度 = `stage_start + (local_progress / 100) * (stage_end - stage_start)`。例如转录阶段 50% → `20 + 0.5 * 50 = 45%`。`GUIProgressBridge` 在 `core/progress_bridge.py` 中实现，还支持批处理嵌套：当一次处理多个文件时，外层进度按文件数分配，内层进度按当前文件的阶段分配。`ProgressCallback` 是一个 Python Protocol（类似 TypeScript 的 Interface），定义了 `update(progress, message)` 和 `is_cancelled()` 两个方法，所有引擎都依赖这个抽象而非具体的 UI 组件。

---

## 四、工程实践

### Q11: 你提到经历过一次从 Flet 到 Electron 的迁移，这个过程中遇到了什么挑战？

**A:** 这是项目中最大的架构变动，主要挑战：

1. **前后端分离**：原本 Flet 直接调用 Python 函数，迁移后变成了 HTTP 通信，需要设计完整的 API 层（路由、数据模型、WebSocket）
2. **状态管理**：Flet 是命令式 UI，状态在 Python 端；迁移到 React 后需要用 React Query 管理服务端状态
3. **进程管理**：新增了 Electron 主进程管理 Python 子进程的逻辑，包括启动检测、错误处理、退出清理
4. **Service 层改造**：原来 Service 直接被 UI 调用，现在需要通过 FastAPI 路由间接调用，需要处理异步到同步的转换（`run_in_executor`）

最大的收获是：**Service 层和 Pipeline 层几乎没有改动**——这说明分层架构的抽象是对的，切换前端框架不需要重写业务逻辑。

> **技术细节：** 这次迁移的关键洞察是**分层架构的价值在于隔离变化**。迁移过程中改动最大的是：(1) 新增 `api/` 整个目录（路由、schemas、WebSocket、任务管理），约 500 行新代码；(2) 新增 `src/electron/` 整个前端，约 2000 行新代码。而 `services/`、`pipeline/`、`engine/` 三个目录的改动仅限于：Service 方法签名从同步改为 async（因为 FastAPI 需要），以及进度回调从直接调用 GUI 改为通过 WebSocket 推送。这验证了"洋葱架构"（Onion Architecture）的核心思想——业务逻辑在最内层，不依赖外层的 UI 框架选择。

### Q12: 内存泄漏是怎么发现的？怎么解决的？

**A:** 发现过程：关闭应用窗口后，用 `ps aux` 发现进程还在运行，RSS 占用 378MB。进一步排查发现翻译模型（6-12GB）从未被释放。

根本原因有几个：
1. **循环引用**：Pipeline 持有 Context 引用，Context 持有模型引用，模型持有回调引用，形成环，Python GC 无法回收
2. **后台线程泄漏**：Whisper 转录使用后台线程，任务结束后线程未被正确终止
3. **GPU 显存**：`torch` 占用的显存不会自动释放

解决方案：
1. 定义了 `ResourceCleanupProtocol` 接口，要求所有持有资源的组件实现清理方法
2. 使用 `weakref` 弱引用打破循环引用
3. 实现多层清理机制：Pipeline 完成后通知 Service → Service 释放资源 → GUI 关闭时触发全局清理
4. 调用 `torch.cuda.empty_cache()` 释放显存

修复后关闭应用能正确释放 9-15GB 内存。

> **技术细节：** Python 的垃圾回收器（GC）使用引用计数作为主要机制，但**引用计数无法处理循环引用**（A→B→A）。当 Pipeline 持有 ProcessingContext、Context 持有模型实例、模型持有进度回调（回调中又引用了 Context）时，就形成了循环引用。解决方案之一是使用 `weakref.ref()` 创建弱引用——弱引用不增加引用计数，不会阻止对象被回收。`ResourceCleanupProtocol` 定义在 `core/resource_protocol.py` 中，是一个 Python Protocol（结构化子类型），要求实现 `cleanup()` 方法。Pipeline 执行完毕后会遍历所有实现了该协议的组件并调用 `cleanup()`。`torch.cuda.empty_cache()` 释放的是 PyTorch 的 CUDA 缓存分配器持有的空闲显存，不会影响正在使用的张量。

### Q13: 配置系统为什么用 TOML 而不是 JSON 或 YAML？

**A:** 主要考虑：
1. **可读性**：TOML 比 JSON 更易读（支持注释、不需要引号），比 YAML 更安全（不会有意外的类型转换）
2. **Python 生态**：`tomllib` 是 Python 3.11+ 标准库，零依赖
3. **适合扁平/半嵌套配置**：项目配置不复杂，TOML 的 `[section]` 语法刚好够用

配置用 Pydantic v2 模型做校验，支持 `MF_` 环境变量覆盖。更新配置用双下划线语法：`update_config(whisper__beam_size=7)`。

> **技术细节：** TOML（Tom's Obvious Minimal Language）的设计哲学是"明显应该是最小化的"。相比 JSON：支持注释（`#`）、不需要给 key 加引号、尾逗号不报错。相比 YAML：不会把 `on`/`yes`/`true` 混淆为布尔值、缩进敏感度更低。Python 3.11+ 内置 `tomllib`（只读），写入需要第三方库 `tomli_w`。项目中的 `AppConfigManager` 在 `config/manager.py` 中，Pydantic 模型在 `config/models.py` 中定义。环境变量覆盖机制是 Pydantic v2 的 `model_validator(mode="before")` 实现的——从 `os.environ` 中读取 `MF_` 前缀的变量，映射到对应字段。

### Q14: 项目的"无模型"构建策略是什么意思？

**A:** 翻译模型很大（M2M100-1.2B 约 9.9GB），如果捆绑在安装包里：
- 安装包体积巨大
- 用户可能只需要其中一个模型
- 模型更新需要重新发版

所以采用"无模型"策略：
- PyInstaller 打包不包含 ML 模型
- 首次启动时引导用户下载所需模型
- 模型存储在 `./models/` 目录，独立于应用

模型管理有完整的下载/删除/完整性校验机制，还根据系统内存判断是否适合本地翻译模型（M2M100-1.2B 需要 ~5GB RAM），否则推荐使用 LLM API。

> **技术细节：** 模型下载使用 `huggingface_hub.snapshot_download()`，它会将整个 HuggingFace 仓库下载到 `models/{org}/{model_name}/` 目录。下载是增量的——如果文件已存在且校验和匹配，会跳过。模型完整性校验通过 `models/model_registry.py` 中的 `is_model_complete()` 实现：对比本地文件总大小与 HuggingFace API 返回的预期大小。`PyInstaller` 打包时通过 `.spec` 文件的 `excludes` 列表排除 `torch`、`transformers`、`faster_whisper` 等大型依赖，将打包体积从 ~10GB 降至 ~200MB。用户首次运行时通过 Setup Wizard 引导 `pip install` 这些 ML 依赖。

---

## 五、性能与优化

### Q15: Faster Whisper 的转录速度优化是怎么做的？

**A:** 几个关键优化：

1. **量化**：使用 int8 量化，内存减半，速度提升
2. **VAD 过滤**：启用 Voice Activity Detection，跳过静音片段，减少无效计算
3. **硬件适配**：自动检测 CUDA/CPU，CUDA 使用 float16
4. **进度追踪**：通过自定义 tqdm 回调实时报告转录进度，同时支持取消

有一个坑是 Faster Whisper 的 `transcribe()` 返回的是 `(segments_generator, info)`，**生成器必须被消费**，否则什么都不会发生。这个在早期踩过。

> **技术细节：** INT8 量化是将神经网络权重从 float32（4 字节）压缩到 int8（1 字节），内存占用减少约 75%。量化后的模型精度损失极小，因为神经网络对权重的小幅扰动有天然的鲁棒性。VAD（Voice Activity Detection）使用 Silero VAD 模型（仅 2MB），在转录前先扫描音频，标记出有人声的片段，Whisper 只对这些片段做推理，静音部分直接跳过。对于对话类视频（大量静音间隔），VAD 可以将转录时间缩短 30-50%。`beam_size` 参数控制 Beam Search 的宽度——值越大搜索空间越大、结果越准确，但速度越慢。项目中默认 `beam_size=5`。

### Q16: 大文件（比如 2 小时的视频）怎么处理？

**A:** 主要是转录阶段的挑战。2 小时视频转录可能需要 30 分钟以上：

1. **进度追踪**：Faster Whisper 逐段转录，我们通过 tqdm 回调获取实时进度
2. **取消机制**：使用 `CancellationToken`，转录循环中每次迭代检查是否取消
3. **内存管理**：音频提取为临时文件，不全部加载到内存
4. **批处理**：`BatchProcessor` 支持多文件批量处理，逐个执行

> **技术细节：** `CancellationToken` 在 `core/tool.py` 中实现，内部封装了 `threading.Event`。与直接使用 `threading.Event` 相比，它提供了语义化的 `cancel()` 和 `is_cancelled()` 方法，并且是协作式取消（Cooperative Cancellation）——引擎代码需要在合适的位置主动检查 `is_cancelled()`，而不是暴力终止线程。Faster Whisper 的转录是一个生成器，每次 `next()` 返回一个 segment，我们在每次迭代之间检查取消标志，实现"逐段可取消"。音频提取使用 FFmpeg 的 `-vn`（去掉视频轨）和 `-ar 48000`（重采样到 48kHz）参数，输出为临时 WAV 文件，转录完成后自动清理。

### Q17: 模型选择逻辑是怎么设计的？

**A:** 根据硬件自动推荐：

```python
# 查询可用内存和显存
total_ram = get_system_total_memory_gb()
available_vram = get_available_vram_gb()

# 翻译模型选择（唯一本地模型）
if total_ram >= 16:  # 9.9GB 模型需要 16GB RAM
    recommend "facebook/m2m100_1.2B"
else:  # 内存不足
    recommend "使用 LLM API 翻译"
```

模型注册表（`MODEL_REGISTRY`）里记录了每个模型的文件大小、运行内存需求、支持的语言等信息，选择时综合考虑。

> **技术细节：** `MODEL_REGISTRY` 在 `models/model_registry.py` 中是一个字典，每个模型条目是 `ModelInfo` dataclass，包含 `huggingface_id`、`file_size_gb`、`runtime_memory_gb`（CPU 推理所需内存）、`gpu_memory_gb`（GPU 推理所需显存）、`supported_languages` 等字段。`get_best_translation_model_for_installation()` 函数通过 `psutil.virtual_memory().available` 获取可用内存、`torch.cuda.mem_get_info()` 获取可用显存，然后从最大的模型开始尝试，找到第一个硬件能满足的模型推荐给用户。这个逻辑在首次启动的 Setup Wizard 中调用。

---

## 六、异常处理与可靠性

### Q18: 如果 LLM API 调用失败怎么办？

**A:** 多层防护：

1. **重试机制**：基于 tenacity，API 调用最多重试 3 次，指数退避
2. **降级策略**：批量 → 纠正 → 分批 → 逐句 → 本地回退（前面提到的）
3. **异常分类**：区分 `RateLimitError`（等一等再试）、`AuthenticationError`（配置问题）、`NetworkError`（网络问题），不同错误不同处理
4. **异常包装**：`wrap_exceptions` 上下文管理器自动将标准 Python 异常转换为业务异常

> **技术细节：** tenacity 是 Python 的重试库，通过装饰器配置重试策略。本项目使用 `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))` 实现 3 次重试，等待时间从 1 秒指数增长到最多 10 秒。异常层次结构定义在 `exceptions.py` 中：`MediaFactoryError`（基类）→ `ProcessingError` → `NetworkError`/`RateLimitError` 等。每个异常携带 `severity`（FATAL/RECOVERABLE/WARNING）和 `context`（上下文字典），API 层将其序列化为 JSON 返回给前端。`wrap_exceptions` 上下文管理器使用 `sys.exc_info()` 捕获当前异常，通过类型映射表（如 `ConnectionError → NetworkError`）自动转换。

### Q19: 并发任务怎么管理？

**A:** `TaskManager` 是任务管理的核心：

- 每个任务有独立的 `CancellationToken` 用于取消
- 任务状态机：IDLE → PENDING → RUNNING → COMPLETED/FAILED/CANCELLED
- 后台清理循环：自动清理完成超过 1 小时的任务
- WebSocket 订阅机制：客户端只收到自己订阅的任务的进度

当前是串行执行（一个任务完成后才执行下一个），批量任务通过队列排队。

> **技术细节：** `TaskManager` 在 `api/task_manager.py` 中实现，使用 Python `asyncio` 的事件循环。每个任务通过 `asyncio.create_task()` 创建为异步任务，任务函数内部用 `loop.run_in_executor(None, pipeline.execute, context)` 将同步的 Pipeline 执行丢到线程池。`CancellationToken` 是线程安全的（内部用 `threading.Event`），可以从 WebSocket 处理线程中调用 `cancel()`，Pipeline 线程中调用 `is_cancelled()` 检测。任务清理循环是一个 `asyncio.Task`，每 5 分钟检查一次，删除 `completed_at` 超过 1 小时的任务记录。

### Q20: Windows 平台兼容性遇到过什么问题？

**A:** 几个典型问题：

1. **stdout/stderr 崩溃**：PyInstaller 打包后 Windows 下 stdout/stderr 可能无效，huggingface_hub 进度条写入时崩溃。修复方法是确保 stdout/stderr 有效
2. **路径处理**：Windows 路径用反斜杠，跨平台路径拼接需要注意
3. **多进程支持**：PyInstaller 的 `multiprocessing.freeze_support()` 必须在入口点调用
4. **FFmpeg**：使用 `imageio-ffmpeg` 内置 FFmpeg，避免依赖系统安装

> **技术细节：** PyInstaller 将 Python 代码打包为单个可执行文件，但打包后的环境与正常 Python 环境有差异。最常见的问题是 `sys.stdout`/`sys.stderr` 被设为 `None`（因为 Windows GUI 子系统没有控制台），任何 `print()` 或 `tqdm` 输出都会抛出 `AttributeError`。修复方法是在入口点检查并重定向：`if sys.stdout is None: sys.stdout = open(os.devnull, 'w')`。`multiprocessing.freeze_support()` 是 PyInstaller 多进程的必要调用——它告诉 Python 当前运行在冻结（frozen）环境中，使用正确的模块导入机制。`imageio-ffmpeg` 将 FFmpeg 二进制文件打包在 Python 包内，通过 `imageio_ffmpeg.get_ffmpeg_exe()` 获取路径，避免了用户手动安装 FFmpeg 的麻烦。

---

## 七、过度设计的反思

### Q21: 你提到删了 500+ 行冗余代码，具体是什么情况？

**A:** 这是项目早期过度设计的教训。最初参考了一些企业级架构模式，引入了很多当时觉得"以后会用到"的抽象：

- **Engine ABC 基类**：定义了完整的生命周期接口，但没有任何子类继承它
- **EngineState 枚举**：定义了引擎状态机，但从未被使用
- **配置观察者模式**：实现了配置变更通知，但没有任何组件订阅
- **线程锁**：给单线程配置管理加了锁

后来做了一次系统性的代码审查，发现这些抽象完全没有实际使用场景，果断删除了。这让我学到一个原则：**不为假设的未来需求做设计，等真正需要时再加**。

> **技术细节：** 判断代码是否是"过度设计"可以用一个简单的标准：**删除它，如果没有任何测试失败、没有任何调用者报错，那它就是过度设计**。这次清理中，`Engine ABC` 被删除后零影响——因为没有任何类继承它，所有引擎都是独立的类，没有公共接口需求。`EngineState` 枚举定义了 `IDLE/LOADING/RUNNING/DONE/ERROR` 五个状态，但引擎的实际状态管理是通过函数参数和返回值传递的，不需要一个状态机。Python 的鸭子类型（Duck Typing）意味着：如果不需要多态分发，就不需要定义基类。

### Q22: 如果重新做这个项目，会改什么？

**A:**
1. **一开始就用 Electron + FastAPI**，而不是先 Flet 再迁移。虽然迁移过程 Service 层基本没改，但 API 层、前端全部重写，浪费了不少时间
2. **不做过度抽象**：不提前定义基类和接口，等有 2-3 个具体实现时再提取
3. **更早考虑资源管理**：内存泄漏问题如果一开始就设计清理协议，后期修复成本低很多
4. **测试先行**：目前测试覆盖不够，核心流程应该从一开始就有测试

> **技术细节：** "等有 2-3 个具体实现时再提取抽象"被称为**三次法则**（Rule of Three），是 Martin Fowler 在《Refactoring》中提出的：第一次做某事时直接做；第二次做类似的事时可以容忍重复；第三次再做时才应该提取公共抽象。"一开始就设计清理协议"对应的概念是**资源获取即初始化**（RAII，Resource Acquisition Is Initialization），在 Python 中通过 `__enter__`/`__exit__` 实现。如果在创建 Engine 类的同时就要求实现 `cleanup()` 方法，后续就不会出现忘记释放资源的问题——接口约束了行为。

---

## 八、扩展性

### Q23: 如果要支持一种新的 LLM 服务（比如 Gemini），需要改什么？

**A:** 几乎不需要改代码。项目设计了统一的 OpenAI 兼容后端，只要新服务提供 OpenAI 兼容的 API（`/v1/chat/completions`），只需在 `constants.py` 的 `BASE_URL_PRESETS` 加一条预设：

```python
"gemini": {
    "display_name": "Gemini",
    "base_url": "https://xxx/v1",
    "model_examples": ["gemini-pro"],
},
```

前端会自动显示新的服务卡片，用户填入 API Key 就能用了。这就是统一后端架构的好处。

> **技术细节：** 这得益于**策略模式的统一接口**设计。`OpenAICompatibleBackend` 在 `llm/openai_compatible_backend.py` 中，接收 `base_url`、`api_key`、`model` 三个参数构造，所有 LLM 服务只要兼容 `/v1/chat/completions` 接口格式，就能用同一个后端类。`BASE_URL_PRESETS` 字典在 `constants.py` 中定义，前端 `LLMConfig/index.tsx` 读取这个字典渲染服务卡片列表。添加新服务只需在字典中加一条，前端通过 React Query 的 `useLLMPresetsQuery()` 自动获取最新列表。`initialize_llm_backend()` 函数从 `config.toml` 的 `[openai_compatible]` section 读取当前预设配置，合并预设默认值和用户自定义值后创建后端实例。

### Q24: 如果要支持新的字幕格式（比如 WebVTT），需要改什么？

**A:** 主要改两层：
1. **Engine 层**：在 `SRTEngine` 中添加 WebVTT 的解析和生成逻辑（实际上已经有 VTT 支持了）
2. **API 层**：在 `schemas.py` 中添加格式选项

Pipeline 层和 Service 层不需要改动，因为字幕格式是 Engine 层的内部细节。

> **技术细节：** 这体现了**信息隐藏**（Information Hiding）原则。Pipeline 和 Service 只知道"给引擎一段文本和时间轴，引擎返回一个字幕文件路径"，至于文件是 SRT、ASS 还是 VTT 格式，是 Engine 层的内部实现。`SRTEngine` 在 `engine/srt.py` 中同时支持 SRT 和 VTT 两种格式的解析和生成——它们的时间戳格式略有不同（SRT 用逗号分隔毫秒 `00:00:00,000`，VTT 用点号 `00:00:00.000`），但结构几乎一样。添加新格式只需在该引擎中新增一个 `generate_vtt_to_path()` 方法，对上层完全透明。

---

## 九、构建与部署

### Q25: 打包流程是怎样的？

**A:** 两步打包：

1. **PyInstaller 打包 Python 后端**：`pyinstaller scripts/pyinstaller/installer_simple.spec`
   - 不含 ML 依赖（torch、transformers 等），减小体积
   - 用户首次启动时通过引导安装 ML 依赖

2. **electron-builder 打包 Electron 前端**：`cd src/electron && npm run build`
   - 将 PyInstaller 产物嵌入 Electron 包
   - 生成 macOS .dmg / Windows .exe 安装包

> **技术细节：** PyInstaller 的 `.spec` 文件是打包配置的核心，定义了 `Analysis`（分析依赖）、`PYZ`（压缩 Python 字节码）、`EXE`（生成可执行文件）三个步骤。`hiddenimports` 列表用于声明动态导入的模块（PyInstaller 的静态分析无法检测到这些）。`hooks/` 目录下的钩子文件（如 `hook-uvicorn.py`）告诉 PyInstaller 需要额外包含哪些数据文件和模块。electron-builder 的 `electron-builder.yml` 配置了 `extraResources` 字段，将 PyInstaller 产物复制到 Electron 应用的 `resources/` 目录下，Electron 主进程启动时通过 `pythonManager.ts` 找到并执行这个可执行文件。

### Q26: 版本管理怎么做的？

**A:** 单一真相源：版本号只定义在 `pyproject.toml` 的 `project.version` 中。代码通过 `_version.py` 读取，`download_model.py` 和构建脚本也从这里读取。changelog 用 git-cliff 从 git commit 自动生成。

> **技术细节：** `_version.py` 通过 `tomllib` 读取 `pyproject.toml`，解析 `[project]` section 的 `version` 字段，提供 `get_version()` 函数。构建脚本和 API 的版本接口都调用这个函数，确保全项目版本号一致。git-cliff 是一个 Conventional Commits 风格的 changelog 生成器，通过 `cliff.toml` 配置文件定义了 commit type 到 changelog section 的映射（如 `feat` → `### Features`，`fix` → `### Bug Fixes`）。发布流程：更新 `pyproject.toml` 版本号 → git commit → git-cliff 生成 CHANGELOG → git tag → git push。

---

## 十、技术细节快问快答

### Q27: Faster Whisper 不支持 MPS（Apple Silicon GPU），怎么处理的？

**A:** 确实不支持。CTranslate2（Faster Whisper 底层）没有 MPS 后端。Apple Silicon 用户只能用 CPU 推理。好消息是 Faster Whisper 的 CPU int8 量化性能已经不错，大 v3 模型在 M 系列芯片上也能实时转录。

> **技术细节：** MPS（Metal Performance Shaders）是 Apple 的 GPU 加速框架，PyTorch 通过 `device="mps"` 支持。但 CTranslate2（Faster Whisper 的推理引擎）是用 C++ 实现的，目前只支持 CUDA（NVIDIA GPU）和 CPU 后端。这意味着即使在 M3 Max 这样的高性能芯片上，Faster Whisper 也只能用 CPU 推理。不过由于 int8 量化和 ARM64 原生优化的加持，`large-v3` 模型在 M 系列芯片上的转录速度约为 0.1x-0.3x 实时速度（即处理 10 分钟音频需要 30-100 秒），对大多数场景来说够用。

### Q28: WebSocket 断线重连怎么做的？

**A:** 前端实现了自动重连机制：断线后最多重试 5 次，间隔 3 秒。重连后重新订阅之前的 task_id。由于进度是幂等的（当前进度覆盖之前的），重连后不会出现进度错乱。

> **技术细节：** 重连实现在 `src/electron/renderer/src/api/client.ts` 中。WebSocket 的 `onclose` 回调中检查 `retryCount < MAX_RETRIES`，如果满足则用 `setTimeout` 延迟 3 秒后创建新连接。重连成功后遍历之前订阅的 `task_id` 列表，逐个发送 `subscribe` 消息。进度数据的幂等性保证了即使重连期间服务端推送了多次进度，前端只会显示最新值（React state 的特性）。这是一种**最终一致性**（Eventual Consistency）设计——短暂的不一致（断线期间）是可以接受的，重连后会自动恢复到正确状态。

### Q29: 怎么处理 huggingface_hub 的进度条问题？

**A:** huggingface_hub 默认用 tqdm 进度条，在 GUI 环境下会输出到 stdout 导致崩溃。解决方案是禁用 huggingface_hub 的默认进度条，通过回调接口获取下载进度，再推送到前端显示。

> **技术细节：** `huggingface_hub.snapshot_download()` 的 `HF_HUB_DISABLE_PROGRESS_BARS=1` 环境变量可以全局禁用 tqdm 进度条。更精细的控制是通过 `tqdm` 的 `disable` 参数：`snapshot_download(..., tqdm_class=lambda *a, **k: _ SilentTqdm(*a, **k))`。但最干净的方式是使用回调参数，本项目通过自定义进度回调获取下载字节数和总字节数，然后通过 WebSocket 推送到前端的模型管理页面显示下载进度条。这个问题的根源是 **CLI 工具和 GUI 应用对 stdout 的处理方式不同**——CLI 期望有终端输出，GUI 环境下 stdout 可能不存在或被重定向。

### Q30: 项目用的是同步还是异步？

**A:** 混合模型：
- **API 层**：async（FastAPI 原生支持）
- **Service 层**：async 接口，内部用 `run_in_executor` 把 CPU 密集的 Pipeline/Engine 逻辑丢到线程池
- **Pipeline/Engine 层**：纯同步（ML 推理本身是同步的）

这样既不阻塞 FastAPI 的事件循环，又不需要把整个推理链路改成 async。

> **技术细节：** `asyncio.run_in_executor(None, func, *args)` 将同步函数 `func` 提交到默认线程池（`ThreadPoolExecutor`）执行，返回一个 `awaitable` 对象。`None` 参数表示使用默认执行器。这意味着 FastAPI 的事件循环线程不会被 Pipeline 的同步代码阻塞——它可以继续处理其他 HTTP 请求和 WebSocket 消息。为什么不把 Engine 改成 async？因为 Faster Whisper、FFmpeg subprocess、PyTorch 推理都是同步阻塞调用，没有 async API。强制包装成 async 只会增加复杂度（需要 `asyncio.to_thread`），而性能不会有任何提升——CPU 密集型任务在 async 中反而更慢（GIL + 上下文切换开销）。这个模式是 Python Web 开发中处理 CPU 密集型任务的标准做法。
