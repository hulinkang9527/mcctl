"""MCP 客户端抽象与离线演示实现。

- ``McdServer``：统一门面，核心是 ``call_tool(name, arguments)``，与 MCP
  ``tools/call`` 一一对应；上层引擎/命令只依赖这个接口。
- ``MockMCPClient``：无 Token 时使用，内置仿真数据与可连续运行的业务状态机
  （领券、算价、下单、取消、抽奖、积分兑换），让任何人 clone 后零配置即可
  体验完整闭环。真实接入见 ``mcp_client.RealMCPClient``。
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from mcctl import mock_data as D
from mcctl.models import Coupon


class McdServer:
    """麦当劳 MCP 服务门面（抽象基类）。"""

    mode = "abstract"

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:  # noqa: D401
        raise NotImplementedError

    # —— 便于上层使用的少量语义化封装（全部基于 call_tool） ——
    async def tools(self) -> list[str]:
        raise NotImplementedError


def _ok(data: Any, *, note: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": True, "source": "mock", "data": data}
    if note:
        out["note"] = note
    return out


class MockMCPClient(McdServer):
    """离线演示客户端：模拟麦当劳 MCP 的全部已开放工具。"""

    mode = "mock"

    def __init__(self, seed: int | None = 1024) -> None:
        self._rnd = random.Random(seed)
        # 可变业务状态
        self._addresses = list(D.ADDRESSES)
        self._available = list(D.AVAILABLE_COUPONS)
        self._my_coupons = list(D.MY_COUPONS)
        self._points = D.POINTS_ACCOUNT.available
        self._orders: dict[str, dict[str, Any]] = {}
        self._prizes: list[dict[str, Any]] = []
        self._mall_orders: list[dict[str, Any]] = []
        self._draws = 0

    async def tools(self) -> list[str]:
        return list(_TOOL_HANDLERS.keys())

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _meal_dict(m) -> dict[str, Any]:
        return m.to_dict()

    def _find_coupon(self, cid: str) -> Coupon | None:
        for c in self._available + self._my_coupons:
            if c.coupon_id == cid:
                return c
        return None

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone(timedelta(hours=8)))

    # ------------------------------------------------------------------ dispatch
    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        args = arguments or {}
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            return {"ok": False, "error": f"mock 未实现工具：{name}（真实 MCP 支持）"}
        return await handler(self, args)


# ===========================================================================
# 各工具处理函数（签名统一为 (client, args)）
# ===========================================================================
async def _now_time(c: MockMCPClient, a: dict) -> Any:
    now = c._now()
    return _ok({
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "timezone": "Asia/Shanghai (UTC+8)",
        "period": _period_of(now),
    })


def _period_of(now: datetime) -> str:
    h = now.hour
    if 5 <= h < 10:
        return "breakfast"
    if 22 <= h or h < 5:
        return "late-night"
    return "regular"


async def _list_nutrition(c: MockMCPClient, a: dict) -> Any:
    period = a.get("period", "regular")
    category = a.get("category")
    keyword = (a.get("keyword") or "").strip()
    meals = D.meals_for_period(period)
    if category:
        meals = [m for m in meals if m.category == category]
    if keyword:
        meals = [m for m in meals if keyword in m.name]
    return _ok({
        "total": len(meals),
        "period": period,
        "foods": [m.to_dict() for m in meals],
        "disclaimer": "演示数据为近似值，真实营养以麦当劳官方 MCP 实时返回为准。",
    })


async def _query_meals(c: MockMCPClient, a: dict) -> Any:
    period = a.get("period", "regular")
    category = a.get("category")
    meals = D.meals_for_period(period)
    if category:
        meals = [m for m in meals if m.category == category]
    return _ok({"store_id": a.get("store_id", "ST_NJDL"), "period": period,
                "menu": [{"code": m.code, "name": m.name, "category": m.category,
                          "price": m.price, "tags": m.tags} for m in meals]})


async def _meal_detail(c: MockMCPClient, a: dict) -> Any:
    m = D.MEAL_BY_CODE.get(a.get("code", ""))
    if not m:
        return {"ok": False, "error": "餐品编码不存在"}
    return _ok({"code": m.code, "name": m.name, "price": m.price,
                "components": [{"name": m.name, "qty": 1}],
                "replaceable_options": [], "tags": m.tags})


async def _query_addresses(c: MockMCPClient, a: dict) -> Any:
    return _ok({"addresses": [x.to_dict() for x in c._addresses]})


async def _create_address(c: MockMCPClient, a: dict) -> Any:
    aid = "ADDR_" + "".join(c._rnd.choices(string.digits, k=3))
    from mcctl.models import Address
    addr = Address(aid, a.get("contact", "麦门信徒"), a.get("phone", "138****0000"),
                   a.get("address", ""), a.get("detail", ""))
    c._addresses.append(addr)
    return _ok({"address": addr.to_dict()}, note="演示环境已创建地址")


async def _nearby_stores(c: MockMCPClient, a: dict) -> Any:
    return _ok({"stores": [s.to_dict() for s in sorted(D.STORES, key=lambda s: s.distance_m)]})


async def _delivery_stores(c: MockMCPClient, a: dict) -> Any:
    stores = [s for s in D.STORES if "delivery" in s.features]
    return _ok({"address_id": a.get("address_id", "ADDR_1"),
                "stores": [s.to_dict() for s in stores]})


async def _meal_assistance(c: MockMCPClient, a: dict) -> Any:
    return _ok({"store_id": a.get("store_id"), "assistance": [
        {"type": "企业团餐", "supported": True},
        {"type": "助餐补贴/企业结算", "supported": True},
    ]})


async def _store_coupons(c: MockMCPClient, a: dict) -> Any:
    return _ok({"store_id": a.get("store_id", "ST_NJDL"),
                "coupons": [x.to_dict() for x in c._my_coupons + c._available[:3]]})


async def _available_coupons(c: MockMCPClient, a: dict) -> Any:
    return _ok({"available": [x.to_dict() for x in c._available],
                "count": len(c._available)})


async def _auto_bind(c: MockMCPClient, a: dict) -> Any:
    claimed = []
    for cpn in c._available:
        cpn.claimed = True
        c._my_coupons.append(cpn)
        claimed.append(cpn.coupon_id)
    c._available.clear()
    return _ok({"claimed_count": len(claimed), "claimed_ids": claimed,
                "message": f"已一键领取 {len(claimed)} 张麦麦省优惠券"},
               note="真实环境由 auto-bind-coupons 自动领取全部可领券")


async def _my_coupons(c: MockMCPClient, a: dict) -> Any:
    return _ok({"coupons": [x.to_dict() for x in c._my_coupons],
                "count": len(c._my_coupons)})


def _price(c: MockMCPClient, a: dict) -> dict[str, Any]:
    items = a.get("items", [])
    channel = a.get("channel", "到店取餐")
    lines, subtotal = [], 0.0
    for it in items:
        m = D.MEAL_BY_CODE.get(it.get("code"))
        if not m:
            continue
        qty = int(it.get("qty", 1))
        line_total = round(m.price * qty, 2)
        subtotal += line_total
        lines.append({"code": m.code, "name": m.name, "qty": qty,
                      "unit_price": m.price, "line_total": line_total})
    subtotal = round(subtotal, 2)
    delivery_fee = 9.0 if channel == "麦乐送" and subtotal < 39 else 0.0

    discount, applied, best = 0.0, [], None
    cart_codes = {it.get("code") for it in items}
    categories = {D.MEAL_BY_CODE[code].category for code in cart_codes if code in D.MEAL_BY_CODE}
    for cid in a.get("coupon_ids", []):
        cpn = c._find_coupon(cid)
        if not cpn:
            continue
        # 组合券要求餐篮同时含小食/甜点与饮品
        if cpn.scope == "组合" and not ({"小食", "甜点"} & categories and "饮品" in categories):
            continue
        d = cpn.discount_on(subtotal, cart_codes)
        if d > discount:
            discount, best = d, cpn
    gifts = []
    for cid in a.get("coupon_ids", []):
        cpn = c._find_coupon(cid)
        if cpn and cpn.kind == "gift":
            gifts.append(cpn.description)
    if best:
        applied.append(best.title)
    total = round(max(0.0, subtotal + delivery_fee - discount), 2)
    return {
        "channel": channel, "lines": lines, "subtotal": subtotal,
        "delivery_fee": round(delivery_fee, 2), "discount": round(discount, 2),
        "applied_coupons": applied, "gifts": gifts, "total": total,
    }


async def _calculate_price(c: MockMCPClient, a: dict) -> Any:
    return _ok(_price(c, a))


async def _create_order(c: MockMCPClient, a: dict) -> Any:
    price = _price(c, a)
    if price["subtotal"] <= 0:
        return {"ok": False, "error": "购物车为空，无法下单"}
    oid = "MCD" + "".join(c._rnd.choices(string.digits, k=10))
    channel = a.get("channel", "到店取餐")
    store_name = a.get("store_name", "麦当劳南京东路步行街餐厅")
    eta = {"麦乐送": "约30分钟送达", "到店取餐": "约8分钟后可取",
           "堂食外带": "约6分钟出餐", "得来速": "约5分钟车道取餐"}.get(channel, "约10分钟")
    order = {
        "order_id": oid, "status": "待支付", "channel": channel,
        "store_name": store_name, "items": price["lines"],
        "subtotal": price["subtotal"], "delivery_fee": price["delivery_fee"],
        "discount": price["discount"], "total": price["total"],
        "gifts": price["gifts"],
        "pay_url": f"https://open.mcd.cn/mcp/demo-pay/{oid}",
        "created_at": c._now().strftime("%Y-%m-%d %H:%M:%S"), "eta": eta,
    }
    c._orders[oid] = order
    return _ok({"order": order, "pay_url": order["pay_url"]},
               note="演示订单不会真实扣款；真实环境返回官方支付链接")


async def _cancel_order(c: MockMCPClient, a: dict) -> Any:
    oid = a.get("order_id", "")
    if oid in c._orders:
        c._orders[oid]["status"] = "已取消"
        return _ok({"order_id": oid, "status": "已取消"})
    return {"ok": False, "error": "未找到订单"}


async def _query_order(c: MockMCPClient, a: dict) -> Any:
    oid = a.get("order_id", "")
    if oid in c._orders:
        return _ok({"order": c._orders[oid]})
    return {"ok": False, "error": "未找到订单"}


async def _order_list(c: MockMCPClient, a: dict) -> Any:
    return _ok({"orders": list(c._orders.values())[-20:][::-1], "count": len(c._orders)})


async def _campaigns(c: MockMCPClient, a: dict) -> Any:
    status = a.get("status")
    camps = D.CAMPAIGNS
    if status:
        camps = [x for x in camps if x.status == status]
    return _ok({"campaigns": [x.to_dict() for x in camps]})


async def _my_account(c: MockMCPClient, a: dict) -> Any:
    return _ok({"points": {"available": c._points, "total_earned": D.POINTS_ACCOUNT.total_earned,
                           "frozen": 0, "expiring": D.POINTS_ACCOUNT.expiring}})


async def _mall_products(c: MockMCPClient, a: dict) -> Any:
    return _ok({"products": [x.to_dict() for x in D.MALL_PRODUCTS]})


async def _mall_detail(c: MockMCPClient, a: dict) -> Any:
    for p in D.MALL_PRODUCTS:
        if p.product_id == a.get("product_id"):
            return _ok({"product": p.to_dict()})
    return {"ok": False, "error": "商品不存在"}


async def _mall_create_order(c: MockMCPClient, a: dict) -> Any:
    pid = a.get("product_id", "")
    product = next((p for p in D.MALL_PRODUCTS if p.product_id == pid), None)
    if not product:
        return {"ok": False, "error": "商品不存在"}
    if c._points < product.points:
        return {"ok": False, "error": f"积分不足：需要 {product.points}，当前 {c._points}"}
    c._points -= product.points
    mid = "MALL" + "".join(c._rnd.choices(string.digits, k=8))
    rec = {"mall_order_id": mid, "product": product.name, "cost_points": product.points,
           "status": "兑换成功", "created_at": c._now().strftime("%Y-%m-%d %H:%M:%S"),
           "voucher_code": "MCD-" + "".join(c._rnd.choices(string.ascii_uppercase + string.digits, k=10))}
    c._mall_orders.append(rec)
    return _ok({"redemption": rec, "points_left": c._points}, note="演示兑换，不真实扣减积分")


async def _mall_order_list(c: MockMCPClient, a: dict) -> Any:
    return _ok({"orders": c._mall_orders[::-1]})


async def _mall_order_detail(c: MockMCPClient, a: dict) -> Any:
    for r in c._mall_orders:
        if r["mall_order_id"] == a.get("mall_order_id"):
            return _ok({"order": r})
    return {"ok": False, "error": "未找到商城订单"}


async def _lottery_info(c: MockMCPClient, a: dict) -> Any:
    info = dict(D.LOTTERY_INFO)
    info["draws_today"] = c._draws
    info["points_available"] = c._points
    info["rational_note"] = D.LOTTERY_RATIONAL_NOTE
    return _ok(info)


async def _draw_lottery(c: MockMCPClient, a: dict) -> Any:
    cost = D.LOTTERY_INFO["cost_points"]
    if c._draws >= D.LOTTERY_INFO["daily_limit"]:
        return {"ok": False, "error": "今日抽奖次数已达上限"}
    if c._points < cost:
        return {"ok": False, "error": f"积分不足：单次抽奖需 {cost} 积分"}
    c._points -= cost
    c._draws += 1
    roll = c._rnd.random()
    # 0.5% / 5% / 30% / 64.5%
    if roll < 0.005:
        prize, gain = "巨无霸兑换券", 0
    elif roll < 0.055:
        prize, gain = "中薯条兑换券", 0
    elif roll < 0.355:
        prize, gain = "20积分", 20
    else:
        prize, gain = "5积分", 5
    c._points += gain
    rec = {"prize": prize, "gain_points": gain, "at": c._now().strftime("%Y-%m-%d %H:%M:%S")}
    c._prizes.append(rec)
    return _ok({"result": rec, "points_left": c._points, "note": D.LOTTERY_RATIONAL_NOTE})


async def _my_prizes(c: MockMCPClient, a: dict) -> Any:
    return _ok({"prizes": c._prizes[::-1], "count": len(c._prizes)})


# —— 主题活动（派对 / 品鉴会） ——
_PARTY_CITIES = ["上海", "北京", "广州", "深圳", "杭州", "成都"]
_PARTY_STORES = {
    "上海": [
        {"code": "ST_LJZ", "name": "麦当劳陆家嘴环路餐厅", "address": "上海市浦东新区陆家嘴环路近IFC",
         "cityCode": "310100", "cityName": "上海市", "distance": 860, "distanceText": "0.9km", "businessStatus": True},
        {"code": "ST_JA", "name": "麦当劳静安嘉里中心餐厅", "address": "上海市静安区南京西路嘉里中心",
         "cityCode": "310100", "cityName": "上海市", "distance": 2100, "distanceText": "2.1km", "businessStatus": True},
        {"code": "ST_HP", "name": "麦当劳外滩中山东一路餐厅", "address": "上海市黄浦区中山东一路",
         "cityCode": "310100", "cityName": "上海市", "distance": 3400, "distanceText": "3.4km", "businessStatus": True},
    ],
}
# 门店 → 可预约日期（按天给出，便于贴近 date_hint 演示）
_PARTY_DATES_BY_STORE = {
    "ST_LJZ": ["2026-10-17", "2026-10-18", "2026-10-24", "2026-10-25", "2026-10-31"],
    "ST_JA": ["2026-10-18", "2026-10-19", "2026-10-25", "2026-10-26", "2026-11-01"],
    "ST_HP": ["2026-10-18", "2026-10-25", "2026-10-26"],
}
# (门店, 日期) → 场次：字段对齐官方 query-party-store-session
# price 为「每人价格（分）」，service 层 ÷100 归一化为元，与真实口径一致。
_PARTY_SESSIONS_BY_STORE_DATE = {
    ("ST_LJZ", "2026-10-18"): [
        {"id": 1101, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 4, "partyMax": 8, "price": 8800, "leftNum": 5},
        {"id": 1102, "timeStart": "14:00", "timeEnd": "15:30", "partyMin": 4, "partyMax": 10, "price": 7800, "leftNum": 2},
        {"id": 1103, "timeStart": "16:30", "timeEnd": "18:00", "partyMin": 4, "partyMax": 12, "price": 6800, "leftNum": 8},
    ],
    ("ST_LJZ", "2026-10-17"): [
        {"id": 1201, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 2, "partyMax": 6, "price": 9800, "leftNum": 3},
        {"id": 1202, "timeStart": "14:00", "timeEnd": "15:30", "partyMin": 2, "partyMax": 6, "price": 8800, "leftNum": 6},
    ],
    ("ST_LJZ", "2026-10-24"): [
        {"id": 1301, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 4, "partyMax": 10, "price": 8200, "leftNum": 7},
        {"id": 1302, "timeStart": "16:30", "timeEnd": "18:00", "partyMin": 4, "partyMax": 12, "price": 6200, "leftNum": 12},
    ],
    ("ST_LJZ", "2026-10-25"): [
        {"id": 1401, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 4, "partyMax": 10, "price": 8500, "leftNum": 6},
        {"id": 1402, "timeStart": "14:00", "timeEnd": "15:30", "partyMin": 4, "partyMax": 10, "price": 7500, "leftNum": 4},
        {"id": 1403, "timeStart": "18:30", "timeEnd": "20:00", "partyMin": 4, "partyMax": 12, "price": 9500, "leftNum": 1},
    ],
    ("ST_LJZ", "2026-10-31"): [
        {"id": 1501, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 4, "partyMax": 10, "price": 9000, "leftNum": 9},
    ],
    ("ST_JA", "2026-10-18"): [
        {"id": 2101, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 4, "partyMax": 8, "price": 9200, "leftNum": 4},
        {"id": 2102, "timeStart": "14:00", "timeEnd": "15:30", "partyMin": 4, "partyMax": 8, "price": 8200, "leftNum": 3},
    ],
    ("ST_JA", "2026-10-19"): [
        {"id": 2201, "timeStart": "16:00", "timeEnd": "17:30", "partyMin": 2, "partyMax": 6, "price": 8800, "leftNum": 5},
    ],
    ("ST_JA", "2026-10-25"): [
        {"id": 2301, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 4, "partyMax": 10, "price": 8600, "leftNum": 7},
        {"id": 2302, "timeStart": "14:00", "timeEnd": "15:30", "partyMin": 4, "partyMax": 10, "price": 7600, "leftNum": 2},
        {"id": 2303, "timeStart": "18:30", "timeEnd": "20:00", "partyMin": 4, "partyMax": 12, "price": 9800, "leftNum": 6},
    ],
    ("ST_JA", "2026-10-26"): [
        {"id": 2401, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 2, "partyMax": 6, "price": 9000, "leftNum": 4},
    ],
    ("ST_JA", "2026-11-01"): [
        {"id": 2501, "timeStart": "14:00", "timeEnd": "15:30", "partyMin": 4, "partyMax": 10, "price": 8000, "leftNum": 10},
    ],
    ("ST_HP", "2026-10-18"): [
        {"id": 3101, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 4, "partyMax": 10, "price": 9900, "leftNum": 6},
    ],
    ("ST_HP", "2026-10-25"): [
        {"id": 3201, "timeStart": "14:00", "timeEnd": "15:30", "partyMin": 4, "partyMax": 10, "price": 7200, "leftNum": 5},
        {"id": 3202, "timeStart": "16:30", "timeEnd": "18:00", "partyMin": 4, "partyMax": 8, "price": 7900, "leftNum": 3},
    ],
    ("ST_HP", "2026-10-26"): [
        {"id": 3301, "timeStart": "10:30", "timeEnd": "12:00", "partyMin": 2, "partyMax": 6, "price": 9400, "leftNum": 2},
    ],
}


async def _party_city(c: MockMCPClient, a: dict) -> Any:
    return _ok({"cities": _PARTY_CITIES})


async def _party_store(c: MockMCPClient, a: dict) -> Any:
    city = a.get("city", "上海")
    stores = _PARTY_STORES.get(city, [
        {"code": "ST_CT", "name": "麦当劳市中心主题餐厅", "address": city,
         "cityCode": "0", "cityName": city, "distance": 1200, "distanceText": "1.2km", "businessStatus": True},
    ])
    return _ok({"city": city, "stores": stores})


async def _party_date(c: MockMCPClient, a: dict) -> Any:
    store = a.get("store", "ST_LJZ")
    return _ok({"store": store, "dates": _PARTY_DATES_BY_STORE.get(store, _PARTY_DATES_BY_STORE["ST_LJZ"])})


async def _party_session(c: MockMCPClient, a: dict) -> Any:
    store = a.get("store", "ST_LJZ")
    date = a.get("date", "2026-10-18")
    return _ok({"store": store, "date": date,
                "sessions": _PARTY_SESSIONS_BY_STORE_DATE.get((store, date), [])})


async def _party_order_create(c: MockMCPClient, a: dict) -> Any:
    pid = "PARTY" + "".join(c._rnd.choices(string.digits, k=8))
    return _ok({"party_order_id": pid, "status": "预约成功",
                "city": a.get("city"), "store": a.get("store"),
                "date": a.get("date"), "session": a.get("session"),
                "people": a.get("people", 6),
                "pay_url": f"https://open.mcd.cn/mcp/demo-pay/{pid}"},
               note="演示预约，不会真实扣款")


async def _promotions(c: MockMCPClient, a: dict) -> Any:
    """query-promotions：查询当前可参与/即将开始的促销活动（离线仿真）。"""
    return _ok({"promotions": [
        {"id": "PM_1024", "title": "1024 程序员节 · 买一送一", "period": "2026-10-20 ~ 2026-10-26",
         "scope": ["BUR_DOUBLE_CHEESE", "BUR_FISH"], "note": "活动期间指定单品买一送一"},
        {"id": "PM_MEAL", "title": "麦麦超值套餐立减 5 元", "period": "2026-10-01 ~ 2026-11-30",
         "scope": ["meal"], "note": "部分套餐可叠加优惠券"},
    ]})


async def _survey_coupon(c: MockMCPClient, a: dict) -> Any:
    """query-survey-coupon：查询问卷任务可领取的优惠券（离线仿真）。"""
    return _ok({"surveys": [
        {"id": "SV_TASTE", "title": "口味偏好小问卷", "reward": "中薯条兑换券", "status": "可参与"},
        {"id": "SV_STORE", "title": "门店体验反馈问卷", "reward": "5 元满减券", "status": "可参与"},
    ]})


# 工具名 → 处理函数映射（覆盖麦当劳 MCP 当前开放的全部工具）
_TOOL_HANDLERS = {
    "now-time-info": _now_time,
    "list-nutrition-foods": _list_nutrition,
    "query-meals": _query_meals,
    "query-meal-detail": _meal_detail,
    "delivery-query-addresses": _query_addresses,
    "delivery-create-address": _create_address,
    "query-nearby-stores": _nearby_stores,
    "delivery-query-stores": _delivery_stores,
    "query-meal-assistance": _meal_assistance,
    "query-store-coupons": _store_coupons,
    "available-coupons": _available_coupons,
    "auto-bind-coupons": _auto_bind,
    "query-my-coupons": _my_coupons,
    "query-promotions": _promotions,
    "query-survey-coupon": _survey_coupon,
    "calculate-price": _calculate_price,
    "create-order": _create_order,
    "cancel-order": _cancel_order,
    "query-order": _query_order,
    "order-list": _order_list,
    "campaign-calendar": _campaigns,
    "query-my-account": _my_account,
    "mall-points-products": _mall_products,
    "mall-product-detail": _mall_detail,
    "mall-create-order": _mall_create_order,
    "mall-order-list": _mall_order_list,
    "mall-order-detail": _mall_order_detail,
    "query-lottery-info": _lottery_info,
    "draw-lottery": _draw_lottery,
    "query-my-prizes": _my_prizes,
    "query-party-city": _party_city,
    "query-party-store": _party_store,
    "query-party-store-date": _party_date,
    "query-party-store-session": _party_session,
    "party-order-create": _party_order_create,
}
