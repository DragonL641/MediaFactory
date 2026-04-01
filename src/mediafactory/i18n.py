"""
轻量级 i18n 翻译器

使用 JSON 字典实现，适合桌面应用场景。
语言偏好从 config.toml 读取，无需额外依赖。
"""

import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

_LOCALES_DIR = Path(__file__).parent / "locales"
_CURRENT_LANG = "en"
_LANG_LOCK = Lock()
_TRANSLATIONS: Dict[str, Dict[str, Any]] = {}
_TRANSLATIONS_LOADED = False


def _load_translations(lang: str) -> Dict[str, Any]:
    """加载指定语言的翻译文件"""
    if lang in _TRANSLATIONS:
        return _TRANSLATIONS[lang]

    file_path = _LOCALES_DIR / f"{lang}.json"
    if not file_path.exists():
        file_path = _LOCALES_DIR / "en.json"

    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            _TRANSLATIONS[lang] = json.load(f)
    else:
        _TRANSLATIONS[lang] = {}

    return _TRANSLATIONS[lang]


def _load_all_translations() -> None:
    """预加载所有翻译文件"""
    global _TRANSLATIONS_LOADED
    if _TRANSLATIONS_LOADED:
        return

    for locale_file in _LOCALES_DIR.glob("*.json"):
        lang = locale_file.stem
        if lang not in _TRANSLATIONS:
            with open(locale_file, "r", encoding="utf-8") as f:
                _TRANSLATIONS[lang] = json.load(f)

    _TRANSLATIONS_LOADED = True


def set_language(lang: str) -> None:
    """设置当前语言"""
    global _CURRENT_LANG
    with _LANG_LOCK:
        _CURRENT_LANG = lang
        _load_translations(lang)


def get_language() -> str:
    """获取当前语言"""
    return _CURRENT_LANG


def t(key: str, **kwargs) -> str:
    """
    翻译 key 为当前语言的字符串

    支持嵌套 key（用点号分隔）和 {{variable}} 插值。
    如果 key 不存在，返回 key 本身作为回退。
    """
    with _LANG_LOCK:
        translations = _load_translations(_CURRENT_LANG)

    # 支持嵌套 key: "progress.model_loading_start"
    parts = key.split(".")
    value = translations
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return key

    if value is None:
        # 回退到英文
        fallback = _load_translations("en")
        value = fallback
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return key

    if value is None:
        return key

    if isinstance(value, str) and kwargs:
        for k, v in kwargs.items():
            value = value.replace(f"{{{{{k}}}}}", str(v))

    return value


def init_i18n() -> None:
    """初始化 i18n，后端固定使用英文"""
    _load_all_translations()
    set_language("en")
