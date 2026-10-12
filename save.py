"""省钱引擎：一键领券 → 门槛校验 → 最优券选择 → 智能凑单 → 到手价。

编排 MCP 工具：available-coupons / auto-bind-coupons / query-my-coupons /
list-nutrition-foods(取餐品价格) / calculate-price，给出"直接用券"与
"凑单后用券"两种方案的实付对比，并明确每一步省了多少钱。
"""
from __future__ import annotations

from typing import Any

from mcctl.models import Coupon, Meal, PriceBreakdown
from mcctl.service import McD


def _bd_dict(bd: PriceBreakdown) -> dict[str, Any]:
    return bd.to_dict()


def best_direct_coupon(coupons: list[Coupon], subtotal: float) -> tuple[Coupon | None, float]:
    """在不凑单的情况下，返回对当前小计优惠最大的券。"""
    best, saving = None, 0.0
    for c in coupons:
        d = c.discount_on(subtotal)
        if d > saving:
            best, saving = c, d
    return best, round(saving, 2)


def _cheapest_topup(meals: list[Meal], gap: float) -> Meal | None:
    """找一份价格不低于 gap 的最便宜小件（小食/甜点/饮品）用于凑单。"""
    cands = [m for m in meals if m.category in ("小食", "甜点", "饮品") and m.price >= gap - 1e-6]
    return min(cands, key=lambda m: m.price, default=None)


async def save_flow(
    mcd: McD,
    cart: list[dict[str, Any]],
    *,
    channel: str = "到店取餐",
    store_id: str = "ST_NJDL",
) -> dict[str, Any]:
    steps: list[str] = []

    # 1) 一键领券
    bind = await mcd.auto_bind()
    claimed = bind.get("claimed_count", 0) if isinstance(bind, dict) else 0
    steps.append(f"① 麦麦省一键领券：自动领取 {claimed} 张当前可领优惠券（auto-bind-coupons）")
    coupons = await mcd.my_coupons()

    # 2) 无券基线价
    base = await mcd.calc_price(cart, channel, [], store_id)
    steps.append(f"② 计算无券基线价：商品 ¥{base.subtotal:.2f}，配送费 ¥{base.delivery_fee:.2f}，"
                 f"应付 ¥{base.total:.2f}（calculate-price）")

    meals = await mcd.meals("regular")
    recommendation = "none"
    final_cart, final_bd = list(cart), base
    direct_info = topup_info = None

    # 3) 直接用券（枚举每张券取实付最低）
    best_bd, best_c = base, None
    for c in coupons:
        if c.kind == "gift":
            continue
        bd = await mcd.calc_price(cart, channel, [c.coupon_id], store_id)
        if bd.total < best_bd.total - 1e-6:
            best_bd, best_c = bd, c
    if best_c and best_bd.total < base.total - 1e-6:
        saved = round(base.total - best_bd.total, 2)
        direct_info = {"coupon": best_c.to_dict(), "breakdown": _bd_dict(best_bd), "saved": saved}
        steps.append(f"③ 直接用券最优：「{best_c.title}」实付 ¥{best_bd.total:.2f}，立省 ¥{saved:.2f}")
        recommendation, final_bd, final_cart = "direct", best_bd, list(cart)
    else:
        steps.append("③ 当前购物车暂无可直接使用的满减券")

    # 4) 凑单后用券（含"满39免外送费"门槛）
    topup_candidates: list[dict[str, Any]] = []
    thresholds: list[tuple[str, float, Coupon | None]] = []
    for c in coupons:
        if c.kind in ("cash", "discount") and base.subtotal < c.threshold:
            thresholds.append(("coupon", c.threshold, c))
    if channel == "麦乐送" and base.delivery_fee > 0:
        thresholds.append(("shipping", 39.0, None))

    for kind, threshold, c in thresholds:
        gap = round(threshold - base.subtotal, 2)
        if gap <= 0 or gap > 16:  # 凑单超过 16 元通常不划算，不推荐
            continue
        add = _cheapest_topup(meals, gap)
        if not add:
            continue
        new_cart = list(cart) + [{"code": add.code, "qty": 1}]
        cids = [c.coupon_id] if c else []
        bd2 = await mcd.calc_price(new_cart, channel, cids, store_id)
        extra_cost = round(bd2.total - base.total, 2)
        gained = (c.amount if c and c.kind == "cash" else 0) + (9.0 if kind == "shipping" else 0)
        net_gain = round(add.price - extra_cost, 2)  # 多得商品的隐含价值口径
        # 划算判定：凑单后多花的钱 < 凑单品价格（相当于折扣买下），且实付增量合理
        if extra_cost < add.price - 1e-6:
            topup_candidates.append({
                "kind": kind, "add": add.to_dict(), "coupon": c.to_dict() if c else None,
                "breakdown": _bd_dict(bd2), "extra_cost": extra_cost,
                "saved_vs_base": round(base.total - bd2.total, 2),
                "net_gain": net_gain, "new_cart": new_cart,
                "reason": (f"再加 ¥{add.price:.0f} 的「{add.name}」跨过 ¥{threshold:g} 门槛，"
                           + (f"用券减 ¥{c.amount:g}" if c else "免 ¥9 外送费")
                           + f"，实际仅多付 ¥{extra_cost:.2f}"),
            })
    if topup_candidates:
        top = min(topup_candidates, key=lambda x: x["breakdown"]["total"])
        topup_info = {k: v for k, v in top.items() if k != "new_cart"}
        steps.append("④ 凑单方案：" + top["reason"] + f"，凑单后实付 ¥{top['breakdown']['total']:.2f}")
        # 凑单方案与直用券取实付更低者为最终推荐
        if recommendation == "none" or top["breakdown"]["total"] <= final_bd.total + 1e-6:
            recommendation, final_bd, final_cart = "topup", PriceBreakdown(**{
                k: top["breakdown"][k] for k in
                ("subtotal", "delivery_fee", "discount", "total", "applied_coupons", "lines")
            }), top["new_cart"]
    else:
        steps.append("④ 凑单检测：当前无需凑单（或凑单不划算）")

    total_saved = round(base.total - final_bd.total, 2)
    saved_pct = round(total_saved / base.total * 100, 1) if base.total else 0.0
    if recommendation == "topup" and total_saved < 0:
        # 凑单是"多买多得"，实付可能略高但更划算，此时节省按获得商品价值口径说明
        total_saved = 0.0
    return {
        "channel": channel,
        "claimed_count": claimed,
        "base": _bd_dict(base),
        "direct": direct_info,
        "topup": topup_info,
        "recommendation": recommendation,
        "final_cart": final_cart,
        "final": _bd_dict(final_bd),
        "total_saved": total_saved,
        "saved_pct": saved_pct,
        "steps": steps,
    }
