# 🎉 麦麦派对策划师（McParty Planner）

> "想给孩子办一场麦当劳生日会，但不知道哪个店能约、哪天有空、多少钱——"
> 派对策划师把这件事从『想办』变成『约上』：你只需要说人数、预算和期望日期，
> 它自动跑完「城市 → 门店 → 日期 → 场次」全链路，在硬约束下求解最优方案。

`mcctl party plan` 是 mcctl 的主题功能（主打亮点）。它没有发明新接口，而是把官方
MCP 已经开放、但几乎没人系统用起来的 **主题活动链路**（`query-party-city` →
`query-party-store` → `query-partystore-date` → `query-partystore-session` →
`party-order-create`）做成一个**约束求解引擎**。

## 为什么值得做

- 官方 35 个工具里，点餐 / 领券 / 配餐赛道挤满了参赛作品；**主题活动预约**（生日派对、
  品鉴会、读书会）在 v1.0.7（2026-07-29）才开放，文档示例完整（城市、门店、日期、场次、
  下单五件套），但几乎没人把它串成产品。
- 派对预约是**真实用户刚需**：家长办生日会、品牌做品鉴会，都需要"选店 → 看档期 → 比价 →
  下单"。原样罗列几十个场次让人挑，是 API 文档思维；按约束自动求解并给出理由，才是产品思维。

## 用法

```bash
# 最简：6 人、无预算上限、不看日期，给出性价比 Top3
mcctl party plan --city 上海 --people 6

# 完整约束：8 人、总预算 600、期望 10-25、只要周末、只看 2km 内门店
mcctl party plan --city 上海 --people 8 --budget 600 \
                  --date-hint 2026-10-25 --weekend --max-distance 2

# 确认无误后一键预约（真实环境跳转官方支付，不自动扣款）
mcctl party plan --city 上海 --people 8 --budget 600 --date-hint 2026-10-25 --confirm
```

## 约束求解规则（`src/mcctl/engines/party.py`）

**硬约束（不满足直接淘汰）：**

| 约束 | 来源字段 | 说明 |
|---|---|---|
| 人数范围 | `partyMin` / `partyMax` | 你们的人数必须落在场次可容纳区间 |
| 预算 | `price` × 人数 | 估算总价 ≤ `--budget`（每人价格口径见下） |
| 剩余名额 | `leftNum` | `leftNum > 0` 才可约 |
| 门店营业 | `businessStatus` | 打烊门店直接跳过 |
| 距离 | `distance` | `--max-distance` 内 |
| 周末偏好 | 日期星期 | `--weekend` 只要周六/周日，`--anyday` 不限 |
| 过期日期 | 与今天比较 | 已过去的日期不可约 |

**软排序分（越高越靠前）：**

```
score = 1/人均价            # 人均越低越优（成本分）
      + 1/(1+距期望天数)     # 越贴近 --date-hint 越优
      + 0.3（周末偏好命中）   # 指定 --weekend 时命中加分
      + min(0.02×剩余名额, 0.1)  # 名额越紧越抢手，轻微加分
```

输出每档方案附**推荐理由**（预算内 / 人均多少 / 支持人数 / 是否命中期望日期 / 名额紧张 / 距离），
让用户不仅拿到答案，还知道为什么是这个答案——这是与"罗列式"工具最大的区别。

## 与官方 MCP 的对应

| 步骤 | 官方工具 | mcctl 封装 |
|---|---|---|
| 城市 | `query-party-city` | `party_cities()` |
| 门店 | `query-party-store` | `party_stores(city)` → `PartyStore`（含距离/营业状态） |
| 日期 | `query-partystore-date` | `party_dates(store)` |
| 场次 | `query-partystore-session` | `party_sessions(store, date)` → `PartySession`（含人数范围/价格/名额） |
| 下单 | `party-order-create` | `party_book(...)`（默认演练，`--confirm` 才执行） |

## 真实接入会踩的坑（开发记录）

1. **价格口径不统一**：官方 `query-partystore-session` 示例的 `price` 展示值与
   `party-order-create` 订单里的单价口径不同（文档示例分别为 1000 与 50 元）。本项目统一约定
   `PartySession.price` 为「每人价格（分）」、service 层 ÷100 归一化为元；接入真实环境时
   以官方最新返回为准，如口径变化只需改 `service.py` 一处换算。
2. **场次名额会变**：`leftNum` 是实时值，策划结果只保证"查询时刻"有效，下单前应复核。
3. **打烊门店不可约**：真实返回里有 `businessStatus`，不做过滤会拿到不可用门店。
4. **日期不可回拨**：接口可能返回今天之前的日期（页面残留），引擎统一按"今天"过滤。

## 测试

`tests/test_party.py` 共 11 个用例（纯引擎、离线可跑），覆盖：人数范围、预算过滤、
名额过滤、距离过滤、打烊门店、周末偏好、日期贴近排序、无可行方案、总价计算、非法约束。

```bash
pytest tests/test_party.py -q
```
