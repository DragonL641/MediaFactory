# 开发调测脚本

本目录包含用于真实模型/API 调测的脚本，供开发人员调试使用。

**注意**：这些脚本会进行真实的模型加载和 API 调用，需要相应的硬件资源和网络连接。

## 目录结构

```
scripts/debug/
├── openai_debug.py       # OpenAI API 调测
├── glm_debug.py          # GLM API 调测
└── README.md
```

## 使用方法

### OpenAI API 调测
```bash
python scripts/debug/openai_debug.py
```

### GLM API 调测
```bash
python scripts/debug/glm_debug.py
```

## 前置条件

### LLM API
- 在 `config.toml` 中配置有效的 API Key
- 确保网络连接正常

## 与 tests/ 的区别

| 目录 | 用途 | 模型/API | 适合 CI/CD |
|------|------|----------|------------|
| `scripts/debug/` | 开发调测 | 真实调用 | 否 |
| `tests/` | 自动化测试 | Mock | 是 |

## 配置示例

在 `config.toml` 中添加以下配置：

```toml
[openai]
api_key = "sk-..."
base_url = ""  # 可选，使用默认值
model = "gpt-4o-mini"

[glm]
api_key = "..."
base_url = "https://open.bigmodel.cn/api/paas/v4/"
model = "glm-4-flash"
```
