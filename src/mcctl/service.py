"""服务门面：根据配置选择真实/离线 MCP，并对上层提供业务 API。

上层（CLI、engines、Skill）只与 ``McD`` 打交道，不直接关心数据来自
官方 MCP 还是离线演示。
"""
from __future__ import annotations

import re
from typing import Any

from mcctl.config import Settings
from mcctl.mcp_client import RealMCPClient
from mcctl.mock_client import MockMCPClient
from mcctl.models import (
    Address,
    Campaign,
    Coupon,
    MallProduct,
    Meal,
    PartyDate,
    PartySession,
    PartyStore,
    PointsAccount,
    PriceBreakdown,
    Store,
)


# 本次进程内成功建立、需要在命令结束时显式关闭的 live 连接
_active_live: list[RealMCPClient] = []


async def get_server(settings: Settings) -> tuple[Any, str]:
    """返回 ``(server, 实际模式说明)``。"""
    if settings.is_mock:
        return MockMCPClient(), "mock"
    if settings.mode.value == "live" and not (settings.token or "").strip():
        raise ConnectionError(
            "未配置 MCD_MCP_TOKEN。请先到 https://open.mcd.cn/mcp 申请 Token，"
            "然后 export MCD_MCP_TOKEN=你的Token；或去掉 --live 用离线演示模式体验。"
            "（也可临时传：mcctl --token <你的Token> --live <命令> —— --token 是全局选项，"
            "要写在子命令之前）"
        )
    live = RealMCPClient(settings.url, settings.token or "")
    ok = await live.health_check()
    if ok:
        # 复用同一条会话：登记后由 aclose_servers() 在命令结束时统一关闭
        _active_live.append(live)
        return live, "live"
    # auto 模式连不上则降级；live 模式直接抛错
    if settings.mode.value == "live":
        raise ConnectionError(
            "无法连接麦当劳 MCP（https://mcp.mcd.cn）——Token 无效、已过期或网络不可达都会走到这里。"
            "请用 `mcctl config` 核对连接配置与 Token 脱敏值，然后重试；"
            "或使用 --mock 体验离线演示。"
        )
    return MockMCPClient(), "mock-fallback"


async def aclose_servers() -> None:
    """关闭本次命令内复用的 live MCP 连接（幂等；mock 模式为空操作）。"""
    for client in _active_live:
        await client.aclose()
    _active_live.clear()


# 离线演示数据使用的样例门店（南京东路）。
# 真实下单/算价时应由上层传入用户实际选中的门店（如门店查询或派对策划结果），
# 而不是无论在哪个城市都按这一家门店计价。
DEFAULT_STORE_ID = "ST_NJDL"
DEFAULT_STORE_NAME = "麦当劳南京东路步行街餐厅"


def _pick(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _num(v: Any, default: float = 0.0) -> float:
    """从数字或 '30g'、'620kcal'、'1,200mg'、'¥26.5' 等带单位字符串中取数。"""
    if v is None or v == "":
        return default
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d+(?:\.\d+)?", str(v).replace(",", ""))
    return float(m.group()) if m else default


def parse_meal(d: dict[str, Any]) -> Meal:
    """容错地把一份餐品 JSON 解析为 Meal（兼容官方字段命名差异）。"""
    return Meal(
        code=str(_pick(d, "code", "mealCode", "sku", "itemCode", "id", default="")),
        name=str(_pick(d, "name", "mealName", "goodsName", "title", default="未知餐品")),
        category=str(_pick(d, "category", "categoryName", "cat", default="")),
        energy_kcal=_num(_pick(d, "energy_kcal", "energyKcal", "energy", "kcal", "calorie")),
        protein_g=_num(_pick(d, "protein_g", "proteinG", "protein")),
        fat_g=_num(_pick(d, "fat_g", "fatG", "fat")),
        carbs_g=_num(_pick(d, "carbs_g", "carbsG", "carbohydrate", "carbs")),
        sodium_mg=_num(_pick(d, "sodium_mg", "sodiumMg", "sodium")),
        calcium_mg=_num(_pick(d, "calcium_mg", "calciumMg", "calcium")),
        price=_num(_pick(d, "price", "unitPrice", "amount", "salePrice")),
        tags=list(_pick(d, "tags", "labels", default=[]) or []),
        period=str(_pick(d, "period", "mealPeriod", default="all")),
    )


def parse_coupon(d: dict[str, Any]) -> Coupon:
    return Coupon(
        coupon_id=str(_pick(d, "coupon_id", "couponId", "id", default="")),
        title=str(_pick(d, "title", "name", "couponName", default="优惠券")),
        kind=str(_pick(d, "kind", "type", default="cash")),
        threshold=_num(_pick(d, "threshold", "minAmount", "fullAmount")),
        amount=_num(_pick(d, "amount", "discountAmount", "reduceAmount")),
        discount=_num(_pick(d, "discount", "discountRate", default=1.0), 1.0),
        scope=str(_pick(d, "scope", "scopeName", default="全场")),
        description=str(_pick(d, "description", "desc", default="")),
        claimed=bool(_pick(d, "claimed", "isClaimed", default=False)),
    )


def parse_store(d: dict[str, Any]) -> Store:
    return Store(
        store_id=str(_pick(d, "store_id", "storeId", "id", default="")),
        name=str(_pick(d, "name", "storeName", default="麦当劳餐厅")),
        address=str(_pick(d, "address", "addr", default="")),
        distance_m=int(_num(_pick(d, "distance_m", "distanceM", "distance", default=0))),
        features=list(_pick(d, "features", "services", "support", default=[]) or []),
    )


class McD:
    """麦当劳业务门面：所有方法都是对 MCP 工具的编排。"""

    def __init__(self, server: Any, mode: str) -> None:
        self.server = server
        self.mode = mode

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    async def call(self, name: str, **arguments: Any) -> Any:
        res = await self.server.call_tool(name, arguments)
        if isinstance(res, dict) and res.get("ok") is False:
            raise RuntimeError(res.get("error", f"{name} 调用失败"))
        return res.get("data", res) if isinstance(res, dict) else res

    # —— 基础 ——
    async def now(self) -> dict[str, Any]:
        return await self.call("now-time-info")

    async def tools(self) -> list[str]:
        return await self.server.tools()

    # —— 菜单 / 营养 ——
    async def meals(self, period: str = "regular", category: str | None = None) -> list[Meal]:
        data = await self.call("list-nutrition-foods", period=period, category=category)
        rows = data.get("foods", data if isinstance(data, list) else []) if isinstance(data, dict) else data
        return [parse_meal(r) for r in (rows or [])]

    async def meal(self, code: str) -> Meal | None:
        for m in await self.meals("regular"):
            if m.code == code:
                return m
        # 早餐等其他时段再找一遍
        for m in await self.meals("breakfast"):
            if m.code == code:
                return m
        return None

    # —— 门店 / 地址 ——
    async def stores(self) -> list[Store]:
        data = await self.call("query-nearby-stores")
        rows = data.get("stores", []) if isinstance(data, dict) else data
        return sorted((parse_store(r) for r in (rows or [])), key=lambda s: s.distance_m)

    async def addresses(self) -> list[Address]:
        data = await self.call("delivery-query-addresses")
        rows = data.get("addresses", []) if isinstance(data, dict) else []
        return [Address(**{k: r.get(k) for k in ("address_id", "contact", "phone", "address", "detail")}) for r in rows]

    # —— 优惠券 ——
    async def available_coupons(self) -> list[Coupon]:
        data = await self.call("available-coupons")
        rows = data.get("available", []) if isinstance(data, dict) else []
        return [parse_coupon(r) for r in rows]

    async def my_coupons(self) -> list[Coupon]:
        data = await self.call("query-my-coupons")
        rows = data.get("coupons", []) if isinstance(data, dict) else []
        return [parse_coupon(r) for r in rows]

    async def auto_bind(self) -> dict[str, Any]:
        return await self.call("auto-bind-coupons")

    async def all_usable_coupons(self) -> list[Coupon]:
        """领券后账户内全部可用券（省钱流程用）。"""
        await self.auto_bind()
        return await self.my_coupons()

    # —— 价格 / 订单 ——
    async def calc_price(
        self,
        items: list[dict[str, Any]],
        channel: str = "到店取餐",
        coupon_ids: list[str] | None = None,
        store_id: str = DEFAULT_STORE_ID,
    ) -> PriceBreakdown:
        data = await self.call("calculate-price", store_id=store_id, channel=channel,
                               items=items, coupon_ids=coupon_ids or [])
        return PriceBreakdown(
            subtotal=_num(data.get("subtotal")),
            delivery_fee=_num(data.get("delivery_fee")),
            discount=_num(data.get("discount")),
            total=_num(data.get("total")),
            applied_coupons=list(data.get("applied_coupons", [])),
            lines=list(data.get("lines", [])),
        )

    async def create_order(self, items, channel="到店取餐", coupon_ids=None,
                          store_id=DEFAULT_STORE_ID, store_name=DEFAULT_STORE_NAME) -> dict[str, Any]:
        return await self.call("create-order", store_id=store_id, store_name=store_name,
                               channel=channel, items=items, coupon_ids=coupon_ids or [])

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        return await self.call("cancel-order", order_id=order_id)

    async def query_order(self, order_id: str) -> dict[str, Any]:
        return await self.call("query-order", order_id=order_id)

    async def order_list(self) -> list[dict[str, Any]]:
        data = await self.call("order-list")
        return data.get("orders", []) if isinstance(data, dict) else []

    # —— 活动 ——
    async def campaigns(self, status: str | None = None) -> list[Campaign]:
        data = await self.call("campaign-calendar", status=status)
        rows = data.get("campaigns", []) if isinstance(data, dict) else []
        return [Campaign(**{k: r.get(k) for k in ("title", "start", "end", "status", "tag", "description")}) for r in rows]

    # —— 积分 / 商城 / 抽奖 ——
    async def account(self) -> PointsAccount:
        data = await self.call("query-my-account")
        p = data.get("points", data) if isinstance(data, dict) else {}
        return PointsAccount(
            available=int(_num(p.get("available"))),
            total_earned=int(_num(p.get("total_earned"))),
            frozen=int(_num(p.get("frozen"))),
            expiring=int(_num(p.get("expiring"))),
        )

    async def mall_products(self) -> list[MallProduct]:
        data = await self.call("mall-points-products")
        rows = data.get("products", []) if isinstance(data, dict) else []
        out = []
        for r in rows:
            out.append(MallProduct(
                product_id=str(_pick(r, "product_id", "productId", "id", default="")),
                name=str(_pick(r, "name", "productName", default="商品")),
                points=int(_num(_pick(r, "points", "pointPrice", default=0))),
                cash_price=_num(_pick(r, "cash_price", "cashPrice", "price")),
                category=str(_pick(r, "category", default="")),
                stock=int(_num(_pick(r, "stock", default=0))),
                description=str(_pick(r, "description", "desc", default="")),
            ))
        return out

    async def redeem(self, product_id: str) -> dict[str, Any]:
        return await self.call("mall-create-order", product_id=product_id)

    async def lottery_info(self) -> dict[str, Any]:
        return await self.call("query-lottery-info")

    async def draw(self) -> dict[str, Any]:
        return await self.call("draw-lottery")

    async def prizes(self) -> list[dict[str, Any]]:
        data = await self.call("query-my-prizes")
        return data.get("prizes", []) if isinstance(data, dict) else []

    # —— 主题派对（麦麦派对策划师） ——
    async def party_cities(self) -> list[str]:
        data = await self.call("query-party-city")
        return data.get("cities", []) if isinstance(data, dict) else []

    async def party_stores(self, city: str) -> list[PartyStore]:
        """城市下可参与主题活动的门店（结构化，含距离 / 营业状态）。"""
        data = await self.call("query-party-store", city=city)
        raw = data.get("stores", []) if isinstance(data, dict) else []
        out: list[PartyStore] = []
        for s in raw:
            if not isinstance(s, dict):
                continue
            status = s.get("businessStatus", s.get("business_status", 1))
            out.append(PartyStore(
                code=str(_pick(s, "code", "storeCode", default="")),
                name=str(_pick(s, "name", "storeName", default="未知门店")),
                city_code=str(_pick(s, "cityCode", "city_code", default="")),
                city_name=str(_pick(s, "cityName", "city_name", default="")),
                address=str(_pick(s, "address", "storeAddress", default="")),
                distance_m=int(_num(_pick(s, "distance", "distanceM", default=0))),
                distance_text=str(_pick(s, "distanceText", "distance_text", default="")),
                business_status=status not in (0, False, "0", "false", "closed"),
            ))
        return out

    async def party_dates(self, store: str) -> list[str]:
        data = await self.call("query-partystore-date", store=store)
        dates = data.get("dates", []) if isinstance(data, dict) else []
        if dates and isinstance(dates[0], dict):
            return [str(d.get("date", d.get("dateStr", ""))) for d in dates if isinstance(d, dict)]
        return [str(d) for d in dates]

    async def party_sessions(self, store: str, date: str) -> list[PartySession]:
        """门店 + 日期下的可约场次（结构化：人数范围 / 价格 / 剩余名额）。"""
        data = await self.call("query-partystore-session", store=store, date=date)
        raw = data.get("sessions", []) if isinstance(data, dict) else []
        out: list[PartySession] = []
        for s in raw:
            if not isinstance(s, dict):
                continue
            out.append(PartySession(
                id=int(_num(_pick(s, "id", "sessionId", default=0))),
                time_start=str(_pick(s, "timeStart", "startTime", default="")),
                time_end=str(_pick(s, "timeEnd", "endTime", default="")),
                party_min=int(_num(_pick(s, "partyMin", "minPeople", "party_min", default=1))),
                party_max=int(_num(_pick(s, "partyMax", "maxPeople", "party_max", default=10))),
                price=round(_num(_pick(s, "price", "pricePerPerson", "perPrice", default=0)) / 100.0, 2),
                left_num=int(_num(_pick(s, "leftNum", "remainNum", "left_num", default=0))),
            ))
        return out

    async def party_book(self, city, store, date, session, people) -> dict[str, Any]:
        return await self.call("party-order-create", city=city, store=store,
                               date=date, session=session, people=people)
