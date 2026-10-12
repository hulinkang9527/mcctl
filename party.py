"""麦麦派对策划师：主题活动场次约束求解引擎。

从「城市 → 门店 → 日期 → 场次」全链路数据中，在 **人数 / 预算 / 日期偏好 /
剩余名额 / 距离** 等硬约束下推荐最优派对方案，并按「人均成本 + 日期贴近度」
排序、给出可读理由——而不是把上百个场次选项原样堆给用户。

价格口径：``PartySession.price`` 统一为「每人价格（元）」，与官方 MCP 返回的
展示口径可能不同，真实接入时由 service 层归一化（见 MCP_INTEGRATION.md）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date
from typing import Any

from mcctl.models import PartySession, PartyStore


@dataclass
class PartyConstraints:
    """一场主题派对的约束条件。"""

    people: int = 6
    budget: float | None = None          # 总预算（元），None 不限制
    date_hint: str = ""                  # 期望日期 yyyy-MM-dd，尽力贴近
    max_distance_km: float | None = None # 门店距离上限（公里）
    want_weekend: bool | None = None     # None 不限；True 仅周末；False 仅工作日
    max_plans: int = 3                   # 返回方案数

    def __post_init__(self) -> None:
        if self.people < 1:
            raise ValueError("people 必须 ≥ 1")
        if self.budget is not None and self.budget <= 0:
            raise ValueError("budget 必须 > 0")
        if self.max_plans < 1:
            raise ValueError("max_plans 必须 ≥ 1")


@dataclass
class PartyPlan:
    """一份可执行的派对策划方案。"""

    store: PartyStore
    date: str
    session: PartySession
    people: int
    total_price: float                    # 估算总价（每人价 × 人数）
    per_person: float
    score: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "store": self.store.to_dict(),
            "date": self.date,
            "session": self.session.to_dict(),
            "people": self.people,
            "total_price": round(self.total_price, 2),
            "per_person": round(self.per_person, 2),
            "score": round(self.score, 3),
            "reasons": self.reasons,
        }


def _date_delta(a: str, b: str) -> int:
    """两个 yyyy-MM-dd 之间的天数差（无解析异常时）。"""
    try:
        d1 = _date.fromisoformat(a)
        d2 = _date.fromisoformat(b)
        return abs((d1 - d2).days)
    except ValueError:
        return 0


def _is_weekend(d: str) -> bool:
    try:
        return _date.fromisoformat(d).weekday() >= 5
    except ValueError:
        return False


def plan_party(
    stores: list[PartyStore],
    dates_by_store: dict[str, list[str]],
    sessions_by_store_date: dict[tuple[str, str], list[PartySession]],
    constraints: PartyConstraints,
) -> list[PartyPlan]:
    """在约束下搜索全部可用场次，返回按评分降序的策划方案列表。

    硬约束（不满足直接淘汰）：
      1. 门店营业中（business_status）；
      2. 距离在 max_distance_km 内；
      3. 人数落在场次 [party_min, party_max] 内；
      4. 场次还有剩余名额（left_num > 0）；
      5. 估算总价 ≤ budget；
      6. 日期满足 want_weekend（若指定）。

    软排序分（越高越靠前）：
      - 人均成本越低越好（成本分 = 1 / per_person）；
      - 日期越贴近 date_hint 越好（贴近分 = 1 / (1 + 天数差)）；
      - 周末偏好命中 +0.3；
      - 剩余名额越紧张说明越抢手，轻微加分（0.02 × min(left,5) 封顶 0.1）。
    """
    if not stores:
        return []
    plans: list[PartyPlan] = []
    today = _date.today().isoformat()

    for store in stores:
        if not store.business_status:
            continue
        if constraints.max_distance_km is not None and store.distance_km > constraints.max_distance_km:
            continue
        for d in dates_by_store.get(store.code, []):
            if d < today:
                continue  # 过期日期不可约
            if constraints.want_weekend is not None and _is_weekend(d) != constraints.want_weekend:
                continue
            for s in sessions_by_store_date.get((store.code, d), []):
                if not (s.party_min <= constraints.people <= s.party_max):
                    continue
                if s.left_num <= 0:
                    continue
                total = round(s.price * constraints.people, 2)
                if constraints.budget is not None and total > constraints.budget + 1e-6:
                    continue

                per_person = round(total / constraints.people, 2)
                cost_score = 1.0 / per_person if per_person > 0 else 0.0
                closeness = 1.0 / (1 + _date_delta(d, constraints.date_hint)) if constraints.date_hint else 0.0
                weekend_bonus = 0.3 if (constraints.want_weekend is True and _is_weekend(d)) else 0.0
                scarcity = min(0.02 * min(s.left_num, 5), 0.1)
                score = cost_score + closeness + weekend_bonus + scarcity

                reasons: list[str] = []
                if constraints.budget is not None:
                    reasons.append(f"总价 ¥{total:.2f} 在预算 ¥{constraints.budget:.0f} 内")
                reasons.append(f"人均仅 ¥{per_person:.2f}")
                if constraints.people >= s.party_min:
                    reasons.append(f"支持 {s.party_min}-{s.party_max} 人（你们 {constraints.people} 人）")
                if constraints.date_hint and _date_delta(d, constraints.date_hint) == 0:
                    reasons.append("正好命中期望日期")
                elif constraints.date_hint:
                    reasons.append(f"距期望日期仅差 {_date_delta(d, constraints.date_hint)} 天")
                if s.left_num <= 3:
                    reasons.append(f"仅剩 {s.left_num} 个名额，手慢无")
                if store.distance_m:
                    reasons.append(f"距你 {store.distance_text or f'{store.distance_km:.1f}km'}")

                plans.append(PartyPlan(
                    store=store, date=d, session=s, people=constraints.people,
                    total_price=total, per_person=per_person, score=score, reasons=reasons,
                ))

    plans.sort(key=lambda p: -p.score)
    return plans[: constraints.max_plans]


def best_plan(
    stores: list[PartyStore],
    dates_by_store: dict[str, list[str]],
    sessions_by_store_date: dict[tuple[str, str], list[PartySession]],
    constraints: PartyConstraints,
) -> PartyPlan | None:
    """返回评分最高的方案；无可行方案返回 None。"""
    plans = plan_party(stores, dates_by_store, sessions_by_store_date, constraints)
    return plans[0] if plans else None
