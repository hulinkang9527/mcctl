---
name: mcctl
description: >-
  麦当劳中国（McDonald's China）点餐与省钱技能「麦门的 kubectl」。当用户想做麦麦人格测试、
  按口味/热量/预算/人数/忌口搭配麦当劳套餐、查询餐品营养热量与菜单、一键领券并计算最省到手价、
  凑单/免配送费建议、到店取餐或麦乐送下单与取消、查询附近门店、查看当月活动、管理积分与商城兑换、
  积分抽奖、**预约生日会/品鉴会（麦麦派对策划师：按人数/预算/日期自动求解最优场次）**时使用。
  基于麦当劳官方 MCP（mcd-mcp，https://mcp.mcd.cn）33 个工具编排，
  所有交易动作默认演练、需用户明确确认才执行。
license: MIT
---

# mcctl — 麦门的 kubectl

把麦当劳中国官方 MCP 的 33 个工具编排成直觉化命令的技能。口号：**`mcctl whoami`，先认清你是哪种麦门人。**

## 何时使用

- "我适合吃麦当劳什么 / 帮我点个麦当劳 / 今天吃什么金拱门"
- "控制热量 / 减脂 / 高蛋白 / 不吃辣 / 预算 30 块 / 4 个人怎么点"
- "有什么券 / 怎么点最划算 / 凑单 / 免配送费 / 到手价多少"
- "附近哪家麦当劳 / 麦乐送 / 到店取餐 / 下单 / 取消订单 / 查订单"
- "积分能换什么 / 积分抽奖 / 这个月有什么活动 / 预约生日会"

## 前置与模式

- 默认 **离线演示模式（mock）**，无需 Token 即可完整跑通；数据为非官方演示数据。
- 用户已在 <https://open.mcd.cn/mcp> 申请 Token 后，通过环境变量 `MCD_MCP_TOKEN` 接入真实数据：
  - 命令行：`export MCD_MCP_TOKEN=...` 后运行；或 `mcctl --live`。
  - MCP Client 配置见仓库根目录 `mcp-config.example.json`（Streamable HTTP，`https://mcp.mcd.cn`）。
- 全局开关放在子命令**之前**：`mcctl [--mock|--live] [--json] <command>`。
- `--json` 输出结构化结果，便于 Agent 解析；不加则输出麦当劳配色的终端表格。

## 核心工作流

### 1）麦麦人格测试（强社交入口，优先用于"不知道吃什么"）

```bash
mcctl whoami            # 交互式 8 题（前 7 题 a/b + 终局四选一），得出 8 型人格之一
mcctl whoami --random   # 随机一型（演示/群聊用）
mcctl personas          # 查看全部 8 型
```

8 型 McPersona：`BIGS` 巨无霸本霸、`FITA` 板烧修行者、`SPCY` 麦辣亡命徒、`SWEET` 麦旋风甜心、
`EARL` 麦满分绅士、`NITE` 麦夜骑士、`SQUAD` 麦乐送团长、`LOYT` 麦门省钱主教。

### 2）人格化命定套餐 / 自定义配餐

```bash
mcctl decide -p FITA                         # 按人格出命定套餐+理由
mcctl decide -p BIGS --people 2 --budget 100 # 双人、预算硬约束
mcctl decide -p SPCY --no-spicy              # 人格但忌口（自动去辣）
mcctl lunch --kcal 700 --protein 35          # 直接按营养目标
mcctl diet --kcal 550 --protein 30 --regular # 控卡高蛋白
mcctl menu -s 板烧                           # 查餐品营养/价格
```

配餐引擎在满足热量上限、蛋白下限、预算、忌口、时段、人数的前提下做组合搜索，并对**本命餐**与人格标签加权；
控卡模式严格不超热量，且优先高蛋白、低脂、低钠与健康饮品（水 / 黑咖 / 零度 / 牛奶）。

### 3）省钱（一键领券 + 凑单 + 到手价）

```bash
mcctl coupons --claim                       # auto-bind-coupons 一键领全部可领券
mcctl save --cart "巨无霸:1,薯条(中):1,可口可乐(中):1"
mcctl save --cart "吉士汉堡:1" --channel 麦乐送   # 外送，会评估凑单/免配送费
```

输出基线价、直接用券最优、凑单方案（"多付 X 元得到价值 Y 元商品"）与节省百分比。
单品券 / 品类券 / 组合券都会校验餐篮是否真的包含对应商品，不会推荐用不了的券。

### 4）安全下单闭环（务必遵守护栏）

```bash
mcctl order new --cart "巨无霸:1,薯条(中):1,零度可乐(中):1"     # 默认仅演练
mcctl order new --cart "..." --channel 麦乐送 --confirm         # 用户确认后才真正下单
mcctl order track <订单号>
mcctl order cancel <订单号> --confirm
mcctl order list
```

### 5）积分 / 抽奖 / 活动 / 派对

```bash
mcctl points                       # 积分总览+商城可兑（无子命令默认总览）
mcctl points redeem <product_id>   # 默认演练，--confirm 才扣积分兑换
mcctl points lottery               # 查看奖品/概率/消耗
mcctl points lottery --draw --confirm
mcctl calendar                     # 当月活动日历
mcctl stores                       # 附近门店
mcctl party cities
mcctl party book --city 上海 --people 8      # 级联选门店/日期/场次，默认演练
mcctl party book --people 8 --confirm
mcctl party plan --city 上海 --people 8 --budget 600 --date-hint 2026-10-25
#   ↑ 麦麦派对策划师：按 人数/预算/期望日期/距离/周末 硬约束求解 Top3 最优场次，
#     附推荐理由；确认后追加 --confirm 一键预约（真实环境跳转官方支付，不自动扣款）
mcctl demo                         # 一条命令演示全流程
mcctl tools                        # 列出 33 个 MCP 工具映射
```

## 安全与合规规则（必须遵守）

1. **任何写操作默认 dry-run**：`create-order`、`cancel-order`、`auto-bind-coupons`、`mall-create-order`、
   `draw-lottery`、`party-order-create` 在没有 `--confirm` 时只能演练。Agent 在调用前必须向用户复述
   餐篮 / 金额 / 渠道 / 门店并取得明确同意，再带 `--confirm` 执行。
2. **真实环境不自动扣款**：下单只生成订单与官方支付链接，由用户自行跳转支付。
3. **不索要、不记录、不回显 Token / 支付凭证 / 个人地址**；Token 只从环境变量读取。
4. **抽奖需提示概率与理性参与**，不得诱导；积分不足时明确告知差额，不强行兑换。
5. 营养信息仅供参考、不构成医疗 / 营养建议；价格与供应以麦当劳官方实时结果为准。
6. 无法连接真实 MCP 或 Token 无效时，明确告知当前为离线演示模式，不得把演示数据冒充官方实时数据。

## 给 Agent 的回复风格

- 先给结论（命定套餐 / 最省到手价 / 订单状态），再给关键依据（热量蛋白、用了哪张券、省了多少）。
- 涉及金额一律展示"基线 → 优惠 → 实付"，并标注渠道（到店取餐 / 麦乐送）。
- 人格结果可带上一句对应的趣味 slogan，但不要编造工具未返回的事实。
