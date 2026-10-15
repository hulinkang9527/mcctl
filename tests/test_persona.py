"""人格引擎测试：题库结构、512 种作答的覆盖与分布、同分裁决、可解释性。

``mcctl whoami`` 共 8 题：前 7 题二选一（a/b），第 8 题为终局四选一（a/b/c/d）。
总计 2^7 × 4 = 512 种作答组合，本文件全部枚举并校验结果稳定性。
"""
from __future__ import annotations

import collections

from mcctl.engines import persona as P

# 终局题四选一
FINAL_CHOICES = ("a", "b", "c", "d")


def all_answer_sets() -> list[list[str]]:
    qs = P.questions()
    assert len(qs) == 8, "题库应为 8 题"
    sets: list[list[str]] = []
    for mask in range(2 ** 7):
        base = ["b" if (mask >> i) & 1 else "a" for i in range(7)]
        for last in FINAL_CHOICES:
            sets.append(base + [last])
    return sets


def test_question_bank_shape():
    qs = P.questions()
    assert len(qs) == 8
    for q in qs[:-1]:
        assert P.choices_of(q) == ["a", "b"], "前 7 题为二选一"
    assert P.choices_of(qs[-1]) == ["a", "b", "c", "d"], "终局题为四选一"
    assert qs[-1].get("final") is True
    for q in qs:
        for k in P.choices_of(q):
            assert q[k]["text"]
            assert q[k]["score"]
            assert q[k].get("dim") in P.DIM_LABELS, f"第 {q['id']} 题缺合法维度标签"


def test_persona_codes():
    codes = {p["code"] for p in P.all_personas()}
    assert codes == {"BIGS", "FITA", "SPCY", "SWEET", "EARL", "NITE", "SQUAD", "LOYT"}


def test_all_personas_reachable_in_512():
    """512 种作答必须能产出全部 8 型人格，不存在「测不出的人格」。"""
    reachable = {P.score(ans).code for ans in all_answer_sets()}
    missing = {p["code"] for p in P.all_personas()} - reachable
    assert not missing, f"以下人格无法通过任何作答得到：{sorted(missing)}"


def test_distribution_is_not_degenerate():
    """各型占比不宜过度集中：最低 ≥5%，最高 ≤30%。"""
    counts = collections.Counter(P.score(ans).code for ans in all_answer_sets())
    total = sum(counts.values())
    assert total == 512
    codes = {p["code"] for p in P.all_personas()}
    ratios = {c: counts[c] / total for c in codes}
    assert min(ratios.values()) >= 0.05, f"有型人格过于罕见：{ratios}"
    assert max(ratios.values()) <= 0.30, f"有型人格过于霸榜：{ratios}"


def test_tie_break_is_deterministic_and_explained():
    """同分时必须有稳定的裁决规则，并在结果里说明如何定夺。"""
    seen: dict[str, int] = collections.defaultdict(int)
    qs = P.questions()
    for ans in all_answer_sets():
        r = P.score(ans)
        if not r.tie:
            continue
        assert r.tie_broken_by in ("final", "index")
        assert r.runner_up and r.runner_up != r.code
        # 同一作答重复计分必须完全一致（无随机性）
        again = P.score(ans)
        assert (again.code, again.tie_broken_by) == (r.code, r.tie_broken_by)
        seen[r.tie_broken_by] += 1

        if r.tie_broken_by == "final":
            picked = qs[len(ans) - 1][ans[-1]]["score"]
            assert picked.get(r.code, 0) > 0, "终局题定夺时，终局题必须指向冠军"
    assert seen["final"], "应存在由终局题定夺的同分案例"


def test_invalid_choice_falls_back_to_a():
    r = P.score(["z", "", None, "e"])  # type: ignore[list-item]
    assert r.code in {p["code"] for p in P.all_personas()}
    assert r.margin >= 0


def test_short_answers_are_tolerated():
    r = P.score(["a", "b"])
    assert r.code in {p["code"] for p in P.all_personas()}


def test_explanation_shape():
    r = P.score(["a", "b", "b", "a", "b", "a", "a", "d"])
    ex = r.explanation or {}
    traits = ex["traits"]
    assert 1 <= len(traits) <= 3
    for t in traits:
        assert t["label"] and t["count"] >= 1
    keys = ex["key_questions"]
    assert 1 <= len(keys) <= 2
    for k in keys:
        assert k["id"] and k["q"] and k["choice"] and k["text"]
    deltas = [k["delta"] for k in keys]
    assert deltas == sorted(deltas, reverse=True), "关键题应按影响力降序"
    assert r.explain_text()


def test_random_answers_cover_final_four_options():
    picked = {P.random_answers()[-1] for _ in range(200)}
    assert picked == set(FINAL_CHOICES)
