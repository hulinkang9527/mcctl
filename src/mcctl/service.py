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
    PartyCity,
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

# 官方在售的主题派对 SPU（麦当劳奇妙生日派对），仅用作「离线演示 / 未指定 --spu」时的兜底；
# 真实模式下由 ``McD.party_products()`` 从 mall-points-products 自动筛出在售派对 SPU。
DEFAULT_PARTY_SPU = 1779


def _party_price(v: Any) -> float:
    """派对场次价格归一化为「每人价格（元）」。

    官方 ``query-party-store-session`` 的 ``price`` 为分（实测 50 元 = 5000），
    离线 Mock 同样按分给数；若上游某天改为直接给元（< 100），这里保持原值不再除。
    """
    raw = _num(v)
    return round(raw / 100.0, 2) if raw >= 100 else round(raw, 2)


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


def _rows(data: Any, *keys: str) -> list[dict[str, Any]]:
    """把工具返回归一化为「行字典列表」。

    官方 MCP 的 ``data`` 多为**裸数组**，而离线 Mock 习惯包一层业务键
    （如 ``{"stores": [...]}``）。这里统一收口，避免解析层只认其中一种形态
    而在真实模式下静默返回空列表。
    """
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for k in (*keys, "list", "items", "data", "rows", "records", "result"):
            v = data.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
    return []


def _all_rows(data: Any) -> list[dict[str, Any]]:
    """字典形态下合并**所有**列表值（官方同一响应里常混装不同集合）。"""
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        out: list[dict[str, Any]] = []
        for v in data.values():
            if isinstance(v, list):
                out.extend(r for r in v if isinstance(r, dict))
        return out
    return []


_CATEGORY_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("早餐", ("麦满分", "早餐", "猪柳蛋", "烟肉蛋", "薯饼")),
    ("主食", ("汉堡", "巨无霸", "麦辣鸡腿", "双牛", "安格斯", "卷", "饭", "堡")),
    ("小食", ("薯条", "鸡块", "鸡翅", "玉米杯", "派", "鸡排", "沙拉", "拼盘", "小食")),
    ("甜点", ("冰淇淋", "圆筒", "新地", "麦旋风", "甜筒", "蛋糕", "松饼")),
    ("饮品", ("可乐", "雪碧", "芬达", "咖啡", "拿铁", "美式", "奶茶", "汁", "水", "茶", "汽水",
             "麦咖啡", "摩卡", "卡布")),
]


def _infer_category(name: str) -> str:
    """真实模式的营养表没有品类字段，按名称关键词兜底归类。

    配餐引擎按「主食 / 小食 / 饮品 / 甜点 / 早餐」分槽位，缺品类会导致
    「没有主食」而直接返回空方案，因此这里必须补齐。
    """
    for cat, keys in _CATEGORY_HINTS:
        if any(k in name for k in keys):
            return cat
    return "小食"


def parse_meal(d: dict[str, Any]) -> Meal:
    """容错地把一份餐品 JSON 解析为 Meal（兼容官方字段命名差异）。"""
    name = str(_pick(d, "name", "mealName", "goodsName", "title", "productName", default="未知餐品"))
    category = str(_pick(d, "category", "categoryName", "cat", default=""))
    if not category and name != "未知餐品":
        category = _infer_category(name)
    return Meal(
        code=str(_pick(d, "code", "mealCode", "sku", "itemCode", "id", "productCode", default="")),
        name=name,
        category=category,
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
        coupon_id=str(_pick(d, "coupon_id", "couponId", "couponCode", "id", default="")),
        title=str(_pick(d, "title", "name", "couponName", default="优惠券")),
        kind=str(_pick(d, "kind", "type", "couponType", default="cash")),
        threshold=_num(_pick(d, "threshold", "minAmount", "fullAmount")),
        amount=_num(_pick(d, "amount", "discountAmount", "reduceAmount")),
        discount=_num(_pick(d, "discount", "discountRate", default=1.0), 1.0),
        scope=str(_pick(d, "scope", "scopeName", "label", default="全场")),
        description=str(_pick(d, "description", "desc", "label", default="")),
        claimed=bool(_pick(d, "claimed", "isClaimed", default=False)),
    )


def parse_store(d: dict[str, Any]) -> Store:
    distance = int(_num(_pick(d, "distance_m", "distanceM", "distance", default=0)))
    if not distance:
        # 官方部分接口只给 "813m" / "3.6km" 这类文本，这里回退解析
        text = str(_pick(d, "distanceText", "distance_text", default=""))
        num = _num(text)
        if num:
            distance = int(num * 1000) if "km" in text.lower() else int(num)
    return Store(
        store_id=str(_pick(d, "store_id", "storeId", "code", "storeCode", "id", default="")),
        name=str(_pick(d, "name", "storeName", "shortName", default="麦当劳餐厅")),
        address=str(_pick(d, "address", "addr", default="")),
        distance_m=distance,
        features=list(_pick(d, "features", "services", "support", default=[]) or []),
    )


def parse_nutrition_table(text: str) -> list[dict[str, Any]]:
    """解析官方 ``list-nutrition-foods`` 的**文本表**返回。

    实测真实模式返回的不是 JSON，而是形如::

        [160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
          猪柳麦满分,null,1288,308,16,16,24,781,213
          ...

    这里按「列名声明 + 逗号分隔行」还原为行字典，避免真实模式下菜单为空。
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return []
    header: list[str] = []
    start = 0
    if lines[0].startswith("[") and "{" in lines[0]:
        cols = lines[0].split("{", 1)[1].split("}", 1)[0]
        header = [c.strip() for c in cols.split(",") if c.strip()]
        start = 1
    elif lines[0].startswith("{"):
        header = [c.strip() for c in lines[0].strip("{}:").split(",") if c.strip()]
        start = 1
    if not header:
        return []
    rows: list[dict[str, Any]] = []
    for ln in lines[start:]:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < len(header):
            continue
        rows.append(dict(zip(header, parts)))
    return rows



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
        data = res.get("data", res) if isinstance(res, dict) else res
        # 官方业务失败（success=false）过去会被下游当成「空结果」静默吞掉，
        # 曾导致真实模式下派对策划显示「没有方案」而不是报错；这里显式抛出。
        if isinstance(data, dict) and data.get("success") is False:
            raise RuntimeError(f"{name} 调用失败：{data.get('message') or data.get('code') or '接口返回 success=false'}")
        return data

    # —— 基础 ——
    async def now(self) -> dict[str, Any]:
        return await self.call("now-time-info")

    async def tools(self) -> list[str]:
        return await self.server.tools()

    # —— 菜单 / 营养 ——
    async def meals(self, period: str = "regular", category: str | None = None) -> list[Meal]:
        """餐品列表。

        真实模式的坑：官方 ``list-nutrition-foods`` 既不需要参数，返回的也是
        ``data`` 里的一整段**文本表**（``[160]{productName,...}:`` + 逗号分隔行），
        而不是 JSON 数组。这里先把带参调用解析一遍，解析不到再按无参重试。
        """
        data = await self.call("list-nutrition-foods", period=period, category=category)
        rows = self._nutrition_rows(data)
        if not rows:
            data = await self.call("list-nutrition-foods")
            rows = self._nutrition_rows(data)
        return [parse_meal(r) for r in rows]

    @staticmethod
    def _nutrition_rows(data: Any) -> list[dict[str, Any]]:
        """从「裸数组 / 字典包裹 / 文本表（含被包在 data 字段里的）」里取出餐品行。"""
        if isinstance(data, str):
            return parse_nutrition_table(data)
        if isinstance(data, dict):
            for key in ("data", "text", "foods", "meals", "list"):
                v = data.get(key)
                if isinstance(v, str):
                    rows = parse_nutrition_table(v)
                    if rows:
                        return rows
            return _rows(data, "foods", "meals")
        return _rows(data, "foods", "meals")

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
        return sorted((parse_store(r) for r in _rows(data, "stores")), key=lambda s: s.distance_m)

    async def addresses(self) -> list[Address]:
        data = await self.call("delivery-query-addresses")
        rows = _rows(data, "addresses")
        return [Address(**{k: r.get(k) for k in ("address_id", "contact", "phone", "address", "detail")}) for r in rows]

    # —— 优惠券 ——
    async def available_coupons(self) -> list[Coupon]:
        data = await self.call("available-coupons")
        return [parse_coupon(r) for r in _rows(data, "available", "coupons")]

    async def my_coupons(self) -> list[Coupon]:
        data = await self.call("query-my-coupons")
        return [parse_coupon(r) for r in _rows(data, "coupons")]

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
        return _rows(data, "orders")

    # —— 活动 ——
    async def campaigns(self, status: str | None = None) -> list[Campaign]:
        data = await self.call("campaign-calendar", status=status)
        rows = _rows(data, "campaigns")
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
        """积分商城可兑换商品（官方返回里的非积分商品，如派对 SPU，会被过滤掉）。"""
        data = await self.call("mall-points-products")
        out = []
        for r in _rows(data, "products", "spus"):
            points = int(_num(_pick(r, "points", "point", "pointPrice", "needPoint", default=0)))
            if points <= 0:
                continue  # 派对/现金类 SPU（point=0）不属于积分兑换商品
            out.append(MallProduct(
                product_id=str(_pick(r, "product_id", "productId", "spuId", "id", default="")),
                name=str(_pick(r, "name", "productName", "spuName", default="商品")),
                points=points,
                cash_price=_num(_pick(r, "cash_price", "cashPrice", "price")),
                category=str(_pick(r, "category", "catName", default="")),
                stock=int(_num(_pick(r, "stock", default=0))),
                description=str(_pick(r, "description", "desc", "selling", default="")),
            ))
        return out

    async def party_products(self) -> list[dict[str, Any]]:
        """在售的主题活动 SPU（``query-party-city`` 等派对工具的必传 ``spuId`` 来源）。

        官方没有独立的「派对商品列表」工具，spuId 需从 ``mall-points-products``
        里按品类筛出（``catName`` 含「派对 / 读书会」等）。
        """
        data = await self.call("mall-points-products")
        out: list[dict[str, Any]] = []
        for r in _all_rows(data):
            name = str(_pick(r, "spuName", "name", "productName", default=""))
            cat = str(_pick(r, "catName", "category", "categoryName", default=""))
            if not any(k in cat or k in name for k in ("派对", "读书会", "团建")):
                continue
            spu_id = int(_num(_pick(r, "spuId", "spu_id", "product_id", "productId", "id", default=0)))
            if spu_id <= 0:
                continue
            out.append({
                "spu_id": spu_id,
                "name": name or "主题活动",
                "category": cat,
                "price": _num(_pick(r, "price", "cash_price", "cashPrice")),
                "selling": str(_pick(r, "selling", "description", "desc", default="")),
            })
        return out

    async def redeem(self, product_id: str) -> dict[str, Any]:
        return await self.call("mall-create-order", product_id=product_id)

    async def lottery_info(self) -> dict[str, Any]:
        return await self.call("query-lottery-info")

    async def draw(self) -> dict[str, Any]:
        return await self.call("draw-lottery")

    async def prizes(self) -> list[dict[str, Any]]:
        data = await self.call("query-my-prizes")
        return _rows(data, "prizes")

    # —— 主题派对（麦麦派对策划师） ——
    # 官方链路必须逐级透传：spuId（出自 mall-points-products）→ 城市 code + 经纬度
    # → storeCode → dateStr → 场次 id，任一环节用名字代替都会调不通。
    async def party_cities(self, spu_id: int = DEFAULT_PARTY_SPU) -> list[PartyCity]:
        """可参与主题活动的城市（``query-party-city(spuId)``）。"""
        data = await self.call("query-party-city", spuId=spu_id)
        out: list[PartyCity] = []
        for c in _rows(data, "cities"):
            name = str(_pick(c, "name", "cityName", default=""))
            code = str(_pick(c, "code", "cityCode", default=""))
            if not code:
                continue
            out.append(PartyCity(
                code=code,
                name=name or code,
                latitude=_num(_pick(c, "latitude", "lat")),
                longitude=_num(_pick(c, "longitude", "lng", "lon")),
                initial=str(_pick(c, "initial", default="")),
            ))
        return out

    @staticmethod
    def match_city(cities: list[PartyCity], keyword: str) -> PartyCity | None:
        """按城市名（可省略「市」）或城市 code 匹配，便于 CLI 用 ``--city 上海``。"""
        kw = (keyword or "").strip()
        if not kw:
            return None
        for c in cities:
            if kw == c.code or kw == c.name:
                return c
        for c in cities:
            if kw.rstrip("市") == c.name.rstrip("市") or kw in c.name:
                return c
        return None

    async def party_stores(self, spu_id: int, city: PartyCity) -> list[PartyStore]:
        """城市下可参与主题活动的门店（``query-party-store(code, lat, lng, spuId)``）。"""
        data = await self.call("query-party-store", spuId=spu_id, code=city.code,
                               latitude=city.latitude, longitude=city.longitude)
        out: list[PartyStore] = []
        for s in _rows(data, "stores"):
            status = _pick(s, "businessStatus", "business_status", default=1)
            out.append(PartyStore(
                code=str(_pick(s, "code", "storeCode", default="")),
                name=str(_pick(s, "name", "storeName", default="未知门店")),
                city_code=str(_pick(s, "cityCode", "city_code", default=city.code)),
                city_name=str(_pick(s, "cityName", "city_name", default=city.name)),
                address=str(_pick(s, "address", "storeAddress", default="")),
                distance_m=int(_num(_pick(s, "distance", "distanceM", default=0))),
                distance_text=str(_pick(s, "distanceText", "distance_text", default="")),
                business_status=status not in (0, False, "0", "false", "closed"),
            ))
        return sorted(out, key=lambda s: s.distance_m)

    async def party_dates(self, spu_id: int, store_code: str) -> list[str]:
        """门店可预约日期（``query-party-store-date(spuId, storeCode)``）。"""
        data = await self.call("query-party-store-date", spuId=spu_id, storeCode=store_code)
        return [str(_pick(d, "date", "dateStr", default="")) for d in _rows(data, "dates")
                if _pick(d, "date", "dateStr", default="")]

    async def party_sessions(self, spu_id: int, store_code: str, date_str: str) -> list[PartySession]:
        """门店 + 日期下的可约场次（``query-party-store-session(spuId, storeCode, dateStr)``）。"""
        data = await self.call("query-party-store-session", spuId=spu_id,
                               storeCode=store_code, dateStr=date_str)
        out: list[PartySession] = []
        for s in _rows(data, "sessions"):
            out.append(PartySession(
                id=int(_num(_pick(s, "id", "sessionId", default=0))),
                time_start=str(_pick(s, "timeStart", "startTime", default="")),
                time_end=str(_pick(s, "timeEnd", "endTime", default="")),
                party_min=int(_num(_pick(s, "partyMin", "minPeople", "party_min", default=1))),
                party_max=int(_num(_pick(s, "partyMax", "maxPeople", "party_max", default=10))),
                price=_party_price(_pick(s, "price", "pricePerPerson", "perPrice", default=0)),
                left_num=int(_num(_pick(s, "leftNum", "remainNum", "left_num", default=0))),
            ))
        return out

    async def party_book(
        self,
        *,
        spu_id: int,
        city_code: str,
        store_code: str,
        date_str: str,
        session: PartySession,
        people: int,
        party_type: int = 1,
    ) -> dict[str, Any]:
        """预约场次（``party-order-create``）。

        官方必传 ``partyType``（1 包场 / 2 拼团）与场次快照字段，因此这里把
        ``PartySession`` 的 id / 时间 / 余位原样回传，避免服务端校验失败。
        """
        return await self.call(
            "party-order-create",
            partyType=party_type,
            spuId=spu_id,
            storeCode=store_code,
            code=city_code,
            dateStr=date_str,
            id=session.id,
            leftNum=session.left_num,
            timeStart=session.time_start,
            timeEnd=session.time_end,
            count=people,
            partyTimeInfo={
                "id": session.id,
                "timeStart": session.time_start,
                "timeEnd": session.time_end,
                "partyMin": session.party_min,
                "partyMax": session.party_max,
                "price": int(round(session.price * 100)),
                "leftNum": session.left_num,
            },
        )
