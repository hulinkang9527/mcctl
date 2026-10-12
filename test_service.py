"""服务层结果解析容错测试（兼容官方 MCP 字段命名差异）。"""
from mcctl.service import parse_coupon, parse_meal, parse_store


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
