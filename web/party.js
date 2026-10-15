// ============================================================
//  麦麦派对策划师 · 网页版（离线演示，数据与后端 mock 一致）
//  复刻 party.py：硬约束筛选（人数/名额/预算/日期/周末）+ 软排序
// ============================================================

const PARTY_STORES = {
  ST_LJZ: { name: "麦当劳陆家嘴环路餐厅", dist: 0.9 },
  ST_JA: { name: "麦当劳静安嘉里中心餐厅", dist: 2.1 },
  ST_HP: { name: "麦当劳外滩中山东一路餐厅", dist: 3.4 },
};

// [门店, 日期, 时间, 每人价, 最少人, 最多人, 剩余名额]
const PARTY_SESSIONS = [
  ["ST_LJZ", "2026-10-17", "10:30-12:00", 98, 2, 6, 3],
  ["ST_LJZ", "2026-10-17", "14:00-15:30", 88, 2, 6, 6],
  ["ST_LJZ", "2026-10-18", "10:30-12:00", 88, 4, 8, 5],
  ["ST_LJZ", "2026-10-18", "14:00-15:30", 78, 4, 10, 2],
  ["ST_LJZ", "2026-10-18", "16:30-18:00", 68, 4, 12, 8],
  ["ST_LJZ", "2026-10-24", "10:30-12:00", 82, 4, 10, 7],
  ["ST_LJZ", "2026-10-24", "16:30-18:00", 62, 4, 12, 12],
  ["ST_LJZ", "2026-10-25", "10:30-12:00", 85, 4, 10, 6],
  ["ST_LJZ", "2026-10-25", "14:00-15:30", 75, 4, 10, 4],
  ["ST_LJZ", "2026-10-25", "18:30-20:00", 95, 4, 12, 1],
  ["ST_LJZ", "2026-10-31", "10:30-12:00", 90, 4, 10, 9],
  ["ST_JA", "2026-10-18", "10:30-12:00", 92, 4, 8, 4],
  ["ST_JA", "2026-10-18", "14:00-15:30", 82, 4, 8, 3],
  ["ST_JA", "2026-10-19", "16:00-17:30", 88, 2, 6, 5],
  ["ST_JA", "2026-10-25", "10:30-12:00", 86, 4, 10, 7],
  ["ST_JA", "2026-10-25", "14:00-15:30", 76, 4, 10, 2],
  ["ST_JA", "2026-10-25", "18:30-20:00", 98, 4, 12, 6],
  ["ST_JA", "2026-10-26", "10:30-12:00", 90, 2, 6, 4],
  ["ST_JA", "2026-11-01", "14:00-15:30", 80, 4, 10, 10],
  ["ST_HP", "2026-10-18", "10:30-12:00", 99, 4, 10, 6],
  ["ST_HP", "2026-10-25", "14:00-15:30", 72, 4, 10, 5],
  ["ST_HP", "2026-10-25", "16:30-18:00", 79, 4, 8, 3],
  ["ST_HP", "2026-10-26", "10:30-12:00", 94, 2, 6, 2],
];

function initParty() {
  const $p = (id) => document.getElementById(id);

  function plan() {
    const people = parseInt($p("partyPeople").value, 10) || 6;
    const budget = parseFloat($p("partyBudget").value) || 0;
    const wantWeekend = $p("partyWeekend").checked;
    const today = new Date(); today.setHours(0, 0, 0, 0);

    const feasible = [];
    for (const s of PARTY_SESSIONS) {
      const [store, date, time, price, min, max, left] = s;
      const d = new Date(date + "T00:00:00");
      if (d < today) continue;
      const isWeekend = d.getDay() === 0 || d.getDay() === 6;
      if (wantWeekend && !isWeekend) continue;
      if (!(people >= min && people <= max)) continue;
      if (left < people) continue;
      const total = price * people;
      if (budget > 0 && total > budget) continue;
      feasible.push({ store, date, time, price, min, max, left, total, per: price });
    }
    render(feasible, people, budget);
  }

  function render(list, people, budget) {
    const box = $p("partyResults");
    if (!list.length) {
      box.innerHTML = `<div class="party-empty">😕 没有满足条件的场次 —— 试试<b>提高预算、调整人数</b>，或取消「仅周末」。</div>`;
      return;
    }
    const cheapest = Math.min(...list.map((x) => x.per));
    list.forEach((x) => {
      x.score = cheapest / x.per + (x.left <= 2 ? 0.1 : x.left <= 4 ? 0.05 : 0);
    });
    list.sort((a, b) => b.score - a.score);
    list = list.slice(0, 4);

    box.innerHTML = list.map((x, i) => {
      const st = PARTY_STORES[x.store];
      const reasons = [];
      if (budget > 0) reasons.push(`总价 ¥${x.total} 在预算 ¥${budget} 内`);
      reasons.push(`人均仅 ¥${x.per}`);
      reasons.push(`支持 ${x.min}-${x.max} 人（你们 ${people} 人）`);
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

  $p("partyGo").addEventListener("click", plan);
  $p("partyPeople").addEventListener("keydown", (e) => { if (e.key === "Enter") plan(); });
  $p("partyBudget").addEventListener("keydown", (e) => { if (e.key === "Enter") plan(); });
  plan(); // 首次默认算一版
}

document.addEventListener("DOMContentLoaded", initParty);
