# 🎉 麦麦派对策划师（McParty Planner）

> "想给孩子办一场麦当劳生日会，但不知道哪个店能约、哪天有空、多少钱——"
> 派对策划师把这件事从『想办』变成『约上』：你只需要说人数、预算和期望日期，
> 它自动跑完「城市 → 门店 → 日期 → 场次」全链路，在硬约束下求解最优方案。

`mcctl party plan` 是 mcctl 的主题功能（主打亮点）。它没有发明新接口，而是把官方
MCP 已经开放、但几乎没人系统用起来的 **主题活动链路**（`query-party-city` →
`query-party-store` → `query-party-store-date` → `query-party-store-session` →
`party-order-create`）做成一个**约束求解引擎**。整条链路已在真实 Token 下跑通
（实测：4 个在售派对 SPU、281 个可参与城市、上海 169 家门店与真实档期/场次）。

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

# 真实模式建议：限门店数 + 限日期范围，避免上百家门店 × 30 天产生大量往返
mcctl --live party plan --city 上海 --people 6 --days 12 --max-stores 6

# 换派对主题（spuId 来自官方 mall-points-products 里的派对类 SPU）
mcctl party cities --spu 1779                 # 看某主题可参与的城市
mcctl party plan --spu 8516 --city 上海 --people 8 --budget 1200
```

## 约束求解规则（`src/mcctl/engines/party.py`）

**硬约束（不满足直接淘汰）：**

| 约束 | 来源字段 | 说明 |
|---|---|---|
| 人数范围 | `partyMin` / `partyMax` | 你们的人数必须落在场次可容纳区间 |
| 预算 | `price` × 人数 | 估算总价 ≤ `--budget`（每人价格口径见下） |
| 剩余名额 | `leftNum` | `leftNum ≥ 人数` 才可约（只"还有空位"不够，必须容得下全部人） |
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

官方链路是**逐级透传**的，参数缺一不可（用城市名或自造参数名会被服务端拒绝）：

| 步骤 | 官方工具（真实参数） | mcctl 封装 |
|---|---|---|
| 主体 | `mall-points-products` 里 `catName` 含「派对/读书会」的 SPU | `party_products()` → `spu_id`（缺省取在售第一个） |
| 城市 | `query-party-city(spuId)` | `party_cities(spu_id)` → `PartyCity(code, name, latitude, longitude)` |
| 门店 | `query-party-store(code, latitude, longitude, spuId)` | `party_stores(spu_id, city)` → `PartyStore`（含距离/营业状态） |
| 日期 | `query-party-store-date(spuId, storeCode)` | `party_dates(spu_id, store_code)` |
| 场次 | `query-party-store-session(spuId, storeCode, dateStr)` | `party_sessions(spu_id, store_code, date_str)` |
| 下单 | `party-order-create(partyType, spuId, storeCode, code, dateStr, id, leftNum, timeStart, timeEnd, count, partyTimeInfo)` | `party_book(...)`（默认演练，`--confirm` 才执行） |

> 城市必须按 **code + 经纬度** 传递，不能只传城市名——这是官方链路的硬要求，
> 也是 mcctl 早期版本在真实模式下"查不到门店"的根因（见下节）。


## 真实接入会踩的坑（真机实测记录）

1. **价格口径**：实测 `query-party-store-session` 的 `price` 是**分**（50 元/人 = `5000`），
   与商城展示价一致。本项目统一约定 `PartySession.price` 为「每人价格（元）」，
   service 层按「≥100 视为分」归一化，口径变化只需改 `_party_price()` 一处。
2. **参数名必须用官方 schema**：`query-party-store` 要 `code + latitude + longitude + spuId`，
   `query-party-store-date` 要 `spuId + storeCode`，`query-party-store-session` 要
   `spuId + storeCode + dateStr`。早期版本传的是 `city=/store=/date=`，服务端拒绝后
   被下游当成空结果，表现为「没有满足约束的场次」而不是报错——现已改为显式抛出业务错误。
3. **失败不能静默**：官方业务失败返回 `success=false`（如 `缺少参数`），
   `McD.call()` 现在会直接抛错，避免把"调不通"伪装成"没有方案"。
4. **返回可能是「说明 + JSON」文本**：真实模式有时把响应包成一段 Markdown 字段说明，
   `json.loads` 整段会失败；`RealMCPClient._extract_json()` 负责把 JSON 片段抠出来，
   否则所有列表解析都会变成空。
5. **规模先限流**：上海一个城市就有 169 家可约门店、日期可约到 30 天后，
   全量扫描是上千次调用。`party plan` 默认只扫最近 8 家门店、未来 14 天，
   可用 `--max-stores / --days` 调整。
6. **场次名额会变**：`leftNum` 是实时值，策划结果只保证"查询时刻"有效，下单前应复核。
7. **打烊门店不可约**：真实返回带 `businessStatus`，不做过滤会拿到不可用门店。
8. **日期不可回拨**：接口可能返回今天之前的日期（页面残留），引擎统一按"今天"过滤。


## 测试

`tests/test_party.py` 共 11 个用例（纯引擎、离线可跑），覆盖：人数范围、预算过滤、
名额过滤、距离过滤、打烊门店、周末偏好、日期贴近排序、无可行方案、总价计算、非法约束。
另有 `tests/test_service.py` 用「假服务端」断言**真实模式下的参数契约**（spuId / code /
经纬度 / storeCode / dateStr 逐级透传）与**返回形态容错**（官方裸数组 vs Mock 字典包裹、
`list-nutrition-foods` 的文本表），防止这类"真实模式才暴露"的问题回归。

```bash
pytest tests/test_party.py tests/test_service.py -q
```
