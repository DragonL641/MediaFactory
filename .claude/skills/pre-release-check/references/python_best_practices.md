# Python 最佳实践参考

本文档提供 Python 代码编写的最佳实践，用于 MediaFactory 代码审查时的参考标准。

---

## PEP 8 代码风格

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块/包 | `snake_case` | `audio_extractor.py` |
| 类 | `PascalCase` | `SubtitleGeneratorTool` |
| 函数/方法 | `snake_case` | `generate_subtitles()` |
| 变量 | `snake_case` | `output_path` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_RETRIES = 3` |
| 私有成员 | `_leading_underscore` | `_private_method()` |
| 类私有 | `__double_underscore` | `__mangling` |

### 导入顺序

```python
# 1. 标准库导入
import os
import sys
from pathlib import Path
from typing import List, Optional

# 2. 第三方库导入
import customtkinter as ctk
from pydantic import BaseModel

# 3. 本地应用导入
from mediafactory.core import Tool
from mediafactory.engine import AudioEngine
```

### 空行规则

```python
# 类定义之间：2 个空行
class AudioEngine:
    pass


class VideoEngine:
    pass


# 方法定义之间：1 个空行
class AudioEngine:
    def extract(self):
        pass

    def process(self):
        pass
```

---

## 类型注解

### 函数类型注解

```python
# 推荐：完整的类型注解
def process_video(
    input_path: str,
    output_path: Optional[str] = None,
    quality: int = 48000
) -> str:
    """处理视频文件并返回输出路径。"""
    if output_path is None:
        output_path = input_path.replace(".mp4", ".wav")
    return output_path

# 复杂类型使用 TypeAlias
AudioConfig = dict[str, int | str]
VideoList = list[tuple[str, Path]]
```

### 类属性类型注解

```python
class SubtitleGeneratorTool(Tool):
    name: str = "subtitle_generator"
    version: str = "2.0.0"
    _config: Optional[ConfigManager] = None
```

### 泛型类型

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        return self.value
```

---

## 资源管理

### 文件操作

```python
# ❌ 错误：未确保关闭
def read_file(path: str) -> str:
    f = open(path)
    content = f.read()
    f.close()  # 如果 read() 抛出异常，不会执行
    return content

# ✅ 正确：使用 with 语句
def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()
```

### 临时资源

```python
# ❌ 错误：异常时不会清理
def process():
    temp_file = create_temp_file()
    result = process_file(temp_file)
    delete_temp_file(temp_file)
    return result

# ✅ 正确：使用 try-finally
def process():
    temp_file = create_temp_file()
    try:
        return process_file(temp_file)
    finally:
        delete_temp_file(temp_file)

# ✅ 更好：使用 context manager
@contextmanager
def temp_file():
    path = create_temp_file()
    try:
        yield path
    finally:
        delete_temp_file(path)

def process():
    with temp_file() as path:
        return process_file(path)
```

### 线程/进程

```python
# ❌ 错误：线程可能泄漏
def run_background():
    thread = threading.Thread(target=worker)
    thread.start()
    # 如果函数返回，线程仍在后台运行

# ✅ 正确：跟踪并管理线程
class BackgroundRunner:
    def __init__(self):
        self._threads: list[threading.Thread] = []

    def run_background(self):
        thread = threading.Thread(target=self._worker, daemon=True)
        thread.start()
        self._threads.append(thread)

    def shutdown(self):
        for thread in self._threads:
            thread.join(timeout=5)
```

---

## 错误处理

### 异常捕获原则

```python
# ❌ 错误：捕获过于宽泛
try:
    result = process()
except Exception:
    pass  # 吞掉所有异常

# ❌ 错误：裸 except
try:
    result = process()
except:
    pass

# ✅ 正确：捕获特定异常
try:
    result = process()
except (ValueError, KeyError) as e:
    log_error(f"Processing failed: {e}")
    raise

# ✅ 最佳：使用项目异常层次
from mediafactory.exceptions import ProcessError

try:
    result = process()
except ProcessError as e:
    log_error_with_context("Processing failed", e)
    raise
```

### 异常链

```python
# ❌ 错误：丢失原始异常
def validate():
    if not is_valid(input_data):
        raise ValueError("Invalid input")

def process():
    try:
        validate()
    except ValueError:
        raise RuntimeError("Processing failed")

# ✅ 正确：保留异常链
def process():
    try:
        validate()
    except ValueError as e:
        raise RuntimeError("Processing failed") from e
```

### 结构化异常

```python
# 项目异常模式
class MediaFactoryError(Exception):
    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        suggestion: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.RECOVERABLE
    ):
        super().__init__(message)
        self.context = context or {}
        self.suggestion = suggestion
        self.severity = severity

# 使用
raise ModelLoadError(
    "Failed to load Whisper model",
    context={"model_name": "large-v3"},
    suggestion="Try using a smaller model or check available memory"
)
```

---

## 并发安全

### 线程安全配置

```python
# ❌ 错误：非线程安全的单例
class Config:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = Config()
        return cls._instance

# ✅ 正确：线程安全的单例
import threading

class Config:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # 双重检查
                    cls._instance = Config()
        return cls._instance
```

### 可取消操作

```python
# CancellationToken 模式
class CancellationToken:
    def __init__(self):
        self._cancelled = False
        self._lock = threading.Lock()

    def cancel(self):
        with self._lock:
            self._cancelled = True

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

# 使用
def process_long(data, token: CancellationToken):
    for item in data:
        if token.is_cancelled():
            return None  # 提前退出
        process_item(item)
```

---

## 性能优化

### 避免不必要的复制

```python
# ❌ 错误：不必要的列表复制
def process_items(items: list[str]) -> list[str]:
    new_items = items.copy()  # 不必要的复制
    for item in new_items:
        item = item.strip()
    return new_items

# ✅ 正确：原地修改
def process_items(items: list[str]) -> list[str]:
    for i, item in enumerate(items):
        items[i] = item.strip()
    return items

# ✅ 更好：使用生成器
def process_items(items: list[str]) -> list[str]:
    return [item.strip() for item in items]
```

### 字符串拼接

```python
# ❌ 错误：循环中拼接
def build_text(parts: list[str]) -> str:
    result = ""
    for part in parts:
        result += part  # 每次创建新字符串
    return result

# ✅ 正确：使用 join
def build_text(parts: list[str]) -> str:
    return "".join(parts)
```

### 批处理

```python
# ❌ 错误：逐个处理
def translate_texts(texts: list[str]) -> list[str]:
    results = []
    for text in texts:
        result = api.translate(text)  # N 次调用
        results.append(result)
    return results

# ✅ 正确：批处理
def translate_texts(texts: list[str]) -> list[str]:
    batch_size = 10
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        result = api.translate_batch(batch)  # N/10 次调用
        results.extend(result)
        time.sleep(5)  # 避免速率限制
    return results
```

---

## 代码组织

### 单一职责原则

```python
# ❌ 错误：函数做多件事
def process_video(path: str) -> str:
    # 1. 验证
    if not os.path.exists(path):
        raise FileNotFoundError()
    # 2. 提取音频
    audio = extract_audio(path)
    # 3. 转录
    text = transcribe(audio)
    # 4. 翻译
    translated = translate(text)
    # 5. 生成 SRT
    srt = generate_srt(translated)
    return srt

# ✅ 正确：分解为多个函数
def process_video(path: str) -> str:
    validate_path(path)
    audio = extract_audio(path)
    segments = transcribe(audio)
    translated = translate_segments(segments)
    return generate_srt(translated)
```

### DRY 原则

```python
# ❌ 错误：重复代码
def method_a():
    config = load_config()
    backend = config.get("backend", "openai")
    api_key = config.get("api_key", "")
    # ...

def method_b():
    config = load_config()
    backend = config.get("backend", "openai")
    api_key = config.get("api_key", "")
    # ...

# ✅ 正确：提取公共逻辑
class BackendConfig:
    def __init__(self):
        config = load_config()
        self.backend = config.get("backend", "openai")
        self.api_key = config.get("api_key", "")

def method_a(config: BackendConfig):
    # ...

def method_b(config: BackendConfig):
    # ...
```

---

## 文档字符串

### Google 风格（推荐）

```python
def process_video(
    input_path: str,
    output_path: str,
    quality: int = 48000
) -> str:
    """从视频文件提取音频并处理。

    Args:
        input_path: 输入视频文件路径。
        output_path: 输出音频文件路径。
        quality: 音频采样率，默认 48000Hz。

    Returns:
        处理后的音频文件路径。

    Raises:
        FileNotFoundError: 如果输入文件不存在。
        ProcessingError: 如果处理失败。

    Examples:
        >>> process_video("video.mp4", "audio.wav")
        'audio.wav'
    """
    pass
```

### 类文档字符串

```python
class AudioEngine(BaseEngine):
    """音频处理引擎。

    使用 ffmpeg 进行音频提取和处理操作。

    Attributes:
        sample_rate: 默认采样率。
        channels: 默认声道数。

    Examples:
        >>> engine = AudioEngine()
        >>> engine.extract("video.mp4", "audio.wav")
    """
    pass
```

---

## 装饰器使用

### 属性缓存

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(arg: str) -> str:
    """计算密集型函数，结果被缓存。"""
    return complex_computation(arg)
```

### 过时警告

```python
import warnings

def deprecated(func):
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{func.__name__} is deprecated",
            DeprecationWarning,
            stacklevel=2
        )
        return func(*args, **kwargs)
    return wrapper
```

### 重试机制

```python
from functools import wraps
import time

def retry(max_attempts: int = 3, delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
```

---

## 常见反模式

### 1. 可变默认参数

```python
# ❌ 错误
def append_item(item, items=[]):
    items.append(item)
    return items  # 多次调用会共享同一个列表

# ✅ 正确
def append_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### 2. 检查类型而非行为

```python
# ❌ 错误
def process(obj):
    if isinstance(obj, list):
        for item in obj:
            print(item)

# ✅ 正确：鸭子类型
def process(obj):
    for item in obj:  # 任何可迭代对象
        print(item)
```

### 3. 使用 `type()` 而非 `isinstance()`

```python
# ❌ 错误：不考虑继承
if type(obj) == MyClass:
    pass

# ✅ 正确：考虑继承
if isinstance(obj, MyClass):
    pass
```

### 4. 忽略返回值

```python
# ❌ 错误：忽略可能的错误
result = process()
if result:
    pass  # 但没有检查 result.success

# ✅ 正确：检查返回值
output = tool.execute(context)
if not output.success:
    handle_error(output.error_message)
```

---

## 测试最佳实践

### pytest 模式

```python
# 使用 pytest fixture
@pytest.fixture
def sample_config():
    return {"backend": "openai", "api_key": "test"}

# 清晰的测试名称
def test_audio_extraction_with_invalid_path_raises_error():
    with pytest.raises(FileNotFoundError):
        engine.extract("nonexistent.mp4", "output.wav")

# 使用 parametrize
@pytest.mark.parametrize("quality", [44100, 48000, 96000])
def test_audio_extraction_quality(quality):
    engine = AudioEngine()
    output = engine.extract("test_video.mp4", "output.wav", quality=quality)
    assert os.path.exists(output)
```

### Mock 使用

```python
# ❌ 错误：过度 Mock
def test_process():
    with patch('module.Class'):
        with patch('module.function'):
            # 测试几乎不涉及真实代码
            pass

# ✅ 正确：只 Mock 外部依赖
def test_process():
    with patch('requests.get') as mock_get:
        mock_get.return_value = Mock(status_code=200)
        result = process()
        assert result.success
```

---

## 性能分析

### 使用 cProfile

```bash
python -m cProfile -o profile.out my_script.py
python -c "import pstats; p = pstats.Stats('profile.out'); p.sort_stats('cumulative').print_stats(20)"
```

### 内存分析

```python
import tracemalloc

tracemalloc.start()
# ... 代码 ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

---

## 类型检查

### mypy 配置

```ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False  # 渐进式类型检查
```

### 类型忽略

```python
# 尽量避免使用 Any
def process(data: Any) -> Any:  # ❌
    pass

# 使用具体类型或 TypeVar
T = TypeVar('T')
def process(data: list[T]) -> list[T]:  # ✅
    pass

# 必要时使用类型忽略
def process(data):  # type: ignore  # 临时方案
    pass
```
