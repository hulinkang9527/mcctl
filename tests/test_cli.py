"""命令行入口的健壮性测试：购物车解析容错、decide 别名 lunch。"""
from __future__ import annotations

from mcctl import mock_data as D
from mcctl.cli import _parse_cart, app
from typer.testing import CliRunner


def _meals():
    return D.meals_for_period("regular") + D.meals_for_period("breakfast")


def test_parse_cart_bad_qty_is_ignored_not_raised():
    """数量非法（非整数 / 非正数）时应忽略该项并返回，而不是抛 ValueError 堆栈。"""
    meals = _meals()
    assert _parse_cart("巨无霸:abc", meals) == []
    assert _parse_cart("巨无霸:0", meals) == []
    assert _parse_cart("巨无霸:-2", meals) == []


def test_parse_cart_valid_qty_and_fuzzy_name():
    meals = _meals()
    cart = _parse_cart("巨无霸:2,薯条(中):1", meals)
    by_name = {item["name"]: item for item in cart}
    assert any("巨无霸" in name for name in by_name)
    big = next(item for item in cart if "巨无霸" in item["name"])
    assert big["qty"] == 2
    assert any("薯条" in item["name"] for item in cart)


def test_lunch_alias_supports_persona_option():
    """lunch 是 decide 的别名，必须能透传 -p 等选项（旧 **kwargs 实现会报 no such option）。"""
    runner = CliRunner()
    result = runner.invoke(app, ["--mock", "--json", "lunch", "-p", "FITA"])
    assert result.exit_code == 0, result.output
    assert "FITA" in result.output
