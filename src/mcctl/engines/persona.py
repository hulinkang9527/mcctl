"""麦麦人格引擎（McPersona）。

加载 ``data/personas.json`` 的 8 型人格与测试题，对作答计分，产出可分享的
"麦籍卡"。CLI（``mcctl whoami``）与 Web Playground 共用同一套题库与结果。
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DATA = Path(__file__).resolve().parent.parent / "data" / "personas.json"

# 答案特点维度：用于结果页解释"你为什么是这一型"
DIM_LABELS = {
    "decisive": "决策果断",
    "explore": "爱做功课",
    "efficiency": "效率优先",
    "saving": "省钱倾向",
    "classic": "经典偏好",
    "novelty": "尝鲜偏好",
    "social": "社交主导",
    "easygoing": "随和跟随",
    "adventurous": "冒险精神",
    "steady": "求稳保守",
    "indulgence": "满足优先",
    "value": "性价比优先",
    "loyal": "认准不变",
    "variety": "喜欢变化",
}

OPTIONS = ("a", "b", "c", "d")


def choices_of(q: dict[str, Any]) -> list[str]:
    """该题实际提供的选项字母（普通题 a/b，终局题 a/b/c/d）。"""
    return [k for k in OPTIONS if k in q]


@dataclass
class PersonaResult:
    code: str
    persona: dict[str, Any]
    scores: dict[str, int]
    answers: list[str]
    margin: int                      # 与第二名的分差（信心度）
    runner_up: str | None = None            # 第二候选人格代号
    runner_up_persona: dict[str, Any] | None = None
    tie: bool = False                       # 冠军是否曾出现同分
    tie_broken_by: str | None = None        # "final"（终局题裁决）/ "index"（图鉴顺序）
    explanation: dict[str, Any] | None = None

    @property
    def signature_meal(self) -> list[str]:
        return self.persona.get("signature_meal", [])

    def explain_text(self) -> list[str]:
        """结果页/终端里的「为什么是它」文案行。"""
        ex = self.explanation or {}
        out: list[str] = []
        traits = ex.get("traits") or []
        if traits:
            out.append("你的答案特点：" + "、".join(f"{t['label']}（{t['count']}）" for t in traits))
        keys = ex.get("key_questions") or []
        for k in keys:
            out.append(f"第 {k['id']} 题「{k['q']}」你选了 {k['choice'].upper()}：{k['text']}")
        if self.tie and self.runner_up:
            rp = self.runner_up_persona or {}
            how = "终局题" if self.tie_broken_by == "final" else "图鉴顺序"
            out.append(f"提示：你与 {rp.get('name', self.runner_up)}（{self.runner_up}）同分，按{how}定夺。")
        return out

    def card_text(self) -> str:
        """纯文本麦籍卡（终端 / 社交分享文案）。"""
        p = self.persona
        lines = [
            "🍔 你的麦麦人格鉴定结果 🍟",
            "------------------------------",
            f"{p['emoji']} {p['name']}（{p['code']}）",
            f"　{p['title']}",
            f"「{p['motto']}」",
            "",
            f"点餐哲学：{p['philosophy']}",
            f"本命一餐：{' + '.join(self.signature_meal) if self.signature_meal else '命运随机'}",
            f"幸运暗号：{p['lucky_code']}",
            f"人格标签：{' / '.join(p.get('traits', []))}",
        ]
        for line in self.explain_text():
            lines.append(line)
        lines += [
            "------------------------------",
            "由 mcctl · 麦门控制面 鉴定（kubectl for McDonald's）",
        ]
        return "\n".join(lines)


def load_data() -> dict[str, Any]:
    with _DATA.open("r", encoding="utf-8") as f:
        return json.load(f)


def all_personas() -> list[dict[str, Any]]:
    return load_data()["personas"]


def questions() -> list[dict[str, Any]]:
    return load_data()["questions"]


def get_persona(code: str) -> dict[str, Any] | None:
    code = code.upper()
    return next((p for p in all_personas() if p["code"] == code), None)


def score(answers: list[str]) -> PersonaResult:
    """answers: 每题选项字母（a/b，终局题可为 c/d），长度可少于总题数。

    同分裁决（确定性，可解释）：
      1. 先看终局题（最后一题且标记 ``final``）指向的人格，若在并列集合内则取之；
      2. 否则按图鉴顺序取并列中最靠前的一型。
    两种情形都会记在 ``tie_broken_by`` 上，结果页如实展示。
    """
    data = load_data()
    qs, ps = data["questions"], data["personas"]
    scores = {p["code"]: 0 for p in ps}
    picks: list[tuple[int, str, dict[str, Any]]] = []
    for i, choice in enumerate(answers):
        if i >= len(qs):
            break
        valid = choices_of(qs[i])
        ch = (choice or "a").lower()
        if ch not in valid:
            ch = "a"
        picked = qs[i][ch]["score"]
        picks.append((i, ch, picked))
        for code, pts in picked.items():
            scores[code] = scores.get(code, 0) + pts

    order = [p["code"] for p in ps]
    rank = {c: i for i, c in enumerate(order)}
    top_pts = max(scores.values())
    tied = [c for c in order if scores[c] == top_pts]
    winner = tied[0]
    tie = len(tied) > 1
    tie_broken_by = None

    if tie:
        # 规则一：终局题指向优先
        if picks:
            idx, _, picked = picks[-1]
            if qs[idx].get("final"):
                cand = [c for c in tied if picked.get(c, 0) > 0]
                if cand:
                    winner, tie_broken_by = cand[0], "final"
        # 规则二：仍无法定夺则按图鉴顺序（winner 初始值）
        if tie_broken_by is None:
            tie_broken_by = "index"

    if tie:
        runner_up = next((c for c in tied if c != winner), None)
    else:
        rest = sorted((c for c in order if c != winner), key=lambda c: (-scores[c], rank[c]))
        runner_up = rest[0] if rest else None

    second_pts = scores[runner_up] if runner_up else 0
    persona = next(p for p in ps if p["code"] == winner)
    explanation = {
        "traits": _traits(answers),
        "key_questions": _key_questions(picks, winner, runner_up),
        "top_score": top_pts,
        "runner_up_score": second_pts,
    }
    return PersonaResult(
        winner, persona, dict(scores), answers, top_pts - second_pts,
        runner_up=runner_up,
        runner_up_persona=next((p for p in ps if p["code"] == runner_up), None),
        tie=tie, tie_broken_by=tie_broken_by, explanation=explanation,
    )


def _traits(answers: list[str]) -> list[dict[str, Any]]:
    """统计各维度被选中的次数，取前 3 作为「答案特点」。"""
    qs = questions()
    counts: dict[str, int] = {}
    for i, raw in enumerate(answers):
        if i >= len(qs):
            break
        valid = choices_of(qs[i])
        ch = (raw or "a").lower()
        if ch not in valid:
            ch = "a"
        dim = qs[i][ch].get("dim")
        if dim:
            counts[dim] = counts.get(dim, 0) + 1
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"key": k, "label": DIM_LABELS.get(k, k), "count": v} for k, v in items[:3]]


def _key_questions(
    picks: list[tuple[int, str, dict[str, Any]]],
    winner: str,
    runner_up: str | None,
    top: int = 2,
) -> list[dict[str, Any]]:
    """按「对冠军的贡献 − 对亚军的贡献」找出最影响结果的两道题。"""
    qs = questions()
    scored: list[tuple[int, int, int, str]] = []  # (delta, winner_points, index, choice)
    for idx, ch, picked in picks:
        w = picked.get(winner, 0)
        r = picked.get(runner_up, 0) if runner_up else 0
        scored.append((w - r, w, idx, ch))
    scored.sort(key=lambda t: (-t[0], -t[1], t[2]))
    out = []
    for delta, wpts, idx, ch in scored[:top]:
        q = qs[idx]
        out.append({
            "id": q["id"], "q": q["q"], "choice": ch,
            "text": q[ch]["text"], "delta": delta, "winner_points": wpts,
        })
    return out


def random_answers(rng: random.Random | None = None) -> list[str]:
    """按每题实际选项数随机作答（普通题二选一、终局题四选一）。"""
    r = rng or random.Random()
    return [r.choice(choices_of(q)) for q in questions()]


def random_result(rng: random.Random | None = None) -> PersonaResult:
    return score(random_answers(rng))


def weights_of(code: str) -> dict[str, Any]:
    p = get_persona(code)
    return (p or {}).get("weights", {})
