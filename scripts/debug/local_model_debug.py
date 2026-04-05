"""本地翻译模型真实调测脚本。

运行方式:
    python scripts/debug/local_model_debug.py

用途:
    开发人员手动调测本地翻译模型（NLLB/M2M），验证翻译功能。

前置条件:
    1. 已下载翻译模型（通过 scripts/utils/download_model.py）
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mediafactory.engine import TranslationEngine
from mediafactory.models.local_models import discover_translation_models
from mediafactory.config import get_config


def test_local_translation():
    """测试本地翻译模型。"""
    print("=" * 60)
    print("本地翻译模型调测")
    print("=" * 60)

    # 发现可用模型
    config = get_config()
    models_dir = Path(config.model.models_dir)
    print(f"模型目录: {models_dir}")

    available_models = discover_translation_models(models_dir)
    if not available_models:
        print("\n❌ 未发现可用的翻译模型")
        print("请先下载模型:")
        print("  python scripts/utils/download_model.py nllb-600m")
        return

    print(f"\n可用模型: {list(available_models.keys())}")

    # 选择第一个可用模型
    model_name = list(available_models.keys())[0]
    model_path = available_models[model_name]
    print(f"使用模型: {model_name}")
    print(f"模型路径: {model_path}")
    print("-" * 40)

    # 创建翻译引擎
    engine = TranslationEngine(
        use_local_models_only=True,
        model_type=model_name,
        device="cpu",
    )

    # 测试用例
    test_cases = [
        ("Hello, world!", "en", "zh"),
        ("This is a test.", "en", "zh"),
        ("How are you?", "en", "zh"),
        ("おはようございます。", "ja", "zh"),
        ("ありがとう。", "ja", "zh"),
    ]

    print("\n翻译测试:")
    print("-" * 40)

    for text, src_lang, tgt_lang in test_cases:
        print(f"\n原文 ({src_lang} -> {tgt_lang}): {text}")

        # 创建测试片段
        segments = [{"start": 0, "end": 5, "text": text}]
        result = {"segments": segments, "language": src_lang}

        try:
            translated = engine.translate(result, src_lang, tgt_lang)
            if translated.get("segments"):
                translated_text = translated["segments"][0].get("text", "")
                print(f"译文: {translated_text}")
            else:
                print("译文: (空)")
        except Exception as e:
            print(f"错误: {e}")

    print("\n" + "=" * 60)
    print("✅ 调测完成")
    print("=" * 60)


def test_batch_translation():
    """测试批量翻译。"""
    print("=" * 60)
    print("批量翻译测试")
    print("=" * 60)

    config = get_config()
    engine = TranslationEngine(
        use_local_models_only=True,
        model_type="nllb-600m",
        device="cpu",
    )

    # 批量测试
    texts = [
        "Hello",
        "World",
        "Test",
    ]

    segments = [{"start": i * 5, "end": (i + 1) * 5, "text": t} for i, t in enumerate(texts)]
    result = {"segments": segments, "language": "en"}

    print(f"批量翻译 {len(texts)} 个文本...")

    try:
        translated = engine.translate(result, "en", "zh")
        for i, seg in enumerate(translated.get("segments", [])):
            print(f"  {texts[i]} -> {seg.get('text', '')}")
        print("✅ 批量翻译成功!")
    except Exception as e:
        print(f"❌ 批量翻译失败: {e}")

    print("=" * 60)


if __name__ == "__main__":
    test_local_translation()
    print("\n")
    test_batch_translation()
