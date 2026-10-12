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


@dataclass
class PersonaResult:
    code: str
    persona: dict[str, Any]
    scores: dict[str, int]
    answers: list[str]
    margin: int                      # 与第二名的分差（信心度）

    @property
    def signature_meal(self) -> list[str]:
        return self.persona.get("signature_meal", [])

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
    """answers: 每题 'a' 或 'b'，长度可少于总题数（按已答计分）。"""
    data = load_data()
    qs, ps = data["questions"], data["personas"]
    scores = {p["code"]: 0 for p in ps}
    for i, choice in enumerate(answers):
        if i >= len(qs):
            break
        choice = (choice or "a").lower()
        picked = qs[i][choice if choice in ("a", "b") else "a"]["score"]
        for code, pts in picked.items():
            scores[code] = scores.get(code, 0) + pts
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], [p["code"] for p in ps].index(kv[0])))
    top_code, top_pts = ordered[0]
    second_pts = ordered[1][1] if len(ordered) > 1 else 0
    persona = next(p for p in ps if p["code"] == top_code)
    return PersonaResult(top_code, persona, dict(scores), answers, top_pts - second_pts)


def random_result(rng: random.Random | None = None) -> PersonaResult:
    r = rng or random.Random()
    return score([r.choice(["a", "b"]) for _ in questions()])


def weights_of(code: str) -> dict[str, Any]:
    p = get_persona(code)
    return (p or {}).get("weights", {})
