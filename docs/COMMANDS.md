# 命令手册（COMMANDS）

> 全局开关放在子命令**之前**：`mcctl [--mock|--live] [--json] [--token T] <command>`。
> 不加 `--mock/--live` 时为 `auto`：配置了 `MCD_MCP_TOKEN` 且连通则用真实数据，否则自动离线演示。
> 所有交易写操作默认**演练**，需显式 `--confirm`。

## 安装

```bash
pip install mcd-mcctl     # PyPI 发行包名（命令行入口仍为 mcctl）
# 或从源码安装：
pip install -e .
mcctl intro                 # 欢迎页 / 快速上手
mcctl demo                  # 一键串演完整剧情（适合第一次体验 / 录屏）
```

## 全局选项

| 选项 | 说明 |
|---|---|
| `--mock` | 强制离线演示数据（无需 Token） |
| `--live` | 强制连接麦当劳官方 MCP |
| `--json` | 输出机器可读 JSON（便于脚本 / Agent 解析） |
| `--token <T>` | 传入 MCP Token（也可用环境变量 `MCD_MCP_TOKEN`） |

## 1. 麦麦人格

```bash
mcctl personas                 # 列出 8 型麦麦人格
mcctl whoami                   # 交互式 8 题（终局题四选一），鉴定人格并生成麦籍卡
mcctl whoami --random          # 随机一型（群聊 / 演示）
mcctl whoami --persona FITA    # 直接指定一型查看麦籍卡
mcctl whoami --share           # 输出可分享文案（含答案特点与关键题）
mcctl whoami --from aabbaaba   # 直接给答案串（8 位；终局题可用 c/d）
```

结果会给出：人格卡 + **第二候选人格** + **答案特点**（决策果断 / 省钱倾向 / 经典偏好…）
+ **影响最大的两道题**；若出现同分，会说明按「终局题」还是「图鉴顺序」定夺。

## 2. 命定套餐 / 配餐

```bash
mcctl decide --persona FITA                 # 按人格出命定套餐+人格化理由（-p 简写）
mcctl decide -p BIGS --people 2 --budget 100
mcctl decide -p SPCY --no-spicy             # 人格但忌口去辣
mcctl decide -p EARL --breakfast            # 早餐时段
mcctl decide -p LOYT --regular --top 5      # 返回 Top5 方案
mcctl diet --kcal 600 --protein 35          # 控卡高蛋白（硬约束）
mcctl diet --kcal 550 --people 2 --budget 80
mcctl diet --breakfast --kcal 450
```

`decide` 常用参数：`-p/--persona`、`--people`、`--budget`、`--kcal`、`--protein`、`--no-spicy`、`--breakfast/--regular`、`--top`、`--wild`。
`diet` 常用参数：`--kcal`、`--protein`、`--people`、`--budget`、`--breakfast`。

## 3. 菜单 / 营养 / 门店

```bash
mcctl menu                              # 全部可售餐品营养
mcctl menu --search 板烧                # 关键词搜索（-s）
mcctl menu --category 主食
mcctl menu --breakfast                  # 早餐菜单
mcctl stores                            # 附近门店（由近及远）
mcctl calendar                          # 当月活动日历
mcctl calendar --status 进行中
```

## 4. 省钱（麦麦省）

```bash
mcctl coupons                           # 可领取 / 我的优惠券
mcctl coupons --claim                   # 一键领取全部可领券（auto-bind-coupons）
mcctl save --cart "巨无霸:1,薯条(中):1,可口可乐(中):1"
mcctl save --cart "吉士汉堡:1" --channel 麦乐送   # 外送，评估凑单 / 免配送费
mcctl save --cart "..." --order --confirm         # 采用推荐方案直接下单（需确认）
```

`--cart` 支持餐品编码或中文名、半角 / 全角括号，形如 `名称:数量,名称:数量`。
输出：无券基线、直接用券最优、凑单方案（多付 X 元得价值 Y 元商品）、节省金额与百分比。

## 5. 点餐 / 订单

```bash
mcctl order new --cart "巨无霸:1,薯条(中):1,零度可乐(中):1"      # 默认演练
mcctl order new --cart "..." --channel 麦乐送                   # 外送
mcctl order new --cart "..." --no-save                          # 不自动领券用券
mcctl order new --cart "..." --confirm                          # 真正创建订单
mcctl order track <订单号>                                      # 查询订单状态
mcctl order list                                                # 历史订单
mcctl order cancel <订单号> --confirm                           # 取消订单
```

`order new` 参数：`--cart`、`--channel`、`--save/--no-save`、`--confirm`。
确认后返回订单号与官方支付链接，跳转支付，不自动扣款。

## 6. 积分 / 商城 / 抽奖

```bash
mcctl points                            # 积分总览 + 商城可兑（无子命令默认总览）
mcctl points overview
mcctl points redeem <product_id>        # 积分兑换（默认演练）
mcctl points redeem <product_id> --confirm
mcctl points lottery                    # 查看抽奖奖品 / 概率 / 消耗
mcctl points lottery --draw             # 抽一次（默认演练）
mcctl points lottery --draw --confirm   # 真正消耗积分抽奖
```

积分不足会拦截并提示差额；抽奖命令固定展示概率与"理性参与、直接兑换更稳妥"的提示。

## 7. 主题派对 / 品鉴会（麦麦派对策划师）

```bash
mcctl party cities                                   # 可参与城市（--spu 切换派对主题）
mcctl party book --city 上海 --people 8              # 级联查询门店/日期/场次（演练）
mcctl party book --city 上海 --store <门店> --date <日期> --session <场次> --people 8 --confirm

# 🎉 派对策划师：人数/预算/日期自动求解最优场次（约束引擎，推荐 Top3）
mcctl party plan --city 上海 --people 8 --budget 600 --date-hint 2026-10-25
mcctl party plan --city 上海 --people 6 --budget 400 --weekend          # 只约周末
mcctl party plan --city 上海 --people 6 --budget 400 --max-distance 2   # 只看 2km 内门店
mcctl party plan --city 上海 --people 8 --budget 600 --date-hint 2026-10-25 --confirm  # 按最优方案直接预约

# 真实模式：一个城市可能上百家门店、可约到 30 天后，建议先限规模
mcctl --live party plan --city 上海 --people 6 --days 12 --max-stores 6
mcctl --live party plan --spu 8516 --city 上海 --people 8 --budget 1200  # 换主题（尊享版生日派对）
```

严格按官方级联 `mall-points-products(spuId) → query-party-city → query-party-store →
query-party-store-date → query-party-store-session → party-order-create`，参数逐级透传
（城市必须传 code + 经纬度，门店传 storeCode，日期传 dateStr），缺一步不下单。
`--city` 支持城市名（可省略「市」）或城市 code；`--spu` 缺省取官方在售的第一个派对 SPU。
`party plan` 的硬约束：人数落在场次 `[partyMin, partyMax]`、估算总价 ≤ 预算、
**剩余名额足以容纳全部人数**（`leftNum >= people`，而不只是"还有空位"）、
门店营业中、距离 ≤ 上限、周末偏好；软排序：人均成本 + 日期贴近度 + 名额稀缺度。
无可行方案时如实返回空并给出淘汰原因（`没有满足约束的派对场次（上海 扫描了 6/169 家门店）…`），
**不会为凑数推荐一个不满足约束的场次**。

网页版派对策划师复用同一套硬约束，并额外处理：人数非整数 / 少于 1 / 超过 12、
预算为 0 或负数、只勾"仅周末"但无周末场次、场次字段缺失（缺 `leftNum` 保守判为不可预订，
缺门店/日期/时间/价格直接跳过并计数），全部给出「没有找到符合条件的方案」+ 原因 + 放宽建议。
价格口径：实测官方 `query-party-store-session.price` 为**分**（50 元/人 = `5000`），
本项目统一「每人价格（元）」，service 层按「≥100 视为分」归一化，以官方最新返回为准。

## 8. 连接与诊断

```bash
mcctl tools                 # 列出当前连接的 MCP 工具（tools/list），真实模式显示官方 35 个
mcctl config                # 查看当前模式与连接配置（Token 脱敏）
```

## JSON 示例

```bash
$ mcctl --mock --json decide -p FITA --regular --top 1
# 返回 persona / constraints / plans / best（含 cart、per_person 的 kcal/protein/price、score_detail、reasons）
```

## 离线与真实

- **离线（默认 / `--mock`）**：数据来自 `mock_data.py`，为非官方演示数据，全链路可跑。
- **真实（`--live` 或配置 Token）**：调用 `https://mcp.mcd.cn`，需在 <https://open.mcd.cn/mcp> 申请 Token。
- 401（Token 无效）、429（超 600 次/分钟）、网络错误都会给出提示；auto 模式下自动降级离线以便继续。
