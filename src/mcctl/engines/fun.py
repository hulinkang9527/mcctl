"""趣味玩法引擎：今日麦门运势（daily）、盲盒点餐（roll）、人格合餐（pair）。

这三个命令刻意保持"一条命令出结果、零参数也能玩"：
- ``daily`` 按当天日期做随机种子，同一天同签，方便截图分享；
- ``roll`` 真随机，从当前菜单里抽一套主食+小食+饮品，专治选择困难；
- ``pair`` 两人格合餐：把两个人格的本命餐合并去重，给出"双人分享装"。
"""
from __future__ import annotations

import random
from datetime import date as _date
from typing import Any

from mcctl.engines import persona as P
from mcctl.service import McD

# 今日宜 / 忌 / 箴言：围绕麦门 + 程序员趣味，便于截图分享
GOOD_LUCK = [
    "点经典不纠结", "加一份小食", "出门先领券", "堂食趁热", "和朋友拼分享装",
    "板烧去酱", "零度可乐配一切", "凑满减再下单", "外送准时点", "麦乐鸡蘸两酱",
    "今天的命定套餐值得加一份薯饼", "得来速不停车",
]
BAD_LUCK = [
    "空腹刷菜单", "冲动加单", "麦辣配甜饮", "纠结超过三分钟",
    "点超预算还嘴硬", "薯条放凉", "为了满减硬凑不爱吃的", "把麦乐鸡分给别人",
    "可乐去冰", "边剪视频边点餐（必多加小食）",
]
QUOTES = [
    "人生就像巨无霸，层次要够。",
    "薯条要趁热，机会要趁早。",
    "减肥从下一顿开始，这顿先吃完。",
    "麦门不保佑纠结的人。",
    "你点的不是套餐，是今天的确定性。",
    "面包会有的，可乐也会有的。",
    "选择困难的时候，就交给骰子。",
    "每一单都值得被认真对待。",
    "今天的热量，是明天的蛋白质。",
    "别问吃什么，问就是麦麦人格说了算。",
]


def fortune(day: str | None = None) -> dict[str, Any]:
    """今日麦门运势。同一天同签（以日期为种子）。"""
    day = day or _date.today().isoformat()
    rng = random.Random(f"mcctl-daily::{day}")
    personas = P.all_personas()
    p = rng.choice(personas)
    return {
        "date": day,
        "persona": p,
        "good": rng.choice(GOOD_LUCK),
        "bad": rng.choice(BAD_LUCK),
        "quote": rng.choice(QUOTES),
        "lucky_number": rng.randint(1, 99),
        "lucky_code": p.get("lucky_code", ""),
    }


async def roll(mcd: McD) -> dict[str, Any]:
    """盲盒点餐：从当前菜单真随机抽一套主食 + 小食 + 饮品。"""
    meals = await mcd.meals("regular")
    mains = [m for m in meals if m.category == "主食"]
    sides = [m for m in meals if m.category == "小食"]
    drinks = [m for m in meals if m.category == "饮品"]
    rng = random.Random()
    main = rng.choice(mains) if mains else None
    side = rng.choice(sides) if sides else None
    drink = rng.choice(drinks) if drinks else None

    items = [m for m in (main, side, drink) if m is not None]
    return {
        "items": [m.to_dict() for m in items],
        "kcal": round(sum(m.energy_kcal for m in items), 1),
        "protein_g": round(sum(m.protein_g for m in items), 1),
        "price": round(sum(m.price for m in items), 2),
        "mood": rng.choice([
            "今天这盲盒，香。", "闭眼点的，往往最对。", "骰子说你值得这一套。",
            "这套配得离谱地合理。", "不纠结，直接冲。",
        ]),
    }


# 人格合餐评语：按两人本命餐重叠度分档
PAIR_VERDICT = {
    "soul": [
        "天生一对，连口味都像。", "你们共享的不是食物，是灵魂。", "这俩人，直接上双份。",
    ],
    "ally": [
        "有点像，但各有坚持——正好一人一半。", "能吃到一起，也能让到一起。",
        "口味有交集，分享装最合适。",
    ],
    "contrast": [
        "完全不同，谁也不抢谁的。", "一个要辣一个要甜，凑成一顿完整的。",
        "正好各点各的，谁也不亏。",
    ],
}


async def pair(mcd: McD, code_a: str, code_b: str) -> dict[str, Any]:
    """人格合餐：把两个人格的本命餐合并去重，作为双人分享装。"""
    pa = P.get_persona(code_a)
    pb = P.get_persona(code_b)
    if pa is None or pb is None:
        raise ValueError(f"未知人格代号：{code_a if pa is None else code_b}")

    meals_a = list(pa.get("signature_meal", []))
    meals_b = list(pb.get("signature_meal", []))
    overlap = sorted(set(meals_a) & set(meals_b))

    seen: set[str] = set()
    merged: list[str] = []
    for c in meals_a + meals_b:
        if c not in seen:
            seen.add(c)
            merged.append(c)

    lines = []
    total_kcal = total_protein = 0.0
    total_price = 0.0
    for c in merged:
        m = await mcd.meal(c)
        if m is None:
            continue
        qty = 2 if c in overlap else 1
        lines.append({"code": m.code, "name": m.name, "category": m.category,
                      "qty": qty, "unit_price": m.price, "line_total": round(m.price * qty, 2),
                      "kcal_each": m.energy_kcal})
        total_kcal += m.energy_kcal * qty
        total_protein += m.protein_g * qty
        total_price += m.price * qty

    if len(overlap) >= 2:
        tier = "soul"
    elif len(overlap) == 1:
        tier = "ally"
    else:
        tier = "contrast"
    verdict = random.Random(f"mcctl-pair::{pa['code']}::{pb['code']}").choice(PAIR_VERDICT[tier])

    return {
        "persona_a": pa,
        "persona_b": pb,
        "overlap": overlap,
        "lines": lines,
        "tier": tier,
        "verdict": verdict,
        "people": 2,
        "total_kcal": round(total_kcal, 1),
        "protein_g": round(total_protein, 1),
        "total_price": round(total_price, 2),
        "per_person_price": round(total_price / 2, 2),
        "per_person_kcal": round(total_kcal / 2, 1),
    }
