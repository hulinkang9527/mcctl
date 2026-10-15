"""人格决策引擎：把"麦麦人格"翻译成配餐约束，再交给组合优化求解。

``decide`` 是最省心的入口——不用懂热量、不用翻菜单、不用研究券，
告诉它"几个人、什么场景/预算"，它按你的人格直接给出命定套餐与理由。
"""
from __future__ import annotations

import random
from typing import Any

from mcctl.engines import persona as P
from mcctl.engines.diet import MealConstraints, Plan, optimize_meal
from mcctl.service import McD


def weights_to_constraints(
    weights: dict[str, Any],
    *,
    period: str,
    people: int,
    budget: float | None,
    kcal: float | None,
    protein: float | None,
    no_spicy: bool,
    prefer_tags: list[str] | None = None,
    signature_codes: list[str] | None = None,
) -> MealConstraints:
    kcal_pref = weights.get("kcal", "mid")
    c = MealConstraints(period=period, people=people, weights=weights, budget_total=budget,
                        prefer_tags=prefer_tags or [], signature_codes=signature_codes or [])
    c.allow_spicy = not no_spicy
    c.with_dessert = bool(weights.get("sweet"))
    c.prefer_healthy_drink = kcal_pref == "low" or bool(weights.get("protein_first"))

    if kcal is not None:
        c.max_kcal = float(kcal)
        c.target_kcal = float(kcal) * 0.92
    elif kcal_pref == "low":
        c.max_kcal = 620.0
        c.target_kcal = 560.0
    elif kcal_pref == "high":
        c.target_kcal = 900.0
    else:
        c.target_kcal = 760.0

    if protein is not None:
        c.min_protein = float(protein)
    elif weights.get("protein_first"):
        c.min_protein = 34.0 if kcal_pref != "low" else 30.0
    return c


async def resolve_persona(
    mcd: McD,
    *,
    persona_code: str | None = None,
    answers: list[str] | None = None,
    wild: bool = False,
) -> tuple[dict[str, Any], P.PersonaResult | None]:
    """返回 (persona_dict, PersonaResult|None)。"""
    if answers:
        res = P.score(answers)
        return res.persona, res
    if persona_code:
        p = P.get_persona(persona_code)
        if p:
            return p, None
    if wild:
        res = P.random_result()
        return res.persona, res
    # 默认：巨无霸本霸（最不会出错的经典决策）
    return P.get_persona("BIGS"), None  # type: ignore[return-value]


async def decide(
    mcd: McD,
    *,
    persona_code: str | None = None,
    answers: list[str] | None = None,
    wild: bool = False,
    people: int = 1,
    budget: float | None = None,
    kcal: float | None = None,
    protein: float | None = None,
    period: str | None = None,
    no_spicy: bool = False,
    top_k: int = 3,
) -> dict[str, Any]:
    persona, presult = await resolve_persona(mcd, persona_code=persona_code, answers=answers, wild=wild)

    # 真实时段来自 MCP now-time-info；早餐只在早餐时段售卖
    if period is None:
        try:
            now = await mcd.now()
            period = "breakfast" if now.get("period") == "breakfast" else "regular"
        except Exception:
            period = "regular"

    constraints = weights_to_constraints(
        persona.get("weights", {}), period=period, people=people,
        budget=budget, kcal=kcal, protein=protein, no_spicy=no_spicy,
        prefer_tags=persona.get("prefer_tags", []),
        signature_codes=persona.get("signature_meal", []),
    )
    meals = await mcd.meals(period)
    plans = optimize_meal(meals, constraints, top_k=top_k)
    for i, p in enumerate(plans):
        p.persona_code = persona["code"]
        # 仅最优方案带人格口号，次优/第三方案保持简洁
        _persona_reasons(p, persona, with_head=(i == 0))

    return {
        "persona": persona,
        "persona_result": presult,
        "period": period,
        "people": people,
        "constraints": {
            "target_kcal": constraints.target_kcal, "max_kcal": constraints.max_kcal,
            "min_protein": constraints.min_protein, "budget_total": budget,
        },
        "plans": [p.to_dict() for p in plans],
        "best": plans[0].to_dict() if plans else None,
    }


def _persona_reasons(plan: Plan, persona: dict[str, Any], *, with_head: bool = True) -> None:
    if with_head:
        head = f"{persona['emoji']} {persona['name']}的命定套餐：{persona['motto']}"
        plan.reasons = [head] + plan.reasons
