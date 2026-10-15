"""人格引擎测试。"""
import itertools

from mcctl.engines import persona as P


def test_questions_and_personas():
    assert len(P.questions()) == 8
    codes = {p["code"] for p in P.all_personas()}
    assert codes == {"BIGS", "FITA", "SPCY", "SWEET", "EARL", "NITE", "SQUAD", "LOYT"}


def test_each_persona_is_reachable():
    """枚举前7题 a/b + 第8题四选一，保证 8 型人格都能被鉴定出来。"""
    letters = [["a", "b"]] * 7 + [["a", "b", "c", "d"]]
    reachable = {P.score(list(c)).code for c in itertools.product(*letters)}
    assert reachable == {p["code"] for p in P.all_personas()}


def test_known_answers():
    # 全 a：结果必须是合法代号
    res = P.score(["a"] * 8)
    assert res.code in {p["code"] for p in P.all_personas()}
    assert res.persona["name"]
    assert res.code in res.card_text()


def test_persona_lookup():
    assert P.get_persona("fita")["code"] == "FITA"
    assert P.get_persona("NOPE") is None


def test_signature_meal_defined():
    for p in P.all_personas():
        assert p["signature_meal"], f"{p['code']} 缺少本命餐"
        assert p["lucky_code"].startswith("mcctl")
