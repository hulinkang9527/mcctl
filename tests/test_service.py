"""服务层测试。

覆盖两类真实模式（live）踩过的坑：

1. **返回结构容错**：官方 MCP 的 ``data`` 是裸数组，离线 Mock 是 ``{key: [...]}``
   包裹，解析层必须两种都认，否则真实模式会静默返回空列表。
2. **参数名契约**：派对链路必须按官方 schema 传 ``spuId / code / latitude /
   longitude / storeCode / dateStr``，用业务中文名或自定义参数名传会被服务端拒绝
   （历史上就是这么坏的，且失败被吞成「没有方案」）。
"""
from __future__ import annotations

import asyncio

from mcctl.models import PartySession, PartyStore
from mcctl.service import McD, parse_coupon, parse_meal, parse_nutrition_table, parse_store


def test_parse_meal_standard():
    m = parse_meal({"code": "X1", "name": "测试堡", "category": "主食", "energy_kcal": 500,
                    "protein_g": 25, "price": 22, "tags": ["人气"]})
    assert m.code == "X1" and m.energy_kcal == 500 and m.protein_g == 25 and m.price == 22


def test_parse_meal_alt_keys_and_units():
    m = parse_meal({"mealCode": "Y2", "mealName": "官方命名堡", "energy": "620kcal",
                    "protein": "30g", "unitPrice": "26.5", "tags": ["辣"]})
    assert m.code == "Y2" and m.name == "官方命名堡"
    assert m.energy_kcal == 620 and m.protein_g == 30 and m.price == 26.5


def test_parse_meal_missing_defaults():
    m = parse_meal({"code": "Z3", "name": "三无餐品"})
    assert m.energy_kcal == 0 and m.price == 0 and m.tags == []


def test_parse_coupon_alt_keys():
    c = parse_coupon({"couponId": "CP1", "couponName": "满30减8", "type": "cash",
                      "minAmount": 30, "discountAmount": 8})
    assert c.coupon_id == "CP1" and c.threshold == 30 and c.amount == 8
    assert c.discount_on(30) == 8 and c.discount_on(29) == 0


def test_parse_store():
    s = parse_store({"storeId": "S9", "storeName": "测试餐厅", "distanceM": 1200,
                     "services": ["delivery", "pickup"]})
    assert s.store_id == "S9" and s.distance_m == 1200 and s.distance_km == 1.2
    assert "delivery" in s.features


# --------------------------------------------------------------------------- 假服务端
class SpyServer:
    """记录 ``call_tool`` 的入参，并按工具名返回**官方形态**（裸数组）的数据。"""

    mode = "live"

    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name, arguments=None):
        self.calls.append((name, dict(arguments or {})))
        return {"ok": True, "source": "live", "data": self.responses.get(name)}

    async def tools(self):
        return list(self.responses)

    def args_of(self, name: str) -> dict:
        for n, a in self.calls:
            if n == name:
                return a
        raise AssertionError(f"未调用 {name}，实际调用：{[c[0] for c in self.calls]}")


def _run(coro):
    return asyncio.run(coro)


CITY_ROW = {"code": 310100, "latitude": 31.2304, "longitude": 121.4737,
            "name": "上海市", "initial": "S", "sortNo": 1}
STORE_ROW = {"code": "1960713", "name": "麦当劳安康时代购物广场餐厅", "address": "金州南路 95 号",
             "cityCode": "610900", "cityName": "安康市", "distance": 813, "distanceText": "813m",
             "businessStatus": 1, "onlineBusinessStatus": True}
DATE_ROW = {"date": "2026-10-16", "storeCode": "1960713"}
SESSION_ROW = {"id": 36888219, "timeStart": "12:00", "timeEnd": "13:30", "partyMin": 5,
               "partyMax": 12, "price": 5000, "leftNum": 12}


def _party_server() -> SpyServer:
    return SpyServer({
        "mall-points-products": [{"spuId": 1779, "spuName": "麦当劳奇妙生日派对",
                                  "catName": "生日类派对", "point": "0", "price": "50"},
                                 {"spuId": 9001, "spuName": "巨无霸兑换券", "catName": "餐饮券",
                                  "point": "3000", "price": "0"}],
        "query-party-city": [CITY_ROW],
        "query-party-store": [STORE_ROW],
        "query-party-store-date": [DATE_ROW],
        "query-party-store-session": [SESSION_ROW],
        "party-order-create": {"party_order_id": "PARTY123", "status": "预约成功"},
    })


def test_bare_array_shapes_are_parsed():
    """官方裸数组 vs Mock 字典包裹：两种都要能解析出数据。"""
    bare = SpyServer({"query-nearby-stores": [STORE_ROW]})
    mcd = McD(bare, "live")
    assert [s.store_id for s in _run(mcd.stores())] == ["1960713"]

    wrapped = SpyServer({"query-nearby-stores": {"stores": [STORE_ROW]}})
    assert [s.store_id for s in _run(McD(wrapped, "live").stores())] == ["1960713"]


def test_mall_products_filters_non_points_spu():
    """官方同一响应里混装的 point=0 派对 SPU 不应出现在积分商城里。"""
    mcd = McD(_party_server(), "live")
    products = _run(mcd.mall_products())
    assert [p.product_id for p in products] == ["9001"]
    assert products[0].points == 3000


def test_party_products_picks_party_spu():
    mcd = McD(_party_server(), "live")
    products = _run(mcd.party_products())
    assert [p["spu_id"] for p in products] == [1779]


def test_party_chain_sends_official_params():
    """派对链路逐级透传：spuId → code+经纬度 → storeCode → dateStr。"""
    spy = _party_server()
    mcd = McD(spy, "live")

    cities = _run(mcd.party_cities(1779))
    assert spy.args_of("query-party-city") == {"spuId": 1779}
    assert cities[0].code == "310100" and cities[0].latitude == 31.2304

    city = McD.match_city(cities, "上海")          # 名字（可省略「市」）→ 带 code/经纬度的对象
    assert city is not None and city.code == "310100"

    stores = _run(mcd.party_stores(1779, city))
    assert spy.args_of("query-party-store") == {
        "spuId": 1779, "code": "310100", "latitude": 31.2304, "longitude": 121.4737}
    assert stores[0].code == "1960713" and stores[0].business_status

    dates = _run(mcd.party_dates(1779, stores[0].code))
    assert spy.args_of("query-party-store-date") == {"spuId": 1779, "storeCode": "1960713"}
    assert dates == ["2026-10-16"]

    sessions = _run(mcd.party_sessions(1779, stores[0].code, dates[0]))
    assert spy.args_of("query-party-store-session") == {
        "spuId": 1779, "storeCode": "1960713", "dateStr": "2026-10-16"}
    # price 官方口径为分（实测 50 元 = 5000），service 层归一化为元
    assert sessions[0].price == 50.0 and sessions[0].left_num == 12


def test_party_book_sends_session_snapshot():
    spy = _party_server()
    mcd = McD(spy, "live")
    session = PartySession(id=36888219, time_start="12:00", time_end="13:30",
                           party_min=5, party_max=12, price=50.0, left_num=12)
    order = _run(mcd.party_book(spu_id=1779, city_code="610900", store_code="1960713",
                                date_str="2026-10-16", session=session, people=8))
    assert order["party_order_id"] == "PARTY123"
    args = spy.args_of("party-order-create")
    assert args["partyType"] == 1 and args["spuId"] == 1779 and args["code"] == "610900"
    assert args["storeCode"] == "1960713" and args["dateStr"] == "2026-10-16"
    assert args["id"] == 36888219 and args["leftNum"] == 12 and args["count"] == 8
    assert args["partyTimeInfo"]["timeStart"] == "12:00"


def test_match_city_by_name_or_code():
    cities = _run(McD(_party_server(), "live").party_cities(1779))
    assert McD.match_city(cities, "310100") is cities[0]
    assert McD.match_city(cities, "上海") is cities[0]      # 省略「市」
    assert McD.match_city(cities, "上海市") is cities[0]
    assert McD.match_city(cities, "火星") is None
    assert McD.match_city(cities, "") is None


def test_party_stores_sorted_by_distance():
    near = dict(STORE_ROW, code="A", distance=300)
    far = dict(STORE_ROW, code="B", distance=5200)
    spy = SpyServer({"query-party-store": [far, near]})
    stores = _run(McD(spy, "live").party_stores(1779, _city_stub()))
    assert [s.code for s in stores] == ["A", "B"]


def _city_stub():
    from mcctl.models import PartyCity
    return PartyCity(code="310100", name="上海市", latitude=31.23, longitude=121.47)


# --------------------------------------------------------------------------- 真实模式返回形态
NUTRITION_TEXT = """[160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
  猪柳麦满分,null,1288,308,16,16,24,781,213
  中薯条,null,1210,289,4,12,38,165,18
  圆筒冰淇淋,null,391,93,2,3,14,36,77
"""


def test_live_nutrition_text_table_is_parsed():
    """官方 list-nutrition-foods 返回文本表（不是 JSON），必须能还原成餐品列表。"""
    rows = parse_nutrition_table(NUTRITION_TEXT)
    assert len(rows) == 3
    m = parse_meal(rows[0])
    assert m.name == "猪柳麦满分" and m.energy_kcal == 308
    assert m.protein_g == 16 and m.fat_g == 16 and m.carbs_g == 24
    assert m.sodium_mg == 781 and m.calcium_mg == 213


def test_meals_handles_text_table_response():
    spy = SpyServer({"list-nutrition-foods": NUTRITION_TEXT})
    meals = _run(McD(spy, "live").meals())
    assert [m.name for m in meals] == ["猪柳麦满分", "中薯条", "圆筒冰淇淋"]


def test_nutrition_table_ignores_malformed_lines():
    assert parse_nutrition_table("") == []
    assert parse_nutrition_table("不是表头的一行") == []
    text = "[2]{a,b}:\n  1,2\n  坏了\n  3,4\n"
    assert parse_nutrition_table(text) == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
