"""网页 ↔ Python 人格计分一致性（parity）测试。

网页端把题库与计分规则抽到了 ``web/persona-core.js``（纯逻辑、无 DOM），
这里用 Node 直接加载它，枚举 512 种作答，与 Python 引擎逐条比对：

- 冠军人格代号
- 第二候选人格（runner-up）
- 是否同分、以及同分裁决方式（final / index）
- 各人格得分、领先分差
- 答案特点（traits）与影响最大的两道题

任一侧改了题库或权重而另一侧没跟上，本测试会立刻失败。
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from mcctl.engines import persona as P

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "tests" / "js_persona_probe.js"


def _run_probe() -> list[dict]:
    node = shutil.which("node")
    if not node:
        pytest.skip("未找到 node，跳过网页/Python 一致性校验")
    proc = subprocess.run([node, str(PROBE)], capture_output=True, text=True, cwd=str(ROOT))
    if proc.returncode != 0:
        pytest.skip(f"node 探针执行失败：{proc.stderr.strip()[:200]}")
    return json.loads(proc.stdout)


def test_js_and_python_agree_on_all_512_answers():
    rows = _run_probe()
    assert len(rows) == 512, f"探针应枚举 512 种作答，实际 {len(rows)}"

    for row in rows:
        answers = list(row["answers"])
        r = P.score(answers)
        ctx = f"answers={''.join(answers)}"
        assert r.code == row["code"], f"{ctx} 冠军不一致：py={r.code} js={row['code']}"
        assert r.runner_up == row["runnerUp"], f"{ctx} 第二候选不一致"
        assert r.tie == row["tie"], f"{ctx} 同分判定不一致"
        assert r.tie_broken_by == row["tieBrokenBy"], f"{ctx} 同分裁决不一致"
        assert r.margin == row["margin"], f"{ctx} 领先分差不一致"
        assert {k: r.scores[k] for k in row["scores"]} == row["scores"], f"{ctx} 得分不一致"

        py_traits = ",".join(f"{t['key']}:{t['count']}" for t in (r.explanation or {})["traits"])
        assert py_traits == row["traits"], f"{ctx} 答案特点不一致"

        py_keys = ",".join(
            f"{k['id']}{k['choice']}{k['delta']}" for k in (r.explanation or {})["key_questions"]
        )
        assert py_keys == row["keys"], f"{ctx} 关键题不一致"


def test_persona_codes_match_between_web_and_python():
    rows = _run_probe()
    py = {p["code"] for p in P.all_personas()}
    js = {row["code"] for row in rows} | {r for row in rows for r in [row["runnerUp"]] if r}
    assert js <= py, f"网页出现了 Python 侧不存在的人格：{sorted(js - py)}"
    assert py == js, f"两型人格集合不一致，Python 独有：{sorted(py - js)}"


def test_question_bank_identical_between_web_and_python():
    """题库逐条比对：题干、选项文案、分值、维度标签必须完全一致。"""
    node = shutil.which("node")
    if not node:
        pytest.skip("未找到 node")
    # json.dumps 产出的正是合法的 JS 字符串字面量（双引号 + 反斜杠转义）
    path_literal = json.dumps(str(ROOT / "web" / "persona-core.js"))
    script = f"const p=require({path_literal});console.log(JSON.stringify(p.QUESTIONS));"
    proc = subprocess.run([node, "-e", script], capture_output=True, text=True, cwd=str(ROOT))
    if proc.returncode != 0:
        pytest.skip(f"读取网页题库失败：{proc.stderr.strip()[:200]}")
    js_qs = json.loads(proc.stdout)
    py_qs = P.questions()
    assert len(js_qs) == len(py_qs)
    for jq, pq in zip(js_qs, py_qs):
        assert jq["q"] == pq["q"], f"题干不一致：{jq['q']} vs {pq['q']}"
        assert bool(jq.get("final")) == bool(pq.get("final"))
        for k in P.choices_of(pq):
            assert jq[k]["text"] == pq[k]["text"], f"选项文案不一致：{jq[k]['text']}"
            assert jq[k]["score"] == pq[k]["score"], f"分值不一致：{jq[k]['score']}"
            assert jq[k]["dim"] == pq[k]["dim"], f"维度标签不一致：{jq[k]['dim']}"
