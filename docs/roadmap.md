# 路线图（需求池）

> **以后做什么的唯一登记处。** 条目从 Later/Next 流向 Now，开工后回链 spec/plan 路径，ship 后删除条目——流动历史看 git，本文件不留尸体。
>
> 字段：一句话 / 来源（日期+出典）/ 验收要点 / 依赖。验收要点写**种子级**即可，开工时 brainstorming 会带着它深化；宁可先入池，不要在登记时设计。

## Now

（在做的工作包——附 spec / plan 路径回链）

## Next

## Later

- 跨批翻译上下文：批边界约 5% 句子缺前后文；优先试零成本杠杆——把 batch_size 40 调小（竞品 10-12，顺带降低长输出格式漂移），而非加窗口机制（来源：2026-10-04 R1 讨论，边际效益评估后撤出）
- 转录段级幻觉过滤（消费 no_speech_prob/avg_logprob + 复读正则 + 幻听短语黑名单）：参数层主防线已在（condition_on_previous_text 默认 False + faster-whisper 库默认阈值）；待实际素材触发再做（来源：2026-10-04 R1 讨论）
- ASR/翻译结果缓存（重跑不重复消耗，配合任务历史；来源：同上，VideoCaptioner）
- 两步反思翻译开关（直译→反思→重写，token 翻倍；来源：同上，VideoLingo/VideoCaptioner）
- 老片增强小件包（P0）：deinterlace 检查（FFmpeg bwdif 前置）+ CodeFormer 人脸修复 + film grain 后处理 + spandrel 换社区模型（4x-UltraSharp 类）——老片观感九成缺口，估算 2-3 工程日（来源：2026-10-04 视频增强对比会话）
- 帧插值（P1，RIFE 可选 stage）：24→60fps，老片"高级感"最大杠杆，估算 3-5 工程日（来源：同上）；P0 收口实看后再定去留
- 时序模型（P2，BasicVSR++ 类）：消播放闪烁，估算 1 周+；触发条件 = P0/P1 落地后实看仍扎眼；落地时连自研 temporal_smoother 一并重评（来源：同上）
- 观察项：第三代生成式修复（SeedVR2 级）——量化生态把它压进 8GB 消费级卡再重评（来源：同上；定位冻结与明确不做已移入 product-spec 稳定层）
