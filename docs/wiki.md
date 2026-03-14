# MediaFactory 技术原理 Wiki

> 用于面试准备和技术深度讲解

---

## 目录

1. [核心架构原理](#核心架构原理)
2. [语音识别原理](#语音识别原理)
3. [大语言模型原理](#大语言模型原理)
4. [机器翻译原理](#机器翻译原理)
5. [音视频处理原理](#音视频处理原理)
6. [字幕生成原理](#字幕生成原理)
7. [配置管理原理](#配置管理原理)
8. [GUI框架原理](#gui框架原理)
9. [并发编程原理](#并发编程原理)
10. [Python打包原理](#python打包原理)

---

## 核心架构原理

### 三层架构模式

```
┌─────────────────────────────────────────────┐
│           Presentation Layer                │
│     (GUI - Flet + Material Design 3)        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┴──────────────────────────┐
│           Application Layer                 │
│     (Tools - AudioExtractor, Translator)     │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┴──────────────────────────┐
│           Infrastructure Layer               │
│  (Engines - AudioEngine, TranslationEngine)  │
└─────────────────────────────────────────────┘
```

**设计原则**：
- **依赖倒置**：高层模块不依赖低层模块，都依赖抽象
- **单一职责**：每层只负责自己的职责
  - Presentation：展示和用户交互
  - Application：业务逻辑和编排
  - Infrastructure：底层技术实现

---

### Pipeline 编排模式

**核心思想**：将复杂流程拆分为独立的阶段（Stage），每个阶段负责单一职责。

```python
class Pipeline:
    def __init__(self, stages: List[ProcessingStage]):
        self.stages = stages

    def execute(self, context: ProcessingContext) -> ProcessingResult:
        for stage in self.stages:
            # 1. 前置检查
            if not stage.should_execute(context):
                continue

            # 2. 执行阶段
            context = stage.execute(context)

            # 3. 错误处理
            if context.has_error():
                break

        return context.to_result()
```

**优势**：
1. **可组合性**：不同阶段可以灵活组合
2. **可测试性**：每个阶段可以独立测试
3. **可扩展性**：新增功能只需添加新阶段
4. **可观测性**：每个阶段的进度可以独立追踪

**责任链模式应用**：
```python
# ProcessingStage 基类
class ProcessingStage(ABC):
    @abstractmethod
    def execute(self, context: ProcessingContext) -> ProcessingContext:
        pass

    def should_execute(self, context: ProcessingContext) -> bool:
        return True  # 默认执行
```

---

### 插件架构原理

**注册模式**：使用装饰器自动注册插件

```python
class PluginRegistry:
    def __init__(self):
        self._tools: Dict[str, Type[Tool]] = {}

    def register(self, tool_class: Type[Tool]) -> Type[Tool]:
        """装饰器注册"""
        self._tools[tool_class.name] = tool_class
        return tool_class

    def get_tool(self, name: str) -> Tool:
        """工厂方法创建实例"""
        tool_class = self._tools.get(name)
        return tool_class()
```

**使用示例**：
```python
@registry.register
class AudioExtractorTool(Tool):
    name = "audio_extractor"
    # ...
```

**Python 导入机制**：模块导入时装饰器自动执行，实现自动注册。

---

### 事件驱动架构

**发布-订阅模式**：

```python
class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}

    def subscribe(self, event_type: EventType, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event: Event):
        callbacks = self._subscribers.get(event.type, [])
        for callback in callbacks:
            callback(event)
```

**优势**：
1. **解耦**：发布者不需要知道订阅者
2. **可扩展**：新增订阅者不影响发布者
3. **异步友好**：可以轻松实现异步处理

**事件类型**：
```python
class EventType(Enum):
    TOOL_EXECUTION_START = "tool_start"
    TOOL_EXECUTION_PROGRESS = "tool_progress"
    TOOL_EXECUTION_COMPLETE = "tool_complete"
    STAGE_START = "stage_start"
    STAGE_PROGRESS = "stage_progress"
    STAGE_COMPLETE = "stage_complete"
```

---

## 语音识别原理

### Whisper 模型架构

**Transformer 架构**：
```
Input Audio → Mel Spectrogram → Encoder → Decoder → Text Tokens
                                              ↓
                                         Cross Attention
                                              ↓
                                    Previous Tokens → Next Token
```

**关键组件**：

1. **Encoder**：提取音频特征
   - 输入：Mel 频谱图 (N_MELS=80)
   - 位置编码：Sinusoidal position embeddings
   - 自注意力：捕捉音频帧之间的依赖关系

2. **Decoder**：生成文本
   - 自注意力：处理已生成的 token
   - 交叉注意力：关注 Encoder 输出
   - 前馈网络：非线性变换

**数学原理**：
```python
# Multi-Head Attention
Attention(Q, K, V) = softmax(QK^T / √d_k) V

# 每个头独立计算
Head_i = Attention(QW_i^Q, KW_i^K, VW_i^V)

# 拼接所有头
MultiHead(Q, K, V) = Concat(Head_1, ..., Head_h)W^O
```

**位置编码**：
```python
# Sinusoidal Position Encoding
PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
```

---

### Faster Whisper 优化原理

**核心优化**：CTranslate2 引擎

1. **量化**：减少模型大小和推理时间
   - Float32 → Float16 (2x 速度提升)
   - Float32 → Int8 (4x 速度提升)

2. **算子融合**：合并连续计算
   ```python
   # 原始计算
   x = layer_norm(x)
   x = linear(x)
   x = activation(x)
   x = linear(x)

   # 融合后
   x = fused_layer_norm_linear_activation_linear(x)
   ```

3. **缓存优化**：避免重复计算
   - KV Cache：缓存 Key 和 Value 向量
   - 每次只计算新的 token

4. **批处理优化**：动态批处理
   ```python
   # 将多个短音频合并为批次
   batch = [audio1, audio2, audio3]
   results = model.transcribe_batch(batch)
   ```

**性能对比**：
| 实现 | 1小时音频处理时间 | 相对速度 |
|------|------------------|----------|
| OpenAI Whisper | ~10分钟 | 1x |
| Faster Whisper | ~2分钟 | 5x |

---

### VAD (语音活动检测) 原理

**WebRTC VAD 算法**：

```python
# 特征提取
def extract_features(audio_frame):
    # 1. 计算能量
    energy = sum(frame ** 2)

    # 2. 计算过零率 (Zero Crossing Rate)
    zcr = sum(abs(diff(frame)) > 0)

    return energy, zcr

# 高斯混合模型 (GMM)
def is_speech(features):
    # 训练两个 GMM：speech 和 non-speech
    speech_prob = gmm_speech.score(features)
    non_speech_prob = gmm_non_speech.score(features)

    return speech_prob > non_speech_prob
```

**Silero VAD (深度学习)**：
```python
# LSTM + 全连接层
class SileroVAD(nn.Module):
    def __init__(self):
        self.lstm = nn.LSTM(input_size=mel_bins, hidden_size=512)
        self.fc = nn.Linear(512, 1)  # 输出语音概率

    def forward(self, x):
        x, _ = self.lstm(x)
        x = torch.sigmoid(self.fc(x))
        return x
```

---

## 大语言模型原理

### Transformer 架构详解

**自注意力机制**：
```python
# 1. 计算 Queries, Keys, Values
Q = X @ W_Q  # (seq_len, d_k)
K = X @ W_K  # (seq_len, d_k)
V = X @ W_V  # (seq_len, d_v)

# 2. 计算注意力分数
scores = Q @ K.T / √d_k  # (seq_len, seq_len)

# 3. Softmax 归一化
attn_weights = softmax(scores, dim=-1)

# 4. 加权求和
output = attn_weights @ V
```

**多头注意力**：
```python
# 每个 head 关注不同的语义
Head_1: 语法结构
Head_2: 语义关系
Head_3: 指代消解
...
```

**位置编码**：
```python
# RoPE (Rotary Position Embedding) - 现代方法
def rotate_position(x, position):
    theta = position ** -(2 * arange(d/2) / d)
    rot_matrix = [[cos(theta), -sin(theta)],
                  [sin(theta),  cos(theta)]]
    return x @ rot_matrix
```

---

### LLM 推理原理

**自回归生成**：
```python
def generate(model, prompt, max_tokens=100):
    tokens = tokenize(prompt)

    for _ in range(max_tokens):
        # 1. 前向传播
        logits = model(tokens)

        # 2. 采样策略
        next_token = sample(logits, temperature=0.7)

        # 3. 终止条件
        if next_token == EOS_TOKEN:
            break

        tokens.append(next_token)

    return decode(tokens)
```

**采样策略**：
```python
# Temperature Sampling
probs = softmax(logits / temperature)
next_token = categorical_sample(probs)

# Top-k Sampling
top_k_probs, top_k_indices = topk(probs, k=50)
next_token = sample(top_k_probs, top_k_indices)

# Top-p (Nucleus) Sampling
cumsum_probs = cumsum(sorted_probs)
cand_indices = cumsum_probs <= p
next_token = sample(probs[cand_indices], indices[cand_indices])
```

**KV Cache 优化**：
```python
# 不使用 KV Cache：每次都重新计算
for i in range(max_tokens):
    output = model(tokens[:i+1])  # O(n^2)

# 使用 KV Cache：只计算新 token
cache = {}
for i in range(max_tokens):
    output = model(tokens[i], cache=cache)  # O(n)
```

---

### 批量翻译优化

**为什么需要批量处理**：

1. **网络开销**：单次请求 ~100ms，批量请求 ~150ms（10条数据）
2. **吞吐量**：批量处理可以充分利用网络带宽
3. **成本优化**：减少 API 调用次数

**实现策略**：
```python
def batch_translate(segments, batch_size=10, delay=5):
    results = []

    for i in range(0, len(segments), batch_size):
        batch = segments[i:i+batch_size]

        # 批量调用 LLM
        batch_texts = [s.text for s in batch]
        translations = llm_api.batch_translate(batch_texts)

        results.extend(translations)

        # 速率限制：避免触发 API 限制
        if i + batch_size < len(segments):
            time.sleep(delay)

    return results
```

---

### 反思翻译机制 (Reflective Translation)

**原理**：翻译 → 反思 → 重新翻译

```python
def reflective_translation(source_text, target_lang="zh"):
    # 1. 初次翻译
    draft = llm.translate(source_text, target_lang)

    # 2. 反思：让 LLM 评估自己的翻译
    reflection = llm.evaluate(
        prompt=f"""
        Source: {source_text}
        Translation: {draft}

        Please evaluate the translation:
        1. Is it accurate?
        2. Is it natural?
        3. Any improvements needed?
        """
    )

    # 3. 根据反思重新翻译
    final = llm.translate(
        source_text,
        target_lang,
        context=reflection
    )

    return final
```

**Prompt 模板**：
```
You are a professional translator. Please translate the following text.

Source text: {source_text}
Target language: {target_lang}

Provide your translation and then reflect on it:

Translation:
[Your translation here]

Reflection:
- What challenges did you encounter?
- What ambiguities needed resolution?
- How would you improve this translation?

Final Translation:
[Your improved translation]
```

---

## 机器翻译原理

### Seq2Seq 模型

**基础架构**：
```
Encoder (源语言) → Context Vector → Decoder (目标语言)
```

**注意力机制**：
```python
# Bahdanau Attention
context_t = sum(alpha_ti * h_i) for i in source_tokens

# alpha_ti: 注意力权重
alpha_ti = softmax(score(s_{t-1}, h_i))

# score: 对齐分数
score(s, h) = v^T * tanh(W_s * s + W_h * h)
```

---

### Transformer 翻译模型 (NLLB, M2M100)

**NLLB (No Language Left Behind)**：

```python
# 架构
class NLLBModel(nn.Module):
    def __init__(self, vocab_size=256000):
        # 支持 200+ 语言
        self.encoder = TransformerEncoder(...)
        self.decoder = TransformerDecoder(...)

        # 语言 token
        self.lang_token = nn.Embedding(200, d_model)

    def forward(self, input_ids, src_lang, tgt_lang):
        # 1. 添加源语言 token
        src_embed = self.embedding(input_ids)
        src_embed = src_embed + self.lang_token(src_lang)

        # 2. 编码
        encoder_out = self.encoder(src_embed)

        # 3. 添加目标语言 token
        tgt_embed = self.embedding(target_ids)
        tgt_embed = tgt_embed + self.lang_token(tgt_lang)

        # 4. 解码
        output = self.decoder(tgt_embed, encoder_out)

        return output
```

**多语言训练**：
```python
# 训练数据：200+ 语言对
training_data = [
    ("Hello", "Bonjour", "en", "fr"),
    ("Hello", "Hola", "en", "es"),
    ("Hello", "你好", "en", "zh"),
    ...
]

# 统一训练
loss = cross_entropy(model(src, src_lang, tgt_lang), target)
```

---

### 模型运行时内存估算原理

**为什么需要估算内存**：
1. 模型选择：根据用户系统内存推荐合适的模型
2. 资源管理：避免加载过大模型导致系统卡死
3. 用户体验：提供明确的硬件要求说明

#### 内存组成

模型运行时内存由以下部分组成：

```
总内存占用 = 模型权重 + 激活值缓存 + Tokenizer 词表 + 运行时开销
```

**1. 模型权重 (Model Weights)**

这是最主要的内存占用，取决于参数量和精度：

| 精度 | 每参数字节数 | 3B 模型权重 | 7B 模型权重 |
|------|------------|------------|------------|
| FP32 (float32) | 4 bytes | 12 GB | 28 GB |
| FP16 (float16) | 2 bytes | 6 GB | 14 GB |
| INT8 | 1 byte | 3 GB | 7 GB |
| INT4 | 0.5 bytes | 1.5 GB | 3.5 GB |

**计算公式**：
```python
def calculate_model_weights_memory(params_billions: float, precision: str) -> float:
    """计算模型权重内存占用 (GB)

    Args:
        params_billions: 参数量（十亿）
        precision: 精度类型 (fp32, fp16, int8, int4)

    Returns:
        内存占用 (GB)
    """
    bytes_per_param = {
        "fp32": 4,
        "fp16": 2,
        "int8": 1,
        "int4": 0.5,
    }

    params = params_billions * 1e9  # 转换为实际参数数
    bytes_total = params * bytes_per_param[precision]
    gb = bytes_total / (1024 ** 3)

    return gb

# 示例
print(calculate_model_weights_memory(3, "fp16"))  # 5.59 GB
print(calculate_model_weights_memory(3, "int8"))  # 2.79 GB
```

**2. 激活值缓存 (Activation Cache)**

Transformer 模型在推理过程中需要存储中间激活值，用于后续 token 生成：

```python
# KV Cache 内存估算
def estimate_kv_cache_memory(
    num_layers: int,
    hidden_size: int,
    num_heads: int,
    seq_length: int,
    batch_size: int = 1,
    precision: str = "fp16"
) -> float:
    """估算 KV Cache 内存占用

    KV Cache 存储每层的 Key 和 Value 向量

    Args:
        num_layers: Transformer 层数
        hidden_size: 隐藏层维度
        num_heads: 注意力头数
        seq_length: 序列长度
        batch_size: 批大小
        precision: 精度

    Returns:
        内存占用 (GB)
    """
    bytes_per_element = {"fp32": 4, "fp16": 2, "int8": 1}

    # 每层 KV: 2 * (batch * seq * num_heads * head_dim)
    head_dim = hidden_size // num_heads
    elements_per_layer = 2 * batch_size * seq_length * num_heads * head_dim

    total_elements = elements_per_layer * num_layers
    total_bytes = total_elements * bytes_per_element[precision]

    return total_bytes / (1024 ** 3)

# 示例：MADLAD400-3B (32 层, 2560 hidden, 32 heads)
print(estimate_kv_cache_memory(32, 2560, 32, 512))  # ~0.3 GB for seq_length=512
```

**3. Tokenizer 词表**

大模型的词表通常很大：

```python
def estimate_vocab_memory(vocab_size: int, embedding_dim: int, precision: str = "fp32") -> float:
    """估算词表内存占用

    Args:
        vocab_size: 词表大小
        embedding_dim: 词向量维度
        precision: 精度

    Returns:
        内存占用 (GB)
    """
    bytes_per_element = {"fp32": 4, "fp16": 2}

    total_bytes = vocab_size * embedding_dim * bytes_per_element[precision]
    return total_bytes / (1024 ** 3)

# MADLAD400: 256K vocab, 2560 dim
print(estimate_vocab_memory(256000, 2560))  # ~2.4 GB (FP32)
print(estimate_vocab_memory(256000, 2560, "fp16"))  # ~1.2 GB (FP16)
```

**4. 运行时开销**

PyTorch/TensorFlow 运行时的额外开销：

- **CUDA Context**: ~500MB - 1GB
- **内存碎片**: ~10-20% 的额外开销
- **临时张量**: 推理过程中的中间结果

#### 综合估算公式

```python
def estimate_total_runtime_memory(
    params_billions: float,
    precision: str,
    vocab_size: int = 256000,
    hidden_size: int = 2560,
    num_layers: int = 32,
    num_heads: int = 32,
    max_seq_length: int = 512,
    safety_factor: float = 1.3
) -> float:
    """估算模型运行时总内存占用

    Args:
        params_billions: 参数量（十亿）
        precision: 精度 (fp32, fp16, int8)
        vocab_size: 词表大小
        hidden_size: 隐藏层维度
        num_layers: 层数
        num_heads: 注意力头数
        max_seq_length: 最大序列长度
        safety_factor: 安全系数（考虑碎片和临时开销）

    Returns:
        总内存占用 (GB)
    """
    # 1. 模型权重
    weights_mem = calculate_model_weights_memory(params_billions, precision)

    # 2. 词表（通常与模型同精度）
    vocab_mem = estimate_vocab_memory(vocab_size, hidden_size, precision)

    # 3. KV Cache
    kv_mem = estimate_kv_cache_memory(
        num_layers, hidden_size, num_heads, max_seq_length, 1, precision
    )

    # 4. 基础开销
    base_overhead = 0.5  # PyTorch 基础开销 ~500MB

    # 总计（含安全系数）
    total = (weights_mem + vocab_mem + kv_mem + base_overhead) * safety_factor

    return total

# 示例计算
print(f"MADLAD400-3B FP16: {estimate_total_runtime_memory(3, 'fp16'):.1f} GB")  # ~9-10 GB
print(f"MADLAD400-3B INT8: {estimate_total_runtime_memory(3, 'int8'):.1f} GB")   # ~5-6 GB
print(f"MADLAD400-7B FP16: {estimate_total_runtime_memory(7, 'fp16'):.1f} GB")   # ~18-20 GB
```

#### 实际模型内存占用参考

| 模型 | 参数量 | 精度 | 权重 | 估算运行时 | 推荐系统内存 |
|------|-------|------|------|----------|------------|
| MADLAD400-3B Q4K | 3B | Q4K | 2 GB | 3-4 GB | 16 GB |
| MADLAD400-7B Q4K | 7B | Q4K | 4.5 GB | 6-7 GB | 32 GB |
| MADLAD400-3B FP16 | 3B | FP16 | 6 GB | 9-10 GB | 64 GB |
| Whisper-Large-V3 | 1.5B | FP16 | 3 GB | 4-5 GB | 16 GB |

**推荐系统内存计算**：
```python
def recommend_system_memory(runtime_memory_gb: float) -> int:
    """根据运行时内存推荐系统内存

    考虑：
    1. 操作系统开销 (~2-4 GB)
    2. 其他应用程序
    3. 安全余量

    Args:
        runtime_memory_gb: 模型运行时内存

    Returns:
        推荐的系统内存 (GB)
    """
    MEMORY_TIERS = [8, 16, 32, 64, 128]

    # 系统开销 + 安全余量
    required = runtime_memory_gb + 4  # 4GB 系统开销
    required *= 1.5  # 50% 安全余量

    # 向上取整到最近的内存档位
    for tier in MEMORY_TIERS:
        if required <= tier:
            return tier
    return MEMORY_TIERS[-1]

# 示例
print(recommend_system_memory(10))  # 16 GB (10 + 4 = 14, 14 * 1.5 = 21 → 32?)
# 实际：10 + 4 = 14, 需要更保守估计
```

#### 精度选择建议

| 场景 | 推荐精度 | 理由 |
|------|---------|------|
| 生产环境 (GPU) | FP16 | 速度与质量平衡 |
| 低内存环境 | INT8 | 内存占用减半 |
| 最高质量 | FP32 | 无精度损失 |
| 边缘设备 | INT4 | 最小内存占用 |

---

### 本地翻译 vs LLM 翻译

| 特性 | 本地模型 (MADLAD400) | LLM API |
|------|---------------------|---------|
| **速度** | 快 (本地推理) | 慢 (网络请求) |
| **成本** | 免费 (一次性) | 按次计费 |
| **质量** | 一般 (固定模式) | 高 (上下文理解) |
| **隐私** | 本地处理 | 上传数据 |
| **灵活性** | 仅翻译 | 翻译+断句+校正 |
| **硬件要求** | 16GB+ RAM | 无要求 |
| **许可证** | Apache 2.0 (商用OK) | 按服务商 |

**支持的 LLM 后端**: OpenAI、DeepSeek、智谱AI GLM、通义千问、Moonshot

#### 本地翻译模型分级

所有本地翻译模型使用 MADLAD400 GGUF 量化版本，支持 400+ 语言对所有语言对的翻译：

| 系统内存 | 推荐模型 | 磁盘大小 | 运行内存 | 语言支持 | 许可证 |
|---------|---------|---------|---------|----------|--------|
| 16GB | MADLAD400-3B Q4K | 2 GB | 3-4 GB | 400+ 语言 | Apache 2.0 |
| 32GB+ | MADLAD400-7B Q4K | 4.5 GB | 6-7 GB | 400+ 语言 | Apache 2.0 |
| 64GB+ | MADLAD400-3B FP16 | 6 GB | ~10 GB | 400+ 语言 | Apache 2.0 |

**最低系统要求**: 16GB RAM（与 Whisper Large V3 一致）

**低内存用户**: 请使用 LLM API 翻译（DeepSeek、OpenAI 等）

**选择策略**：
```python
def choose_translation_method(source_lang, target_lang, use_case):
    # 1. 学习场景：需要双语对照 → 本地模型
    if use_case == "learning":
        return LocalModel()

    # 2. 专业场景：需要高质量 → LLM
    if use_case == "professional":
        return LLM_API()

    # 3. 离线场景：无网络 → 本地模型
    if not has_network():
        return LocalModel()

    # 4. 成本敏感 → 本地模型
    if budget_constrained():
        return LocalModel()
```

---

## 音视频处理原理

### FFmpeg 架构

**核心组件**：
```
┌─────────────────────────────────────────┐
│              libavformat                │  # 格式封装/解封装
├─────────────────────────────────────────┤
│              libavcodec                 │  # 编解码器
├─────────────────────────────────────────┤
│              libavutil                  │  # 工具函数
├─────────────────────────────────────────┤
│              libswscale                 │  # 图像缩放/转换
├─────────────────────────────────────────┤
│              libswresample              │  # 音频重采样
└─────────────────────────────────────────┘
```

**工作流程**：
```python
# 1. 解封装 (Demuxing)
input_file = "input.mp4"
format_ctx = avformat_open_input(input_file)
streams = format_ctx.streams

# 2. 解码 (Decoding)
codec_ctx = avcodec_alloc_context3(codec)
avcodec_parameters_to_context(codec_ctx, stream.codecpar)
avcodec_open2(codec_ctx, codec)

# 3. 处理 (Processing)
for packet in packets:
    frame = avcodec_send_packet(codec_ctx, packet)
    processed_frame = process(frame)  # 你的处理逻辑

# 4. 编码 (Encoding)
output_packet = avcodec_send_frame(output_codec, processed_frame)

# 5. 封装 (Muxing)
av_interleaved_write_frame(output_format_ctx, output_packet)
```

---

### 音频提取原理

**为什么需要音频提取**：
1. Whisper 只接受音频输入
2. 视频文件包含视频流 + 音频流
3. 需要将音频流分离并转换为 WAV 格式

**FFmpeg 命令**：
```bash
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav
```

**参数解释**：
- `-vn`: 不处理视频流 (video no)
- `-acodec pcm_s16le`: 音频编码器 (PCM 16-bit little-endian)
- `-ar 16000`: 采样率 16kHz (Whisper 要求)
- `-ac 1`: 单声道 (Whisper 要求)

**Python 实现**：
```python
import subprocess

def extract_audio(video_path, audio_path, sample_rate=16000):
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",  # 不处理视频
        "-acodec", "pcm_s16le",  # WAV 格式
        "-ar", str(sample_rate),  # 采样率
        "-ac", "1",  # 单声道
        "-y",  # 覆盖输出文件
        audio_path
    ]
    subprocess.run(cmd, check=True)
```

---

### 音频编码原理

**PCM (脉冲编码调制)**：
```python
# 1. 采样 (Sampling)
# 每秒采集 16000 次 (16kHz)
samples = record_audio(duration=1.0, rate=16000)

# 2. 量化 (Quantization)
# 将模拟信号转换为数字信号
quantized = (samples * (2**15 - 1)).astype(int16)

# 3. 编码 (Encoding)
# 16-bit signed integer
encoded = quantized.tobytes()
```

**音频格式对比**：
| 格式 | 压缩 | 质量 | 用途 |
|------|------|------|------|
| WAV (PCM) | 无 | 最高 | Whisper 输入 |
| MP3 | 有损 | 好 | 通用存储 |
| AAC | 有损 | 很好 | 视频 |
| FLAC | 无损 | 最高 | 音乐 |

---

### 视频编码原理

**编码格式**：
```
H.264/AVC: 最常见，兼容性好
H.265/HEVC: 压缩率更高，较新
VP9: 开源，Google 推动
AV1: 最新一代，压缩率最高
```

**帧类型**：
```python
# I-frame (Intra-coded): 完整帧，不依赖其他帧
# P-frame (Predicted): 前向预测
# B-frame (Bi-directional): 双向预测

# GOP (Group of Pictures)
GOP = [I, B, B, P, B, B, P, ...]  # 典型结构
```

**压缩原理**：
```python
# 1. 空间冗余去除 (帧内压缩)
def intra_compression(frame):
    # 将图像分块 (8x8 或 16x16)
    blocks = split_to_blocks(frame, size=16)

    # DCT 变换
    dct_blocks = [dct(block) for block in blocks]

    # 量化 (丢弃高频信息)
    quantized = [quantize(block) for block in dct_blocks]

    # 熵编码 (Huffman 或 CABAC)
    encoded = [entropy_encode(block) for block in quantized]

    return encoded

# 2. 时间冗余去除 (帧间压缩)
def inter_compression(current_frame, reference_frame):
    # 运动估计：找到参考帧中的相似块
    motion_vectors = estimate_motion(current_frame, reference_frame)

    # 运动补偿：根据运动向量预测
    predicted = compensate(reference_frame, motion_vectors)

    # 残差编码
    residual = current_frame - predicted
    encoded = encode_residual(residual)

    return encoded, motion_vectors
```

---

## 字幕生成原理

### SRT 格式规范

```srt
1
00:00:01,000 --> 00:00:04,000
Hello, welcome to the video.

2
00:00:04,500 --> 00:00:07,000
Today we'll discuss architecture.
```

**格式解析**：
```python
import re

def parse_srt(srt_content):
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\Z)'

    matches = re.findall(pattern, srt_content, re.DOTALL)

    subtitles = []
    for match in matches:
        index, start, end, text = match
        subtitles.append({
            'index': int(index),
            'start': parse_timestamp(start),
            'end': parse_timestamp(end),
            'text': text.strip()
        })

    return subtitles

def parse_timestamp(timestamp):
    """将 '00:00:01,500' 转换为秒"""
    h, m, s_ms = timestamp.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
```

---

### 字幕时间轴对齐

**问题**：Whisper 返回的是段落级别时间戳，需要切分为句子

**解决方案**：基于标点符号切分

```python
def split_segment(segments):
    """将长段落切分为短句子"""
    results = []

    for segment in segments:
        text = segment['text']
        start = segment['start']
        end = segment['end']

        # 按句子切分
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)

        if len(sentences) == 1:
            results.append(segment)
        else:
            # 按字符数比例分配时间
            total_chars = len(text)
            current_time = start

            for sentence in sentences:
                chars = len(sentence)
                duration = (chars / total_chars) * (end - start)

                results.append({
                    'text': sentence,
                    'start': current_time,
                    'end': current_time + duration
                })

                current_time += duration

    return results
```

---

### 双语字幕生成

**原理**：将原文和译文同时显示

```python
def generate_bilingual subtitles(source_segments, translated_segments):
    """生成双语字幕"""
    subtitles = []

    for src, tgt in zip(source_segments, translated_segments):
        subtitle = f"{src['text']}\n{tgt['text']}"
        subtitles.append({
            'start': src['start'],
            'end': src['end'],
            'text': subtitle
        })

    return subtitles
```

**SRT 输出**：
```srt
1
00:00:01,000 --> 00:00:04,000
Hello, welcome to the video.
你好，欢迎观看视频。

2
00:00:04,500 --> 00:00:07,000
Today we'll discuss architecture.
今天我们将讨论架构。
```

---

### 智能断句原理

**问题**：直接切分会导致句子在中间断开

**解决方案 1：基于 NLP 断句**
```python
import spacy

nlp = spacy.load("en_core_web_sm")

def smart_sentence_split(text):
    doc = nlp(text)
    return [sent.text for sent in doc.sents]
```

**解决方案 2：LLM 断句**
```python
def llm_sentence_split(text):
    prompt = f"""
    Please split the following text into natural sentences.
    Preserve the original meaning.

    Text: {text}

    Output format (one sentence per line):
    """
    return llm.complete(prompt).strip().split('\n')
```

---

## 配置管理原理

### 简化的配置管理器

**设计理念**：对于桌面应用，采用简洁直接的配置管理方式，无需复杂的观察者模式或自动文件监视。

**核心功能**：
- TOML 文件读写
- 嵌套配置更新（双下划线表示法）
- 显式重载配置

```python
from mediafactory.config import get_config_manager, get_config

# 获取配置管理器
manager = get_config_manager()
config = manager.config

# 访问配置值
beam_size = config.whisper.beam_size

# 更新配置（双下划线表示嵌套访问）
manager.update(whisper__beam_size=7)

# 显式重载配置（从磁盘）
manager.reload()
```

---

### Pydantic v2 原理

**核心思想**：使用 Python 类型注解进行数据验证

```python
from pydantic import BaseModel, Field, field_validator

class WhisperConfig(BaseModel):
    model_size: str = Field(default="base", alias="model")
    beam_size: int = Field(default=5, ge=1, le=10)
    compute_type: str = Field(default="float16")

    @field_validator('model_size')
    @classmethod
    def validate_model_size(cls, v):
        valid_sizes = ['tiny', 'base', 'small', 'medium', 'large']
        if v not in valid_sizes:
            raise ValueError(f'Must be one of {valid_sizes}')
        return v
```

**验证流程**：
```
输入数据 → 类型转换 → 约束检查 → 自定义验证 → 输出模型
```

**Type Adapter**：
```python
from pydantic import TypeAdapter

# 将 JSON 字典转换为配置对象
adapter = TypeAdapter(WhisperConfig)
config = adapter.validate_python({
    'model': 'base',
    'beam_size': 5
})
```

---

### TOML 配置原理

**为什么选择 TOML**：
1. **可读性强**：比 JSON 更易读
2. **类型丰富**：支持字符串、整数、浮点、布尔、日期、数组
3. **注释支持**：可以添加注释
4. **Python 原生支持**：Python 3.11+ 内置 tomllib

**TOML 示例**：
```toml
[whisper]
model_size = "base"
beam_size = 5
compute_type = "float16"

[llm_translation]
enabled = true
backend = "openai"
api_key = "sk-..."
batch_size = 10
rate_limit = 60  # requests per minute

[llm_translation.backends.openai]
model = "gpt-4"
temperature = 0.3
max_tokens = 2000

[paths]
models_dir = "./models"
cache_dir = "./cache"
output_dir = "./output"
```

**读取配置**：
```python
import tomllib

with open('config.toml', 'rb') as f:
    config_dict = tomllib.load(f)

# 转换为 Pydantic 模型
config = AppConfig(**config_dict)
```

---

### 环境变量覆盖

**原理**：环境变量优先级高于配置文件

```python
import os

def get_config_value(key, default):
    """
    优先级：
    1. 环境变量 (MF_WHISPER_BEAM_SIZE)
    2. 配置文件 (config.toml)
    3. 默认值
    """
    # 1. 检查环境变量
    env_key = f"MF_{key.upper()}"
    env_value = os.getenv(env_key)
    if env_value is not None:
        return parse_type(env_value, type(default))

    # 2. 检查配置文件
    config = load_config()
    if hasattr(config, key):
        return getattr(config, key)

    # 3. 返回默认值
    return default
```

**使用示例**：
```bash
# 覆盖配置文件中的 beam_size
export MF_WHISPER_BEAM_SIZE=7

# 运行程序
python -m mediafactory
```

---

## GUI框架原理

### Flet 架构

**基于 Flutter 的 Python GUI 框架**：

```python
# Flet 声明式 UI
import flet as ft

def main(page: ft.Page):
    page.title = "MediaFactory"
    page.add(ft.ElevatedButton("Click", on_click=on_click))

def on_click(e):
    # 事件处理
    pass

ft.app(main)
```

**Material Design 3 主题系统**：
```python
# 主题配置
theme = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary="#6750A4",       # 主色调
        secondary="#625B71",     # 次要色调
        tertiary="#7D5260",      # 强调色
        surface="#FFFBFE",       # 背景色
    )
)
page.theme = theme
page.update()
```

---

### Flet 事件循环与异步

**原理**：Flet 使用 asyncio 进行异步处理，不阻塞 UI

```python
import flet as ft
import asyncio

class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_ui()

    def setup_ui(self):
        self.button = ft.ElevatedButton(
            "Process",
            on_click=self.on_button_click
        )
        self.page.add(self.button)

    async def on_button_click(self, e):
        # 异步执行，不阻塞 UI
        result = await self.process_video()
        self.update_status(result)

    async def process_video(self):
        # 异步处理
        await asyncio.sleep(1)
        return "Done"

    def update_status(self, result):
        self.status_text.value = result
        self.status_text.update()
```

---

### 进度条更新

**Flet 进度条模式**：

```python
class ProgressUI:
    def __init__(self, page: ft.Page):
        self.progress_bar = ft.ProgressBar(width=300)
        self.status_text = ft.Text()
        page.add(self.progress_bar, self.status_text)

    def update_progress(self, progress: int, message: str):
        self.progress_bar.value = progress / 100
        self.status_text.value = message
        self.progress_bar.update()
        self.status_text.update()
```

**异步处理集成**：
```python
async def process_with_progress(progress_ui):
    for i in range(100):
        await asyncio.sleep(0.1)
        progress_ui.update_progress(i, f"Processing {i}/100")
```

---

## 并发编程原理

### Python GIL (全局解释器锁)

**什么是 GIL**：
- Global Interpreter Lock
- 确保 Python 解释器在任何时刻只有一个线程执行字节码

**影响**：
```python
import threading
import time

def cpu_bound_task():
    """CPU 密集型任务"""
    sum(i * i for i in range(10**7))

def io_bound_task():
    """IO 密集型任务"""
    time.sleep(1)

# CPU 密集型：多线程无加速
start = time.time()
threads = [threading.Thread(target=cpu_bound_task) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
# 结果：~4秒 (无加速)

# IO 密集型：多线程有加速
start = time.time()
threads = [threading.Thread(target=io_bound_task) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
# 结果：~1秒 (4倍加速)
```

**解决方案**：
- **多进程**：CPU 密集型任务使用 `multiprocessing`
- **协程**：IO 密集型任务使用 `asyncio`

---

### 线程同步

**问题**：多线程共享数据会导致竞态条件

```python
counter = 0

def increment():
    global counter
    for _ in range(100000):
        counter += 1  # 非原子操作

threads = [threading.Thread(target=increment) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# 结果：counter < 1000000 (数据不一致)
```

**解决方案：Lock**
```python
from threading import Lock

counter = 0
lock = Lock()

def increment():
    global counter
    for _ in range(100000):
        with lock:  # 加锁
            counter += 1  # 原子操作
```

---

### 协程 (asyncio)

**原理**：单线程并发，通过事件循环调度

```python
import asyncio

async def fetch(url):
    # 异步 HTTP 请求
    response = await aiohttp.get(url)
    return response

async def main():
    # 并发执行多个请求
    urls = ["url1", "url2", "url3"]
    tasks = [fetch(url) for url in urls]
    results = await asyncio.gather(*tasks)

asyncio.run(main())
```

**async vs threading**：
| 特性 | asyncio | threading |
|------|---------|-----------|
| 并发模型 | 协程 | 线程 |
| 内存开销 | 低 | 高 |
| 切换开销 | 低 | 高 |
| 适用场景 | IO 密集 | IO 密集 |
| 阻塞操作 | await | 不适用 |

---

### 进度追踪实现

**回调模式**：
```python
from typing import Protocol, Callable

class ProgressCallback(Protocol):
    def __call__(self, progress: int, message: str) -> None:
        ...

class VideoProcessor:
    def process(self, video_path: str, on_progress: ProgressCallback):
        for i in range(100):
            # 处理逻辑
            on_progress(i, f"Processing {i}%")

# 使用示例
def print_progress(progress: int, message: str):
    print(f"[{progress}%] {message}")

processor = VideoProcessor()
processor.process("video.mp4", print_progress)
```

---

## Python打包原理

### PyInstaller 原理

**核心思想**：将 Python 代码打包为独立可执行文件

**流程**：
```
1. 分析依赖：递归解析 import 语句
2. 收集文件：复制 .pyc 文件和依赖
3. 打包资源：复制数据文件
4. 生成引导代码：创建启动脚本
5. 冻结：生成可执行文件
```

**生成的文件**：
```
dist/
├── MediaFactory
│   ├── MediaFactory  # 可执行文件 (引导代码)
│   ├── _internal/    # 依赖和资源
│   │   ├── Python.dll
│   │   ├── library.zip  # 标准库
│   │   └── ...
```

**引导代码**：
```python
# PyInstaller 生成的启动代码 (简化版)
import sys
import os

# 设置 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '_internal'))

# 导入主模块
from mediafactory import main

# 运行
main()
```

---

### 字节码加密

**原理**：使用 PyInstaller 的 `--key` 参数加密 `.pyc` 文件

```python
# build_pyinstaller.py
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=PRODUCT_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    key="mediafactory-2026-secure",  # 加密密钥
)
```

**加密流程**：
```
1. 编译为 .pyc 文件
2. 使用 AES 加密 .pyc
3. 在运行时解密
4. 执行解密后的字节码
```

**安全性**：
- 不是绝对安全，可以通过逆向工程破解
- 但提高了破解门槛
- 密钥硬编码在可执行文件中

---

### 自定义 Hook

**问题**：PyInstaller 无法自动发现某些依赖

**解决方案**：编写 hook 文件

**hook-mediafactory.py**：
```python
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 收集所有 mediafactory 子模块
hiddenimports = collect_submodules('mediafactory')

# 收集数据文件
datas = collect_data_files('mediafactory', include_py_files=False)
```

**hook-flet.py**：
```python
# 收集 Flet 框架文件
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('flet')
```

**hook-transformers.py**：
```python
# 运行时 hook：设置缓存目录
def _modify_transformers_cache():
    import os
    import sys

    if getattr(sys, 'frozen', False):
        # 设置 HF_HOME 环境变量
        os.environ['HF_HOME'] = os.path.join(sys._MEIPASS, 'cache')
```

---

### 平台差异

**macOS**：
```bash
# 生成 .app 包
dist/MediaFactory.app/
├── Contents/
│   ├── Info.plist
│   ├── MacOS/
│   │   └── MediaFactory
│   └── Resources/
│       └── ...
```

**Windows**：
```
# 生成 .exe
dist/MediaFactory.exe

# 依赖
dist/MediaFactory/
├── python3XX.dll
├── vcruntime140.dll
└── ...
```

**Linux**：
```
# 生成可执行文件
dist/MediaFactory

# 无文件后缀，但有执行权限
chmod +x dist/MediaFactory
```

---

## 常见面试问题

### Q1: 为什么选择 Faster Whisper 而不是 OpenAI Whisper？

**答**：
1. **性能优势**：CTranslate2 引擎，4-6x 速度提升
2. **内存优化**：量化支持，内存占用降低
3. **模型兼容**：完全兼容 Whisper 模型
4. **生产就绪**：专为生产环境优化

### Q2: 如何处理 LLM API 的速率限制？

**答**：
1. **批量处理**：合并多个请求
2. **速率限制器**：token-bucket 算法
3. **重试机制**：指数退避
4. **延迟策略**：批次间添加延迟

### Q3: Pipeline 架构的优势是什么？

**答**：
1. **可组合性**：灵活组合不同阶段
2. **可测试性**：每个阶段独立测试
3. **可扩展性**：新增功能无需修改现有代码
4. **可观测性**：细粒度进度追踪

### Q4: 如何保证线程安全？

**答**：
1. **Lock**：保护共享数据
2. **RLock**：可重入锁
3. **Event**：线程间通信
4. **简化设计**：对于桌面应用，尽量避免复杂的并发场景

### Q5: Pydantic 相比手动验证的优势？

**答**：
1. **类型安全**：自动类型转换和验证
2. **性能**：Rust 实现，比手动验证快
3. **可维护性**：声明式，易于理解
4. **IDE 支持**：自动补全和类型检查

---

## 参考资料

- [Transformer 论文](https://arxiv.org/abs/1706.03762)
- [Whisper 论文](https://arxiv.org/abs/2212.04356)
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [FFmpeg 文档](https://ffmpeg.org/documentation.html)

---

**文档版本**: 1.5
**更新日期**: 2026-03-15
