"""OpenAI API 真实调测脚本。

运行方式:
    python scripts/debug/openai_debug.py

用途:
    开发人员手动调测 OpenAI API，验证连接和翻译功能。

前置条件:
    1. 在 config.toml 中配置有效的 OpenAI API Key
    2. 确保网络连接正常
"""

from mediafactory.config import get_config_manager
from mediafactory.llm.factory import create_backend
from mediafactory.llm.base import TranslationRequest


def main():
    """运行 OpenAI API 调测。"""
    config_manager = get_config_manager()
    config = config_manager.config

    api_key = config.openai.api_key or ""
    base_url = config.openai.base_url or ""
    model = config.openai.model or "gpt-4o-mini"

    print("=" * 60)
    print("OpenAI API 调测")
    print("=" * 60)
    print(f"API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '(too short)'}")
    print(f"Base URL: {base_url or '(default)'}")
    print(f"模型: {model}")
    print("=" * 60)

    # 创建后端
    backend = create_backend(
        "openai", api_key=api_key, base_url=base_url, model=model
    )

    if backend is None:
        print("❌ 后端创建失败")
        return

    # 连接测试
    print("\n--- 连接测试 ---")
    result = backend.test_connection()
    print(f"成功: {result.get('success')}")
    print(f"消息: {result.get('message')}")

    if not result.get("success"):
        print("\n❌ 连接测试失败，请检查 API Key 和网络连接")
        return

    # 翻译测试
    print("\n--- 翻译测试 ---")
    test_cases = [
        ("Hello, world!", "en", "zh"),
        ("This is a test of translation system.", "en", "zh"),
        ("おはようございます。", "ja", "zh"),
    ]

    for text, src_lang, tgt_lang in test_cases:
        print(f"\n原文 ({src_lang} -> {tgt_lang}): {text}")
        request = TranslationRequest(text=text, src_lang=src_lang, tgt_lang=tgt_lang)
        result = backend.translate(request)

        if result.success:
            translated = result.translated_text
            if isinstance(translated, list):
                translated = translated[0] if translated else ""
            print(f"译文: {translated}")
        else:
            print(f"错误: {result.error_message}")

    print("\n" + "=" * 60)
    print("✅ 调测完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
