"""配餐 / 决策引擎测试。"""
import asyncio

import pytest

from mcctl import mock_data as D
from mcctl.engines.decide import decide
from mcctl.engines.diet import MealConstraints, optimize_meal
from mcctl.mock_client import MockMCPClient
from mcctl.service import McD


def _mcd() -> McD:
    return McD(MockMCPClient(seed=1), "mock")


def _run(coro):
    return asyncio.run(coro)


def test_cutting_constraints_respected():
    """控卡模式：方案不得显著超出热量上限，且最优解命中板烧（FITA 本命）。"""
    meals = D.meals_for_period("regular")
    c = MealConstraints(period="regular", people=1, max_kcal=620, target_kcal=560,
                        min_protein=28, prefer_healthy_drink=True,
                        weights={"kcal": "low", "protein_first": True},
                        prefer_tags=["高蛋白", "低脂", "低卡", "健康"],
                        signature_codes=["BUR_BANSHAO", "SIDE_APPLE", "DRK_WATER"])
    plans = optimize_meal(meals, c, top_k=5)
    assert plans
    for p in plans:
        assert p.per_kcal <= 620 * 1.12            # 最多吃到兜底放宽
    codes = {l.meal.code for l in plans[0].lines}
    assert "BUR_BANSHAO" in codes                  # 最优解是板烧
    assert plans[0].per_protein >= 28 * 0.9


def test_budget_is_hard_constraint():
    meals = D.meals_for_period("regular")
    c = MealConstraints(period="regular", people=1, budget_total=30,
                        weights={"kcal": "mid", "value": 0.95},
                        signature_codes=["BUR_DOUBLE_CHEESE"])
    plans = optimize_meal(meals, c, top_k=5)
    assert plans
    assert plans[0].per_price <= 30 * 1.12


def test_breakfast_only_serves_breakfast():
    meals = D.meals_for_period("breakfast")
    c = MealConstraints(period="breakfast", people=1, weights={"kcal": "mid", "breakfast": True})
    plans = optimize_meal(meals, c, top_k=3)
    assert plans
    for l in plans[0].lines:
        assert l.meal.period in ("breakfast", "all")


def test_all_personas_produce_valid_combo():
    async def go():
        mcd = _mcd()
        # 固定 regular 时段：本命餐均为常规菜单（EARL 早餐单独覆盖），避免依赖真实时钟时段
        for code in ["BIGS", "FITA", "SPCY", "SWEET", "NITE", "SQUAD", "LOYT"]:
            res = await decide(mcd, persona_code=code, people=2 if code == "SQUAD" else 1, period="regular")
            best = res["best"]
            assert best is not None, f"{code} 没有产出套餐"
            assert best["cart"], f"{code} 餐篮为空"
            sig = set(res["persona"]["signature_meal"])
            got = {x["code"] for x in best["cart"]}
            assert got & sig, f"{code} 未命中本命餐"
    _run(go())


def test_earl_breakfast_persona():
    async def go():
        mcd = _mcd()
        res = await decide(mcd, persona_code="EARL", period="breakfast")
        codes = {x["code"] for x in res["best"]["cart"]}
        assert codes & {"BP_SAUSAGE_EGG", "BP_SAUSAGE_MCFEN", "BP_EGG_MCFEN"}
    _run(go())


def test_no_spicy_filter():
    meals = D.meals_for_period("regular")
    c = MealConstraints(period="regular", allow_spicy=False, weights={"kcal": "mid"})
    plans = optimize_meal(meals, c, top_k=5)
    for l in plans[0].lines:
        assert "辣" not in "".join(l.meal.tags)
