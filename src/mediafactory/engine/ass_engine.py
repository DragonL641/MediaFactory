"""ASS/SSA 字幕引擎。

支持生成 Advanced SubStation Alpha 格式字幕，提供丰富的样式支持。
ASS 格式支持：字体、颜色、位置、边框、阴影、特效等。
支持从外部 .ass 样式文件加载样式模板。
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from .srt import BilingualLayout
from ..exceptions import ProcessingError
from ..core.exception_wrapper import convert_exception
from ..logging import log_info, log_warning
from ..i18n import t


# 样式模板目录
STYLES_DIR = Path(__file__).parent.parent / "resources" / "subtitle_styles"


class ASSEngine:
    """处理 ASS/SSA 字幕文件的生成。"""

    # 默认样式配置
    # 平台感知默认字体
    import sys
    _DEFAULT_FONT = "PingFang SC" if sys.platform == "darwin" else "Microsoft YaHei"

    DEFAULT_STYLE = {
        "Name": "Default",
        "Fontname": _DEFAULT_FONT,
        "Fontsize": "44",
        "PrimaryColour": "&H00FFFFFF",  # 白色 (BGR格式)
        "SecondaryColour": "&H000000FF",
        "OutlineColour": "&H00000000",  # 黑色边框
        "BackColour": "&H00000000",
        "Bold": "-1",
        "Italic": "0",
        "Underline": "0",
        "StrikeOut": "0",
        "ScaleX": "100",
        "ScaleY": "100",
        "Spacing": "0",
        "Angle": "0",
        "BorderStyle": "1",
        "Outline": "2",
        "Shadow": "1",
        "Alignment": "2",  # 底部居中
        "MarginL": "10",
        "MarginR": "10",
        "MarginV": "30",
        "Encoding": "1",
    }

    # 副字幕样式（用于双语字幕的小字）
    SECONDARY_STYLE = {
        "Name": "Secondary",
        "Fontname": "Microsoft YaHei",
        "Fontsize": "30",
        "PrimaryColour": "&H00FFFFFF",
        "SecondaryColour": "&H000000FF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H00000000",
        "Bold": "0",
        "Italic": "0",
        "Underline": "0",
        "StrikeOut": "0",
        "ScaleX": "100",
        "ScaleY": "100",
        "Spacing": "0",
        "Angle": "0",
        "BorderStyle": "1",
        "Outline": "1.5",
        "Shadow": "0.5",
        "Alignment": "2",
        "MarginL": "10",
        "MarginR": "10",
        "MarginV": "30",
        "Encoding": "1",
    }

    # 预设样式模板
    STYLE_PRESETS = {
        "default": {
            "Default": DEFAULT_STYLE,
            "Secondary": SECONDARY_STYLE,
        },
        "科普风": {
            "Default": {
                **DEFAULT_STYLE,
                "Fontname": "Microsoft YaHei",
                "Fontsize": "44",
                "PrimaryColour": "&H00e6e8f1",
                "Outline": "3.0",
                "OutlineColour": "&H06060606",
                "Shadow": "2.2",
            },
            "Secondary": SECONDARY_STYLE,
        },
        "番剧风": {
            "Default": {
                **DEFAULT_STYLE,
                "Fontname": "Microsoft YaHei",
                "Fontsize": "46",
                "PrimaryColour": "&H00e6e8f1",
                "OutlineColour": "&H00987f5",
                "Outline": "2.6",
                "Shadow": "2.6",
            },
            "Secondary": {
                **SECONDARY_STYLE,
                "OutlineColour": "&H00987f5",
            },
        },
        "新闻风": {
            "Default": {
                **DEFAULT_STYLE,
                "Fontname": "SimHei",
                "Fontsize": "42",
                "PrimaryColour": "&H00FFFF00",  # 黄色
                "OutlineColour": "&H00000000",
                "Outline": "2.5",
            },
            "Secondary": SECONDARY_STYLE,
        },
    }

    def __init__(self):
        """初始化 ASS 引擎。"""
        pass

    def generate_to_path(
        self,
        output_path: str,
        segments: List[Dict[str, Any]],
        style_preset: str = "default",
        style_file: Optional[str] = None,
        custom_styles: Optional[Dict[str, Dict[str, str]]] = None,
        bilingual: bool = False,
        layout: str = BilingualLayout.TRANSLATE_ON_TOP,
        play_res_x: int = 1280,
        play_res_y: int = 720,
    ) -> None:
        """生成 ASS 字幕文件。

        Args:
            output_path: 输出文件路径
            segments: 字幕分段列表
            style_preset: 样式预设名称（default, 科普风, 番剧风, 新闻风）
            style_file: 外部样式文件路径（.ass 格式），优先级高于 style_preset
            custom_styles: 自定义样式字典，覆盖预设样式
            bilingual: 是否生成双语字幕
            layout: 双语布局（仅当 bilingual=True 时生效）
            play_res_x: 视频分辨率宽度
            play_res_y: 视频分辨率高度

        Raises:
            ProcessingError: 如果生成失败
        """
        try:
            # 获取样式（优先使用外部文件）
            if style_file:
                styles = self._load_styles_from_file(style_file)
                log_info(f"[ASSEngine] 使用外部样式文件: {style_file}")
            else:
                styles = self._get_styles(style_preset, custom_styles)

            # 应用自定义覆盖
            if custom_styles:
                for style_name, style_override in custom_styles.items():
                    if style_name in styles:
                        styles[style_name] = {**styles[style_name], **style_override}
                    else:
                        styles[style_name] = style_override

            # 构建 ASS 内容
            content = self._build_ass_content(
                segments=segments,
                styles=styles,
                bilingual=bilingual,
                layout=layout,
                play_res_x=play_res_x,
                play_res_y=play_res_y,
            )

            # 确保目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 写入文件
            with open(output_path, "w", encoding="utf-8-sig") as f:
                f.write(content)

            log_info(f"[ASSEngine] 生成 ASS 字幕: {output_path}")

        except ProcessingError:
            raise
        except Exception as e:
            raise convert_exception(
                e,
                context={"output_path": output_path, "segment_count": len(segments)},
            ) from e

    def _load_styles_from_file(self, filepath: str) -> Dict[str, Dict[str, str]]:
        """从 ASS 文件加载样式。

        Args:
            filepath: ASS 样式文件路径

        Returns:
            样式配置字典

        Raises:
            ProcessingError: 如果文件不存在或解析失败
        """
        # 检查是否是相对路径，尝试从内置样式目录查找
        path = Path(filepath)
        if not path.is_absolute():
            builtin_path = STYLES_DIR / filepath
            if builtin_path.exists():
                path = builtin_path
            elif not path.exists():
                # 尝试添加 .ass 后缀
                builtin_path = STYLES_DIR / f"{filepath}.ass"
                if builtin_path.exists():
                    path = builtin_path

        if not path.exists():
            raise ProcessingError(
                message=t("error.styleFileNotExist", path=filepath),
                context={"filepath": filepath},
            )

        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except Exception as e:
            raise ProcessingError(
                message=t("error.cannotReadStyleFile", error=str(e)),
                context={"filepath": str(path)},
            ) from e

        styles = {}
        in_styles_section = False

        # 解析样式
        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("[V4+ Styles]"):
                in_styles_section = True
                continue
            elif line.startswith("[") and in_styles_section:
                break  # 进入下一个部分

            if in_styles_section and line.startswith("Style:"):
                # 解析样式行
                style_dict = self._parse_style_line(line)
                if style_dict:
                    style_name = style_dict.get("Name", "Default")
                    styles[style_name] = style_dict

        if not styles:
            log_warning(f"[ASSEngine] 样式文件未包含有效样式: {path}")
            # 返回默认样式
            return {
                "Default": self.DEFAULT_STYLE.copy(),
                "Secondary": self.SECONDARY_STYLE.copy(),
            }

        # 确保有 Default 样式
        if "Default" not in styles:
            styles["Default"] = self.DEFAULT_STYLE.copy()

        return styles

    def _parse_style_line(self, line: str) -> Optional[Dict[str, str]]:
        """解析 ASS 样式行。

        Args:
            line: 样式行（以 "Style:" 开头）

        Returns:
            样式字典，解析失败返回 None
        """
        # 格式: Style: Name,Fontname,Fontsize,PrimaryColour,...
        match = re.match(r"Style:\s*(.+)", line)
        if not match:
            return None

        values = match.group(1).split(",")
        if len(values) < 22:
            return None

        # ASS 样式字段顺序
        field_names = [
            "Name",
            "Fontname",
            "Fontsize",
            "PrimaryColour",
            "SecondaryColour",
            "OutlineColour",
            "BackColour",
            "Bold",
            "Italic",
            "Underline",
            "StrikeOut",
            "ScaleX",
            "ScaleY",
            "Spacing",
            "Angle",
            "BorderStyle",
            "Outline",
            "Shadow",
            "Alignment",
            "MarginL",
            "MarginR",
            "MarginV",
            "Encoding",
        ]

        style = {}
        for i, name in enumerate(field_names):
            if i < len(values):
                style[name] = values[i].strip()

        return style

    def _get_styles(
        self,
        preset: str,
        custom_styles: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Dict[str, Dict[str, str]]:
        """获取样式配置。

        Args:
            preset: 预设名称
            custom_styles: 自定义样式覆盖

        Returns:
            样式配置字典
        """
        # 获取预设样式
        styles = self.STYLE_PRESETS.get(preset, self.STYLE_PRESETS["default"]).copy()

        # 应用自定义覆盖
        if custom_styles:
            for style_name, style_override in custom_styles.items():
                if style_name in styles:
                    styles[style_name] = {**styles[style_name], **style_override}
                else:
                    styles[style_name] = style_override

        return styles

    def _build_ass_content(
        self,
        segments: List[Dict[str, Any]],
        styles: Dict[str, Dict[str, str]],
        bilingual: bool,
        layout: str,
        play_res_x: int,
        play_res_y: int,
    ) -> str:
        """构建 ASS 文件内容。

        Args:
            segments: 字幕分段
            styles: 样式配置
            bilingual: 是否双语
            layout: 双语布局
            play_res_x: 分辨率宽度
            play_res_y: 分辨率高度

        Returns:
            ASS 文件内容
        """
        lines = []

        # Script Info 部分
        lines.append("[Script Info]")
        lines.append("; Script generated by MediaFactory")
        lines.append("ScriptType: v4.00+")
        lines.append(f"PlayResX: {play_res_x}")
        lines.append(f"PlayResY: {play_res_y}")
        lines.append("WrapStyle: 0")
        lines.append("ScaledBorderAndShadow: yes")
        lines.append("YCbCr Matrix: TV.709")
        lines.append("")

        # Styles 部分
        lines.append("[V4+ Styles]")
        lines.append(
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        )

        # 写入样式（Default、Secondary 等）
        for style_name, style in styles.items():
            style_line = self._format_style(style_name, style)
            lines.append(style_line)

        lines.append("")

        # Events 部分
        lines.append("[Events]")
        lines.append(
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        )

        for segment in segments:
            start = segment.get("start", 0)
            end = segment.get("end", 0)
            text = segment.get("text", "").strip()
            original_text = segment.get("original_text", "").strip()
            # 处理双语
            if bilingual and original_text:
                if layout == BilingualLayout.TRANSLATE_ON_TOP:
                    # 译文在上（主字幕），原文在下（副字幕）
                    # 先写副字幕（原文）
                    lines.append(
                        self._format_dialogue(start, end, "Secondary", original_text)
                    )
                    # 再写主字幕（译文）
                    lines.append(self._format_dialogue(start, end, "Default", text))
                elif layout == BilingualLayout.ORIGINAL_ON_TOP:
                    # 原文在上（主字幕），译文在下（副字幕）
                    lines.append(self._format_dialogue(start, end, "Secondary", text))
                    lines.append(
                        self._format_dialogue(start, end, "Default", original_text)
                    )
                elif layout == BilingualLayout.ONLY_ORIGINAL:
                    lines.append(
                        self._format_dialogue(start, end, "Default", original_text)
                    )
                else:
                    # ONLY_TRANSLATE 或默认
                    lines.append(self._format_dialogue(start, end, "Default", text))
            else:
                # 单语
                lines.append(self._format_dialogue(start, end, "Default", text))

        lines.append("")

        return "\n".join(lines)

    def _format_style(self, name: str, style: Dict[str, str]) -> str:
        """格式化样式行。

        Args:
            name: 样式名称
            style: 样式配置

        Returns:
            样式行字符串
        """
        return (
            f"Style: {name},"
            f"{style.get('Fontname', 'Arial')},"
            f"{style.get('Fontsize', '40')},"
            f"{style.get('PrimaryColour', '&H00FFFFFF')},"
            f"{style.get('SecondaryColour', '&H000000FF')},"
            f"{style.get('OutlineColour', '&H00000000')},"
            f"{style.get('BackColour', '&H00000000')},"
            f"{style.get('Bold', '0')},"
            f"{style.get('Italic', '0')},"
            f"{style.get('Underline', '0')},"
            f"{style.get('StrikeOut', '0')},"
            f"{style.get('ScaleX', '100')},"
            f"{style.get('ScaleY', '100')},"
            f"{style.get('Spacing', '0')},"
            f"{style.get('Angle', '0')},"
            f"{style.get('BorderStyle', '1')},"
            f"{style.get('Outline', '2')},"
            f"{style.get('Shadow', '1')},"
            f"{style.get('Alignment', '2')},"
            f"{style.get('MarginL', '10')},"
            f"{style.get('MarginR', '10')},"
            f"{style.get('MarginV', '30')},"
            f"{style.get('Encoding', '1')}"
        )

    def _format_dialogue(
        self,
        start: float,
        end: float,
        style: str,
        text: str,
    ) -> str:
        """格式化对话行。

        Args:
            start: 开始时间（秒）
            end: 结束时间（秒）
            style: 样式名称
            text: 字幕文本

        Returns:
            对话行字符串
        """
        start_time = self._format_time(start)
        end_time = self._format_time(end)
        # 转义换行符
        text = text.replace("\n", "\\N")
        return f"Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{text}"

    def _format_time(self, seconds: float) -> str:
        """将秒数格式化为 ASS 时间格式 (H:MM:SS.cc)。

        Args:
            seconds: 秒数

        Returns:
            ASS 时间字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds - int(seconds)) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def get_available_presets(self) -> List[str]:
        """获取可用的样式预设列表。

        Returns:
            预设名称列表
        """
        return list(self.STYLE_PRESETS.keys())

    def get_available_style_files(self) -> List[str]:
        """获取可用的外部样式文件列表。

        Returns:
            样式文件名列表（不含路径）
        """
        if not STYLES_DIR.exists():
            return []

        files = []
        for f in STYLES_DIR.iterdir():
            if f.suffix.lower() == ".ass":
                files.append(f.stem)  # 返回不含扩展名的文件名

        return sorted(files)

    def get_style_file_path(self, name: str) -> Optional[str]:
        """获取样式文件的完整路径。

        Args:
            name: 样式文件名（可含或不含 .ass 后缀）

        Returns:
            样式文件完整路径，不存在则返回 None
        """
        if not name.endswith(".ass"):
            name = f"{name}.ass"

        path = STYLES_DIR / name
        return str(path) if path.exists() else None
