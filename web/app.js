/* mcctl Playground — 麦麦人格测试（纯静态，离线可跑；计分逻辑与 src/mcctl/engines/persona.py 一致） */

// ⚠️ 发布前把这里改成你的公开仓库地址（README / 页面 Star 按钮会用到）
const REPO_URL = "https://github.com/hulinkang9527/mcctl";
const INSTALL_CMD = "pip install mcctl\nmcctl whoami     # 或一键演示：mcctl demo";

// ---- 命定套餐 code → 展示名 ----
const MEALS = {
  BUR_BIGMAC: ["🍔", "巨无霸"],
  SIDE_FRIES_M: ["🍟", "薯条（中）"],
  SIDE_FRIES_L: ["🍟", "薯条（大）"],
  DRK_COLA_M: ["🥤", "可口可乐（中）"],
  DRK_COLA_ZERO: ["🥤", "零度可乐（中）"],
  BUR_BANSHAO: ["🍗", "板烧鸡腿堡"],
  SIDE_APPLE: ["🍎", "苹果片"],
  DRK_WATER: ["💧", "饮用纯净水"],
  BUR_MALA_CHICKEN: ["🌶️", "麦辣鸡腿堡"],
  SIDE_SPICY_WINGS: ["🍗", "麦辣鸡翅（2块）"],
  DRK_ICED_TEA: ["🧊", "冰红茶（中）"],
  DESS_MCFLURRY_OREO: ["🍦", "奥利奥麦旋风"],
  DESS_PIE_PINEAPPLE: ["🥧", "菠萝派"],
  DRK_ORANGE: ["🍊", "100% 橙汁"],
  BP_SAUSAGE_EGG: ["🥪", "猪柳蛋麦满分"],
  BP_HASHBROWN: ["🥔", "脆薯饼"],
  BP_COFFEE: ["☕", "鲜煮咖啡"],
  BUR_CRISPY_CHICKEN: ["🍗", "脆汁鸡鸡腿堡"],
  SIDE_NUGGETS_10: ["🧆", "麦乐鸡（10块）"],
  BUR_DOUBLE_CHEESE: ["🍔", "双层吉士汉堡"],
};

// ---- 8 型人格 ----
const PERSONAS = [
  { code: "BIGS", emoji: "🍔", name: "巨无霸本霸", title: "麦门压舱石 · 双层牛肉执政官",
    motto: "面包夹山河，一顿管八小时。", color: ["#DA291C", "#FFC72C"],
    traits: ["经典派", "大份量", "决策果断"],
    desc: "团队主心骨，相信经典永不出错，追求确定性与掌控感。",
    cta: "mcctl decide -p BIGS", meal: ["BUR_BIGMAC", "SIDE_FRIES_M", "DRK_COLA_M"] },
  { code: "FITA", emoji: "🥗", name: "板烧修行者", title: "高蛋白苦行僧 · 体脂率刺客",
    motto: "板烧去酱，可乐换零，人生也要做减法。", color: ["#2E9E5B", "#DFF3E4"],
    traits: ["控卡", "高蛋白", "极度自律"],
    desc: "把身体当长期项目运营，进麦当劳也能精准锁定高蛋白低卡。",
    cta: "mcctl diet --kcal 600", meal: ["BUR_BANSHAO", "SIDE_APPLE", "DRK_WATER"] },
  { code: "SPCY", emoji: "🌶️", name: "麦辣亡命徒", title: "味蕾极限运动员 · 新品首批内测官",
    motto: "不辣不欢，不新不点，平淡是原罪。", color: ["#E8531E", "#FFD23F"],
    traits: ["嗜辣", "猎奇", "限定猎人"],
    desc: "味蕾极限运动员，永远冲在新品和限定的第一线。",
    cta: "mcctl decide -p SPCY", meal: ["BUR_MALA_CHICKEN", "SIDE_SPICY_WINGS", "DRK_ICED_TEA"] },
  { code: "SWEET", emoji: "🍦", name: "麦旋风甜心", title: "快乐水本水 · 第二份半价永远的神",
    motto: "正餐只是铺垫，甜品才是正文。", color: ["#B6508C", "#FFD9EC"],
    traits: ["甜品脑", "仪式感", "快乐优先"],
    desc: "为生活保留一块柔软的甜，麦旋风那一格永远留给快乐。",
    cta: "mcctl decide -p SWEET", meal: ["DESS_MCFLURRY_OREO", "DESS_PIE_PINEAPPLE", "DRK_ORANGE"] },
  { code: "EARL", emoji: "☕", name: "麦满分绅士", title: "清晨秩序守护者 · 吉士蛋麦满分爵士",
    motto: "早起的人，才有资格优雅地咬下第一口麦满分。", color: ["#9A6B24", "#F3E2C0"],
    traits: ["早餐党", "规律", "咖啡续命"],
    desc: "秩序感从清晨开始，一份热乎的麦满分是你与世界体面的仪式。",
    cta: "mcctl decide -p EARL --breakfast", meal: ["BP_SAUSAGE_EGG", "BP_HASHBROWN", "BP_COFFEE"] },
  { code: "NITE", emoji: "🌙", name: "麦夜骑士", title: "深夜脆汁鸡召唤师 · 加班补给线",
    motto: "天快亮了，而我的麦乐送刚到。", color: ["#3B366F", "#B7AEFF"],
    traits: ["夜宵", "续命", "外送常客"],
    desc: "城市入睡时你还醒着，深夜送达的麦当劳是 deadline 谈判的盟友。",
    cta: "mcctl decide -p NITE", meal: ["BUR_CRISPY_CHICKEN", "SIDE_NUGGETS_10", "DRK_COLA_ZERO"] },
  { code: "SQUAD", emoji: "🎉", name: "麦乐送团长", title: "拼单永远的发起人 · 第二份半价组织者",
    motto: "一个人吃是快餐，一群人吃是麦门团建。", color: ["#006DB6", "#FFC72C"],
    traits: ["社交核心", "拼单团长", "派对策划"],
    desc: "群里那句『有人要拼麦当劳吗』的发起人，把一顿饭变成聚会。",
    cta: "mcctl party --people 6", meal: ["BUR_BIGMAC", "BUR_MALA_CHICKEN", "SIDE_NUGGETS_10", "SIDE_FRIES_L", "DRK_COLA_M", "DRK_COLA_ZERO"] },
  { code: "LOYT", emoji: "🪙", name: "麦门省钱主教", title: "麦麦省首席领券官 · 积分套利大祭司",
    motto: "没有券的订单是不完整的，省到就是赚到。", color: ["#8A6410", "#FFE9A8"],
    traits: ["券王", "积分精算", "极致性价比"],
    desc: "把每次下单当作小型套利，到手价是你唯一的信仰。",
    cta: "mcctl save", meal: ["BUR_DOUBLE_CHEESE", "SIDE_FRIES_M", "DRK_COLA_ZERO"] },
];

// ---- 6 道 a/b 题（与 personas.json 一致）----
const QUESTIONS = [
  { q: "你最常在什么状态下打开麦当劳？", a: ["清晨，困，但想体面地开始一天", { EARL: 2, FITA: 1 }], b: ["深夜，代码/方案还没跑完", { NITE: 2, SPCY: 1 }] },
  { q: "打开菜单，你的第一眼会找？", a: ["经典招牌，老伙计最稳", { BIGS: 2, EARL: 1 }], b: ["本期新品和限定，不试就亏了", { SPCY: 2, SWEET: 1 }] },
  { q: "你怎么看待热量这回事？", a: ["蛋白质和热量必须心里有数", { FITA: 2, LOYT: 1 }], b: ["吃都吃了，快乐从不计卡", { SWEET: 2, NITE: 1 }] },
  { q: "下单前，你会研究优惠券和到手价吗？", a: ["必须先领券、凑满减，省到就是赚到", { LOYT: 2, SQUAD: 1 }], b: ["没太注意，想吃就点", { BIGS: 2, SWEET: 1 }] },
  { q: "吃麦当劳对你来说主要是？", a: ["快速回血，吃完继续战斗", { NITE: 2, BIGS: 1 }], b: ["犒劳自己，需要一点仪式感", { SWEET: 2, EARL: 1 }] },
  { q: "账户里的积分和一次抽奖机会，你会？", a: ["积分当钱花，兑换最划算的", { LOYT: 2, FITA: 1 }], b: ["当然抽一把，万一中了呢", { SQUAD: 2, SPCY: 1 }] },
];

// ---------- DOM ----------
const $ = (id) => document.getElementById(id);
const quizEl = $("quiz"), resultEl = $("result"), featuresEl = $("features");
let answers = [];

document.querySelectorAll("[id$='Star']").forEach((a) => (a.href = REPO_URL));
$("installBlock").textContent = INSTALL_CMD;

function showQuiz() {
  answers = [];
  resultEl.classList.add("hidden");
  featuresEl.classList.remove("hidden");
  quizEl.classList.remove("hidden");
  renderQuestion();
  quizEl.scrollIntoView({ behavior: "smooth", block: "start" });
}
function renderQuestion() {
  const i = answers.length;
  const item = QUESTIONS[i];
  $("qCount").textContent = `${i + 1} / ${QUESTIONS.length}`;
  $("progressBar").style.width = `${(i / QUESTIONS.length) * 100 + 8}%`;
  $("qText").textContent = `${i + 1}. ${item.q}`;
  $("optA").textContent = item.a[0];
  $("optB").textContent = item.b[0];
}
function choose(choice) {
  const i = answers.length;
  answers.push(QUESTIONS[i][choice][1]);
  if (answers.length < QUESTIONS.length) {
    renderQuestion();
  } else {
    finish();
  }
}

function score() {
  const tally = Object.fromEntries(PERSONAS.map((p) => [p.code, 0]));
  answers.forEach((sc) => Object.entries(sc).forEach(([k, v]) => (tally[k] += v)));
  let best = PERSONAS[0].code, max = -1;
  for (const p of PERSONAS) { // 平局时保持 PERSONAS 顺序，与 Python max 行为一致
    if (tally[p.code] > max) { max = tally[p.code]; best = p.code; }
  }
  return PERSONAS.find((p) => p.code === best);
}

function finish() {
  const p = score();
  $("rCode").textContent = p.code;
  $("rName").textContent = `${p.emoji} ${p.name}`;
  $("rTitle").textContent = p.title;
  $("rMotto").textContent = `“${p.motto}”`;
  $("rDesc").textContent = p.desc;
  $("rTraits").innerHTML = p.traits.map((t) => `<span>${t}</span>`).join("");
  $("rMeals").innerHTML = p.meal
    .map((c) => `<li><span class="dot"></span><span style="font-size:1.2rem">${MEALS[c][0]}</span> ${MEALS[c][1]}</li>`)
    .join("");
  $("rCmd").textContent = `$ ${p.cta}`;
  drawCard(p);
  quizEl.classList.add("hidden");
  resultEl.classList.remove("hidden");
  resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
  window.__lastPersona = p;
}

// ---------- Canvas 麦籍卡 ----------
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
function wrapText(ctx, text, x, y, maxW, lh) {
  let line = "", yy = y;
  for (const ch of text) {
    if (ctx.measureText(line + ch).width > maxW && line) {
      ctx.fillText(line, x, yy); line = ch; yy += lh;
    } else line += ch;
  }
  ctx.fillText(line, x, yy);
  return yy;
}

function drawCard(p) {
  const cv = $("cardCanvas"), ctx = cv.getContext("2d");
  const W = 1080, H = 1350, dark = "#1c1410", [c1, c2] = p.color;
  ctx.clearRect(0, 0, W, H);

  // 背景主色 + 像素点阵
  ctx.fillStyle = c1; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "rgba(255,255,255,0.08)";
  for (let y = 0; y < H; y += 36)
    for (let x = 0; x < W; x += 36)
      if ((x / 36 + y / 36) % 2 === 0) ctx.fillRect(x, y, 10, 10);

  // 顶部深色条
  ctx.fillStyle = dark; ctx.fillRect(0, 0, W, 96);
  ctx.fillStyle = "#FFC72C";
  ctx.font = "bold 34px monospace"; ctx.textBaseline = "middle";
  ctx.fillText("🍔 mcctl · 麦门的 kubectl", 48, 48);
  ctx.fillStyle = "#fff"; ctx.font = "bold 26px monospace"; ctx.textAlign = "right";
  ctx.fillText("McPERSONA 麦籍卡", W - 48, 48);
  ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";

  // 浅色面板
  ctx.fillStyle = c2; roundRect(ctx, 60, 130, W - 120, 1080, 18); ctx.fill();
  ctx.strokeStyle = dark; ctx.lineWidth = 8; roundRect(ctx, 60, 130, W - 120, 1080, 18); ctx.stroke();

  // 大 emoji
  ctx.font = "150px serif"; ctx.textAlign = "center";
  ctx.fillText(p.emoji, W / 2, 300);

  // 代号
  ctx.fillStyle = dark; ctx.font = "bold 120px monospace";
  ctx.fillText(p.code, W / 2, 430);
  // 中文名
  ctx.font = "bold 58px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.fillText(p.name, W / 2, 510);
  // title
  ctx.fillStyle = "#DA291C"; ctx.font = "bold 32px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.fillText(p.title, W / 2, 566);

  // motto 引用
  ctx.fillStyle = "rgba(28,20,16,0.08)"; roundRect(ctx, 120, 600, W - 240, 110, 12); ctx.fill();
  ctx.fillStyle = dark; ctx.font = "34px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  wrapText(ctx, `“${p.motto}”`, 150, 660, W - 300, 44);

  // traits
  let tx = 200;
  ctx.font = "bold 30px 'PingFang SC','Microsoft YaHei',sans-serif";
  p.traits.forEach((t) => {
    const w = ctx.measureText(t).width + 56;
    ctx.fillStyle = "#FFC72C"; roundRect(ctx, tx, 748, w, 58, 8); ctx.fill();
    ctx.strokeStyle = dark; ctx.lineWidth = 3; roundRect(ctx, tx, 748, w, 58, 8); ctx.stroke();
    ctx.fillStyle = dark; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(t, tx + w / 2, 778);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    tx += w + 28;
  });

  // 命定套餐（条目多时自动收紧行高，避免与命令框重叠）
  ctx.fillStyle = dark; ctx.font = "bold 36px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.textAlign = "left";
  ctx.fillText("🎯 命定套餐", 120, 880);
  const many = p.meal.length > 4;
  let my = many ? 950 : 940, lh = many ? 36 : 62;
  p.meal.forEach((code) => {
    ctx.font = many ? "30px serif" : "40px serif"; ctx.fillText(MEALS[code][0], 145, my);
    ctx.font = (many ? "28px " : "34px ") + "'PingFang SC','Microsoft YaHei',sans-serif";
    ctx.fillStyle = dark; ctx.fillText(MEALS[code][1], many ? 205 : 220, my);
    my += lh;
  });

  // 幸运命令
  ctx.fillStyle = dark; ctx.fillRect(120, 1150, W - 240, 70);
  ctx.fillStyle = "#8be9a0"; ctx.font = "bold 30px monospace"; ctx.textBaseline = "middle";
  ctx.fillText(`$ ${p.cta}`, 148, 1186);
  ctx.textBaseline = "alphabetic";

  // 底部
  ctx.fillStyle = dark; ctx.fillRect(0, H - 70, W, 70);
  ctx.fillStyle = "#FFC72C"; ctx.font = "bold 26px monospace"; ctx.textBaseline = "middle";
  ctx.fillText("mcctl whoami  ·  非官方创意演示  ·  open.mcd.cn/mcp", 48, H - 34);
  // 右下像素徽标
  ctx.fillStyle = "#FFC72C";
  for (let i = 0; i < 8; i++)
    for (let j = 0; j < 8; j++)
      if ((i * 3 + j * 5 + p.code.charCodeAt(0)) % 3 === 0)
        ctx.fillRect(W - 150 + i * 14, H - 58 + j * 6, 12, 4);
  ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
}

// ---------- 下载 / 分享 ----------
function downloadCard() {
  const a = document.createElement("a");
  a.download = `mcctl-${window.__lastPersona.code}-麦籍卡.png`;
  a.href = $("cardCanvas").toDataURL("image/png");
  a.click();
  toast("麦籍卡已下载，快晒到群里 🍔");
}
async function share() {
  const p = window.__lastPersona;
  const text = `我在【mcctl 麦麦人格测试】里是「${p.emoji} ${p.name} ${p.code}」——${p.motto}\n来测测你是哪种麦门人，还能一键算麦当劳最省到手价 👉 `;
  const url = location.href.split("#")[0];
  if (navigator.share) {
    try { await navigator.share({ title: "mcctl 麦麦人格测试", text, url }); } catch (_) {}
  } else if (navigator.clipboard) {
    await navigator.clipboard.writeText(text + url);
    toast("分享文案与链接已复制，去粘贴给朋友吧 📋");
  } else {
    toast("请手动复制地址栏链接分享");
  }
}
let toastTimer;
function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 2400);
}

// ---------- 事件 ----------
$("startBtn").addEventListener("click", showQuiz);
$("quizRestart").addEventListener("click", showQuiz);
$("againBtn").addEventListener("click", showQuiz);
$("downloadBtn").addEventListener("click", downloadCard);
$("shareBtn").addEventListener("click", share);
document.querySelectorAll(".opt").forEach((b) =>
  b.addEventListener("click", () => choose(b.dataset.choice)));
