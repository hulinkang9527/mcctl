"""派对策划师 · 网页端边界用例（web/party.js）。

覆盖评审点名要测的几类输入：
- 人数 0 / 负数 / 超过上限；
- 预算 0 / 负数 / 远低于所有方案；
- 只选周末但没有满足条件的场次；
- 所有候选方案都不符合预算；
- 返回场次缺少字段（left 缺失按不可预订处理，关键字段缺失直接跳过）。

断言在 Python 侧，期望值与后端 engines/party.py 的硬约束保持一致：
宁可返回「没有找到符合条件的方案」，也绝不推荐一个不满足约束的结果。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "tests" / "js_party_probe.js"


def _d(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _next_weekday(days: int) -> str:
    d = date.today() + timedelta(days=days)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


def _next_weekend(days: int) -> str:
    d = date.today() + timedelta(days=days)
    while d.weekday() < 5:
        d += timedelta(days=1)
    return d.isoformat()


# 一份最小可用场次：4 人起、10 人上限、人均 80、剩余 6 名额
def _sessions(overrides=None):
    base = [
        {"store": "S1", "date": _d(3), "time": "10:30-12:00", "price": 80,
         "min": 4, "max": 10, "left": 6},
        {"store": "S2", "date": _d(9), "time": "14:00-15:30", "price": 120,
         "min": 4, "max": 10, "left": 6},
    ]
    return overrides if overrides is not None else base


def _run(cases: list[dict]) -> dict[str, dict]:
    node = shutil.which("node")
    if not node:
        pytest.skip("未找到 node，跳过网页端派对边界用例")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False)
        tmp = f.name
    proc = subprocess.run([node, str(PROBE), tmp], capture_output=True, text=True, cwd=str(ROOT))
    Path(tmp).unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr[:500]
    return {row["name"]: row for row in json.loads(proc.stdout)}


def test_zero_and_negative_people_yield_no_plan():
    res = _run([
        {"name": "zero", "people": 0, "budget": None, "weekend": False, "sessions": _sessions()},
        {"name": "negative", "people": -3, "budget": None, "weekend": False, "sessions": _sessions()},
        {"name": "over", "people": 13, "budget": None, "weekend": False, "sessions": _sessions()},
    ])
    for name in ("zero", "negative", "over"):
        assert res[name]["ok"] is False, f"{name} 应无可行方案"
        assert res[name]["count"] == 0
        assert res[name]["issue"]["people"] > 0, f"{name} 应被人数硬约束淘汰"


def test_budget_zero_or_too_low_yields_no_plan():
    sessions = _sessions()
    res = _run([
        {"name": "zero_budget", "people": 6, "budget": 0, "weekend": False, "sessions": sessions},
        {"name": "low_budget", "people": 6, "budget": 100, "weekend": False, "sessions": sessions},
    ])
    for name in ("zero_budget", "low_budget"):
        assert res[name]["ok"] is False
        assert res[name]["count"] == 0
        assert res[name]["issue"]["budget"] > 0, f"{name} 应被预算硬约束淘汰"


def test_weekend_only_without_weekend_sessions():
    # 只提供工作日场次，却要求「仅周末」→ 必须无方案
    weekday = _next_weekday(2)
    sessions = [{"store": "S1", "date": weekday, "time": "10:30-12:00",
                 "price": 80, "min": 4, "max": 10, "left": 6}]
    res = _run([{"name": "weekend_none", "people": 6, "budget": 1000,
                 "weekend": True, "sessions": sessions}])
    row = res["weekend_none"]
    assert row["ok"] is False and row["count"] == 0
    assert row["issue"]["weekend"] > 0, "应被周末偏好淘汰"


def test_all_candidates_over_budget():
    sessions = [
        {"store": "S1", "date": _d(3), "time": "10:30-12:00", "price": 90,
         "min": 4, "max": 10, "left": 6},
        {"store": "S2", "date": _d(4), "time": "14:00-15:30", "price": 100,
         "min": 4, "max": 10, "left": 6},
    ]
    res = _run([{"name": "over_budget", "people": 8, "budget": 200,
                 "weekend": False, "sessions": sessions}])
    assert res["over_budget"]["ok"] is False and res["over_budget"]["count"] == 0


def test_missing_left_num_treated_as_unbookable():
    sessions = [
        {"store": "S1", "date": _d(3), "time": "10:30-12:00", "price": 80,
         "min": 4, "max": 10},  # 缺 left → 视为 0，不可预订
    ]
    res = _run([{"name": "missing_left", "people": 6, "budget": 1000,
                 "weekend": False, "sessions": sessions}])
    assert res["missing_left"]["ok"] is False
    assert res["missing_left"]["issue"]["left"] > 0, "缺 left 应保守判为名额不足"


def test_missing_key_fields_are_skipped():
    sessions = [
        {"store": "S1", "date": _d(3)},                                  # 缺 time/price
        {"store": "", "date": _d(3), "time": "10:30-12:00", "price": 80},  # 缺门店
        {"store": "S3", "date": _d(3), "time": "10:30-12:00", "price": 80,
         "min": 4, "max": 10, "left": 6},                              # 完整
    ]
    res = _run([{"name": "broken", "people": 6, "budget": 1000,
                 "weekend": False, "sessions": sessions}])
    row = res["broken"]
    assert row["ok"] is True and row["count"] == 1
    assert row["plans"][0]["store"] == "S3"
    assert row["issue"]["broken"] == 2, "两条缺字段记录应被跳过且计数"


def test_happy_path_sorted_and_within_budget():
    sessions = _sessions()
    res = _run([{"name": "happy", "people": 6, "budget": 1000,
                 "weekend": False, "sessions": sessions}])
    row = res["happy"]
    assert row["ok"] is True and row["count"] == len(sessions)
    # 人均低者排前面
    assert row["plans"][0]["per"] <= row["plans"][-1]["per"]
    for p in row["plans"]:
        assert p["total"] <= 1000


def test_expired_dates_excluded():
    sessions = [
        {"store": "S1", "date": _d(-5), "time": "10:30-12:00", "price": 80,
         "min": 4, "max": 10, "left": 6},
    ]
    res = _run([{"name": "expired", "people": 6, "budget": 1000,
                 "weekend": False, "sessions": sessions}])
    assert res["expired"]["ok"] is False
    assert res["expired"]["issue"]["expired"] == 1
