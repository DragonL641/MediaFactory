# 路线图（需求池）

> **以后做什么的唯一登记处。** 条目从 Later/Next 流向 Now，开工后回链 spec/plan 路径，ship 后删除条目——流动历史看 git，本文件不留尸体。
>
> 字段：一句话 / 来源（日期+出典）/ 验收要点 / 依赖。验收要点写**种子级**即可，开工时 brainstorming 会带着它深化；宁可先入池，不要在登记时设计。

## Now

（在做的工作包——附 spec / plan 路径回链）

## Next

### Ollama pull 可靠性与进度收尾（R3 质量收尾）
- 来源：2026-10-05 冒烟测试（pull 全程无进度反馈；流挂起数分钟后自愈、空流假成功均实测复现，根因=框架层流式读竞态，不再深挖、以看门狗+校验兜底）
- 验收要点：
  - [ ] pull 进度在 Local Models 卡片内可见（当前 toast 引导去的任务队列按设计不显示 DOWNLOAD 任务）
  - [ ] 流看门狗：无事件超时判失败，消灭无限挂起
  - [ ] 完成后校验 is_model_installed，假完成改标 FAILED
  - [ ] `LLM Response` 日志按真实成败打印（openai_compatible_backend.py 尾部无条件 SUCCESS）
  - [ ] 顺带清算：同名并发 pull 409 竞态、取消逐事件轮询
- 依赖：无
- 估算：1 天

## Later

- 表单/队列卫生批：任务表单 use_llm 复选框移除或锁定（R2 遗留）；localModels 查询不随 task_complete 失效；runner 同步探测阻塞事件循环 ≤4s；单向门 startswith 判定可绕（非资损）；content-filter 降级批产物未过术语提取（R2 遗留）（来源：2026-10-04/05 R2/R3 评审 deferred minors + 冒烟；半天-一天）
- 跨批翻译上下文：批边界约 5% 句子缺前后文；优先试零成本杠杆——把 batch_size 40 调小（竞品 10-12，顺带降低长输出格式漂移），而非加窗口机制（来源：2026-10-04 R1 讨论，边际效益评估后撤出）
- 转录段级幻觉过滤（消费 no_speech_prob/avg_logprob + 复读正则 + 幻听短语黑名单）：参数层主防线已在（condition_on_previous_text 默认 False + faster-whisper 库默认阈值）；待实际素材触发再做（来源：2026-10-04 R1 讨论）
- ASR/翻译结果缓存（重跑不重复消耗，配合任务历史；来源：同上，VideoCaptioner）
- 两步反思翻译开关（直译→反思→重写，token 翻倍；来源：同上，VideoLingo/VideoCaptioner）
- README 对比表补 VideoLingo/KlicStudio（宽松协议位已被 Apache 系占据，加列价值存疑待裁决）；顺带修「Local Translation」行语义（原指 M2M100，现应指 Ollama 主渠道）（来源：2026-10-04 对比会话发现；CLAUDE.md 与 tmp/ 两项已于 2026-10-05 完成）
- 视频增强定位（收口）：自用 + 免费 + 老片子（低清糊画面）场景；冻结向第三代（生成式修复）的画质投入——观感差距主要来自工程缺口而非模型代际（来源：2026-10-04 视频增强对比会话：三代技术演进 + Topaz/SeedVR2 对标分析，硬件约束见该次讨论）
- 老片增强小件包（P0）：deinterlace 检查（FFmpeg bwdif 前置）+ CodeFormer 人脸修复 + film grain 后处理 + spandrel 换社区模型（4x-UltraSharp 类）——老片观感九成缺口，估算 2-3 工程日（来源：同上）
- 帧插值（P1，RIFE 可选 stage）：24→60fps，老片"高级感"最大杠杆，估算 3-5 工程日（来源：同上）
- 时序模型（P2，BasicVSR++ 类）：消播放闪烁，估算 1 周+；触发条件 = P0/P1 落地后实看仍扎眼（来源：同上）
- 观察项：第三代生成式修复（SeedVR2 级）——量化生态把它压进 8GB 消费级卡再重评；明确不做：Topaz CLI 集成（license 禁止再分发）、云端 GPU 渲染（商业模式变更）（来源：同上）
