"""核心数据模型。

字段命名尽量贴近麦当劳 MCP 工具返回的业务语义；真实模式下由
``mcp_client`` 将 MCP ``tools/call`` 返回的 JSON 归一化为这些模型，
离线演示模式下由 ``mock_client`` 直接构造。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Meal:
    """餐品（含营养成分与展示价格）。"""

    code: str
    name: str
    category: str = ""                 # 主食 / 小食 / 甜点 / 饮品 / 早餐 / 套餐
    energy_kcal: float = 0.0           # 能量
    protein_g: float = 0.0             # 蛋白质
    fat_g: float = 0.0                 # 脂肪
    carbs_g: float = 0.0               # 碳水化合物
    sodium_mg: float = 0.0             # 钠
    calcium_mg: float = 0.0            # 钙
    price: float = 0.0                 # 展示价（真实应付以 calculate-price 为准）
    tags: list[str] = field(default_factory=list)
    period: str = "all"                # breakfast / regular / all

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Coupon:
    """优惠券。"""

    coupon_id: str
    title: str
    kind: str = "cash"                 # cash 满减 / discount 折扣 / gift 赠品
    threshold: float = 0.0             # 满 threshold 元可用
    amount: float = 0.0                # 减 amount 元（cash）
    discount: float = 1.0              # 折扣率（discount，如 0.8）
    scope: str = "全场"                # 全场 / 品类 / 单品 / 组合
    description: str = ""
    claimed: bool = False              # 是否已领取到账户
    apply_codes: list[str] = field(default_factory=list)  # 适用餐品 code（空=全场）

    def discount_on(self, subtotal: float, cart_codes: set[str] | None = None) -> float:
        """该券在给定小计金额下能优惠的金额（不满足门槛/不适用于餐篮返回 0）。"""
        if self.apply_codes and cart_codes and not (cart_codes & set(self.apply_codes)):
            return 0.0
        if subtotal + 1e-6 < self.threshold:
            return 0.0
        if self.kind == "cash":
            return min(self.amount, subtotal)
        if self.kind == "discount":
            return round(subtotal * (1 - self.discount), 2)
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Store:
    """麦当劳门店。"""

    store_id: str
    name: str
    address: str = ""
    distance_m: int = 0
    features: list[str] = field(default_factory=list)  # delivery/pickup/drivethru/party/breakfast

    @property
    def distance_km(self) -> float:
        return round(self.distance_m / 1000.0, 2)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["distance_km"] = self.distance_km
        return d


@dataclass
class Address:
    address_id: str
    contact: str
    phone: str
    address: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PriceBreakdown:
    """价格计算结果（calculate-price）。"""

    subtotal: float
    delivery_fee: float = 0.0
    discount: float = 0.0
    total: float = 0.0
    applied_coupons: list[str] = field(default_factory=list)
    lines: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Order:
    order_id: str
    status: str
    channel: str = "到店取餐"          # 麦乐送 / 到店取餐 / 堂食外带 / 得来速 / 主题活动
    items: list[dict[str, Any]] = field(default_factory=list)
    total: float = 0.0
    pay_url: str = ""
    created_at: str = ""
    eta: str = ""
    store_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Campaign:
    """营销活动（campaign-calendar）。"""

    title: str
    start: str
    end: str
    status: str = "ongoing"            # ongoing / upcoming / past
    tag: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PartyCity:
    """主题活动可参与城市（query-party-city，按 spuId 返回）。

    官方返回城市 code + 经纬度，二者都是后续 ``query-party-store`` 的必传参数，
    因此城市不能只用名字传递。
    """

    code: str
    name: str
    latitude: float = 0.0
    longitude: float = 0.0
    initial: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PartyStore:
    """主题活动可参与门店（query-party-store）。

    字段对齐官方 MCP 返回：code / name / address / distance / businessStatus 等。
    """

    code: str
    name: str
    city_code: str = ""
    city_name: str = ""
    address: str = ""
    distance_m: int = 0
    distance_text: str = ""
    business_status: bool = True

    @property
    def distance_km(self) -> float:
        return round(self.distance_m / 1000.0, 2)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["distance_km"] = self.distance_km
        return d


@dataclass
class PartyDate:
    """主题活动可预约日期（query-party-store-date）。"""

    date: str
    store_code: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PartySession:
    """主题活动可预约场次（query-party-store-session）。

    字段对齐官方返回：id / timeStart / timeEnd / partyMin / partyMax / price / leftNum。
    注意：官方示例中 ``price`` 的展示口径（分 / 每人元）随接口版本可能不同，
    本项目统一归一化为「每人价格（元）」，真实模式接入时以官方最新返回为准。
    """

    id: int
    time_start: str
    time_end: str
    party_min: int = 1
    party_max: int = 10
    price: float = 0.0                # 每人价格（元）
    left_num: int = 0                 # 剩余名额

    @property
    def label(self) -> str:
        return f"{self.time_start}-{self.time_end}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PointsAccount:
    available: int = 0
    total_earned: int = 0
    frozen: int = 0
    expiring: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MallProduct:
    product_id: str
    name: str
    points: int = 0
    cash_price: float = 0.0
    category: str = ""
    stock: int = 1
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Combo:
    """引擎产出的套餐组合。"""

    items: list[Meal]
    label: str = ""
    reasons: list[str] = field(default_factory=list)
    coupon: Coupon | None = None
    price: PriceBreakdown | None = None
    persona_code: str = ""

    @property
    def total_kcal(self) -> float:
        return round(sum(m.energy_kcal for m in self.items), 1)

    @property
    def protein_g(self) -> float:
        return round(sum(m.protein_g for m in self.items), 1)

    @property
    def fat_g(self) -> float:
        return round(sum(m.fat_g for m in self.items), 1)

    @property
    def carbs_g(self) -> float:
        return round(sum(m.carbs_g for m in self.items), 1)

    @property
    def sodium_mg(self) -> float:
        return round(sum(m.sodium_mg for m in self.items), 0)

    @property
    def subtotal(self) -> float:
        return round(sum(m.price for m in self.items), 2)

    @property
    def final_price(self) -> float:
        return self.price.total if self.price else self.subtotal

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "persona_code": self.persona_code,
            "items": [m.to_dict() for m in self.items],
            "nutrition": {
                "energy_kcal": self.total_kcal,
                "protein_g": self.protein_g,
                "fat_g": self.fat_g,
                "carbs_g": self.carbs_g,
                "sodium_mg": self.sodium_mg,
            },
            "subtotal": self.subtotal,
            "final_price": self.final_price,
            "coupon": self.coupon.to_dict() if self.coupon else None,
            "price": self.price.to_dict() if self.price else None,
            "reasons": self.reasons,
        }
