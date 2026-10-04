"""TermDict 单元测试。"""

import pytest

from mediafactory.llm.term_memory import TermDict

pytestmark = [pytest.mark.unit]


class TestRegistration:
    def test_register_user_and_hit(self):
        d = TermDict()
        assert d.register_user({"Kubernetes": "K8s"}) == 1
        assert d.hits(["We deploy on Kubernetes today"]) == {"kubernetes": "K8s"}

    def test_key_normalized_to_lowercase(self):
        d = TermDict()
        d.register_user({"Kubernetes": "K8s"})
        d.learn("KUBERNETES", "K8s")  # 大小写变体 → 同一 key，译法一致 → None
        assert len(d.dump()) == 1
        assert d.dump()["kubernetes"]["source"] == "user"

    def test_short_key_dropped(self):
        d = TermDict()
        assert d.register_user({"a": "字母A"}) == 0
        assert d.learn("x", "未知") is None
        assert d.dump() == {}

    def test_empty_translation_dropped(self):
        d = TermDict()
        assert d.register_user({"Kubernetes": "  "}) == 0

    def test_max_terms_cap(self):
        d = TermDict(max_terms=3)
        for i in range(5):
            d.learn(f"term{i}", f"词条{i}")
        assert len(d.dump()) == 3


class TestLearn:
    def test_learn_new(self):
        d = TermDict()
        assert d.learn("Jon Snow", "琼恩·雪诺") == "new"
        assert d.dump()["jon snow"]["source"] == "auto"

    def test_learn_same_translation_returns_none(self):
        d = TermDict()
        d.learn("Jon Snow", "琼恩·雪诺")
        assert d.learn("Jon Snow", "琼恩·雪诺") is None

    def test_learn_conflict_is_first_wins(self):
        d = TermDict()
        d.register_user({"Kubernetes": "K8s"})
        assert d.learn("Kubernetes", "库伯内提斯") == "conflict"
        assert d.dump()["kubernetes"]["translation"] == "K8s"  # user 译法不动

    def test_conflict_source_differs_user_vs_auto(self):
        d = TermDict()
        d.learn("Jon Snow", "琼恩·雪诺")  # auto 先入
        assert d.learn("Jon Snow", "雪诺") == "conflict"
        assert d.dump()["jon snow"]["translation"] == "琼恩·雪诺"


class TestHitsAndRender:
    def test_hits_case_insensitive_and_empty_when_no_terms(self):
        d = TermDict()
        assert d.hits(["anything"]) == {}
        d.register_user({"Kubernetes": "K8s"})
        assert d.hits(["KUBERNETES cluster"]) == {"kubernetes": "K8s"}
        assert d.hits(["unrelated text"]) == {}

    def test_hits_multiple_terms(self):
        d = TermDict()
        d.register_user({"Kubernetes": "K8s", "Docker": "Docker"})
        hits = d.hits(["Kubernetes and Docker"])
        assert hits == {"kubernetes": "K8s", "docker": "Docker"}

    def test_render_format(self):
        d = TermDict()
        assert d.render({}) == ""
        out = d.render({"kubernetes": "K8s"})
        assert out.startswith("# Terminology (must follow)")
        assert "- kubernetes → K8s" in out


class TestConflictFix:
    def test_apply_conflict_fixes_replaces_wrong_translation(self):
        d = TermDict()
        d.register_user({"Kubernetes": "K8s"})
        fixed = d.apply_conflict_fixes(
            ["这是 库伯内提斯 集群", "无冲突句"],
            {"kubernetes": "库伯内提斯"},
        )
        assert fixed[0] == "这是 K8s 集群"
        assert fixed[1] == "无冲突句"

    def test_apply_conflict_fixes_unknown_key_noop(self):
        d = TermDict()
        fixed = d.apply_conflict_fixes(["原文"], {"ghost": "幽灵"})
        assert fixed == ["原文"]


class TestDump:
    def test_dump_shape(self):
        d = TermDict()
        d.register_user({"Kubernetes": "K8s"})
        d.learn("Jon Snow", "琼恩·雪诺")
        assert d.dump() == {
            "kubernetes": {"translation": "K8s", "source": "user"},
            "jon snow": {"translation": "琼恩·雪诺", "source": "auto"},
        }
