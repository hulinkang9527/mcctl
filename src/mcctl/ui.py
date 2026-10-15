"""终端渲染（rich）：ASCII 横幅、表格、人格卡、价格单、订单等。"""
from __future__ import annotations

import json
from typing import Any

from rich.box import HEAVY_HEAD, ROUNDED
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

MCD_GOLD = "#FFC72C"
MCD_RED = "#DA291C"
MCD_GREEN = "#2E9E5B"

console = Console()

BANNER = """[bold #FFC72C]
 ███╗   ███╗ ██████╗ ██████╗████████╗██╗
 ████╗ ████║██╔════╝██╔════╝╚══██╔══╝██║
 ██╔████╔██║██║     ██║        ██║   ██║
 ██║╚██╔╝██║██║     ██║        ██║   ██║
 ██║ ╚═╝ ██║╚██████╗╚██████╗   ██║   ███████╗
 ╚═╝     ╚═╝ ╚═════╝ ╚═════╝   ╚═╝   ╚══════╝[/bold #FFC72C]
[bold white]麦门控制面[/bold white] · [bold #DA291C]The kubectl for McDonald's[/bold #DA291C] 🍔🍟🥤"""


def show_banner(mode: str) -> None:
    tag = {
        "live": "[bold white on #2E9E5B] LIVE 官方实时数据 [/]",
        "mock": "[bold black on #FFC72C] DEMO 离线演示数据 [/]",
        "mock-fallback": "[bold black on #FFC72C] DEMO 连接失败已降级·离线演示 [/]",
    }.get(mode, mode)
    console.print(Panel.fit(BANNER + "\n" + tag, border_style=MCD_GOLD, padding=(0, 2)))


def info(msg: str) -> None:
    console.print(f"[bold {MCD_GOLD}]›[/bold {MCD_GOLD}] {msg}")


def warn(msg: str) -> None:
    console.print(f"[bold {MCD_RED}]![/bold {MCD_RED}] {msg}")


def print_json(data: Any) -> None:
    console.print_json(json.dumps(data, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
def table_meals(meals: list[dict[str, Any]], title: str = "可售餐品") -> Table:
    t = Table(title=title, box=ROUNDED, header_style=f"bold {MCD_GOLD}", expand=False)
    for col, justify in [("餐品", "left"), ("分类", "left"), ("热量kcal", "right"),
                         ("蛋白g", "right"), ("脂肪g", "right"), ("钠mg", "right"),
                         ("价格¥", "right"), ("标签", "left")]:
        t.add_column(col, justify=justify, no_wrap=(col not in ("餐品", "标签")))
    for m in meals:
        t.add_row(m["name"], m.get("category", ""), str(int(m.get("energy_kcal", 0))),
                  str(m.get("protein_g", 0)), str(m.get("fat_g", 0)),
                  str(int(m.get("sodium_mg", 0))), f"{m.get('price', 0):.0f}",
                  "·".join(m.get("tags", [])[:3]))
    return t


def table_coupons(coupons: list[dict[str, Any]], title: str = "优惠券") -> Table:
    t = Table(title=title, box=ROUNDED, header_style=f"bold {MCD_GOLD}")
    t.add_column("券名"); t.add_column("类型"); t.add_column("门槛/优惠", justify="right"); t.add_column("范围")
    for c in coupons:
        rule = (f"满{c['threshold']:g}减{c['amount']:g}" if c["kind"] == "cash"
                else f"{c['discount']*10:.0f}折" if c["kind"] == "discount" else "赠品/升级")
        t.add_row(c["title"], {"cash": "满减", "discount": "折扣", "gift": "赠品"}.get(c["kind"], c["kind"]),
                  rule, c.get("scope", ""))
    return t


def table_stores(stores: list[dict[str, Any]]) -> Table:
    t = Table(title="附近门店（由近及远）", box=ROUNDED, header_style=f"bold {MCD_GOLD}")
    t.add_column("门店"); t.add_column("地址"); t.add_column("距离", justify="right"); t.add_column("服务")
    name_map = {"delivery": "外送", "pickup": "取餐", "drivethru": "得来速",
                "breakfast": "早餐", "party": "派对", "dinein": "堂食"}
    for s in stores:
        t.add_row(s["name"], s.get("address", ""), f"{s.get('distance_km', 0)} km",
                  "/".join(name_map.get(x, x) for x in s.get("features", [])))
    return t


def render_price(bd: dict[str, Any], title: str = "价格明细") -> Panel:
    t = Table(box=ROUNDED, show_header=True, header_style=f"bold {MCD_GOLD}")
    t.add_column("餐品"); t.add_column("数量", justify="right"); t.add_column("小计¥", justify="right")
    for ln in bd.get("lines", []):
        t.add_row(ln["name"], f"×{ln['qty']}", f"{ln['line_total']:.2f}")
    t.add_row("", "", "")
    t.add_row("商品合计", "", f"{bd['subtotal']:.2f}")
    t.add_row("配送费", "", f"{bd.get('delivery_fee', 0):.2f}")
    if bd.get("discount"):
        t.add_row("[#2E9E5B]优惠[/]", "", f"[#2E9E5B]-{bd['discount']:.2f}[/]")
    t.add_row("[bold]应付合计[/]", "", f"[bold {MCD_RED}]¥{bd['total']:.2f}[/]")
    sub = f"[#2E9E5B]已用券：{'、'.join(bd.get('applied_coupons', []))}[/]" if bd.get("applied_coupons") else ""
    gifts = f"赠品：{'、'.join(bd.get('gifts', []))}" if bd.get("gifts") else ""
    return Panel(t, title=f"[bold]{title}[/]", subtitle=" ".join(x for x in (sub, gifts) if x),
                 border_style=MCD_GOLD)


def render_order(o: dict[str, Any]) -> Panel:
    body = Text()
    body.append(f"订单号：{o.get('order_id')}\n", style="bold")
    body.append(f"状态：{o.get('status')}　渠道：{o.get('channel')}　门店：{o.get('store_name','')}\n")
    body.append(f"预计：{o.get('eta','')}\n")
    body.append(f"应付：¥{o.get('total', 0):.2f}", style=f"bold {MCD_RED}")
    if o.get("pay_url"):
        body.append(f"\n支付链接：{o['pay_url']}", style="underline #006DB6")
    return Panel(body, title="🧾 订单", border_style=MCD_RED)


def table_campaigns(camps: list[dict[str, Any]]) -> Table:
    t = Table(title="麦当劳活动日历", box=ROUNDED, header_style=f"bold {MCD_GOLD}")
    t.add_column("状态"); t.add_column("活动"); t.add_column("时间"); t.add_column("说明")
    style = {"ongoing": "[bold #2E9E5B]进行中[/]", "upcoming": "[bold]即将开始[/]", "past": "[dim]已结束[/]"}
    for c in camps:
        t.add_row(style.get(c["status"], c["status"]),
                  f"{c['title']}\n[dim]{c.get('tag','')}[/]",
                  f"{c['start']}\n~{c['end']}", c.get("description", ""))
    return t


def table_party_plans(plans: list[dict[str, Any]], city: str = "", people: int = 0) -> Table:
    """麦麦派对策划师：候选方案表。"""
    t = Table(title=f"🎉 派对策划方案（{city or '·'} · {people}人）",
              box=ROUNDED, header_style=f"bold {MCD_GOLD}", expand=False)
    for col, justify in [("#", "right"), ("门店", "left"), ("日期", "left"), ("场次", "left"),
                         ("总价¥", "right"), ("人均¥", "right"), ("推荐理由", "left")]:
        t.add_column(col, justify=justify, no_wrap=(col in ("#", "总价¥", "人均¥", "场次")))
    for i, p in enumerate(plans, 1):
        s = p["store"]
        store = s["name"]
        if s.get("distance_text"):
            store = f"{s['name']} [dim]({s['distance_text']})[/]"
        t.add_row(str(i), store, p["date"], f"{p['session']['time_start']}-{p['session']['time_end']}",
                  f"{p['total_price']:.2f}", f"{p['per_person']:.2f}",
                  "\n".join(f"✓ {r}" for r in p.get("reasons", [])))
    return t


def render_account(p: dict[str, Any], products: list[dict[str, Any]] | None = None) -> Panel:
    t = Table(box=ROUNDED, show_header=False)
    t.add_column(no_wrap=True); t.add_column(justify="right")
    t.add_row("可用积分", f"[bold {MCD_GOLD}]{p['available']}[/]")
    t.add_row("累计积分", str(p.get("total_earned", 0)))
    t.add_row("冻结积分", str(p.get("frozen", 0)))
    t.add_row("即将过期", f"[bold {MCD_RED}]{p.get('expiring', 0)}[/]")
    if products:
        t.add_row("", "")
        t.add_row("[bold]积分可兑（前5）[/]", "")
        for x in products[:5]:
            t.add_row(x["name"], f"{x['points']} 分")
    return Panel(t, title="🪙 我的积分 / 麦麦商城", border_style=MCD_GOLD)


def persona_panel(persona: dict[str, Any], scores: dict[str, int] | None = None,
                  margin: int | None = None, runner_up: str | None = None,
                  explanation: dict[str, Any] | None = None) -> Panel:
    c1, c2 = persona.get("color", [MCD_RED, MCD_GOLD])
    body = Text()
    body.append(f"{persona['emoji']} {persona['name']}（{persona['code']}）\n", style=f"bold {c1}")
    body.append(f"{persona['title']}\n", style="italic")
    body.append(f"「{persona['motto']}」\n\n", style=f"bold {c2}")
    body.append(f"点餐哲学：{persona['philosophy']}\n")
    body.append(f"人格标签：{' / '.join(persona.get('traits', []))}\n")
    body.append(f"幸运暗号：{persona.get('lucky_code','')}\n", style="dim")
    if margin is not None:
        lead = "第二候选人格" if (runner_up and margin == 0) else "第二名"
        body.append(f"鉴定置信度：领先{lead} {margin} 分\n", style="dim")
    if runner_up:
        body.append(f"第二候选人格：{runner_up}\n", style="dim")
    if explanation:
        traits = explanation.get("traits") or []
        if traits:
            body.append("你的答案特点：" + "、".join(
                f"{t['label']}（{t['count']}）" for t in traits) + "\n", style="dim")
        for k in explanation.get("key_questions", []):
            body.append(f"· 第{k['id']}题「{k['q']}」→ {k['choice'].upper()}：{k['text']}\n",
                        style="dim")
    return Panel(body, title="🪪 你的麦麦人格（McPersona）", border_style=c1)


def render_plan(plan: dict[str, Any], persona: dict[str, Any] | None = None) -> Panel:
    t = Table(box=ROUNDED, header_style=f"bold {MCD_GOLD}")
    t.add_column("餐品"); t.add_column("数量", justify="right"); t.add_column("单价¥", justify="right")
    for ln in plan["cart"]:
        t.add_row(ln["name"], f"×{ln['qty']}", f"{ln['unit_price']:.0f}")
    nut = plan["nutrition_total"]
    pp = plan["per_person"]
    t.add_row("", "", "")
    t.add_row(f"[bold]{plan['label']}[/]（{plan['people']}人）", "人均热量", f"{pp['kcal']:.0f} kcal")
    t.add_row("整单合计", f"¥{plan['subtotal']:.2f}", f"人均 ¥{pp['price']:.1f}")
    t.add_row("蛋白/脂肪/碳水", "", f"{nut['protein_g']:.0f}/{nut['fat_g']:.0f}/{nut['carbs_g']:.0f} g")
    t.add_row("钠", "", f"{nut['sodium_mg']:.0f} mg")
    reasons = Text("\n".join(f"✓ {r}" for r in plan.get("reasons", [])), style="dim")
    return Panel(Group(t, reasons), title="🎯 命定套餐", border_style=MCD_GOLD)


# ---------------------------------------------------------------------------
def daily_panel(data: dict[str, Any]) -> Panel:
    """今日麦门运势卡片。"""
    p = data["persona"]
    body = Text()
    body.append(f"📅 {data['date']}　", style="bold")
    body.append(f"今日幸运人格：{p['emoji']} {p['name']}（{p['code']}）\n", style=f"bold {MCD_GOLD}")
    body.append("\n")
    body.append("宜：", style=MCD_GREEN)
    body.append(f"{data['good']}\n")
    body.append("忌：", style=MCD_RED)
    body.append(f"{data['bad']}\n")
    body.append(f"\n「{data['quote']}」\n", style="italic")
    body.append(f"幸运数字：{data['lucky_number']}　", style="bold")
    body.append(f"幸运暗号：{data['lucky_code']}\n", style="dim")
    return Panel(body, title="🥠 今日麦门运势", border_style=MCD_GOLD)


def daily_share_text(data: dict[str, Any]) -> str:
    """可直接转发的纯文本麦门运势。"""
    p = data["persona"]
    return "\n".join([
        "🥠 今日麦门运势 🥓",
        "------------------------------",
        f"📅 {data['date']}",
        f"幸运人格：{p['emoji']} {p['name']}（{p['code']}）",
        f"宜：{data['good']}",
        f"忌：{data['bad']}",
        f"「{data['quote']}」",
        f"幸运数字：{data['lucky_number']}　幸运暗号：{data['lucky_code']}",
        "------------------------------",
        "由 mcctl · 麦门控制面 抽签",
    ])


def roll_panel(data: dict[str, Any]) -> Panel:
    """盲盒点餐结果卡片。"""
    items = data["items"]
    t = Table(box=ROUNDED, show_header=False)
    t.add_column("盲盒", no_wrap=True)
    t.add_column(justify="right")
    icons = ["🍔", "🍟", "🥤"]
    for i, it in enumerate(items):
        icon = icons[i] if i < len(icons) else "·"
        t.add_row(f"{icon} {it['name']}", f"¥{it['price']:.0f}")
    t.add_row("", "")
    t.add_row("合计 / 热量", f"¥{data['price']:.2f} / {data['kcal']:.0f} kcal")
    return Panel(Group(t, Text(f"🎲 {data['mood']}", style="italic")),
                 title="🎰 麦门盲盒（roll）", border_style=MCD_RED)


def pair_panel(data: dict[str, Any]) -> Panel:
    """人格合餐卡片：双人分享装。"""
    a, b = data["persona_a"], data["persona_b"]
    head = Text()
    head.append(f"💞 {a['emoji']} {a['name']}（{a['code']}）", style=f"bold {MCD_GOLD}")
    head.append("  ×  ")
    head.append(f"{b['emoji']} {b['name']}（{b['code']}）\n", style=f"bold {MCD_RED}")
    head.append(f"🎯 {data['verdict']}", style="italic")

    t = Table(box=ROUNDED, show_header=True, header_style=f"bold {MCD_GOLD}")
    t.add_column("合餐"); t.add_column("数量", justify="right"); t.add_column("小计¥", justify="right")
    for ln in data["lines"]:
        t.add_row(ln["name"], f"×{ln['qty']}", f"{ln['line_total']:.2f}")
    t.add_row("", "", "")
    t.add_row("[bold]双人分享装合计[/]", "", f"[bold {MCD_RED}]¥{data['total_price']:.2f}[/]")
    t.add_row("人均（2人）", f"¥{data['per_person_price']:.2f}", f"{data['per_person_kcal']:.0f} kcal")
    if data["overlap"]:
        t.add_row("共享本命餐", "、".join(data["overlap"]), "")
    return Panel(Group(head, t), title="💑 麦门人格合餐", border_style=MCD_GOLD)


def pair_share_text(data: dict[str, Any]) -> str:
    """可转发的纯文本人格合餐。"""
    a, b = data["persona_a"], data["persona_b"]
    items = " + ".join(f"{ln['name']}×{ln['qty']}" for ln in data["lines"])
    return "\n".join([
        "💑 麦门人格合餐",
        "------------------------------",
        f"{a['emoji']} {a['name']}（{a['code']}） × {b['emoji']} {b['name']}（{b['code']}）",
        data["verdict"],
        f"合餐：{items}",
        f"合计 ¥{data['total_price']:.2f}（人均 ¥{data['per_person_price']:.2f} / {data['per_person_kcal']:.0f} kcal）",
        "------------------------------",
        "由 mcctl · 麦门控制面 撮合",
    ])
