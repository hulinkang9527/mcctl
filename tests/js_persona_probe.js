/* 供 tests/test_persona_parity.py 调用：枚举全部 512 种作答，输出人格结果 JSON。
 *
 * 用法：node tests/js_persona_probe.js
 *
 * 用意在保证「网页计分内核 web/persona-core.js」与「Python 引擎
 * src/mcctl/engines/persona.py」在题库与计分规则上逐字一致——
 * CLI 与网页给出的结果必须能对得上。 */
const path = require("path");
const core = require(path.resolve(__dirname, "..", "web", "persona-core.js"));

const FINAL = ["a", "b", "c", "d"];
const out = [];
for (let mask = 0; mask < 1 << 7; mask++) {
  const base = [];
  for (let i = 0; i < 7; i++) base.push((mask >> i) & 1 ? "b" : "a");
  for (const last of FINAL) {
    const ans = base.concat([last]);
    const r = core.scoreAll(ans);
    out.push({
      answers: ans.join(""),
      code: r.code,
      runnerUp: r.runnerUp,
      tie: r.tie,
      tieBrokenBy: r.tieBrokenBy,
      margin: r.margin,
      scores: r.scores,
      traits: r.explanation.traits.map((t) => `${t.key}:${t.count}`).join(","),
      keys: r.explanation.keyQuestions.map((k) => `${k.id}${k.choice}${k.delta}`).join(","),
    });
  }
}
console.log(JSON.stringify(out));
