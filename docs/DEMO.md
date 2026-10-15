# 离线演示与录屏脚本（DEMO）

无需 Token、无需联网，安装后即可完整演示全部 33 个 MCP 工具链路。以下脚本也适合录制参赛宣传视频 / GIF。

## 0. 准备

```bash
# 方式 A：直接安装 PyPI 发行包
pip install mcd-mcctl

# 方式 B：从源码安装
git clone <你的仓库地址> mcctl && cd mcctl
pip install -e .

mcctl intro          # 欢迎页
```

## 1. 一键全剧情（最快）

```bash
mcctl demo
```

依次串演：麦麦人格 → 人格化配餐 → 双人餐外送领券凑单到手价 → 下单演练 → 当月活动 → 积分商城。

## 2. 分段录屏脚本（推荐 60~90 秒）

```bash
# ① 社交钩子：麦麦人格测试
mcctl whoami --random
mcctl personas

# ② 人格化命定套餐（控卡人群）
mcctl decide -p FITA
mcctl decide -p BIGS --people 2 --budget 100

# ③ 硬核能力：控卡高蛋白，硬约束卡死
mcctl diet --kcal 600 --protein 35

# ④ 省钱：46 元餐篮，满 40 减 10
mcctl coupons --claim
mcctl save --cart "巨无霸:1,薯条(中):1,可口可乐(中):1"

# ⑤ 外送小额，智能凑单 / 免配送费
mcctl save --cart "吉士汉堡:1" --channel 麦乐送

# ⑥ 安全下单：先演练，再 --confirm（跳转官方支付，不自动扣款）
mcctl order new --cart "巨无霸:1,薯条(中):1,零度可乐(中):1"
mcctl order new --cart "巨无霸:1,薯条(中):1,零度可乐(中):1" --confirm

# ⑦ 积分 / 抽奖（含理性提示）
mcctl points
mcctl points lottery

# ⑧ 活动日历 / 派对预约
mcctl calendar
mcctl party book --city 上海 --people 8

# ⑨ 展示真实 MCP 工具映射
mcctl tools
```

## 3. 网页 Playground（零安装体验）

直接用浏览器打开 `web/index.html`（纯静态、无需后端 / 构建）：

1. 点击"开始麦麦人格测试"，完成 8 题（最后一题为终局四选一）；
2. 查看人格、命定套餐与命定命令；
3. "下载麦籍卡"得到一张可发朋友圈 / 群聊的像素风 PNG；"分享我的人格"复制文案；
4. Star 按钮引导回到 GitHub 仓库，把路人转化为 Star 与 CLI 用户。

> 部署：把 `web/` 目录放到 GitHub Pages / 任意静态托管即可，仓库地址在 `web/app.js` 顶部 `REPO_URL` 修改。

## 4. JSON 模式（给 Agent / 脚本）

```bash
mcctl --mock --json decide -p SPCY --regular --top 3
mcctl --mock --json save --cart "巨无霸:1,薯条(中):1,可口可乐(中):1"
```

## 5. 切到真实数据

```bash
export MCD_MCP_TOKEN=在 https://open.mcd.cn/mcp 申请到的 Token
mcctl --live tools          # 应列出官方 33 个工具
mcctl --live calendar       # 真实当月活动
mcctl config                # 确认模式（Token 脱敏）
```

## 6. 跑测试

```bash
pip install -e ".[dev]"
pytest                      # 41 个用例：人格/配餐/省钱/派对策划/33工具状态机/字段容错
```

> 演示数据均为非官方示例；真实餐品、价格、优惠与供应状态以麦当劳官方渠道实时结果为准。
