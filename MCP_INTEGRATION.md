# MCP 集成说明（MCP_INTEGRATION）

> 本文件说明 `mcctl`（麦门的 kubectl）**实际接入的麦当劳 MCP Server、使用到的 Tool、端到端调用流程与业务价值**。
> 所有交易类动作（下单 / 领券 / 兑换 / 抽奖 / 派对预约）默认只做**演练（dry-run）**，必须显式追加 `--confirm` 才会真正调用写操作，且真实环境跳转官方支付，不会自动扣款。

## 1. 接入的 MCP Server

| 项 | 值 |
|---|---|
| 提供方 | 麦当劳中国（McDonald's China），官方开放平台 |
| Server 名称 | `mcd-mcp` |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | **Streamable HTTP** |
| 鉴权方式 | 请求头 `Authorization: Bearer <MCD_MCP_TOKEN>` |
| Token 申请 | <https://open.mcd.cn/mcp>（手机号登录 → 控制台 → 激活） |
| 限流 | 600 次 / 分钟，超限返回 `429`；Token 无效返回 `401` |
| 官方文档 | <https://github.com/M-China/mcd-mcp-server> |

`mcctl` 使用官方 Python MCP SDK（`mcp` 包）的 `streamablehttp_client` + `ClientSession` 完成 `initialize → tools/list → tools/call` 全流程，见 [`src/mcctl/mcp_client.py`](src/mcctl/mcp_client.py)。

### 双客户端与自动降级

- **RealMCPClient**（`mcp_client.py`）：真实 MCP 链路。配置了 `MCD_MCP_TOKEN` 即启用。
- **MockMCPClient**（`mock_client.py`）：**离线演示客户端**，1:1 实现了官方全部 33 个工具的状态机（领券、算价、门槛凑单、下单、取消、抽奖、积分兑换、派对预约），数据为贴近真实的**非官方演示数据**。
- 未配置 Token、或健康检查失败（网络错误 / 401 / 429）时自动降级到 Mock，保证任何人 **clone 即可零配置体验**；配置 Token 后无缝切换真实数据。
- 切换：`mcctl --live ...`（强制真实）、`mcctl --mock ...`（强制离线）、默认 `auto`。

> ⚠️ 仓库中**不包含任何真实 Token / 密钥**；配置仅使用环境变量占位符 `${MCD_MCP_TOKEN}`，见 [`mcp-config.example.json`](mcp-config.example.json) 与 [`.env.example`](.env.example)。

## 2. 使用到的 MCP Tool（全量 33 个）

官方 MCP Server 当前开放的 **33 个工具全部被接入**，按业务域分组如下。

### 2.1 时间 / 菜单 / 营养（决策基础）

| Tool | 官方名称 | mcctl 中的用途 |
|---|---|---|
| `now-time-info` | 当前时间信息 | 判断早餐 / 常规时段，自动过滤可售餐品 |
| `query-meals` | 可售卖餐品列表 | 拉取门店菜单、餐品编码、分类、标签 |
| `query-meal-detail` | 餐品详情 | 查看套餐组成与可替换项 |
| `list-nutrition-foods` | 餐品营养信息列表 | 热量 / 蛋白 / 脂肪 / 碳水 / 钠 / 钙，配餐引擎核心数据源 |

### 2.2 门店 / 地址 / 助餐

| Tool | 官方名称 | mcctl 中的用途 |
|---|---|---|
| `query-nearby-stores` | 附近可用门店 | `mcctl stores` 按距离列出到店餐厅 |
| `delivery-query-addresses` | 可配送地址列表 | 外送前选择收货地址 |
| `delivery-create-address` | 新增配送地址 | 无地址时创建 |
| `delivery-query-stores` | 可配送门店列表 | 外送场景查询可配送门店 |
| `query-meal-assistance` | 查询助餐服务 | 企业团餐场景 |

### 2.3 优惠券 / 麦麦省（省钱引擎）

| Tool | 官方名称 | mcctl 中的用途 |
|---|---|---|
| `available-coupons` | 麦麦省可领券列表 | `mcctl coupons` 展示可领券 |
| `auto-bind-coupons` | 一键领券 | `mcctl coupons --claim`、`save` 流程第①步自动领全部可领券 |
| `query-store-coupons` | 门店可用券 | 点餐时按门店取可用优惠 |
| `query-my-coupons` | 我的优惠券 | 领取后查询账户券 |

### 2.4 算价 / 下单闭环

| Tool | 官方名称 | mcctl 中的用途 |
|---|---|---|
| `calculate-price` | 商品价格计算 | 商品金额、配送费、优惠金额、应付总价；省钱引擎反复调用做方案比选 |
| `create-order` | 创建订单 | `mcctl order new --confirm`，返回订单详情与官方支付链接 |
| `cancel-order` | 取消订单 | `mcctl order cancel` |
| `query-order` | 订单详情 | `mcctl order track` 查状态 / 配送进度 |
| `order-list` | 历史订单 | `mcctl order list` |

### 2.5 活动日历

| Tool | 官方名称 | mcctl 中的用途 |
|---|---|---|
| `campaign-calendar` | 活动日历查询 | `mcctl calendar` 展示当月进行中 / 未来 / 往期活动 |

### 2.6 积分 / 麦麦商城

| Tool | 官方名称 | mcctl 中的用途 |
|---|---|---|
| `query-my-account` | 我的积分查询 | `mcctl points` 总览可用 / 累计 / 冻结 / 即将过期积分 |
| `mall-points-products` | 商城商品列表 | 列出积分可兑商品 |
| `mall-product-detail` | 商城商品详情 | 查看积分、有效期、说明 |
| `mall-create-order` | 积分兑换下单 | `mcctl points redeem --confirm`，含积分校验 / 扣减 / 发券 |
| `mall-order-list` | 商城订单列表 | 兑换记录 |
| `mall-order-detail` | 商城订单详情 | 单笔兑换详情 |

### 2.7 积分抽奖

| Tool | 官方名称 | mcctl 中的用途 |
|---|---|---|
| `query-lottery-info` | 抽奖活动信息 | `mcctl points lottery` 展示奖品、概率、消耗规则 |
| `draw-lottery` | 积分抽奖 | `mcctl points lottery --draw --confirm`，**附理性参与提示** |
| `query-my-prizes` | 我的奖品 | 中奖记录 |

### 2.8 主题派对 / 品鉴会（麦麦派对策划师）

| Tool | 官方名称 | mcctl 中的用途 |
|---|---|---|
| `query-party-city` | 可参与城市 | `mcctl party cities` |
| `query-party-store` | 城市可参与门店（含距离/营业状态） | `mcctl party book` 级联第一步 / `party plan` 候选门店 |
| `query-partystore-date` | 可预约日期 | 级联第二步 |
| `query-partystore-session` | 可预约场次（人数范围/价格/剩余名额） | 级联第三步 |
| `party-order-create` | 主题活动下单 | `mcctl party book --confirm` / `party plan --confirm` |

**`mcctl party plan`（主打亮点）把这条链路做成约束求解**：按 人数 / 预算 / 期望日期 /
距离 / 周末偏好 硬约束过滤全部（门店 × 日期 × 场次）组合，按人均成本 + 日期贴近度排序，
输出 Top3 方案与推荐理由。结构化模型：`PartyStore`（distance / businessStatus）、
`PartyDate`、`PartySession`（partyMin / partyMax / price / leftNum），见 `models.py` 与
`docs/PARTY.md`。

> ⚠️ 价格口径：官方 `query-partystore-session` 的 `price` 展示值与下单单价口径不同（文档示例
> 分别为 1000 与 50 元）。本项目统一约定为「每人价格（分）」，service 层 ÷100 归一化为元；
> 真实接入以官方最新返回为准。

## 3. 端到端调用流程

### 3.1 `mcctl whoami` → `mcctl decide`（人格化命定套餐）

```text
now-time-info ──► 判断早餐/常规时段
        │
list-nutrition-foods ──► 拉取该时段全部餐品营养+价格
        │
本地人格引擎（8 型 McPersona 计分）
        │
约束求解（热量/蛋白/预算/忌口 × 本命餐/标签偏好）
        │
campaign-calendar（可选叠加当季活动）
        ▼
输出命定套餐 + 人格化理由 + 营养/价格
```

人格测试本身在本地完成（6 道 a/b 题，无敏感数据），其结果作为权重喂给配餐引擎；配餐引擎只依赖 MCP 的菜单与营养数据。

### 3.2 `mcctl save`（一键领券 + 凑单 + 到手价，省钱核心）

```text
auto-bind-coupons ──────── ① 一键领取全部可领券
        │
calculate-price(无券) ──── ② 基线价（商品+配送费）
        │
calculate-price(逐券试算) ─ ③ 枚举每张券，取到手价最低者
        │
available/calculate-price ─ ④ 若差一点到门槛：
        │                     搜索最便宜的凑单小食，
        │                     计算"多付 X 元得到价值 Y 元商品"，
        │                     同时评估跨满减档 / 免配送费档
        ▼
输出：直接用券方案 vs 凑单方案 vs 维持原案，标注节省金额与百分比
```

关键业务规则（Mock 与真实保持一致）：
- **单品券 / 品类券**只在餐篮包含指定商品时生效（如"麦乐鸡立减"不会用到只买汉堡的订单）；
- **组合券**要求餐篮同时含小食 / 甜点与饮品；
- **满减门槛**按商品小计判断；外送另有**满额免配送费**档；
- 凑单建议必须满足"多付的钱 < 凑单品价值"，否则不推荐，避免为了用券乱买。

### 3.3 `mcctl order new`（安全下单闭环）

```text
query-nearby-stores / delivery-query-stores ── 选定门店
save 流程（自动领券+算价）────────────────── 得到最优餐篮与券
        │  无 --confirm：仅打印演练明细，不调用写接口
        │  有 --confirm：
create-order ─► 返回订单号 + 官方支付链接（跳转支付，不自动扣款）
query-order ──► 跟踪状态；cancel-order ──► 可取消
```

### 3.4 `mcctl points` / `lottery` / `party book` / `party plan`

- 积分：`query-my-account → mall-points-products → mall-create-order`，积分不足时拦截并提示差额。
- 抽奖：`query-lottery-info` 明示概率与消耗，`draw-lottery` 需二次确认，并提示"积分更稳妥的用法是直接兑换餐饮券"。
- 派对：严格按官方级联 `city → store → date → session → party-order-create`，缺一步都不下单。

**`party plan`（麦麦派对策划师）完整流程：**

```text
query-party-city ──► 城市
query-party-store ──► 候选门店（含距离 / businessStatus）
  └─ query-partystore-date ──► 每店可约日期
       └─ query-partystore-session ──► 每店每日期场次
            │  （partyMin/partyMax/price/leftNum 结构化）
            ▼
本地约束引擎 engines/party.py：人数/预算/日期/距离/周末/名额 硬过滤
            │
            人均成本 + 日期贴近度 排序
            ▼
输出 Top3 方案 + 推荐理由 → --confirm 才调用 party-order-create（官方支付跳转）
```

## 4. 业务价值

1. **把 33 个离散工具编排成"说人话"的场景**：开发者 / 普通用户不必理解 MCP 工具名，用 `whoami / decide / save / order / points / party` 等直觉命令即可完成复杂链路。
2. **真省钱、可解释**：所有优惠结论都由 `calculate-price` 现算，给出基线、用券、凑单三种到手价与节省百分比，拒绝"伪优惠"。
3. **安全可控**：交易写操作全链路 dry-run + `--confirm` 二次确认 + 官方支付跳转，Token 仅存于本地环境变量。
4. **零门槛可玩**：无 Token 也能用离线 Mock 完整体验全部 33 工具链路，配 Token 即切真实数据，利于开源传播与二次开发。
5. **可嵌入 Agent**：同时提供 CLI、Python SDK 与 Agent Skill（见 [`skill/SKILL.md`](skill/SKILL.md)），可装进 WorkBuddy / Cursor 等 MCP Client。

## 5. 错误码处理

| code | 含义 | mcctl 行为 |
|---|---|---|
| 401 | Token 无效 / 过期 / 缺失 | 提示检查 Token；自动降级 Mock 以便继续体验 |
| 429 | 超过 600 次/分钟 | 提示降频；建议稍后重试 |
| 网络错误 | 无法连接 `mcp.mcd.cn` | 健康检查失败后降级 Mock，并在输出中标注当前模式 |

> 营养与价格信息仅供参考，不构成医疗 / 营养建议，餐品、价格与供应状态以麦当劳官方渠道实时结果为准。
