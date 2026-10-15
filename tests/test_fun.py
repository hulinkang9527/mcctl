"""趣味玩法测试：每日运势、盲盒点餐、人格合餐。"""
import asyncio

from typer.testing import CliRunner

from mcctl import mock_data as D  # noqa: F401
from mcctl.cli import app
from mcctl.engines import persona as P
from mcctl.engines.fun import fortune, pair, roll
from mcctl.mock_client import MockMCPClient
from mcctl.service import McD


def _mcd() -> McD:
    return McD(MockMCPClient(seed=3), "mock")


def test_fortune_is_deterministic_for_same_day():
    a = fortune("2026-10-15")
    b = fortune("2026-10-15")
    assert a == b


def test_fortune_changes_with_day():
    a = fortune("2026-10-15")
    b = fortune("2026-10-16")
    assert a["date"] == "2026-10-15" and b["date"] == "2026-10-16"
    # 至少内容有变化（人格/宜忌/箴言/幸运数字组合）
    sig_a = (a["persona"]["code"], a["good"], a["bad"], a["quote"], a["lucky_number"])
    sig_b = (b["persona"]["code"], b["good"], b["bad"], b["quote"], b["lucky_number"])
    assert sig_a != sig_b


def test_fortune_persona_is_known():
    codes = {p["code"] for p in P.all_personas()}
    f = fortune("2026-10-15")
    assert f["persona"]["code"] in codes
    assert f["good"] and f["bad"] and f["quote"]


def test_roll_returns_full_combo():
    async def go():
        res = await roll(_mcd())
        return res
    res = asyncio.run(go())
    cats = {i["category"] for i in res["items"]}
    assert "主食" in cats and "小食" in cats and "饮品" in cats
    assert res["price"] > 0 and res["kcal"] > 0


def test_cli_daily_and_roll():
    runner = CliRunner()
    r1 = runner.invoke(app, ["--json", "daily"])
    assert r1.exit_code == 0, r1.output
    assert "good" in r1.stdout
    r2 = runner.invoke(app, ["--mock", "--json", "roll"])
    assert r2.exit_code == 0, r2.output
    assert "items" in r2.stdout


def test_pair_merges_signature_meals():
    async def go():
        return await pair(_mcd(), "BIGS", "FITA")
    res = asyncio.run(go())
    assert res["persona_a"]["code"] == "BIGS" and res["persona_b"]["code"] == "FITA"
    assert len(res["lines"]) >= 3
    assert res["total_price"] > 0 and res["per_person_price"] > 0
    assert res["tier"] in ("soul", "ally", "contrast")


def test_pair_rejects_unknown_code():
    async def go():
        return await pair(_mcd(), "BIGS", "NOPE")
    try:
        asyncio.run(go())
        raise AssertionError("应当报错")
    except ValueError:
        pass


def test_cli_pair():
    runner = CliRunner()
    r = runner.invoke(app, ["--mock", "--json", "pair", "--a", "BIGS", "--b", "SWEET"])
    assert r.exit_code == 0, r.output
    assert "lines" in r.stdout
