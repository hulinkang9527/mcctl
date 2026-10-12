# 提交与上线操作指南（SUBMISSION GUIDE）

工程已在本地完整跑通并通过 41 个测试。下面是**需要你本人操作**的最后几步（涉及你的手机号、GitHub 账号与发布动作，无法代做）。全程约 15 分钟。

> 比赛：2026 麦当劳程序员创意开发大赛（M-CODE / 1024 程序员节）。排名按 GitHub 公开 Star，**严禁刷榜**。

## 第 0 步：把占位符换成你的仓库地址（已由协助方完成 ✅）

仓库地址已替换为 `hulinkang9527/mcctl`（涉及 `web/app.js` 的 `REPO_URL`、`pyproject.toml` 的
`Homepage/Repository`、`README.md` 的 `git clone` 地址），验证无残留占位符：

```bash
grep -rn "your-name\|<your-name>" .   # 期望：无输出（docs/SUBMISSION-GUIDE.md 的示例文本除外）
```

## 第 1 步：申请麦当劳 MCP Token（真实数据才需要，不申请也能离线演示）

1. 打开 <https://open.mcd.cn/mcp>，右上角【登录】，用手机号验证登录；
2. 右上角【控制台】→【激活】，同意服务协议，一键复制 MCP Token；
3. 本地设置环境变量（**切勿写进仓库**）：
   ```bash
   cp .env.example .env        # 然后把 Token 填进 .env（.env 已被 .gitignore 忽略）
   # 或： export MCD_MCP_TOKEN=你的Token
   mcctl --live tools          # 能列出官方 33 个工具即成功
   ```

## 第 2 步：在 GitHub 创建 Public 仓库并推送

1. 在 GitHub 新建仓库，名称 `mcctl`，**选 Public**，不要勾选自动生成 README（避免冲突）；
2. 推送：
   ```bash
   git remote add origin https://github.com/你的用户名/mcctl.git
   git branch -M main
   git push -u origin main
   ```
3. 仓库**创建时间需在 2025-12-25 ~ 2026-10-25 之间**（现在创建即符合）。

## 第 3 步：（强烈建议）开启网页 Playground 的 GitHub Pages

零安装的人格测试是拉星利器：

1. 仓库页 **Settings → Pages → Source 选 `main` 分支 / `/web` 目录 → Save**；
2. 约 1 分钟后得到 `https://你的用户名.github.io/mcctl/`；
3. 把这个链接放到 README 最顶部、社区发帖文案里，让人不点命令行也能 30 秒玩到并回流 Star。

## 第 4 步：按官方模板发报名 Issue

到**官方活动仓库的 Issues**（以官方活动页实际入口为准：`M-China` 或其页面跳转的 `M-China-Official` 组织下的 `mcd-developer-innovation-challenge`），新建 Issue，正文**≤1000 字、不要贴图**：

```text
【参赛申请】
项目名称：mcctl · 麦门的 kubectl
项目地址：https://github.com/你的用户名/mcctl
项目简介：mcctl 把麦当劳中国官方 MCP 的 33 个工具编排成一套程序员友好的命令行（灵感来自 kubectl）：麦麦人格测试 mcctl whoami（8 型人格 + 可分享像素风麦籍卡）、人格化控卡高蛋白配餐、一键领券/智能凑单/真实到手价、到店与外送安全下单闭环、积分兑换抽奖、活动日历，以及主打亮点「麦麦派对策划师」mcctl party plan——按人数/预算/期望日期约束求解生日派对/品鉴会最优场次（城市→门店→日期→场次→下单全链路）。同时提供可装入 WorkBuddy/Cursor 的 Agent Skill，以及零安装的像素风网页 Playground。真实 MCP 与离线 Mock 双客户端自动降级，clone 即可完整体验，配置 Token 即切真实数据；含 41 个单元测试与 CI，所有交易动作默认演练、二次确认，不接触支付与凭证。
```

提交后系统会在 Issue 下回复报名成功 / 失败原因；失败按提示改完重发即可。

## 第 5 步：合规争取 Star（可以做 / 不能做）

可以做：
- 把 Pages 网页 + 一条演示视频 / GIF（脚本见 `docs/DEMO.md`）发到 V2EX、掘金、少数派、即刻、小红书、B 站、知乎、X 等，遵守各版规、注明非官方原创；
- 突出技术点：33 工具全量接入、Real/Mock 双客户端降级、组合搜索配餐、券规则校验、交易安全护栏；
- 认真回复 Issue / PR，鼓励别人加新人格、新餐品、新语言。

绝不可以（官方明令，违者取消资格）：
- 机器人 / 脚本刷 Star、群控、买 Star、批量注册账号、互刷群；
- 冒充麦当劳官方、把演示数据说成官方实时数据；
- 在仓库放真实 Token、密钥、他人个人信息。

## 提交前自查

- [ ] 占位符已全部替换（`grep -rn "your-name" .` 无输出）
- [ ] 仓库 Public，已推送 main
- [ ] README.md / CONTEST_DECLARATION.md（未改动）/ MCP_INTEGRATION.md / 源代码 / workbuddy.md 齐全
- [ ] `pytest` 全绿、`mcctl --mock demo` 正常、网页可打开
- [ ] Pages 已部署、报名 Issue 已发（≤1000 字、无图）
- [ ] 定榜时间：2026-10-26 00:00；收货 / 兑奖信息截止 2026-11-14，留意 GitHub 注册邮箱
