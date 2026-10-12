"""麦麦派对策划师：场次约束求解引擎单测。

覆盖：硬约束（人数范围 / 预算 / 名额 / 距离 / 营业状态 / 周末偏好 / 过期日期）
与软排序（人均成本、日期贴近度、稀缺性加分）的正确性。
"""
from __future__ import annotations

from datetime import date, timedelta

from mcctl.engines.party import PartyConstraints, PartyPlan, plan_party
from mcctl.models import PartySession, PartyStore


def _d(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _store(code: str, distance_m: int = 1000, open: bool = True) -> PartyStore:
    return PartyStore(code=code, name=f"{code}餐厅", distance_m=distance_m,
                      distance_text=f"{distance_m/1000:.1f}km", business_status=open)


def _session(sid: int, pmin: int, pmax: int, price_yuan: float,
             left: int = 5, start: str = "10:30", end: str = "12:00") -> PartySession:
    return PartySession(id=sid, time_start=start, time_end=end,
                        party_min=pmin, party_max=pmax, price=price_yuan, left_num=left)


def _fixture() -> tuple[list[PartyStore], dict[str, list[str]], dict[tuple[str, str], list[PartySession]]]:
    s1 = _store("S1", 1000)          # 近
    s2 = _store("S2", 8000, open=False)  # 远且打烊
    s3 = _store("S3", 3000)          # 中距离
    stores = [s1, s2, s3]
    d1, d2 = _d(5), _d(12)           # 一个近日期一个远日期
    dates = {s1.code: [d1, d2], s2.code: [d1], s3.code: [d1, d2]}
    sessions = {
        (s1.code, d1): [
            _session(101, 4, 10, 88, left=5),   # 命中人数、预算内
            _session(102, 4, 10, 130, left=5),  # 超预算
            _session(103, 2, 3, 60, left=5),    # 人数超上限
        ],
        (s1.code, d2): [
            _session(104, 4, 10, 68, left=0),   # 无名额
        ],
        (s2.code, d1): [
            _session(201, 1, 20, 50, left=9),   # 打烊门店被排除
        ],
        (s3.code, d1): [
            _session(301, 4, 10, 82, left=4),
        ],
        (s3.code, d2): [
            _session(302, 4, 10, 100, left=2),
        ],
    }
    return stores, dates, sessions


def test_basic_recommendation_returns_sorted_plans():
    stores, dates, sessions = _fixture()
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=6, budget=600, date_hint=_d(5)))
    assert plans, "应至少返回一个方案"
    assert all(isinstance(p, PartyPlan) for p in plans)
    # 打烊门店、超预算、人数不符、无名额的场次都不应出现
    codes = {(p.store.code, p.date, p.session.id) for p in plans}
    assert ("S2", _d(5), 201) not in codes
    assert ("S1", _d(5), 102) not in codes
    assert ("S1", _d(5), 103) not in codes
    assert ("S1", _d(12), 104) not in codes
    # 评分降序
    scores = [p.score for p in plans]
    assert scores == sorted(scores, reverse=True)


def test_budget_filters_expensive_sessions():
    stores, dates, sessions = _fixture()
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=6, budget=500))
    for p in plans:
        assert p.total_price <= 500 + 1e-6


def test_people_out_of_range_excluded():
    stores, dates, sessions = _fixture()
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=3, budget=None))
    for p in plans:
        assert p.session.party_min <= 3 <= p.session.party_max


def test_no_left_num_excluded():
    stores, dates, sessions = _fixture()
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=6, budget=None))
    for p in plans:
        assert p.session.left_num > 0


def test_distance_limit_filters_stores():
    stores, dates, sessions = _fixture()
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=6, budget=600, max_distance_km=2))
    # 只有 S1（1km）满足距离
    assert plans
    assert all(p.store.code == "S1" for p in plans)


def test_closed_store_excluded():
    stores, dates, sessions = _fixture()
    plans = plan_party(stores, dates, sessions, PartyConstraints(people=6))
    assert all(p.store.code != "S2" for p in plans)


def test_weekend_preference():
    stores, dates, sessions = _fixture()
    # 构造一个仅含周末日期的新日期表
    def _weekend_after(days: int) -> str:
        d = date.today() + timedelta(days=days)
        while d.weekday() < 5:  # 找到下一个周六
            d += timedelta(days=1)
        return d.isoformat()

    sat = _weekend_after(3)
    stores = [_store("S1")]
    dates = {"S1": [sat]}
    sessions = {("S1", sat): [_session(1, 1, 20, 80, left=5)]}
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=4, want_weekend=True))
    assert plans and plans[0].date == sat
    # 指定 want_weekend=False（工作日）时，纯周末日期应无结果
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=4, want_weekend=False))
    assert plans == []


def test_date_hint_ranks_closer_first():
    stores, dates, sessions = _fixture()
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=6, budget=600, date_hint=_d(5)))
    assert plans
    # 第一个方案的日期应该是最贴近期望日期的（同分比较下先按评分，日期贴近加成使 d1 优先）
    assert plans[0].date == _d(5)


def test_no_viable_plan_returns_empty():
    stores, dates, sessions = _fixture()
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=100, budget=50))
    assert plans == []


def test_budget_total_price_is_people_times_price():
    stores, dates, sessions = _fixture()
    plans = plan_party(stores, dates, sessions,
                       PartyConstraints(people=6, budget=600, date_hint=_d(5)))
    for p in plans:
        assert abs(p.total_price - p.session.price * 6) < 1e-6
        assert abs(p.per_person - p.session.price) < 1e-6


def test_invalid_constraints_raise():
    stores, dates, sessions = _fixture()
    for bad in (dict(people=0), dict(budget=0), dict(max_plans=0)):
        try:
            plan_party(stores, dates, sessions, PartyConstraints(**bad))
            raise AssertionError(f"应抛出 ValueError: {bad}")
        except ValueError:
            pass
