"""离线 MCP 客户端状态机测试（覆盖点餐/领券/抽奖/积分/派对闭环）。"""
import asyncio

from mcctl.mock_client import MockMCPClient


def _run(coro):
    return asyncio.run(coro)


def test_all_33_tools_implemented():
    client = MockMCPClient()
    tools = _run(client.tools())
    assert len(tools) == 33
    # 关键业务工具齐全
    for name in ["list-nutrition-foods", "calculate-price", "create-order", "cancel-order",
                 "auto-bind-coupons", "campaign-calendar", "query-my-account",
                 "mall-create-order", "draw-lottery", "party-order-create", "now-time-info"]:
        assert name in tools


def test_nutrition_and_meals():
    client = MockMCPClient()
    res = _run(client.call_tool("list-nutrition-foods", {"period": "regular"}))
    assert res["ok"] and res["data"]["total"] > 20
    names = [f["name"] for f in res["data"]["foods"]]
    assert "巨无霸" in names


def test_price_calculation():
    client = MockMCPClient()
    res = _run(client.call_tool("calculate-price", {
        "channel": "到店取餐",
        "items": [{"code": "BUR_BIGMAC", "qty": 1}, {"code": "SIDE_FRIES_M", "qty": 1}],
        "coupon_ids": []}))
    d = res["data"]
    assert d["subtotal"] == 35 and d["delivery_fee"] == 0 and d["total"] == 35


def test_delivery_fee_threshold():
    client = MockMCPClient()
    low = _run(client.call_tool("calculate-price",
                                {"channel": "麦乐送", "items": [{"code": "BUR_HAM_CHEESE", "qty": 1}]}))["data"]
    assert low["delivery_fee"] == 9 and low["total"] == 21
    high = _run(client.call_tool("calculate-price",
                                 {"channel": "麦乐送",
                                  "items": [{"code": "BUR_BIGMAC", "qty": 1}, {"code": "BUR_ANGUS", "qty": 1}]}))["data"]
    assert high["delivery_fee"] == 0  # 满39免配送


def test_auto_bind_moves_coupons():
    client = MockMCPClient()
    r1 = _run(client.call_tool("available-coupons"))
    n = r1["data"]["count"]
    assert n >= 1
    _run(client.call_tool("auto-bind-coupons"))
    r2 = _run(client.call_tool("available-coupons"))
    assert r2["data"]["count"] == 0
    mine = _run(client.call_tool("query-my-coupons"))["data"]["count"]
    assert mine >= n


def test_order_lifecycle():
    client = MockMCPClient()
    empty = _run(client.call_tool("create-order", {"channel": "到店取餐", "items": []}))
    assert empty["ok"] is False
    created = _run(client.call_tool("create-order", {
        "channel": "到店取餐", "items": [{"code": "BUR_BIGMAC", "qty": 1}]}))["data"]
    oid = created["order"]["order_id"]
    assert created["pay_url"].endswith(oid) and created["order"]["status"] == "待支付"
    cancel = _run(client.call_tool("cancel-order", {"order_id": oid}))["data"]
    assert cancel["status"] == "已取消"


def test_points_redeem_and_insufficient():
    client = MockMCPClient()
    # 1280 分换不起 3000 分的巨无霸券
    fail = _run(client.call_tool("mall-create-order", {"product_id": "MALL_BIGMAC"}))
    assert fail["ok"] is False
    # 可以换 800 分的薯条券，积分扣减
    ok = _run(client.call_tool("mall-create-order", {"product_id": "MALL_FRIES"}))["data"]
    assert ok["points_left"] == 480 and ok["redemption"]["voucher_code"]


def test_lottery_costs_points_and_has_limit():
    client = MockMCPClient(seed=1)
    for _ in range(5):
        r = _run(client.call_tool("draw-lottery"))
        assert r["ok"]
    sixth = _run(client.call_tool("draw-lottery"))
    assert sixth["ok"] is False  # 每日上限5次


def test_party_booking_flow():
    client = MockMCPClient()
    cities = _run(client.call_tool("query-party-city"))["data"]["cities"]
    assert "上海" in cities
    book = _run(client.call_tool("party-order-create", {
        "city": "上海", "store": "麦当劳陆家嘴环路餐厅", "date": "2026-10-25",
        "session": "18:30-20:00", "people": 8}))["data"]
    assert book["status"] == "预约成功" and book["party_order_id"]
