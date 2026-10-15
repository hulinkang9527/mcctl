/* mcctl Playground — 麦麦人格测试（纯静态，离线可跑；计分逻辑与 src/mcctl/engines/persona.py 一致） */

const REPO_URL = "https://github.com/hulinkang9527/mcctl";
const SITE_URL = "https://hulinkang9527.github.io/mcctl/";
const INSTALL_CMD = "pip install mcd-mcctl   # 命令行入口仍是 mcctl\nmcctl whoami     # 或一键演示：mcctl demo";

// 当前页面地址（用于分享与二维码）；本地 file:// 打开时回退到线上地址
function pageUrl() {
  if (location.protocol === "http:" || location.protocol === "https:") {
    return location.origin + location.pathname;
  }
  return SITE_URL;
}
function personaUrl(code) {
  return pageUrl() + "?p=" + code;
}

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

// ---- 8 道题（前 7 题二选一，第 8 题为四选一结局题，权重 1）----
const QUESTIONS = [
  { q: "你到店/打开点餐页后，通常是？", a: ["秒选熟悉套餐，不纠结（果断）", { BIGS: 2, EARL: 1 }], b: ["研究菜单很久，来回对比（探索）", { SPCY: 2, SWEET: 1 }] },
  { q: "下单前，你会先研究优惠券吗？", a: ["直接下单，省时间（效率）", { NITE: 2, BIGS: 1 }], b: ["先把优惠券全部研究一遍（省钱）", { LOYT: 2, FITA: 1 }] },
  { q: "你点餐更偏爱？", a: ["固定搭配，次次都差不多（稳定）", { EARL: 2, BIGS: 1 }], b: ["每次都试新组合（尝鲜）", { SWEET: 2, SPCY: 1 }] },
  { q: "朋友聚餐时，你通常是？", a: ["拍板、算预算、张罗的人（主导）", { SQUAD: 2, LOYT: 1 }], b: ["跟着大家选，吃啥都行（跟随）", { FITA: 2, SWEET: 1 }] },
  { q: "面对新品，你会？", a: ["立刻尝试，怕错过（冒险）", { SPCY: 2, SQUAD: 1 }], b: ["继续买熟悉的，稳妥", { FITA: 2, BIGS: 1 }] },
  { q: "你更在意？", a: ["吃得满足、分量够、开心（满足）", { BIGS: 2, SWEET: 1 }], b: ["每一块钱都花得划算（价值）", { LOYT: 2, SQUAD: 1 }] },
  { q: "你有固定的必点款吗？", a: ["有，认准了就一直点（忠诚）", { EARL: 2, BIGS: 1 }], b: ["没有，喜欢不断更换（变化）", { NITE: 2, SQUAD: 1 }] },
  { q: "如果今天的麦门之旅只能选一个结局，你选？", final: true,
    a: ["极致省钱（券王结局）", { LOYT: 1 }], b: ["快乐尝鲜（新品结局）", { SPCY: 1 }],
    c: ["稳定满足（经典结局）", { BIGS: 1 }], d: ["朋友全员满意（团长结局）", { SQUAD: 1 }] },
];

// ---------- DOM ----------
const $ = (id) => document.getElementById(id);
const quizEl = $("quiz"), resultEl = $("result"), featuresEl = $("features");
let answers = [];

document.querySelectorAll("[id$='Star']").forEach((a) => (a.href = REPO_URL));
$("starRail").href = REPO_URL;
$("installBlock").textContent = INSTALL_CMD;

function showQuiz() {
  answers = [];
  resultEl.classList.add("hidden");
  $("friendBar").classList.add("hidden");
  featuresEl.classList.remove("hidden");
  quizEl.classList.remove("hidden");
  renderQuestion();
  quizEl.scrollIntoView({ behavior: "smooth", block: "start" });
}
function renderQuestion() {
  const i = answers.length;
  const item = QUESTIONS[i];
  const qEl = $("qText"), optsEl = $("quizOpts");
  qEl.classList.add("q-out");
  setTimeout(() => {
    qEl.classList.remove("q-out");
    qEl.textContent = `${i + 1}. ${item.q}`;
    const letters = ["a", "b", "c", "d"].filter((k) => item[k]);
    optsEl.innerHTML = letters.map((k) =>
      `<button class="opt" data-choice="${k}"><span class="opt__key">${k.toUpperCase()}</span><span class="opt__text">${item[k][0]}</span></button>`
    ).join("");
    $("qCount").textContent = `${i + 1} / ${QUESTIONS.length}`;
    $("progressBar").style.width = `${(i / QUESTIONS.length) * 100 + 8}%`;
    qEl.classList.add("q-in");
    optsEl.classList.add("opts-in");
    setTimeout(() => {
      qEl.classList.remove("q-in");
      optsEl.classList.remove("opts-in");
    }, 320);
  }, 170);
}
function choose(choice) {
  const i = answers.length;
  const btn = document.querySelector(`.opt[data-choice="${choice}"]`);
  if (btn) {
    const r = btn.getBoundingClientRect();
    popFx(r.left + r.width / 2, r.top + r.height / 2,
      choice === "a" ? ["🍔", "🥤", "🍟"] : ["🌶️", "🍦", "☕"]);
  }
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
  renderResult(score(), { mine: true });
}

// ---------- 结果渲染（自己测 / 好友深链 共用）----------
function renderResult(p, opts) {
  opts = opts || {};
  const mine = !!opts.mine;
  $("rCode").textContent = p.code;
  $("rName").textContent = `${p.emoji} ${p.name}`;
  $("rTitle").textContent = p.title;
  const motto = `“${p.motto}”`;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    $("rMotto").textContent = motto;
  } else {
    $("rMotto").textContent = "";
    $("rMotto").classList.add("type-caret");
    let k = 0;
    const iv = setInterval(() => {
      $("rMotto").textContent = motto.slice(0, ++k);
      if (k >= motto.length) { clearInterval(iv); $("rMotto").classList.remove("type-caret"); }
    }, 42);
  }
  $("rDesc").textContent = p.desc;
  $("rTraits").innerHTML = p.traits.map((t) => `<span>${t}</span>`).join("");
  $("rMeals").innerHTML = p.meal
    .map((c) => `<li><span class="dot"></span><span style="font-size:1.2rem">${MEALS[c][0]}</span> ${MEALS[c][1]}</li>`)
    .join("");
  $("rCmd").textContent = `$ ${p.cta}`;
  $("hintCode").textContent = `${p.emoji} ${p.name} ${p.code}`;
  drawCard(p);
  quizEl.classList.add("hidden");
  resultEl.classList.remove("hidden");

  // 好友深链：展示横幅，引导测自己的
  const fb = $("friendBar");
  if (mine) {
    fb.classList.add("hidden");
    $("startBtn").textContent = "▶ 开始麦麦人格测试";
  } else {
    $("friendText").innerHTML =
      `你的朋友是 <b>${p.emoji} ${p.name}（${p.code}）</b>——${p.motto}<br>你呢？30 秒测出你的麦门人格 🍔`;
    fb.classList.remove("hidden");
    $("startBtn").textContent = "▶ 测我的麦门人格";
  }

  const panel = document.querySelector(".result__panel");
  panel.classList.remove("enter"); void panel.offsetWidth; panel.classList.add("enter");
  resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
  window.__lastPersona = p;
  if (mine) toast(`🍟 麦门神谕：${ORACLES[Math.floor(Math.random() * ORACLES.length)]}`);
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

// 在卡片上画二维码（白底 + 静默区），失败时静默降级不影响出卡
function drawQR(ctx, text, x, y, size) {
  if (typeof qrcode !== "function") return;
  try {
    const qr = qrcode(0, "M");
    qr.addData(text);
    qr.make();
    const n = qr.getModuleCount();
    const quiet = 3;
    const cell = size / (n + quiet * 2);
    ctx.save();
    ctx.fillStyle = "#FFFFFF";
    roundRect(ctx, x - 10, y - 10, size + 20, size + 20, 12);
    ctx.fill();
    ctx.fillStyle = "#1c1410";
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        if (qr.isDark(r, c)) {
          ctx.fillRect(
            x + (c + quiet) * cell,
            y + (r + quiet) * cell,
            Math.ceil(cell), Math.ceil(cell)
          );
        }
      }
    }
    ctx.restore();
  } catch (e) {
    /* 二维码不可用时仍保留文字网址，不阻断出卡 */
  }
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
  ctx.fillStyle = c2; roundRect(ctx, 60, 118, W - 120, 922, 18); ctx.fill();
  ctx.strokeStyle = dark; ctx.lineWidth = 8; roundRect(ctx, 60, 118, W - 120, 922, 18); ctx.stroke();

  // 大 emoji
  ctx.font = "150px serif"; ctx.textAlign = "center";
  ctx.fillText(p.emoji, W / 2, 265);

  // 代号
  ctx.fillStyle = dark; ctx.font = "bold 120px monospace";
  ctx.fillText(p.code, W / 2, 390);
  // 中文名
  ctx.font = "bold 58px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.fillText(p.name, W / 2, 468);
  // title
  ctx.fillStyle = "#DA291C"; ctx.font = "bold 32px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.fillText(p.title, W / 2, 522);

  // motto 引用
  ctx.fillStyle = "rgba(28,20,16,0.08)"; roundRect(ctx, 110, 552, W - 220, 110, 12); ctx.fill();
  ctx.fillStyle = dark; ctx.font = "34px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  wrapText(ctx, `“${p.motto}”`, 140, 610, W - 280, 44);

  // traits
  let tx = 200;
  ctx.font = "bold 30px 'PingFang SC','Microsoft YaHei',sans-serif";
  p.traits.forEach((t) => {
    const w = ctx.measureText(t).width + 56;
    ctx.fillStyle = "#FFC72C"; roundRect(ctx, tx, 696, w, 58, 8); ctx.fill();
    ctx.strokeStyle = dark; ctx.lineWidth = 3; roundRect(ctx, tx, 696, w, 58, 8); ctx.stroke();
    ctx.fillStyle = dark; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(t, tx + w / 2, 726);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    tx += w + 28;
  });

  // 命定套餐（条目多时自动收紧行高，避免溢出面板）
  ctx.fillStyle = dark; ctx.font = "bold 36px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.textAlign = "left";
  ctx.fillText("🎯 命定套餐", 120, 812);
  const many = p.meal.length > 4;
  let my = many ? 864 : 880, lh = many ? 34 : 62;
  p.meal.forEach((code) => {
    ctx.font = many ? "30px serif" : "40px serif"; ctx.fillText(MEALS[code][0], 145, my);
    ctx.font = (many ? "28px " : "34px ") + "'PingFang SC','Microsoft YaHei',sans-serif";
    ctx.fillStyle = dark; ctx.fillText(MEALS[code][1], many ? 200 : 220, my);
    my += lh;
  });

  // 幸运命令
  ctx.fillStyle = dark; ctx.fillRect(120, 1058, W - 240, 64);
  ctx.fillStyle = "#8be9a0"; ctx.font = "bold 30px monospace"; ctx.textBaseline = "middle";
  ctx.fillText(`$ ${p.cta}`, 148, 1090);
  ctx.textBaseline = "alphabetic";

  // 底部深色条：二维码 + 扫码引导 + 项目网址
  ctx.fillStyle = dark; ctx.fillRect(0, 1134, W, H - 1134);
  const qrSize = 150;
  drawQR(ctx, personaUrl(p.code), W - 56 - qrSize, 1168, qrSize);
  ctx.textBaseline = "middle"; ctx.textAlign = "left";
  ctx.fillStyle = "#FFC72C"; ctx.font = "bold 34px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.fillText("扫码测你是哪种麦门人 →", 48, 1206);
  ctx.fillStyle = "#FFFFFF"; ctx.font = "26px monospace";
  ctx.fillText("🍔 mcctl · 麦门的 kubectl", 48, 1253);
  ctx.fillStyle = "#FFC72C"; ctx.font = "bold 26px monospace";
  ctx.fillText("hulinkang9527.github.io/mcctl", 48, 1294);
  ctx.textBaseline = "alphabetic";
}

// ---------- 下载 / 分享 ----------
function downloadCard() {
  const a = document.createElement("a");
  a.download = `mcctl-${window.__lastPersona.code}-麦籍卡.png`;
  a.href = $("cardCanvas").toDataURL("image/png");
  a.click();
  toast("麦籍卡已下载，快晒到群里 🍔");
}

// 分享文案 A/B：社交型人格走「组队版」，其余走「挑战版」
function shareText(p) {
  const url = personaUrl(p.code);
  if (p.code === "SQUAD" || p.code === "NITE") {
    return `我是「${p.emoji} ${p.name}」——${p.motto}\n` +
      `来测测你是 8 型麦门人的哪一派，还能一键算麦当劳最省到手价 👉 ${url}`;
  }
  return `我在【mcctl 麦门人格测试】里测出是「${p.emoji} ${p.name} ${p.code}」——${p.motto}\n` +
    `你是哪种麦门人？30 秒测，敢晒代号吗 👉 ${url}`;
}

async function share() {
  const p = window.__lastPersona;
  const text = shareText(p);
  const url = personaUrl(p.code);
  if (navigator.share) {
    try { await navigator.share({ title: "mcctl 麦门人格测试", text, url }); }
    catch (e) { if (e && e.name !== "AbortError") copyShare(text); return; }
  } else {
    copyShare(text);
  }
}
async function copyShare(text) {
  if (navigator.clipboard) {
    try { await navigator.clipboard.writeText(text); }
    catch (e) { toast("复制失败，请手动复制地址栏链接"); return; }
  } else {
    toast("请手动复制地址栏链接分享"); return;
  }
  toast("已复制！发到群里喊一句「我是 " + $("hintCode").textContent +
    "，评论区报你的人格代号，看谁和我一派」🃏", 4200);
}

let toastTimer;
function toast(msg, ms) {
  const t = $("toast"); t.textContent = msg; t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), ms || 2600);
}

// ---------- 8 型人格图鉴 ----------
function renderGallery() {
  $("galleryGrid").innerHTML = PERSONAS.map((p) => `
    <button class="gcard" data-code="${p.code}" style="--gc:${p.color[0]};--gc2:${p.color[1]}">
      <span class="gcard__emoji">${p.emoji}</span>
      <span class="gcard__code">${p.code}</span>
      <span class="gcard__name">${p.name}</span>
      <span class="gcard__motto">${p.motto}</span>
    </button>`).join("");
  document.querySelectorAll(".gcard").forEach((b) =>
    b.addEventListener("click", () => {
      const p = PERSONAS.find((x) => x.code === b.dataset.code);
      renderResult(p, { mine: false });
    }));
}

// ---------- 趣味反馈 ----------
const ORACLES = PERSONAS.map((p) => p.motto);
function popFx(x, y, emojis) {
  for (let i = 0; i < 6; i++) {
    const s = document.createElement("span");
    s.className = "fx-pop";
    s.textContent = emojis[i % emojis.length];
    s.style.left = x + "px";
    s.style.top = y + "px";
    s.style.setProperty("--dx", (Math.random() * 170 - 85).toFixed(0) + "px");
    s.style.setProperty("--dy", (Math.random() * -150 - 40).toFixed(0) + "px");
    s.style.setProperty("--rot", (Math.random() * 140 - 70).toFixed(0) + "deg");
    document.body.appendChild(s);
    setTimeout(() => s.remove(), 900);
  }
}
const RAIN_EMOJIS = ["🍔", "🍟", "🥤", "🍦", "🌶️", "☕", "🌙", "🪙"];
function rainFx() {
  for (let i = 0; i < 22; i++) {
    const s = document.createElement("span");
    s.className = "fx-rain";
    s.textContent = RAIN_EMOJIS[i % RAIN_EMOJIS.length];
    s.style.left = (Math.random() * 96).toFixed(1) + "vw";
    s.style.animationDelay = (Math.random() * 0.7).toFixed(2) + "s";
    document.body.appendChild(s);
    setTimeout(() => s.remove(), 2700);
  }
}
let logoClicks = 0, logoTimer;
$("logoEaster").addEventListener("click", () => {
  logoClicks++;
  clearTimeout(logoTimer);
  logoTimer = setTimeout(() => (logoClicks = 0), 1400);
  if (logoClicks >= 5) { logoClicks = 0; rainFx(); toast("🎉 麦门万岁！彩蛋已触发"); }
});

// ---------- 事件 ----------
$("startBtn").addEventListener("click", showQuiz);
function showDemo() {
  const sec = $("demoSec");
  sec.classList.remove("hidden");
  sec.scrollIntoView({ behavior: "smooth", block: "start" });
}
$("demoBtn").addEventListener("click", showDemo);
$("demoStart").addEventListener("click", () => { showQuiz(); });
$("quizRestart").addEventListener("click", showQuiz);
$("againBtn").addEventListener("click", showQuiz);
$("friendBtn").addEventListener("click", showQuiz);
$("downloadBtn").addEventListener("click", downloadCard);
$("shareBtn").addEventListener("click", share);
$("starRailX").addEventListener("click", (e) => {
  e.preventDefault(); e.stopPropagation();
  $("starRail").classList.add("hidden");
});
$("quizOpts").addEventListener("click", (e) => {
  const btn = e.target.closest(".opt");
  if (btn) choose(btn.dataset.choice);
});

// ---------- 麦门玩法：daily / roll / pair ----------
const GOOD_LUCK = ["点经典不纠结","加一份小食","出门先领券","堂食趁热","和朋友拼分享装","板烧去酱","零度可乐配一切","凑满减再下单","外送准时点","麦乐鸡蘸两酱","加一份薯饼","得来速不停车"];
const BAD_LUCK = ["空腹刷菜单","冲动加单","麦辣配甜饮","纠结超过三分钟","点超预算还嘴硬","薯条放凉","为满减硬凑不爱吃的","把麦乐鸡分给别人","可乐去冰","边剪视频边点餐"];
const QUOTES = ["人生就像巨无霸，层次要够。","薯条要趁热，机会要趁早。","减肥从下一顿开始，这顿先吃完。","麦门不保佑纠结的人。","你点的不是套餐，是今天的确定性。","面包会有的，可乐也会有的。","选择困难的时候，就交给骰子。","今天的热量，是明天的蛋白质。","别问吃什么，问就是麦麦人格说了算。"];
const PAIR_VERDICT = {
  soul: ["天生一对，连口味都像。","你们共享的不是食物，是灵魂。","这俩人，直接上双份。"],
  ally: ["有点像，但各有坚持——正好一人一半。","能吃到一起，也能让到一起。","口味有交集，分享装最合适。"],
  contrast: ["完全不同，谁也不抢谁的。","一个要辣一个要甜，凑成一顿完整的。","正好各点各的，谁也不亏。"]
};

function hashStr(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }
function seededRng(seed) { let s = seed % 233280; if (s <= 0) s += 233280; return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; }; }
function pick(rng, arr) { return arr[Math.floor(rng() * arr.length)]; }

function mealCategory(code) {
  if (code.startsWith("BUR_")) return "主食";
  if (code.startsWith("SIDE_")) return "小食";
  return "饮品";
}

function renderPlay(html) { $("playPanel").innerHTML = html; }

function playDaily() {
  const day = new Date().toISOString().slice(0, 10);
  const rng = seededRng(hashStr("mcctl-daily::" + day));
  const p = pick(rng, PERSONAS);
  const good = pick(rng, GOOD_LUCK), bad = pick(rng, BAD_LUCK), quote = pick(rng, QUOTES);
  const num = 1 + Math.floor(rng() * 99);
  renderPlay(`
    <div class="play-card" style="--pc:${p.color[0]}">
      <div class="play-card__date">📅 ${day}</div>
      <div class="play-card__persona">今日幸运人格：${p.emoji} ${p.name}（${p.code}）</div>
      <div class="play-card__line"><span class="play-tag play-tag--good">宜</span> ${good}</div>
      <div class="play-card__line"><span class="play-tag play-tag--bad">忌</span> ${bad}</div>
      <div class="play-card__quote">「${quote}」</div>
      <div class="play-card__num">幸运数字：<b>${num}</b></div>
    </div>`);
}

function playRoll() {
  const rng = seededRng((Date.now() % 233280) | 0);
  const codes = Object.keys(MEALS);
  const byCat = { "主食": [], "小食": [], "饮品": [] };
  codes.forEach((c) => byCat[mealCategory(c)].push(c));
  const main = pick(rng, byCat["主食"]), side = pick(rng, byCat["小食"]), drink = pick(rng, byCat["饮品"]);
  const items = [["🍔", main], ["🍟", side], ["🥤", drink]];
  const mood = pick(rng, ["今天这盲盒，香。","闭眼点的，往往最对。","骰子说你值得这一套。","这套配得离谱地合理。","不纠结，直接冲。"]);
  renderPlay(`
    <div class="play-card">
      <div class="play-card__title">🎰 麦门盲盒</div>
      ${items.map(([ic, c]) => `<div class="play-card__line">${ic} ${MEALS[c][1]}</div>`).join("")}
      <div class="play-card__mood">🎲 ${mood}</div>
    </div>`);
}

function playPair() {
  const ca = $("pairA").value, cb = $("pairB").value;
  if (!ca || !cb) { toast("先选两个人格代号"); return; }
  const pa = PERSONAS.find((p) => p.code === ca), pb = PERSONAS.find((p) => p.code === cb);
  const merged = [], seen = new Set();
  pa.meal.concat(pb.meal).forEach((c) => { if (!seen.has(c)) { seen.add(c); merged.push(c); } });
  const overlap = pa.meal.filter((c) => pb.meal.includes(c));
  const tier = overlap.length >= 2 ? "soul" : overlap.length === 1 ? "ally" : "contrast";
  const rng = seededRng(hashStr(pa.code + "::" + pb.code));
  const verdict = pick(rng, PAIR_VERDICT[tier]);
  renderPlay(`
    <div class="play-card" style="--pc:${pa.color[0]}">
      <div class="play-card__title">💑 ${pa.emoji} ${pa.name} × ${pb.emoji} ${pb.name}</div>
      <div class="play-card__quote">🎯 ${verdict}</div>
      ${merged.map((c) => `<div class="play-card__line">${MEALS[c][0]} ${MEALS[c][1]}${overlap.includes(c) ? " <span class='play-tag play-tag--good'>共享</span>" : ""}</div>`).join("")}
    </div>`);
}

function initPlay() {
  // 填充人格下拉
  const opts = PERSONAS.map((p) => `<option value="${p.code}">${p.emoji} ${p.code} ${p.name}</option>`).join("");
  $("pairA").innerHTML = opts; $("pairB").innerHTML = opts;
  $("pairB").value = "FITA";
  document.querySelectorAll(".play__tab").forEach((btn) =>
    btn.addEventListener("click", () => {
      document.querySelectorAll(".play__tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const t = btn.dataset.play;
      $("pairRow").classList.toggle("hidden", t !== "pair");
      if (t === "daily") playDaily();
      else if (t === "roll") playRoll();
      else playPair();
    }));
  $("pairGo").addEventListener("click", playPair);
  // 模式徽章展开/收起
  $("modeBadge").addEventListener("click", () => $("modeNote").classList.remove("hidden"));
  $("modeNoteX").addEventListener("click", () => $("modeNote").classList.add("hidden"));
}

// ---------- 初始化：好友深链 ?p=CODE ----------
(function init() {
  renderGallery();
  initPlay();
  const code = (new URLSearchParams(location.search).get("p") || "").toUpperCase();
  const p = PERSONAS.find((x) => x.code === code);
  if (p) {
    renderResult(p, { mine: false });
    // 保持地址栏干净，后续分享会重新生成带参数的链接
    try { history.replaceState(null, "", location.pathname); } catch (e) {}
  }
})();
