"""省钱引擎与优惠券规则测试。"""
import asyncio

from mcctl.engines.save import best_direct_coupon, save_flow
from mcctl.mock_client import MockMCPClient
from mcctl.models import Coupon
from mcctl.service import McD


def _run(coro):
    return asyncio.run(coro)


def _mcd() -> McD:
    return McD(MockMCPClient(seed=7), "mock")


def test_coupon_threshold_and_scope():
    full40 = Coupon("C1", "满40减10", "cash", 40, 10)
    assert full40.discount_on(39) == 0
    assert full40.discount_on(40) == 10
    assert full40.discount_on(100) == 10
    # 单品券：餐篮不含指定商品时不可用
    nugget = Coupon("C2", "麦乐鸡减8", "cash", 24, 8, apply_codes=["SIDE_NUGGETS_10"])
    assert nugget.discount_on(50, {"BUR_BIGMAC"}) == 0
    assert nugget.discount_on(50, {"SIDE_NUGGETS_10"}) == 8


def test_best_direct_coupon_picks_max():
    coupons = [Coupon("A", "满40减10", "cash", 40, 10),
               Coupon("B", "满25减5", "cash", 25, 5)]
    c, saving = best_direct_coupon(coupons, 46)
    assert c.coupon_id == "A" and saving == 10


def test_save_flow_applies_best_coupon():
    async def go():
        mcd = _mcd()
        cart = [{"code": "BUR_BIGMAC", "qty": 1}, {"code": "SIDE_FRIES_M", "qty": 1},
                {"code": "DRK_COLA_M", "qty": 1}]
        res = await save_flow(mcd, cart, channel="到店取餐")
        assert res["base"]["subtotal"] == 46
        assert res["final"]["total"] == 36          # 满40减10
        assert res["total_saved"] == 10
    _run(go())


def test_single_item_coupon_not_misapplied():
    async def go():
        mcd = _mcd()
        # 只买巨无霸，麦乐鸡单品券不应生效
        bd = await mcd.calc_price([{"code": "BUR_BIGMAC", "qty": 1}], "到店取餐",
                                  ["CPN_NUGGET"])
        assert bd.discount == 0 and bd.total == 24
    _run(go())


def test_topup_suggestion_for_small_delivery_order():
    async def go():
        mcd = _mcd()
        res = await save_flow(mcd, [{"code": "BUR_HAM_CHEESE", "qty": 1}], channel="麦乐送")
        # 吉士堡12元 + 9元配送，应给出凑单到满减门槛的建议
        assert res["topup"] is not None
        add_price = res["topup"]["add"]["price"]
        assert res["topup"]["extra_cost"] < add_price  # 多付的钱低于凑单品价值
    _run(go())
