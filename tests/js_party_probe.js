/* 供 tests/test_party_web.py 调用：对派对策划师的边界输入做批量求解。
 *
 * 用法：node tests/js_party_probe.js <cases.json>
 *   输入：[{name, people, budget(null=不限), weekend, sessions:[...]}]
 *   输出：[{name, ok, count, plans:[{store,date,time,total,per}], issue:{...}}]
 *
 * 这里只做计算，断言放在 Python 侧，方便与后端 party.py 用同一套期望。
 */
const fs = require("fs");
const path = require("path");
const m = require(path.resolve(__dirname, "..", "web", "party.js"));

const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = cases.map((c) => {
  const res = m.planParty({
    people: c.people,
    budget: c.budget === null ? null : c.budget,
    weekend: !!c.weekend,
    sessions: c.sessions,
  });
  return {
    name: c.name,
    ok: res.ok,
    count: res.plans.length,
    plans: res.plans.map((p) => ({ store: p.store, date: p.date, time: p.time,
                                   total: p.total, per: p.per })),
    issue: res.issue,
  };
});
console.log(JSON.stringify(out));
