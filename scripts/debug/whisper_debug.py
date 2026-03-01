"""Whisper 模型真实调测脚本。

运行方式:
    python scripts/debug/whisper_debug.py

用途:
    开发人员手动调测 Whisper 模型，验证转录功能。

前置条件:
    1. 已下载 Faster Whisper 模型
    2. 有测试音频文件
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from mediafactory.engine import RecognitionEngine
from mediafactory.models.whisper_runtime import select_model_and_device
from mediafactory.logging import log_info


def test_transcription(audio_path: str = None):
    """测试音频转录。

    Args:
        audio_path: 音频文件路径，如果为 None 则使用默认测试文件
    """
    print("=" * 60)
    print("Whisper 模型调测")
    print("=" * 60)

    # 选择模型和设备
    model_size, device = select_model_and_device()
    print(f"模型: {model_size}")
    print(f"设备: {device}")

    # 如果没有提供音频文件，提示用户
    if audio_path is None:
        print("\n请提供音频文件路径进行测试:")
        print("  python scripts/debug/whisper_debug.py /path/to/audio.wav")
        print("\n使用临时测试...")
        # 创建一个简单的测试
        _test_model_loading(model_size, device)
        return

    audio_path = Path(audio_path)
    if not audio_path.exists():
        print(f"❌ 音频文件不存在: {audio_path}")
        return

    print(f"\n音频文件: {audio_path}")
    print("-" * 40)

    # 创建识别引擎
    engine = RecognitionEngine()

    # 执行转录
    print("\n开始转录...")
    result = engine.transcribe(
        audio_path=str(audio_path),
        model_size=model_size,
        device=device,
        language=None,  # 自动检测
    )

    # 输出结果
    print("\n转录结果:")
    print("-" * 40)
    if result.get("segments"):
        for i, seg in enumerate(result["segments"][:10], 1):  # 只显示前10个
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "")
            print(f"[{start:.1f}s - {end:.1f}s] {text}")

        if len(result["segments"]) > 10:
            print(f"... 共 {len(result['segments'])} 个片段")

        print(f"\n检测语言: {result.get('language', 'unknown')}")
        print(f"✅ 转录完成!")
    else:
        print("❌ 未检测到语音")

    print("=" * 60)


def _test_model_loading(model_size: str, device: str):
    """测试模型加载。"""
    print("\n测试模型加载...")
    print("-" * 40)

    try:
        from faster_whisper import WhisperModel

        print(f"正在加载 {model_size} 模型...")
        model = WhisperModel(model_size, device=device, compute_type="int8")
        print(f"✅ 模型加载成功!")

        # 测试一个空的转录
        print("\n模型已就绪，可以进行转录测试。")

    except ImportError:
        print("❌ faster-whisper 未安装")
        print("   请运行: pip install faster-whisper")
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_transcription(sys.argv[1])
    else:
        test_transcription()
