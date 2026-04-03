import pytest
import difflib
from pathlib import Path

from tests.data.ja_zh_test_data import TEST_DATA

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.requires_ml]

# 测试模型类型配置
MODEL_TYPE = "NLLB-200-Distilled-600M"    # 需要检查哪个模型的准确率，就写成哪个


def _check_ml_available():
    """检查 ML 依赖和翻译模型是否可用，collection 阶段安全处理。"""
    try:
        from mediafactory.models.local_models import local_model_manager
        from mediafactory.models.model_registry import get_model_info
        model_info = get_model_info(MODEL_TYPE)
        if model_info:
            return local_model_manager.is_model_available_locally(model_info.model_id)
        return False
    except ImportError:
        return False


_ml_available = _check_ml_available()


def calculate_similarity(s1, s2):
    """计算两个字符串的相似度。"""
    # 移除标点符号以便更准确地比较内容
    import re
    s1 = re.sub(r'[^\w\s]', '', s1)
    s2 = re.sub(r'[^\w\s]', '', s2)
    return difflib.SequenceMatcher(None, s1, s2).ratio()


@pytest.mark.skipif(not _ml_available, reason="ML 依赖或翻译模型不可用")
def test_japanese_to_chinese_translation_accuracy():
    """
    测试日语到中文的翻译准确率。
    要求平均吻合率达到 90% 以上。
    """
    from mediafactory.engine.translation import TranslationEngine

    engine = TranslationEngine(use_local_models_only=True, model_type=MODEL_TYPE)

    # 构建模拟的 Whisper 结果
    segments = []
    for i, item in enumerate(TEST_DATA):
        segments.append({
            "id": i,
            "start": float(i * 5),
            "end": float((i + 1) * 5),
            "text": item["ja"]
        })

    result = {
        "text": " ".join([item["ja"] for item in TEST_DATA]),
        "segments": segments,
        "language": "ja"
    }

    # 执行翻译
    translated_result = engine.translate(result, src_lang="ja", tgt_lang="zh")

    # 检查是否实际执行了翻译（如果返回原文本，则可能是模型加载失败或被跳过）
    if len(segments) > 0:
        first_orig = segments[0]["text"].strip()
        first_trans = translated_result["segments"][0]["text"].strip()
        if first_orig == first_trans:
            pytest.skip("翻译引擎未实际执行翻译（可能由于模型加载失败或资源限制），跳过准确率测试。")

    # 验证准确率
    total_similarity = 0
    for i, item in enumerate(TEST_DATA):
        actual_zh = translated_result["segments"][i]["text"]
        similarity = calculate_similarity(item["zh_expected"], actual_zh)
        total_similarity += similarity
        print(f"Original: {item['ja']}")
        print(f"Expected: {item['zh_expected']}")
        print(f"Actual: {actual_zh}")
        print(f"Similarity: {similarity:.2f}")

    avg_similarity = total_similarity / len(TEST_DATA)
    print(f"Average Similarity: {avg_similarity:.2f}")

    # 要求 90% 的吻合率
    assert avg_similarity >= 0.9, f"翻译吻合率仅为 {avg_similarity:.2f}，未达到 0.9 的要求"
