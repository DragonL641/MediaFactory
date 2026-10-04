"""翻译术语记忆（TermDict）。

单一 dict，两个进货时机：
- 种子：用户 JSON（source="user"），翻译开始前加载
- 滚动：每批翻完后 LLM 自判「值得记忆」的词条（source="auto"）

不变量：
- first-wins：先入典者定译法（setdefault 语义），用户词条靠加载时序天然优先
- key 统一小写、最小长度 2（短 key 会造成子串误命中）
- 提取调用不带历史 dict（成本恒定）；注入按当前批命中过滤
"""

from dataclasses import dataclass

from ..logging import log_debug

_MIN_KEY_LENGTH = 2


@dataclass
class TermEntry:
    """单个术语条目。source: "user"（用户钦定）| "auto"（LLM 滚动积累）。"""

    translation: str
    source: str


class TermDict:
    """术语典：注册种子、滚动学习、按批命中、冲突替换。"""

    def __init__(self, max_terms: int = 200):
        self._terms: dict[str, TermEntry] = {}
        self._max_terms = max_terms

    def register_user(self, mapping: dict[str, str]) -> int:
        """加载用户种子词条。返回实际注册数量。"""
        registered = 0
        for word, translation in (mapping or {}).items():
            if self._register(word, translation, source="user") is not None:
                registered += 1
        return registered

    def learn(self, word: str, translation: str) -> str | None:
        """滚动记忆词条（source=auto）。

        返回 "new"（新入典）/ "conflict"（已有不同译法，未覆盖）/ None（一致或无效）。
        """
        return self._register(word, translation, source="auto")

    def _register(self, word: str, translation: str, source: str) -> str | None:
        key = (word or "").strip().lower()
        value = (translation or "").strip()
        if len(key) < _MIN_KEY_LENGTH or not value:
            return None
        if key not in self._terms and len(self._terms) >= self._max_terms:
            log_debug(f"[TermDict] 已达上限 {self._max_terms}，丢弃: {key!r}")
            return None
        existing = self._terms.get(key)
        if existing is None:
            self._terms[key] = TermEntry(translation=value, source=source)
            return "new"
        if existing.translation != value:
            return "conflict"
        return None

    def source_of(self, key: str) -> str | None:
        """返回词条来源（"user"/"auto"），未收录返回 None。

        用于冲突日志分级：user 冲突 = 注入失效信号（warning），
        auto 冲突 = 常态波动（debug）。
        """
        entry = self._terms.get((key or "").strip().lower())
        return entry.source if entry else None

    def hits(self, texts: list[str]) -> dict[str, str]:
        """返回命中当前批源文本的词条（key → 译法）。"""
        if not self._terms or not texts:
            return {}
        joined = "\n".join(texts).lower()
        return {
            key: entry.translation
            for key, entry in self._terms.items()
            if key in joined
        }

    def render(self, hits: dict[str, str]) -> str:
        """把命中词条渲染为注入文本。空则返回空串。"""
        if not hits:
            return ""
        lines = [f"- {key} → {trans}" for key, trans in hits.items()]
        return "# Terminology (must follow)\n" + "\n".join(lines)

    def apply_conflict_fixes(
        self, translations: list[str], wrong_map: dict[str, str]
    ) -> list[str]:
        """把批内译文中的错误译法替换回 dict 译法。

        wrong_map: {小写源词: 本批出现的错误译法}。
        已知限制：简单子串替换，短错误译法可能误伤更长单词——key 最小长度 2 缓解。
        """
        result = list(translations)
        for key, wrong in wrong_map.items():
            entry = self._terms.get(key)
            if not entry or not wrong:
                continue
            result = [
                t.replace(wrong, entry.translation) if wrong in t else t for t in result
            ]
        return result

    def dump(self) -> dict[str, dict]:
        """导出全部词条（含来源标记），用于落盘日志。"""
        return {
            key: {"translation": e.translation, "source": e.source}
            for key, e in self._terms.items()
        }
