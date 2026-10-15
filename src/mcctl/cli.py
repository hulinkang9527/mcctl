"""mcctl 命令行入口。

示例：
  mcctl intro                      # 欢迎页 / 快速上手
  mcctl whoami                     # 麦麦人格测试（交互式）
  mcctl decide                     # 按人格给出命定套餐
  mcctl diet --kcal 600            # 控卡配餐
  mcctl save --cart 巨无霸:1,薯条(中):1   # 一键领券+凑单+到手价
  mcctl order ... --confirm        # 真正下单（默认仅演练，绝不静默下单）
  mcctl points / lottery / calendar / party / tools
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Optional

import typer
from rich.box import ROUNDED
from rich.table import Table

from mcctl import ui
from mcctl.config import Settings
from mcctl.engines import persona as P
from mcctl.engines.fun import fortune, pair as pair_engine, roll as roll_engine
from mcctl.engines.decide import decide as engine_decide
from mcctl.engines.diet import MealConstraints, optimize_meal
from mcctl.engines.party import PartyConstraints, plan_party
from mcctl.engines.save import save_flow
from mcctl.service import DEFAULT_STORE_ID, McD, aclose_servers, get_server

app = typer.Typer(add_completion=True, help="🍔 mcctl — 麦门控制面（kubectl for McDonald's）",
                  no_args_is_help=False, rich_markup_mode="rich")
cart_app = typer.Typer(help="点餐 / 订单相关")
points_app = typer.Typer(help="积分 / 商城 / 抽奖")
party_app = typer.Typer(help="主题派对 / 品鉴会")
app.add_typer(cart_app, name="order")
app.add_typer(points_app, name="points")
app.add_typer(party_app, name="party")


# --------------------------------------------------------------------------- helpers
def _force_mode(ctx: typer.Context) -> Optional[str]:
    g = ctx.obj
    if g.mock:
        return "mock"
    if g.live:
        return "live"
    return None


async def _make_mcd(force: Optional[str]) -> tuple[McD, str]:
    settings = Settings.load(mode=force)
    server, mode = await get_server(settings)
    return McD(server, mode), mode


def _run(coro):
    async def _guarded():
        try:
            return await coro
        finally:
            # 命令结束（含异常）后，在同一 event loop 内关闭复用的 live MCP 连接
            await aclose_servers()

    try:
        return asyncio.run(_guarded())
    except (ConnectionError, RuntimeError) as exc:
        # 连接 / 鉴权 / 限流类失败：收敛为干净的一行提示，不暴露 SDK 堆栈
        ui.warn(f"✗ {exc}")
        raise typer.Exit(code=2)


def _emit(ctx: typer.Context, data, rich_func=None):
    if ctx.obj.json_out:
        ui.print_json(data)
    elif rich_func:
        rich_func(data)


def _norm_name(s: str) -> str:
    """归一化餐品名：去半角/全角括号与空格，便于中文模糊匹配。"""
    return (s.replace("(", "").replace("（", "").replace(")", "")
             .replace("）", "").replace(" ", "").strip())


def _parse_cart(text: str, meals) -> list[dict]:
    """把 'CODE:qty,中文名:qty' 解析为 [{code,qty}]，支持中文模糊匹配。"""
    by_name = sorted(meals, key=lambda m: -len(m.name))
    norm = {m.code: _norm_name(m.name) for m in meals}
    cart, unknown = [], []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            key, qty = part.rsplit(":", 1)
        elif "：" in part:
            key, qty = part.rsplit("：", 1)
        else:
            key, qty = part, "1"
        key = key.strip()
        try:
            qty = int(qty.strip())
        except ValueError:
            ui.warn(f"数量非法：{key}:{qty.strip()}（数量应为整数，已忽略该项）")
            continue
        if qty <= 0:
            ui.warn(f"数量需为正整数：{key}:{qty}（已忽略该项）")
            continue
        m = next((x for x in meals if x.code.upper() == key.upper()), None)
        if not m:
            nk = _norm_name(key)
            # 精确归一化名优先；否则在包含匹配中选名称最短者，同长优先"中份/人气"
            exact = [x for x in meals if norm[x.code] == nk]
            contained = [x for x in meals if nk in norm[x.code] or norm[x.code] in nk]
            pool = exact or contained
            if pool:
                m = sorted(pool, key=lambda x: (len(norm[x.code]),
                                                0 if "中" in x.name else 1,
                                                0 if "人气" in x.tags else 1))[0]
        if not m:
            unknown.append(key)
            continue
        cart.append({"code": m.code, "name": m.name, "qty": qty})
    if unknown:
        ui.warn(f"未识别餐品：{'、'.join(unknown)}（将忽略）")
    return cart


def _require_confirm(ctx: typer.Context, confirmed: bool, what: str, dry_preview) -> bool:
    """安全护栏：未显式 --confirm 时只演练，不产生真实交易。"""
    if confirmed:
        return True
    if ctx.obj.json_out:
        ui.print_json({"dry_run": True, "would": what, "preview": dry_preview})
    else:
        ui.warn(f"安全护栏：未加 --confirm，仅演练不执行 → {what}")
        ui.console.print(dry_preview)
        ui.console.print("[dim]确认无误后追加 --confirm 执行（真实环境将跳转官方支付，不会自动扣款）。[/dim]")
    return False


# --------------------------------------------------------------------------- root
@app.callback()
def main(
    ctx: typer.Context,
    mock: bool = typer.Option(False, "--mock", help="强制使用离线演示数据（无需 Token）"),
    live: bool = typer.Option(False, "--live", help="强制连接麦当劳官方 MCP"),
    json_out: bool = typer.Option(False, "--json", help="输出机器可读 JSON"),
    token: Optional[str] = typer.Option(None, "--token", help="麦当劳 MCP Token（也可用环境变量）"),
):
    ctx.obj = SimpleNamespace(mock=mock, live=live, json_out=json_out, token=token)
    if token:
        import os
        os.environ["MCD_MCP_TOKEN"] = token
    if ctx.invoked_subcommand is None:
        _run(_intro(ctx))


async def _intro(ctx: typer.Context) -> None:
    mcd, mode = await _make_mcd(_force_mode(ctx))
    if not ctx.obj.json_out:
        ui.show_banner(mode)
        ui.console.print(
            "[bold]30 秒上手[/bold]\n"
            "  1. mcctl whoami                 测一测你的麦麦人格，生成可分享麦籍卡\n"
            "  2. mcctl decide                 按人格 + 实时菜单给出命定套餐\n"
            "  3. mcctl diet --kcal 600        控卡/高蛋白配餐\n"
            "  4. mcctl save --cart 巨无霸:1   一键领券·凑单·算到手价\n"
            "  5. mcctl order ... --confirm    确认后安全下单，返回官方支付链接\n"
            "  6. mcctl points / lottery       积分精算 / 抽奖（理性提示）\n"
            "  7. mcctl calendar / party       活动雷达 / 主题派对预约\n\n"
            "  [dim]所有命令加 --json 可输出结构化数据；加 --mock 使用离线演示数据。[/dim]\n"
            "  [dim]配置麦当劳 MCP Token 后自动切换官方实时数据：https://open.mcd.cn/mcp[/dim]"
        )
    else:
        ui.print_json({"name": "mcctl", "mode": mode, "commands": [
            "whoami", "decide", "diet", "menu", "stores", "coupons", "save",
            "order", "points", "lottery", "calendar", "party", "tools"]})


@app.command("intro")
def intro_cmd(ctx: typer.Context):
    """欢迎页与快速上手。"""
    _run(_intro(ctx))


# --------------------------------------------------------------------------- 人格
@app.command("personas")
def personas_cmd(ctx: typer.Context):
    """列出全部 8 型麦麦人格。"""
    data = P.all_personas()
    if ctx.obj.json_out:
        ui.print_json(data)
        return
    t = Table(title="麦麦人格图鉴（McPersona Index）", box=ROUNDED, header_style=f"bold {ui.MCD_GOLD}")
    t.add_column("代号"); t.add_column("人格"); t.add_column("头衔"); t.add_column("本命一餐")
    for p in data:
        t.add_row(p["code"], f"{p['emoji']} {p['name']}", p["title"], " + ".join(p["signature_meal"][:3]))
    ui.console.print(t)


@app.command("whoami")
def whoami_cmd(
    ctx: typer.Context,
    from_answers: Optional[str] = typer.Option(None, "--from", help="直接给答案串，如 aabbaabbaa"),
    do_random: bool = typer.Option(False, "--random", help="命运随机作答"),
    persona: Optional[str] = typer.Option(None, "--persona", "-p", help="直接查看某型人格卡"),
    share: bool = typer.Option(False, "--share", help="输出便于复制转发的纯文本麦籍卡"),
):
    """鉴定你的麦麦人格，生成麦籍卡（mcctl 的社交裂变入口）。"""
    if persona:
        p = P.get_persona(persona)
        if not p:
            raise typer.BadParameter(f"未知人格代号：{persona}")
        ui.console.print(ui.persona_panel(p))
        return

    answers: list[str] = []
    if from_answers:
        answers = [c for c in from_answers.lower() if c in ("a", "b")]
    elif do_random or ctx.obj.json_out:
        import random
        answers = [random.choice(["a", "b"]) for _ in P.questions()]
    else:
        ui.console.print(ui.Panel.fit("[bold]🍔 麦麦人格快速鉴定[/bold]　凭直觉选 a 或 b（回车默认 a）",
                                      border_style=ui.MCD_GOLD))
        for q in P.questions():
            ui.console.print(f"\n[bold]{q['id']}. {q['q']}[/bold]")
            ui.console.print(f"  [bold {ui.MCD_GOLD}]a[/] {q['a']['text']}")
            ui.console.print(f"  [bold {ui.MCD_RED}]b[/] {q['b']['text']}")
            choice = input("  选择(a/b，回车=a): ").strip().lower()
            answers.append(choice if choice in ("a", "b") else "a")

    result = P.score(answers)
    if ctx.obj.json_out:
        ui.print_json({"code": result.code, "persona": result.persona,
                       "scores": result.scores, "margin": result.margin})
        return
    if share:
        ui.console.print(result.card_text())
    else:
        ui.console.print(ui.persona_panel(result.persona, result.scores, result.margin))
        ui.console.print("[dim]加 --share 输出可转发的纯文本麦籍卡；用 "
                         f"{result.persona['lucky_code']} 解锁你的命定套餐。[/dim]")


# --------------------------------------------------------------------------- 趣味玩法
@app.command("daily")
def daily_cmd(
    ctx: typer.Context,
    share: bool = typer.Option(False, "--share", help="输出便于转发的纯文本运势"),
):
    """今日麦门运势：每日一签，同一天同签。"""
    data = fortune()
    if ctx.obj.json_out:
        ui.print_json({"date": data["date"], "persona": data["persona"]["code"],
                       "persona_name": data["persona"]["name"], "good": data["good"],
                       "bad": data["bad"], "quote": data["quote"],
                       "lucky_number": data["lucky_number"], "lucky_code": data["lucky_code"]})
        return
    if share:
        ui.console.print(ui.daily_share_text(data))
    else:
        ui.console.print(ui.daily_panel(data))


@app.command("roll")
def roll_cmd(
    ctx: typer.Context,
    share: bool = typer.Option(False, "--share", help="输出纯文本盲盒结果"),
):
    """盲盒点餐：随机抽一套主食+小食+饮品，专治选择困难。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        res = await roll_engine(mcd)
        res["mode"] = mode
        return res
    res = _run(go())
    if ctx.obj.json_out:
        ui.print_json(res)
        return
    if share:
        items = " + ".join(i["name"] for i in res["items"])
        ui.console.print("\n".join([
            "🎰 麦门盲盒", "------------------------------",
            f"为你抽到：{items}",
            f"合计 ¥{res['price']:.2f} / {res['kcal']:.0f} kcal",
            res["mood"], "------------------------------",
            "由 mcctl · 麦门控制面 抽取",
        ]))
    else:
        ui.console.print(ui.roll_panel(res))


@app.command("pair")
def pair_cmd(
    ctx: typer.Context,
    persona_a: str = typer.Option(..., "--a", "-a", help="人格代号 A，如 BIGS"),
    persona_b: str = typer.Option(..., "--b", "-b", help="人格代号 B，如 FITA"),
    share: bool = typer.Option(False, "--share", help="输出纯文本合餐文案"),
):
    """人格合餐：两个麦麦人格一起点什么（双人分享装）。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        res = await pair_engine(mcd, persona_a, persona_b)
        res["mode"] = mode
        return res
    try:
        res = _run(go())
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    if ctx.obj.json_out:
        ui.print_json(res)
        return
    if share:
        ui.console.print(ui.pair_share_text(res))
    else:
        ui.console.print(ui.pair_panel(res))


# --------------------------------------------------------------------------- 决策 / 配餐
async def _decide(ctx, **kw):
    mcd, mode = await _make_mcd(_force_mode(ctx))
    res = await engine_decide(mcd, **kw)
    res["mode"] = mode
    return mcd, res


@app.command("decide")
def decide_cmd(
    ctx: typer.Context,
    persona: Optional[str] = typer.Option(None, "--persona", "-p"),
    people: int = typer.Option(1, "--people", "-n"),
    budget: Optional[float] = typer.Option(None, "--budget", "-b", help="整单总预算(元)"),
    kcal: Optional[float] = typer.Option(None, "--kcal", help="人均热量上限"),
    protein: Optional[float] = typer.Option(None, "--protein", help="人均蛋白质下限(g)"),
    breakfast: bool = typer.Option(False, "--breakfast", help="指定早餐时段"),
    regular: bool = typer.Option(False, "--regular", help="指定正餐时段"),
    no_spicy: bool = typer.Option(False, "--no-spicy"),
    wild: bool = typer.Option(False, "--wild", help="命运随机人格"),
    top: int = typer.Option(3, "--top", help="返回前 N 个方案"),
):
    """按麦麦人格 + 实时菜单，给出命定套餐（附理由）。"""
    period = "breakfast" if breakfast else ("regular" if regular else None)
    mcd, res = _run(_decide(ctx, persona_code=persona, people=people, budget=budget,
                            kcal=kcal, protein=protein, period=period, no_spicy=no_spicy,
                            wild=wild, top_k=top))
    if ctx.obj.json_out:
        ui.print_json(res)
        return
    ui.console.print(ui.persona_panel(res["persona"]))
    for plan in res["plans"]:
        ui.console.print(ui.render_plan(plan, res["persona"]))
    if res["mode"] != "live":
        ui.console.print("[dim]当前为离线演示数据；配置 MCP Token 后将基于官方实时菜单与价格计算。[/dim]")


# decide 的口语别名：直接复用 decide_cmd 的完整参数签名注册一次，
# 避免用 **kwargs 转发导致 Typer 推断不出任何选项（lunch -p 会报 no such option）。
app.command("lunch", hidden=True, help="decide 的口语别名")(decide_cmd)


@app.command("diet")
def diet_cmd(
    ctx: typer.Context,
    kcal: float = typer.Option(600.0, "--kcal", help="人均热量上限"),
    protein: Optional[float] = typer.Option(30.0, "--protein", help="人均蛋白质下限(g)"),
    budget: Optional[float] = typer.Option(None, "--budget", "-b"),
    people: int = typer.Option(1, "--people", "-n"),
    breakfast: bool = typer.Option(False, "--breakfast"),
):
    """控卡 / 高蛋白配餐：在真实菜单里组合搜索，硬约束卡死。"""
    period = "breakfast" if breakfast else "regular"

    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        meals = await mcd.meals(period)
        c = MealConstraints(period=period, people=people, max_kcal=kcal, target_kcal=kcal * 0.92,
                            min_protein=protein, budget_total=budget,
                            prefer_healthy_drink=True,
                            weights={"kcal": "low", "protein_first": True})
        plans = optimize_meal(meals, c, top_k=3)
        for p in plans:
            p.persona_code = "FITA"
        return mode, [p.to_dict() for p in plans]

    mode, plans = _run(go())
    if ctx.obj.json_out:
        ui.print_json({"period": period, "plans": plans, "mode": mode})
        return
    ui.info(f"控卡配餐目标：人均 ≤{kcal:g} kcal、蛋白 ≥{protein:g}g" + (f"、预算 ¥{budget:g}" if budget else ""))
    for p in plans:
        ui.console.print(ui.render_plan(p))


# --------------------------------------------------------------------------- 查询
@app.command("menu")
def menu_cmd(
    ctx: typer.Context,
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    search: Optional[str] = typer.Option(None, "--search", "-s"),
    breakfast: bool = typer.Option(False, "--breakfast"),
):
    """查询可售餐品与营养（list-nutrition-foods）。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        period = "breakfast" if breakfast else "regular"
        meals = await mcd.meals(period, category)
        if search:
            meals = [m for m in meals if search in m.name]
        return mode, [m.to_dict() for m in meals]

    mode, meals = _run(go())
    _emit(ctx, {"mode": mode, "total": len(meals), "foods": meals},
          lambda d: ui.console.print(ui.table_meals(d["foods"], f"餐品营养（{len(d['foods'])}）")))


@app.command("stores")
def stores_cmd(ctx: typer.Context):
    """查询附近可服务门店（query-nearby-stores）。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        return mode, [s.to_dict() for s in await mcd.stores()]
    mode, stores = _run(go())
    _emit(ctx, {"mode": mode, "stores": stores},
          lambda d: ui.console.print(ui.table_stores(d["stores"])))


@app.command("coupons")
def coupons_cmd(
    ctx: typer.Context,
    claim: bool = typer.Option(False, "--claim", help="一键领取全部麦麦省券（auto-bind-coupons）"),
):
    """查询可领 / 我的优惠券；--claim 一键全领。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        claimed = None
        if claim:
            claimed = await mcd.auto_bind()
        avail = await mcd.available_coupons()
        mine = await mcd.my_coupons()
        return mode, claimed, [c.to_dict() for c in avail], [c.to_dict() for c in mine]
    mode, claimed, avail, mine = _run(go())
    if ctx.obj.json_out:
        ui.print_json({"mode": mode, "claimed": claimed, "available": avail, "my_coupons": mine})
        return
    if claimed:
        ui.info(claimed.get("message", "已一键领券"))
    ui.console.print(ui.table_coupons(avail, "可领取的麦麦省券"))
    if mine:
        ui.console.print(ui.table_coupons(mine, "我的优惠券"))


# --------------------------------------------------------------------------- 省钱
@app.command("save")
def save_cmd(
    ctx: typer.Context,
    cart: str = typer.Option("巨无霸:1,薯条(中):1,可口可乐(中):1", "--cart", help="餐篮，如 巨无霸:1,麦乐鸡(10块):1"),
    channel: str = typer.Option("到店取餐", "--channel", help="到店取餐/麦乐送/堂食外带/得来速"),
    store: Optional[str] = typer.Option(None, "--store", help="门店编码（默认演示门店；真实下单请传所选门店）"),
    do_order: bool = typer.Option(False, "--order", help="省钱后直接进入下单（仍需 --confirm）"),
    confirm: bool = typer.Option(False, "--confirm", help="确认执行真实交易"),
):
    """一键领券 → 最优券 → 智能凑单 → 到手价（麦门省钱主教）。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        store_id = store or DEFAULT_STORE_ID
        meals = (await mcd.meals("regular")) + (await mcd.meals("breakfast"))
        parsed = _parse_cart(cart, meals)
        result = await save_flow(mcd, parsed, channel=channel, store_id=store_id)
        result["mode"] = mode
        if do_order and _require_confirm(ctx, confirm, f"按省税后餐篮下单（¥{result['final']['total']:.2f}）",
                                         ui.render_price(result["final"], "待下单（演练）")):
            order = await mcd.create_order(result["final_cart"], channel=channel, store_id=store_id)
            result["order"] = order
        return result

    result = _run(go())
    if ctx.obj.json_out:
        ui.print_json(result)
        return
    for s in result["steps"]:
        ui.console.print(s)
    ui.console.print(ui.render_price(result["base"], "无券基线"))
    if result.get("topup"):
        ui.console.print(ui.render_price(result["topup"]["breakdown"], "凑单后用券（推荐）"))
    elif result.get("direct"):
        ui.console.print(ui.render_price(result["direct"]["breakdown"], "直接用券"))
    ui.console.print(f"[bold {ui.MCD_GREEN}]本轮合计节省 ¥{result['total_saved']:.2f}"
                     f"（约 {result['saved_pct']}%）[/]" if result["total_saved"] else
                     "[dim]当前餐篮已较优，无额外可省空间。[/dim]")
    if result.get("order"):
        ui.console.print(ui.render_order(result["order"]["order"]))


# --------------------------------------------------------------------------- 点餐（order 子命令组）
@cart_app.command("new")
def order_new(
    ctx: typer.Context,
    cart: str = typer.Option("巨无霸:1,薯条(中):1", "--cart"),
    channel: str = typer.Option("到店取餐", "--channel"),
    store: Optional[str] = typer.Option(None, "--store", help="门店编码（默认演示门店；真实下单请传所选门店）"),
    use_save: bool = typer.Option(True, "--save/--no-save", help="下单前自动套用最优券"),
    confirm: bool = typer.Option(False, "--confirm", help="确认创建订单（返回官方支付链接）"),
):
    """创建订单：默认仅演练，--confirm 才真正调用 create-order。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        store_id = store or DEFAULT_STORE_ID
        meals = (await mcd.meals("regular")) + (await mcd.meals("breakfast"))
        parsed = _parse_cart(cart, meals)
        coupon_ids = []
        if use_save:
            sv = await save_flow(mcd, parsed, channel=channel, store_id=store_id)
            parsed = sv["final_cart"]
            direct_coupon = (sv.get("direct") or {}).get("coupon")
            coupon_ids = [direct_coupon["coupon_id"]] if direct_coupon else []
            if (sv.get("topup") or {}).get("coupon"):
                coupon_ids = [sv["topup"]["coupon"]["coupon_id"]]
            bd = sv["final"]
        else:
            bd = (await mcd.calc_price(parsed, channel, store_id=store_id)).to_dict()
        preview = ui.render_price(bd, f"待下单·{channel}（演练）")
        do = _require_confirm(ctx, confirm, f"创建{channel}订单 ¥{bd['total']:.2f}", preview)
        order = None
        if do:
            order = await mcd.create_order(parsed, channel=channel, coupon_ids=coupon_ids,
                                           store_id=store_id)
        return mode, bd, order
    mode, bd, order = _run(go())
    if ctx.obj.json_out:
        ui.print_json({"mode": mode, "dry_run": order is None, "price": bd, "order": order})
        return
    if order:
        ui.console.print(ui.render_order(order["order"]))


@cart_app.command("cancel")
def order_cancel(ctx: typer.Context, order_id: str = typer.Argument(...),
                 confirm: bool = typer.Option(False, "--confirm")):
    """取消订单（cancel-order）。"""
    async def go():
        mcd, _ = await _make_mcd(_force_mode(ctx))
        if _require_confirm(ctx, confirm, f"取消订单 {order_id}", ui.Text(f"将取消 {order_id}")):
            return await mcd.cancel_order(order_id)
        return {"dry_run": True, "would_cancel": order_id}
    res = _run(go())
    ui.print_json(res) if ctx.obj.json_out else ui.info(f"取消结果：{res}")


@cart_app.command("track")
def order_track(ctx: typer.Context, order_id: str = typer.Argument(...)):
    """查询订单详情（query-order）。"""
    async def go():
        mcd, _ = await _make_mcd(_force_mode(ctx))
        return await mcd.query_order(order_id)
    res = _run(go())
    if ctx.obj.json_out:
        ui.print_json(res)
    else:
        ui.console.print(ui.render_order(res["order"]))


@cart_app.command("list")
def order_list(ctx: typer.Context):
    """查询历史订单（order-list）。"""
    async def go():
        mcd, _ = await _make_mcd(_force_mode(ctx))
        return await mcd.order_list()
    res = _run(go())
    if ctx.obj.json_out:
        ui.print_json(res)
    elif not res:
        ui.info("暂无历史订单（演示环境）")
    else:
        for o in res:
            ui.console.print(ui.render_order(o))


# --------------------------------------------------------------------------- 积分 / 商城 / 抽奖
@points_app.command("overview")
def points_overview(ctx: typer.Context):
    """积分总览 + 商城可兑（query-my-account / mall-points-products）。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        acc = await mcd.account()
        products = await mcd.mall_products()
        return mode, acc.to_dict(), [p.to_dict() for p in products]
    mode, acc, products = _run(go())
    _emit(ctx, {"mode": mode, "account": acc, "products": products},
          lambda d: ui.console.print(ui.render_account(d["account"], d["products"])))


@points_app.callback(invoke_without_command=True)
def _points_root(ctx: typer.Context):
    """`mcctl points` 无子命令时，默认展示积分总览。"""
    if ctx.invoked_subcommand is None:
        points_overview(ctx)


@points_app.command("redeem")
def points_redeem(ctx: typer.Context, product_id: str = typer.Argument(...),
                  confirm: bool = typer.Option(False, "--confirm")):
    """积分兑换商品（mall-create-order），需 --confirm。"""
    async def go():
        mcd, _ = await _make_mcd(_force_mode(ctx))
        if _require_confirm(ctx, confirm, f"积分兑换 {product_id}", ui.Text(f"将用积分兑换 {product_id}")):
            return await mcd.redeem(product_id)
        return {"dry_run": True, "would_redeem": product_id}
    res = _run(go())
    ui.print_json(res) if ctx.obj.json_out else ui.info(f"兑换结果：{res}")


@points_app.command("lottery")
def lottery_cmd(
    ctx: typer.Context,
    draw: bool = typer.Option(False, "--draw", help="抽一次（100积分，需 --confirm）"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    """查看抽奖活动 / 抽奖（query-lottery-info / draw-lottery），含理性提示。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        info = await mcd.lottery_info()
        result = None
        if draw and _require_confirm(ctx, confirm, "消耗 100 积分抽奖", ui.Text("将消耗 100 积分抽奖")):
            result = await mcd.draw()
        prizes = await mcd.prizes()
        return mode, info, result, prizes
    mode, info, result, prizes = _run(go())
    if ctx.obj.json_out:
        ui.print_json({"mode": mode, "info": info, "draw_result": result, "prizes": prizes})
        return
    t = Table(title="🎰 积分抽奖", box=ROUNDED, header_style=f"bold {ui.MCD_GOLD}")
    t.add_column("奖品"); t.add_column("概率", justify="right")
    for pr in info.get("prizes", []):
        t.add_row(pr["name"], pr["odds"])
    ui.console.print(t)
    ui.warn(info.get("rational_note", "抽奖为概率游戏，请理性参与。"))
    if result:
        ui.info(f"抽奖结果：{result['result']['prize']}")
    if prizes:
        ui.console.print("我的奖品：" + "、".join(p["prize"] for p in prizes))


# --------------------------------------------------------------------------- 活动 / 派对
@app.command("calendar")
def calendar_cmd(ctx: typer.Context, status: Optional[str] = typer.Option(None, "--status", help="ongoing/upcoming/past")):
    """活动日历雷达（campaign-calendar）。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        return mode, [c.to_dict() for c in await mcd.campaigns(status)]
    mode, camps = _run(go())
    _emit(ctx, {"mode": mode, "campaigns": camps},
          lambda d: ui.console.print(ui.table_campaigns(d["campaigns"])))


@party_app.command("cities")
def party_cities(ctx: typer.Context):
    """主题活动可参与城市。"""
    async def go():
        mcd, _ = await _make_mcd(_force_mode(ctx))
        return await mcd.party_cities()
    res = _run(go())
    ui.print_json(res) if ctx.obj.json_out else ui.console.print("可参与城市：" + "、".join(res))


@party_app.command("book")
def party_book(
    ctx: typer.Context,
    city: str = typer.Option("上海", "--city"),
    store: Optional[str] = typer.Option(None, "--store"),
    date: Optional[str] = typer.Option(None, "--date"),
    session: Optional[str] = typer.Option(None, "--session"),
    people: int = typer.Option(6, "--people"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    """主题派对/品鉴会预约（city→store→date→session→order），需 --confirm。"""
    async def go():
        mcd, _ = await _make_mcd(_force_mode(ctx))
        stores = await mcd.party_stores(city)
        sel_store = store or stores[0].code
        dates = await mcd.party_dates(sel_store)
        sel_date = date or dates[0]
        sessions = await mcd.party_sessions(sel_store, sel_date)
        sel_session = session or sessions[0].label
        preview = ui.Text(f"{city} · {sel_store} · {sel_date} {sel_session} · {people}人")
        order = None
        if _require_confirm(ctx, confirm, "预约主题活动", preview):
            order = await mcd.party_book(city, sel_store, sel_date, sel_session, people)
        return {"city": city, "store": sel_store, "date": sel_date, "session": sel_session,
                "people": people, "options": {"stores": [s.name for s in stores], "dates": dates,
                                              "sessions": [s.label for s in sessions]},
                "order": order}
    res = _run(go())
    if ctx.obj.json_out:
        ui.print_json(res)
    else:
        ui.info(f"{res['city']}可选门店：{'、'.join(res['options']['stores'])}")
        ui.info(f"{res['store']}可选日期：{'、'.join(res['options']['dates'])}")
        ui.info(f"{res['date']}可选场次：{'、'.join(res['options']['sessions'])}")
        if res["order"]:
            ui.info(f"✅ {res['order'].get('status')}：{res['order'].get('party_order_id')}")
        else:
            ui.warn("演练模式：追加 --confirm 才会真正预约。")


@party_app.command("plan")
def party_plan(
    ctx: typer.Context,
    city: str = typer.Option("上海", "--city", help="城市（query-party-city）"),
    people: int = typer.Option(6, "--people", help="参与人数"),
    budget: Optional[float] = typer.Option(None, "--budget", help="总预算（元），如 600"),
    date_hint: Optional[str] = typer.Option(None, "--date-hint", help="期望日期 yyyy-MM-dd，如 2026-10-25"),
    weekend: Optional[bool] = typer.Option(None, "--weekend/--anyday", help="仅周末 / 不限"),
    max_distance: Optional[float] = typer.Option(None, "--max-distance", help="门店距离上限（公里）"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    """麦麦派对策划师：按 人数/预算/日期 自动求解最优场次（city→store→date→session 全链路）。"""
    async def go():
        mcd, _ = await _make_mcd(_force_mode(ctx))
        stores = await mcd.party_stores(city)
        # 并发拉取各门店可约日期，避免逐店串行往返（live 模式下每次都是网络调用）
        date_lists = await asyncio.gather(*[mcd.party_dates(st.code) for st in stores])
        dates_by_store = {st.code: ds for st, ds in zip(stores, date_lists)}
        # 再并发拉取每个 (门店, 日期) 下的场次
        session_keys = [(st.code, d) for st in stores
                        for d in dates_by_store.get(st.code, [])]
        session_lists = await asyncio.gather(*[
            mcd.party_sessions(code, d) for code, d in session_keys
        ])
        sessions_by_store_date = dict(zip(session_keys, session_lists))
        constraints = PartyConstraints(people=people, budget=budget,
                                       date_hint=date_hint or "",
                                       max_distance_km=max_distance, want_weekend=weekend,
                                       max_plans=3)
        plans = plan_party(stores, dates_by_store, sessions_by_store_date, constraints)
        order = None
        if plans:
            best = plans[0]
            preview = ui.Text(f"{city} · {best.store.name} · {best.date} {best.session.label} · {people}人 · 总价 ¥{best.total_price:.2f}")
            if _require_confirm(ctx, confirm, "预约最优派对方案", preview):
                order = await mcd.party_book(city, best.store.code, best.date,
                                             best.session.label, people)
        return {"city": city, "people": people, "budget": budget, "date_hint": date_hint,
                "max_distance_km": max_distance, "want_weekend": weekend,
                "plans": [p.to_dict() for p in plans], "order": order}
    res = _run(go())
    if ctx.obj.json_out:
        ui.print_json(res)
        return
    if not res["plans"]:
        ui.warn("没有满足约束的派对场次：请放宽 人数/预算/日期/距离 后重试。")
        return
    ui.console.print(ui.table_party_plans(res["plans"], res["city"], res["people"]))
    if res["order"]:
        ui.info(f"✅ {res['order'].get('status')}：{res['order'].get('party_order_id')}")
    else:
        ui.info("🎯 推荐第 1 号方案；确认后追加 --confirm 一键预约（真实环境跳转官方支付）。")


# --------------------------------------------------------------------------- 系统 / 工具
@app.command("tools")
def tools_cmd(ctx: typer.Context):
    """列出当前连接的麦当劳 MCP 开放工具（tools/list）。"""
    async def go():
        mcd, mode = await _make_mcd(_force_mode(ctx))
        return mode, await mcd.tools()
    mode, tools = _run(go())
    if ctx.obj.json_out:
        ui.print_json({"mode": mode, "tools": tools})
        return
    ui.info(f"当前模式：{mode}，共 {len(tools)} 个 MCP 工具")
    for i, name in enumerate(tools, 1):
        ui.console.print(f"[dim]{i:02d}[/dim] {name}")


@app.command("config")
def config_cmd(ctx: typer.Context):
    """查看当前连接配置（不显示完整 Token）。"""
    settings = Settings.load(mode=_force_mode(ctx))
    masked = (settings.token[:4] + "****" + settings.token[-4:]) if settings.token else "未配置（离线演示）"
    data = {"url": settings.url, "mode": settings.mode.value, "token": masked, "will_use_mock": settings.is_mock}
    if ctx.obj.json_out:
        ui.print_json(data)
    else:
        for k, v in data.items():
            ui.console.print(f"[bold]{k}[/]: {v}")


@app.command("demo")
def demo_cmd(ctx: typer.Context):
    """一键串演完整剧情（人格→配餐→省钱→下单演练→活动→积分），适合录屏/评审。"""
    async def go():
        mcd, mode = await _make_mcd("mock")
        out = {"mode": mode}
        out["now"] = await mcd.now()
        pr = P.score(["b", "a", "a", "a", "b", "b", "a", "a", "b", "a"])
        out["persona"] = {"code": pr.code, "name": pr.persona["name"], "motto": pr.persona["motto"]}
        decision = await engine_decide(mcd, persona_code=pr.code, people=2, budget=120)
        out["recommend"] = decision["plans"][0]
        sv = await save_flow(mcd, [
            {"code": "BUR_BIGMAC", "qty": 1}, {"code": "SIDE_FRIES_M", "qty": 1},
            {"code": "BUR_MALA_CHICKEN", "qty": 1},
            {"code": "DRK_COLA_M", "qty": 2}], channel="麦乐送")
        out["save"] = {"final_total": sv["final"]["total"], "saved": sv["total_saved"], "steps": sv["steps"]}
        out["campaigns"] = [c.to_dict() for c in await mcd.campaigns("ongoing")]
        acc = await mcd.account()
        out["points"] = acc.to_dict()
        return out
    out = _run(go())
    if ctx.obj.json_out:
        ui.print_json(out)
        return
    ui.show_banner("mock")
    ui.console.print(ui.persona_panel(P.get_persona(out["persona"]["code"])))
    ui.console.print(ui.render_plan(out["recommend"]))
    ui.info(f"省钱剧情：双人餐外送，最终实付 ¥{out['save']['final_total']:.2f}，省 ¥{out['save']['saved']:.2f}")
    for s in out["save"]["steps"]:
        ui.console.print("  " + s)
    ui.console.print(ui.table_campaigns(out["campaigns"]))
    ui.console.print(ui.render_account(out["points"]))


if __name__ == "__main__":
    app()
