"""控卡配餐与组合优化引擎。

在（官方 MCP 返回的）真实可售餐品中做"主食 + 小食 + 饮品 (+甜点)"的
组合搜索，在热量 / 三大营养素 / 预算 / 口味等硬约束下，按人格偏好打分排序，
而非简单地把单品丢给用户自己选。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any

from mcctl.models import Meal


@dataclass
class MealConstraints:
    """一餐的约束（人均口径：热量/预算均按人数摊）。"""

    period: str = "regular"            # breakfast / regular
    people: int = 1
    target_kcal: float | None = None   # 人均目标热量
    max_kcal: float | None = None      # 人均热量上限（硬约束）
    min_protein: float | None = None   # 人均蛋白质下限(g)
    budget_total: float | None = None  # 整单总预算(元)
    allow_spicy: bool = True
    with_side: bool = True
    with_drink: bool = True
    with_dessert: bool = False
    prefer_healthy_drink: bool = False # 水/黑咖/零度/牛奶
    weights: dict[str, Any] = field(default_factory=dict)
    prefer_tags: list[str] = field(default_factory=list)   # 人格偏好的餐品标签
    signature_codes: list[str] = field(default_factory=list)  # 人格本命餐 code


@dataclass
class PlanLine:
    meal: Meal
    qty: int = 1


@dataclass
class Plan:
    label: str
    lines: list[PlanLine]
    people: int
    score: float
    score_detail: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    persona_code: str = ""

    @property
    def cart(self) -> list[dict[str, Any]]:
        return [{"code": ln.meal.code, "name": ln.meal.name, "qty": ln.qty,
                 "unit_price": ln.meal.price} for ln in self.lines if ln.qty > 0]

    @property
    def subtotal(self) -> float:
        return round(sum(ln.meal.price * ln.qty for ln in self.lines), 2)

    def _sum(self, attr: str) -> float:
        return round(sum(getattr(ln.meal, attr) * ln.qty for ln in self.lines), 1)

    @property
    def kcal_total(self) -> float:
        return self._sum("energy_kcal")

    @property
    def protein_total(self) -> float:
        return self._sum("protein_g")

    @property
    def fat_total(self) -> float:
        return self._sum("fat_g")

    @property
    def carbs_total(self) -> float:
        return self._sum("carbs_g")

    @property
    def sodium_total(self) -> float:
        return self._sum("sodium_mg")

    @property
    def per_kcal(self) -> float:
        return round(self.kcal_total / self.people, 0)

    @property
    def per_protein(self) -> float:
        return round(self.protein_total / self.people, 1)

    @property
    def per_price(self) -> float:
        return round(self.subtotal / self.people, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "persona_code": self.persona_code,
            "people": self.people,
            "cart": self.cart,
            "nutrition_total": {
                "energy_kcal": self.kcal_total, "protein_g": self.protein_total,
                "fat_g": self.fat_total, "carbs_g": self.carbs_total,
                "sodium_mg": self.sodium_total,
            },
            "per_person": {"kcal": self.per_kcal, "protein_g": self.per_protein,
                           "price": self.per_price},
            "subtotal": self.subtotal,
            "score": round(self.score, 1),
            "reasons": self.reasons,
        }


_HEALTHY_DRINK = {"DRK_WATER", "DRK_AMERICANO", "BP_COFFEE", "DRK_COLA_ZERO", "DRK_MILK"}
_SWEET_DRINK = {"DRK_COLA_M", "DRK_SPRITE", "DRK_ICED_TEA", "DRK_ORANGE"}


def _slot_candidates(meals: list[Meal], c: MealConstraints) -> dict[str, list[Meal | None]]:
    if c.period == "breakfast":
        mains = [m for m in meals if m.category == "早餐"]
        sides = [None] + [m for m in meals if m.category == "早餐" and ("薯饼" in m.name)]
        drinks = [None] + [m for m in meals if m.category == "饮品"]
        return {"main": mains, "side": sides, "drink": drinks, "dessert": [None]}
    mains = [m for m in meals if m.category == "主食"]
    sides = [None] + ([m for m in meals if m.category == "小食"] if c.with_side else [])
    drinks = [None] + ([m for m in meals if m.category == "饮品"] if c.with_drink else [])
    desserts = [None] + ([m for m in meals if m.category == "甜点"] if c.with_dessert else [])
    if not c.allow_spicy:
        mains = [m for m in mains if "辣" not in "".join(m.tags)]
        sides = [m for m in sides if m is None or "辣" not in "".join(m.tags)]
    return {"main": mains, "drink": drinks, "side": sides, "dessert": desserts}


def _aggregate(template: list[Meal], c: MealConstraints, meals: list[Meal]) -> list[PlanLine]:
    """把单人模板按人数展开，并按社交/性价比追加分享装。"""
    qty: dict[str, int] = {}
    for m in template:
        qty[m.code] = qty.get(m.code, 0) + c.people
    w = c.weights or {}
    social = float(w.get("social", 0.2) or 0.2)
    value = float(w.get("value", 0.2) or 0.2)
    by_code = {m.code: m for m in meals}
    # 多人 + 社交/省钱倾向：用分享装替换/加购
    if c.people >= 2 and (social >= 0.6 or value >= 0.6):
        share = "SIDE_NUGGETS_10" if social >= value else "SIDE_FRIES_L"
        if share in by_code:
            extra = max(1, c.people // 3)
            qty[share] = qty.get(share, 0) + extra
    return [PlanLine(by_code[code], q) for code, q in qty.items() if q > 0 and code in by_code]


def _score(lines: list[PlanLine], c: MealConstraints) -> tuple[float, dict[str, float], list[str]]:
    w = c.weights or {}
    kcal_pref = w.get("kcal", "mid")
    people = max(1, c.people)
    per_kcal = sum(l.meal.energy_kcal * l.qty for l in lines) / people
    per_protein = sum(l.meal.protein_g * l.qty for l in lines) / people
    per_fat = sum(l.meal.fat_g * l.qty for l in lines) / people
    per_sodium = sum(l.meal.sodium_mg * l.qty for l in lines) / people
    per_price = sum(l.meal.price * l.qty for l in lines) / people
    all_meals = [l.meal for l in lines]
    tags = "".join("".join(m.tags) for m in all_meals)
    codes = {m.code for m in all_meals}
    cats = {m.category for m in all_meals}

    detail: dict[str, float] = {}
    score = 100.0

    # 控卡模式（有热量上限）：不奖励"吃满上限"，而是不超即可、高蛋白优先；
    # 非控卡模式：奖励热量贴近目标（吃饱但不浪费）。
    cutting = c.max_kcal is not None or kcal_pref == "low"
    if cutting:
        cap = c.max_kcal or 620.0
        over = max(0.0, per_kcal - cap * 0.98)
        detail["热量控制"] = -round(over / cap * 60, 1)
    else:
        target = c.target_kcal or {"low": 550, "mid": 760, "high": 900}.get(kcal_pref, 760)
        detail["热量贴合"] = -round(abs(per_kcal - target) / target * 45, 1)
    score += detail.get("热量控制", detail.get("热量贴合", 0.0))

    # 蛋白质
    if cutting:
        protein_pts = round(min(14, per_protein * 0.45), 1)
        if c.min_protein is not None:
            protein_pts -= round(max(0.0, c.min_protein - per_protein) * 1.6, 1)
        detail["高蛋白偏好"] = protein_pts
    elif c.min_protein is not None:
        gap = max(0.0, c.min_protein - per_protein)
        detail["蛋白达标"] = -round(gap * 1.3, 1)
    elif w.get("protein_first"):
        detail["高蛋白偏好"] = round(min(10, per_protein * 0.25), 1)
    else:
        detail["蛋白达标"] = 0.0
    score += detail.get("高蛋白偏好", detail.get("蛋白达标", 0.0))

    # 健康惩罚（控卡模式阈值更严格）
    if cutting:
        detail["脂肪控制"] = -round(max(0.0, per_fat - 18) * 0.6, 1)
        if per_sodium > 1500:
            detail["钠偏高"] = -round((per_sodium - 1500) / 150 * 1.6, 1)
        elif per_sodium > 900:
            detail["钠偏高"] = -round((per_sodium - 900) / 400 * 1.6, 1)
        else:
            detail["钠偏高"] = 0.0
    else:
        health_boost = 0.7
        if per_sodium > 2000:
            detail["钠偏高"] = -round((per_sodium - 2000) / 150 * health_boost, 1)
        elif per_sodium > 1100:
            detail["钠偏高"] = -round((per_sodium - 1100) / 400 * health_boost, 1)
        else:
            detail["钠偏高"] = 0.0
        detail["脂肪控制"] = 0.0
    score += detail["钠偏高"] + detail["脂肪控制"]

    # 人格 / 口味偏好
    if w.get("spicy") and ("辣" in tags):
        detail["嗜辣匹配"] = 12.0
    if w.get("sweet"):
        detail["甜品满足"] = 12.0 if "甜点" in cats else -4.0
    if float(w.get("novelty", 0) or 0) >= 0.8 and ("新品" in tags or "限定" in tags):
        detail["猎奇新品"] = 8.0
    if float(w.get("value", 0) or 0) >= 0.8:
        detail["性价比"] = round(min(12, max(-6, (38 - per_price) * 0.5)), 1)
    if kcal_pref == "high":
        detail["管饱程度"] = -round(abs(per_kcal - 880) / 880 * 18, 1)
    if w.get("breakfast") and (codes & {"BP_COFFEE", "BP_LATTE", "DRK_AMERICANO"}):
        detail["早餐咖啡"] = 5.0
    if c.prefer_healthy_drink or kcal_pref == "low":
        if codes & _HEALTHY_DRINK:
            detail["饮品健康"] = 8.0
        if codes & _SWEET_DRINK:
            detail["饮品健康"] = -10.0
    # 搭配完整度
    if "主食" in cats and "小食" in cats and "饮品" in cats:
        detail["搭配完整"] = 6.0
    elif c.period == "breakfast" and (codes & {"BP_COFFEE", "BP_LATTE", "DRK_AMERICANO"}):
        detail["搭配完整"] = 5.0
    else:
        detail["搭配完整"] = 0.0

    # 本命餐 / 人格标签偏好（让结果更有辨识度与情感共鸣）
    main_codes = {l.meal.code for l in lines if l.meal.category in ("主食", "早餐")}
    sig = set(c.signature_codes)
    if main_codes & sig:
        detail["本命主餐"] = 10.0
    sig_other = (codes & sig) - main_codes
    if sig_other:
        detail["本命搭配"] = 4.0 * len(sig_other)
    hit_tags = {t for t in c.prefer_tags if t in tags}
    if hit_tags:
        detail["偏好标签"] = round(2.5 * len(hit_tags), 1)
    if w.get("sweet") and ("甜点" in cats) and (codes & _SWEET_DRINK):
        detail["快乐加倍"] = 6.0

    score += sum(v for k, v in detail.items() if k not in
                 ("热量贴合", "热量控制", "蛋白达标", "高蛋白偏好", "钠偏高", "脂肪控制"))

    reasons = [
        f"人均约 {int(per_kcal)} kcal、蛋白质 {per_protein:.0f} g，人均 ¥{per_price:.1f}",
    ]
    if c.min_protein and per_protein >= c.min_protein:
        reasons.append(f"蛋白质 {per_protein:.0f}g 达标（目标 ≥{c.min_protein:g}g）")
    if "辣" in tags:
        reasons.append("含辣味单品，够上头")
    if "甜点" in cats:
        reasons.append("安排了甜品，快乐拉满")
    if "新品" in tags or "限定" in tags:
        reasons.append("含新品/限定，尝鲜优先")
    if codes & _HEALTHY_DRINK and (c.prefer_healthy_drink or kcal_pref == "low"):
        reasons.append("饮品选了低糖/无糖，控卡更稳")
    if c.people >= 2 and (float(w.get("social", 0)) >= 0.6 or float(w.get("value", 0)) >= 0.6):
        reasons.append("多人份加入分享装，摊薄单价更划算")
    return round(score, 1), detail, reasons


def optimize_meal(meals: list[Meal], c: MealConstraints, top_k: int = 3) -> list[Plan]:
    """组合搜索 + 打分排序，返回 top_k 个 Plan。"""
    slots = _slot_candidates(meals, c)
    if not slots["main"]:
        return []
    per_budget = (c.budget_total / c.people) if c.budget_total else None

    candidates: list[Plan] = []
    for main, side, drink, dessert in product(slots["main"], slots["side"], slots["drink"], slots["dessert"]):
        template = [x for x in (main, side, drink, dessert) if x is not None]
        lines = _aggregate(template, c, meals)
        per_kcal = sum(l.meal.energy_kcal * l.qty for l in lines) / c.people
        per_price = sum(l.meal.price * l.qty for l in lines) / c.people
        if c.max_kcal and per_kcal > c.max_kcal + 1e-6:
            continue
        if per_budget and per_price > per_budget + 1e-6:
            continue
        s, detail, reasons = _score(lines, c)
        candidates.append(Plan("待定", lines, c.people, s, detail, reasons))

    # 严格过滤后过少则放宽 12% 兜底
    if len(candidates) < top_k:
        for main, side, drink, dessert in product(slots["main"], slots["side"], slots["drink"], slots["dessert"]):
            template = [x for x in (main, side, drink, dessert) if x is not None]
            lines = _aggregate(template, c, meals)
            per_kcal = sum(l.meal.energy_kcal * l.qty for l in lines) / c.people
            per_price = sum(l.meal.price * l.qty for l in lines) / c.people
            if c.max_kcal and per_kcal > c.max_kcal * 1.12:
                continue
            if per_budget and per_price > per_budget * 1.12:
                continue
            s, detail, reasons = _score(lines, c)
            candidates.append(Plan("待定（接近约束）", lines, c.people, s, detail, reasons))

    # 去重（按餐篮签名）
    uniq: dict[str, Plan] = {}
    for p in sorted(candidates, key=lambda x: -x.score):
        sig = ",".join(sorted(f"{l.meal.code}:{l.qty}" for l in p.lines))
        if sig not in uniq:
            uniq[sig] = p
    ranked = list(uniq.values())[:top_k]
    for i, p in enumerate(ranked):
        p.label = ["最优解", "次优解", "第三选择"][i] if i < 3 else f"方案{i+1}"
    return ranked
