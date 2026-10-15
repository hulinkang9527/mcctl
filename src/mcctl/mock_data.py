"""离线演示数据（mock）。

⚠️ 仅用于无 MCP Token 时的产品演示与自动化测试，数值为贴近公开菜单的
合理近似，**不是麦当劳官方实时数据**。配置真实 Token 后，所有数据改由
麦当劳 MCP（https://mcp.mcd.cn）实时返回，本文件不参与真实流程。
"""
from __future__ import annotations

from mcctl.models import (
    Address,
    Campaign,
    Coupon,
    MallProduct,
    Meal,
    PointsAccount,
    Store,
)

# ---------------------------------------------------------------------------
# 餐品 + 营养（能量 kcal / 蛋白质·脂肪·碳水 g / 钠·钙 mg）+ 展示价
# code 与官方 MCP query-meals / list-nutrition-foods 的餐品编码语义对齐
# ---------------------------------------------------------------------------
MEALS: list[Meal] = [
    # —— 早餐 ——
    Meal("BP_EGG_MCFEN", "吉士蛋麦满分", "早餐", 290, 14, 12, 30, 580, 180, 11.0, ["早餐", "蛋"], "breakfast"),
    Meal("BP_SAUSAGE_MCFEN", "猪柳麦满分", "早餐", 340, 14, 18, 28, 620, 150, 13.0, ["早餐"], "breakfast"),
    Meal("BP_SAUSAGE_EGG", "猪柳蛋麦满分", "早餐", 400, 19, 22, 28, 700, 200, 17.0, ["早餐", "人气", "高蛋白"], "breakfast"),
    Meal("BP_HOTCAKE", "热香饼（3片）", "早餐", 380, 8, 12, 60, 480, 120, 18.0, ["早餐", "甜"], "breakfast"),
    Meal("BP_HASHBROWN", "脆薯饼", "早餐", 150, 2, 9, 16, 320, 20, 6.0, ["早餐", "小食"], "breakfast"),
    Meal("BP_COFFEE", "鲜煮咖啡", "饮品", 5, 0.3, 0, 0.8, 5, 8, 8.0, ["早餐", "咖啡", "低卡", "热"], "all"),
    Meal("BP_LATTE", "拿铁（中）", "饮品", 120, 7, 5, 10, 70, 220, 16.0, ["咖啡", "热"], "all"),
    # —— 主食 / 汉堡 ——
    Meal("BUR_BIGMAC", "巨无霸", "主食", 556, 26, 30, 42, 1000, 250, 24.0, ["招牌", "人气", "牛肉", "经典"], "regular"),
    Meal("BUR_MALA_CHICKEN", "麦辣鸡腿堡", "主食", 500, 24, 25, 46, 1020, 120, 21.0, ["辣", "人气", "鸡肉"], "regular"),
    Meal("BUR_BANSHAO", "板烧鸡腿堡", "主食", 430, 27, 15, 45, 800, 120, 23.0, ["高蛋白", "低脂", "鸡肉", "健身友好"], "regular"),
    Meal("BUR_DOUBLE_CHEESE", "双层吉士汉堡", "主食", 450, 25, 24, 33, 1100, 260, 21.0, ["牛肉", "芝士", "性价比"], "regular"),
    Meal("BUR_ANGUS", "安格斯厚牛培根堡", "主食", 730, 38, 42, 48, 1400, 280, 39.0, ["牛肉", "新品", "高热量", "培根"], "regular"),
    Meal("BUR_CRISPY_CHICKEN", "脆汁鸡鸡腿堡", "主食", 560, 28, 28, 46, 980, 120, 25.0, ["鸡肉", "人气", "夜宵"], "regular"),
    Meal("BUR_FISH", "麦香鱼", "主食", 340, 15, 16, 33, 580, 120, 17.0, ["鱼", "经典", "相对清淡"], "regular"),
    Meal("BUR_MCCHICKEN", "麦香鸡", "主食", 370, 14, 18, 38, 650, 90, 13.0, ["鸡肉", "性价比"], "regular"),
    Meal("BUR_HAM_CHEESE", "吉士汉堡", "主食", 300, 15, 13, 30, 700, 200, 12.0, ["牛肉", "芝士", "小份"], "regular"),
    # —— 小食 ——
    Meal("SIDE_NUGGETS_6", "麦乐鸡（6块）", "小食", 280, 15, 15, 18, 540, 20, 16.0, ["人气", "鸡肉"], "regular"),
    Meal("SIDE_NUGGETS_10", "麦乐鸡（10块）", "小食", 470, 25, 25, 30, 900, 30, 24.0, ["人气", "分享装", "鸡肉"], "regular"),
    Meal("SIDE_FRIES_S", "薯条（小）", "小食", 230, 3, 11, 30, 350, 15, 8.0, ["经典"], "regular"),
    Meal("SIDE_FRIES_M", "薯条（中）", "小食", 340, 4, 16, 45, 520, 20, 11.0, ["经典", "人气"], "regular"),
    Meal("SIDE_FRIES_L", "薯条（大）", "小食", 480, 6, 23, 63, 740, 30, 14.0, ["经典", "分享装"], "regular"),
    Meal("SIDE_SPICY_WINGS", "麦辣鸡翅（2块）", "小食", 240, 15, 16, 8, 600, 15, 14.0, ["辣", "鸡肉"], "regular"),
    Meal("SIDE_JUICY_CHICKEN", "脆汁鸡（1块）", "小食", 220, 18, 12, 10, 480, 15, 13.0, ["高蛋白", "鸡肉"], "regular"),
    Meal("SIDE_APPLE", "苹果片", "小食", 35, 0.3, 0.2, 9, 5, 10, 6.0, ["低卡", "水果", "健康"], "regular"),
    Meal("SIDE_CORN", "杯装玉米粒", "小食", 90, 3, 2, 15, 120, 10, 9.0, ["低卡", "素食", "健康"], "regular"),
    # —— 甜点 ——
    Meal("DESS_MCFLURRY_OREO", "麦旋风（奥利奥）", "甜点", 340, 6, 13, 50, 260, 200, 16.0, ["人气", "甜", "冰"], "regular"),
    Meal("DESS_MCFLURRY_MM", "麦旋风（M&M's）", "甜点", 360, 6, 14, 52, 240, 200, 17.0, ["甜", "冰", "新品"], "regular"),
    Meal("DESS_SUNDAE_CHOC", "新地（巧克力）", "甜点", 290, 6, 8, 48, 180, 200, 12.0, ["甜", "冰"], "regular"),
    Meal("DESS_PIE_PINEAPPLE", "香芋派", "甜点", 260, 3, 14, 31, 300, 20, 7.0, ["甜", "派", "人气"], "regular"),
    Meal("DESS_ICE_CONE", "圆筒冰淇淋", "甜点", 150, 4, 5, 23, 90, 130, 5.0, ["甜", "冰", "性价比"], "regular"),
    # —— 饮品 ——
    Meal("DRK_COLA_M", "可口可乐（中）", "饮品", 210, 0, 0, 52, 15, 10, 11.0, ["冰", "含糖", "经典"], "regular"),
    Meal("DRK_COLA_ZERO", "零度可乐（中）", "饮品", 3, 0, 0, 0, 20, 10, 11.0, ["冰", "无糖", "低卡"], "regular"),
    Meal("DRK_SPRITE", "雪碧（中）", "饮品", 200, 0, 0, 50, 20, 10, 11.0, ["冰", "含糖"], "regular"),
    Meal("DRK_ICED_TEA", "冰红茶（中）", "饮品", 180, 0, 0, 44, 25, 10, 11.0, ["冰", "含糖"], "regular"),
    Meal("DRK_ORANGE", "100%橙汁", "饮品", 170, 2, 0.4, 40, 10, 20, 14.0, ["果汁"], "regular"),
    Meal("DRK_MILK", "纯牛奶", "饮品", 120, 7, 5, 12, 100, 260, 12.0, ["高蛋白", "热", "健康"], "all"),
    Meal("DRK_WATER", "饮用纯净水", "饮品", 0, 0, 0, 0, 0, 5, 7.0, ["低卡", "无糖"], "regular"),
    Meal("DRK_AMERICANO", "美式咖啡（中）", "饮品", 5, 0.3, 0, 0.8, 8, 10, 12.0, ["咖啡", "低卡", "冰/热"], "all"),
]

MEAL_BY_CODE = {m.code: m for m in MEALS}


def meals_for_period(period: str = "regular") -> list[Meal]:
    """按时段过滤可售餐品（all 两个时段都可售）。"""
    return [m for m in MEALS if m.period in ("all", period)]


# ---------------------------------------------------------------------------
# 优惠券（麦麦省 / 门店券）
# ---------------------------------------------------------------------------
# 可领取（available-coupons）
AVAILABLE_COUPONS: list[Coupon] = [
    Coupon("CPN_FULL40_10", "满40元减10元", "cash", 40, 10, scope="全场", description="全场满40元可用，会员专享"),
    Coupon("CPN_FULL25_5", "满25元减5元", "cash", 25, 5, scope="全场", description="全场满25元可用"),
    Coupon("CPN_NUGGET", "麦乐鸡10块 立减8元", "cash", 24, 8, scope="单品", description="仅限麦乐鸡（10块）", apply_codes=["SIDE_NUGGETS_10"]),
    Coupon("CPN_BREAKFAST_GIFT", "早餐随单送脆薯饼", "gift", 15, 0, scope="品类", description="购买早餐主食随单赠送脆薯饼1份"),
    Coupon("CPN_FRIES_UPGRADE", "中薯条免费升级大薯条", "gift", 11, 0, scope="单品", description="购中薯条可免费升级大份"),
    Coupon("CPN_COMBO_6", "小食+饮品组合 立减6元", "cash", 18, 6, scope="组合", description="任意小食搭配中杯饮品"),
]

# 已在账户（query-my-coupons）
MY_COUPONS: list[Coupon] = [
    Coupon("CPN_FULL30_8", "满30元减8元", "cash", 30, 8, scope="全场", description="已领取·会员券", claimed=True),
    Coupon("CPN_ANGUS_15", "安格斯系列 立减15元", "cash", 39, 15, scope="品类", description="已领取·安格斯厚牛系列专用", claimed=True, apply_codes=["BUR_ANGUS"]),
]


# ---------------------------------------------------------------------------
# 门店 / 地址（以上海为例，演示数据）
# ---------------------------------------------------------------------------
STORES: list[Store] = [
    Store("ST_NJDL", "麦当劳南京东路步行街餐厅", "上海市黄浦区南京东路步行街", 420, ["delivery", "pickup", "breakfast", "dinein"]),
    Store("ST_LJZ", "麦当劳陆家嘴环路餐厅", "上海市浦东新区陆家嘴环路近IFC", 860, ["delivery", "pickup", "drivethru", "breakfast", "party"]),
    Store("ST_XJH", "麦当劳徐家汇美罗城餐厅", "上海市徐汇区肇嘉浜路美罗城", 1350, ["delivery", "pickup", "dinein", "breakfast"]),
    Store("ST_JA", "麦当劳静安嘉里中心餐厅", "上海市静安区南京西路嘉里中心", 2100, ["delivery", "pickup", "dinein", "party"]),
    Store("ST_HQ", "麦当劳虹桥火车站餐厅", "上海市闵行区虹桥火车站到达层", 5400, ["delivery", "pickup", "drivethru", "breakfast"]),
]

ADDRESSES: list[Address] = [
    Address("ADDR_1", "麦先生", "138****0000", "上海市浦东新区世纪大道100号", "环球金融中心 66F"),
    Address("ADDR_2", "麦先生", "138****0000", "上海市黄浦区南京东路某弄", "8号 1203室"),
]


# ---------------------------------------------------------------------------
# 活动日历（campaign-calendar，2026-10 程序员节期间，演示数据）
# ---------------------------------------------------------------------------
CAMPAIGNS: list[Campaign] = [
    Campaign("1024 程序员节 · 麦门创意开发大赛", "2026-10-09", "2026-10-25", "ongoing", "M-CODE",
             "基于麦当劳 MCP 开发创意 Skill，Star 榜前列赢巨无霸兑换券与 WorkBuddy 积分。"),
    Campaign("麦辣鸡腿堡 第二个半价", "2026-10-13", "2026-10-26", "ongoing", "辣堡季",
             "活动期间麦辣鸡腿堡第二个半价，嗜辣党拼单正当时。"),
    Campaign("会员日 · 积分翻倍", "2026-10-19", "2026-10-19", "upcoming", "会员日",
             "每周一会员日消费积分双倍累计。"),
    Campaign("程序员节限定 · 巨无霸惊喜价", "2026-10-24", "2026-10-24", "upcoming", "1024",
             "10月24日程序员节当天，巨无霸限时惊喜价（以门店/小程序为准）。"),
    Campaign("麦麦省 · 早餐月卡", "2026-10-08", "2026-11-08", "ongoing", "早餐",
             "早餐月卡用户每日早餐套餐更划算。"),
    Campaign("万圣夜 · 麦旋风新口味", "2026-10-28", "2026-11-03", "upcoming", "新品",
             "万圣节限定麦旋风新口味即将上线。"),
    Campaign("国庆欢聚桶 回归", "2026-09-28", "2026-10-08", "past", "欢聚",
             "国庆期间多人欢聚桶优惠（已结束）。"),
]


# ---------------------------------------------------------------------------
# 积分账户 / 麦麦商城 / 抽奖
# ---------------------------------------------------------------------------
POINTS_ACCOUNT = PointsAccount(available=1280, total_earned=8650, frozen=0, expiring=300)

MALL_PRODUCTS: list[MallProduct] = [
    MallProduct("MALL_BIGMAC", "巨无霸免费兑换券", 3000, 0, "餐饮券", 999, "积分兑换巨无霸1个"),
    MallProduct("MALL_NUGGET", "麦乐鸡（10块）兑换券", 1500, 0, "餐饮券", 999, "积分兑换麦乐鸡10块"),
    MallProduct("MALL_FRIES", "中薯条兑换券", 800, 0, "餐饮券", 999, "积分兑换中薯条1份"),
    MallProduct("MALL_COLA", "中杯可乐兑换券", 500, 0, "饮品券", 999, "积分兑换中杯可乐1杯"),
    MallProduct("MALL_COFFEE_CARD", "McCafé 咖啡5次卡", 2000, 0, "咖啡", 200, "5杯中杯咖啡，30天有效"),
    MallProduct("MALL_TOY", "程序员节限定汉堡回车键", 5000, 0, "周边", 120, "1024程序员节实体周边，数量有限"),
    MallProduct("MALL_BADGE", "程序员节实体徽章", 1200, 0, "周边", 500, "M-CODE 纪念徽章"),
]

# 官方 mall-points-products 除积分商品外，还混装「现金类主题活动 SPU」（point=0、price 有值），
# 派对工具的 spuId 就出自这里；这里按官方字段名（spuId/spuName/catName/price）给一份离线仿真。
PARTY_SPUS: list[dict] = [
    {"spuId": 1779, "spuName": "麦当劳奇妙生日派对", "catName": "生日类派对", "point": "0",
     "price": "50", "shopId": 5, "status": 2, "selling": "上海迪士尼度假区米妮主题",
     "upTime": "2023-03-16 00:00:00", "downTime": "2027-12-31 23:59:59"},
    {"spuId": 8516, "spuName": "麦当劳一起开心鸭尊享版生日派对", "catName": "生日类派对", "point": "0",
     "price": "138", "shopId": 5, "status": 2, "selling": "唐老鸭主题尊享版生日派对",
     "upTime": "2024-10-31 00:00:00", "downTime": "2026-12-31 23:59:59"},
    {"spuId": 1830, "spuName": "麦当劳亲子读书会", "catName": "读书会", "point": "0",
     "price": "45", "shopId": 5, "status": 2, "selling": "一起打造属于你们的亲子阅读时间",
     "upTime": "2023-03-29 00:00:00", "downTime": "2026-12-30 23:59:59"},
]

LOTTERY_INFO = {
    "status": "ongoing",
    "cost_points": 100,
    "title": "麦麦积分幸运抽",
    "prizes": [
        {"name": "巨无霸兑换券", "odds": "0.5%"},
        {"name": "中薯条兑换券", "odds": "5%"},
        {"name": "20积分", "odds": "30%"},
        {"name": "5积分", "odds": "64.5%"},
    ],
    "draws_today": 0,
    "daily_limit": 5,
}
LOTTERY_RATIONAL_NOTE = "抽奖为概率游戏，请理性参与、量力而行，积分更稳妥的用法是直接兑换餐饮券。"
