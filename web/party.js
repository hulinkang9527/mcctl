// ============================================================
//  麦麦派对策划师 · 网页版（离线演示，数据与后端 mock 一致）
//  复刻 party.py：硬约束筛选（人数/名额/预算/日期/周末）+ 软排序
//  边界策略：非法输入 / 无可行方案 / 字段缺失一律「明确告知」，
//  绝不降级推荐一个不满足约束的结果。
// ============================================================

const MAX_PEOPLE = 12;          // 演示数据支持的人数上限
const MIN_PEOPLE = 1;

const PARTY_STORES = {
  ST_LJZ: { name: "麦当劳陆家嘴环路餐厅", dist: 0.9 },
  ST_JA: { name: "麦当劳静安嘉里中心餐厅", dist: 2.1 },
  ST_HP: { name: "麦当劳外滩中山东一路餐厅", dist: 3.4 },
};

/* 场次数据（字段口径与后端 PartySession 一致）：
 *   store / date / time / price(每人元) / min / max / left(剩余名额)
 * 真实 MCP 返回可能缺字段，统一走 normalizeSession 做容错。 */
const PARTY_SESSIONS = [
  { store: "ST_LJZ", date: "2026-10-17", time: "10:30-12:00", price: 98, min: 2, max: 6, left: 3 },
  { store: "ST_LJZ", date: "2026-10-17", time: "14:00-15:30", price: 88, min: 2, max: 6, left: 6 },
  { store: "ST_LJZ", date: "2026-10-18", time: "10:30-12:00", price: 88, min: 4, max: 8, left: 5 },
  { store: "ST_LJZ", date: "2026-10-18", time: "14:00-15:30", price: 78, min: 4, max: 10, left: 2 },
  { store: "ST_LJZ", date: "2026-10-18", time: "16:30-18:00", price: 68, min: 4, max: 12, left: 8 },
  { store: "ST_LJZ", date: "2026-10-24", time: "10:30-12:00", price: 82, min: 4, max: 10, left: 7 },
  { store: "ST_LJZ", date: "2026-10-24", time: "16:30-18:00", price: 62, min: 4, max: 12, left: 12 },
  { store: "ST_LJZ", date: "2026-10-25", time: "10:30-12:00", price: 85, min: 4, max: 10, left: 6 },
  { store: "ST_LJZ", date: "2026-10-25", time: "14:00-15:30", price: 75, min: 4, max: 10, left: 4 },
  { store: "ST_LJZ", date: "2026-10-25", time: "18:30-20:00", price: 95, min: 4, max: 12, left: 1 },
  { store: "ST_LJZ", date: "2026-10-31", time: "10:30-12:00", price: 90, min: 4, max: 10, left: 9 },
  { store: "ST_JA", date: "2026-10-18", time: "10:30-12:00", price: 92, min: 4, max: 8, left: 4 },
  { store: "ST_JA", date: "2026-10-18", time: "14:00-15:30", price: 82, min: 4, max: 8, left: 3 },
  { store: "ST_JA", date: "2026-10-19", time: "16:00-17:30", price: 88, min: 2, max: 6, left: 5 },
  { store: "ST_JA", date: "2026-10-25", time: "10:30-12:00", price: 86, min: 4, max: 10, left: 7 },
  { store: "ST_JA", date: "2026-10-25", time: "14:00-15:30", price: 76, min: 4, max: 10, left: 2 },
  { store: "ST_JA", date: "2026-10-25", time: "18:30-20:00", price: 98, min: 4, max: 12, left: 6 },
  { store: "ST_JA", date: "2026-10-26", time: "10:30-12:00", price: 90, min: 2, max: 6, left: 4 },
  { store: "ST_JA", date: "2026-11-01", time: "14:00-15:30", price: 80, min: 4, max: 10, left: 10 },
  { store: "ST_HP", date: "2026-10-18", time: "10:30-12:00", price: 99, min: 4, max: 10, left: 6 },
  { store: "ST_HP", date: "2026-10-25", time: "14:00-15:30", price: 72, min: 4, max: 10, left: 5 },
  { store: "ST_HP", date: "2026-10-25", time: "16:30-18:00", price: 79, min: 4, max: 8, left: 3 },
  { store: "ST_HP", date: "2026-10-26", time: "10:30-12:00", price: 94, min: 2, max: 6, left: 2 },
];

/** 把可能缺字段的场次记录规整成安全结构；关键字段缺失返回 null 并计入 skipped。 */
function normalizeSession(raw) {
  if (!raw || typeof raw !== "object") return null;
  const store = String(raw.store || raw.storeCode || "").trim();
  const date = String(raw.date || "").trim();
  const time = String(raw.time || raw.timeStart || "").trim();
  const price = Number(raw.price);
  if (!store || !date || !time || !isFinite(price)) return null;
  const min = Number.isFinite(Number(raw.min)) ? Number(raw.min) : 1;
  const max = Number.isFinite(Number(raw.max)) ? Number(raw.max) : MAX_PEOPLE;
  // 剩余名额缺失时保守视为 0（不可预订），避免误推荐
  const left = Number.isFinite(Number(raw.left)) ? Number(raw.left) : 0;
  return { store, date, time, price, min, max, left };
}

function isWeekend(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  if (isNaN(d.getTime())) return false;
  const wd = d.getDay();
  return wd === 0 || wd === 6;
}

/** 返回 {ok, plans, issue}：plans 为空时 issue 说明各场次被淘汰的原因。
 *  ``sessions`` 可注入自定义场次数据（测试 / 真实 MCP 返回）。 */
function planParty({ people, budget, weekend, sessions }) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const list = sessions || PARTY_SESSIONS;

  const feasible = [];
  const issue = { expired: 0, weekend: 0, people: 0, left: 0, budget: 0, broken: 0 };
  const cheapestPrice = list.reduce(
    (m, s) => (isFinite(s.price) && s.price > 0 ? Math.min(m, s.price) : m), Infinity);

  for (const raw of list) {
    const s = normalizeSession(raw);
    if (!s) { issue.broken++; continue; }
    const d = new Date(s.date + "T00:00:00");
    if (isNaN(d.getTime())) { issue.broken++; continue; }
    if (d < today) { issue.expired++; continue; }
    if (weekend && !isWeekend(s.date)) { issue.weekend++; continue; }
    if (!(people >= s.min && people <= s.max)) { issue.people++; continue; }
    if (s.left < people) { issue.left++; continue; }
    const total = Math.round(s.price * people * 100) / 100;
    if (budget !== null && total > budget + 1e-6) { issue.budget++; continue; }
    feasible.push({ ...s, total, per: s.price });
  }

  if (!feasible.length) return { ok: false, plans: [], issue, cheapestPrice };

  const cheapest = Math.min.apply(null, feasible.map((x) => x.per)) || 1;
  feasible.forEach((x) => {
    x.score = cheapest / x.per + (x.left <= 2 ? 0.1 : x.left <= 4 ? 0.05 : 0);
  });
  feasible.sort((a, b) => b.score - a.score);
  return { ok: true, plans: feasible.slice(0, 4), issue, cheapestPrice };
}

/** 无可行方案时的可读原因与放宽建议 */
function explainNoPlan(issue, people, budget, weekend) {
  const bits = [];
  if (issue.broken) bits.push(`${issue.broken} 个场次信息不完整（缺少门店/日期/时间/价格），已跳过`);
  if (issue.expired) bits.push(`${issue.expired} 个场次日期已过`);
  if (weekend && issue.weekend) bits.push(`${issue.weekend} 个场次不在周末`);
  if (issue.people) bits.push(`${issue.people} 个场次不支持 ${people} 人（人数超出场次区间）`);
  if (issue.left) bits.push(`${issue.left} 个场次剩余名额不足以容纳 ${people} 人`);
  if (budget !== null && issue.budget) bits.push(`${issue.budget} 个场次总价超出预算 ¥${budget}`);
  const tips = [];
  if (budget !== null && (issue.budget || issue.left)) tips.push("提高预算");
  if (issue.people) tips.push(`把人数调整到 ${MIN_PEOPLE}-${MAX_PEOPLE} 之间`);
  if (weekend && issue.weekend) tips.push("取消「仅周末」");
  return { detail: bits, tips };
}

function initParty() {
  const $p = (id) => document.getElementById(id);
  const results = $p("partyResults");
  const totalEl = $p("sessionTotal");
  if (totalEl) totalEl.textContent = String(PARTY_SESSIONS.length);

  function readInputs() {
    const rawPeople = $p("partyPeople").value;
    const rawBudget = $p("partyBudget").value;
    const peopleNum = Number(rawPeople);
    const budgetNum = Number(rawBudget);
    return {
      rawPeople: String(rawPeople).trim(),
      rawBudget: String(rawBudget).trim(),
      peopleNum, budgetNum,
      weekend: $p("partyWeekend").checked,
    };
  }

  function run() {
    const { rawPeople, rawBudget, peopleNum, budgetNum, weekend } = readInputs();

    // —— 硬校验：非法输入直接说明，不静默兜底 ——
    if (rawPeople === "") {
      results.innerHTML = `<div class="party-empty">⚠️ 请填写<b>参与人数</b>（${MIN_PEOPLE}-${MAX_PEOPLE} 人）后再生成方案。</div>`;
      return;
    }
    if (!Number.isInteger(peopleNum)) {
      results.innerHTML = `<div class="party-empty">⚠️ 人数必须是<b>整数</b>，当前填写的是「${rawPeople}」。</div>`;
      return;
    }
    if (peopleNum < MIN_PEOPLE || peopleNum > MAX_PEOPLE) {
      results.innerHTML = `<div class="party-empty">⚠️ 演示场次仅支持 <b>${MIN_PEOPLE}-${MAX_PEOPLE} 人</b>，当前填写 ${peopleNum} 人。<br>请调整人数后再试。</div>`;
      return;
    }
    if (rawBudget !== "" && budgetNum < 0) {
      results.innerHTML = `<div class="party-empty">⚠️ 预算不能为<b>负数</b>，当前填写的是 ¥${rawBudget}。</div>`;
      return;
    }
    // 预算留空 = 不限预算；填 0 视为真实预算 ¥0（必然无方案，照实提示）
    const budget = rawBudget === "" ? null : budgetNum;

    const res = planParty({ people: peopleNum, budget, weekend });
    if (!res.ok) {
      const ex = explainNoPlan(res.issue, peopleNum, budget, weekend);
      const need = isFinite(res.cheapestPrice) ? res.cheapestPrice * peopleNum : null;
      results.innerHTML = `
        <div class="party-empty">
          <div class="party-empty__title">🔍 没有找到符合条件的方案</div>
          ${ex.detail.length ? `<ul class="party-empty__list">${ex.detail.map((d) => `<li>${d}</li>`).join("")}</ul>` : ""}
          ${need && budget !== null ? `<p class="party-empty__hint">当前预算 ¥${budget}，最低可行方案约需 <b>¥${Math.round(need)}</b>。</p>` : ""}
          ${ex.tips.length ? `<p class="party-empty__tip">试试：${ex.tips.join(" / ")}</p>` : ""}
        </div>`;
      return;
    }
    results.innerHTML = res.plans.map((x, i) => {
      const st = PARTY_STORES[x.store] || { name: x.store, dist: 0 };
      const reasons = [];
      if (budget !== null) reasons.push(`总价 ¥${x.total} 在预算 ¥${budget} 内`);
      reasons.push(`人均仅 ¥${x.per}`);
      reasons.push(`支持 ${x.min}-${x.max} 人（你们 ${peopleNum} 人）`);
      if (x.left <= 3) reasons.push(`仅剩 ${x.left} 个名额，手慢无`);
      reasons.push(`距你 ${st.dist}km`);
      return `<div class="pcard ${i === 0 ? "pcard--best" : ""}">
        <div class="pcard__rank">${i === 0 ? "🏆 最优推荐" : "第 " + (i + 1) + " 选"}</div>
        <div class="pcard__store">${st.name}<span class="pcard__dist">📍 ${st.dist}km</span></div>
        <div class="pcard__when">🗓️ ${x.date}　🕐 ${x.time}</div>
        <div class="pcard__prices">
          <span class="pcard__total">总价 <b>¥${x.total}</b></span>
          <span class="pcard__per">人均 <b>¥${x.per}</b></span>
        </div>
        <div class="pcard__reasons">${reasons.map((r) => `<span>✓ ${r}</span>`).join("")}</div>
      </div>`;
    }).join("");
  }

  $p("partyGo").addEventListener("click", run);
  $p("partyPeople").addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
  $p("partyBudget").addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
  $p("partyWeekend").addEventListener("change", run);
  run(); // 首次默认算一版
}

// 浏览器环境才挂载（Node 下仅导出纯函数供 parity 测试使用）
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initParty);
}

if (typeof module === "object" && module.exports) {
  module.exports = { planParty, normalizeSession, isWeekend, explainNoPlan, MAX_PEOPLE, MIN_PEOPLE };
}
