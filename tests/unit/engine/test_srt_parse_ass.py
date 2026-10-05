"""SRTEngine.parse 的 .ass 支持（H3：链路宣称支持但解析器缺失）"""

import pytest

pytestmark = [pytest.mark.unit]

ASS_SAMPLE = """[Script Info]
Title: sample
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname
Style: Default,Arial

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.50,Default,,0,0,0,,Hello, world!
Dialogue: 0,0:00:03.20,0:00:05.00,Default,,0,0,0,,Second line with comma
Dialogue: 0,0:01:02.03,0:01:03.00,Default,,0,0,0,,{\\i1}styled{\\i0} text
"""


@pytest.fixture
def ass_file(tmp_path):
    p = tmp_path / "sample.ass"
    p.write_text(ASS_SAMPLE, encoding="utf-8")
    return str(p)


class TestParseAss:
    def test_parses_dialogue_events(self, ass_file):
        from mediafactory.engine.srt import SRTEngine

        segments = SRTEngine().parse(ass_file)
        assert len(segments) == 3
        # H:MM:SS.cc 厘秒时间戳 → 秒
        assert segments[0]["start"] == pytest.approx(1.0)
        assert segments[0]["end"] == pytest.approx(2.5)
        assert segments[2]["start"] == pytest.approx(62.03)

    def test_text_joins_after_ninth_field_and_strips_overrides(self, ass_file):
        from mediafactory.engine.srt import SRTEngine

        segments = SRTEngine().parse(ass_file)
        # 文本内逗号不断句（第 10 字段起全部拼接）
        assert segments[1]["text"] == "Second line with comma"
        # ASS 覆盖标签 {\\...} 剥除
        assert segments[2]["text"] == "styled text"

    def test_empty_events_returns_empty(self, tmp_path):
        from mediafactory.engine.srt import SRTEngine

        p = tmp_path / "empty.ass"
        p.write_text("[Script Info]\n[Events]\n", encoding="utf-8")
        assert SRTEngine().parse(str(p)) == []

    def test_translate_pipeline_route_accepts_ass(self):
        """runner 的 .ass 路由最终不再抛 Unsupported（契约：路由与解析能力对齐）"""
        from mediafactory.engine.srt import SRTEngine

        # parse 层不再对 .ass 抛 Unsupported
        assert hasattr(SRTEngine, "_parse_ass")
