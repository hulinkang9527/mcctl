"""人格引擎测试。"""
from mcctl.engines import persona as P


def test_questions_and_personas():
    assert len(P.questions()) == 6
    codes = {p["code"] for p in P.all_personas()}
    assert codes == {"BIGS", "FITA", "SPCY", "SWEET", "EARL", "NITE", "SQUAD", "LOYT"}


def test_each_persona_is_reachable():
    """枚举 2^6 种作答，保证 8 型人格都能被鉴定出来（题库可区分）。"""
    reachable = set()
    for mask in range(2 ** len(P.questions())):
        answers = ["b" if (mask >> i) & 1 else "a" for i in range(len(P.questions()))]
        reachable.add(P.score(answers).code)
    assert reachable == {p["code"] for p in P.all_personas()}


def test_known_answers():
    # 全 a：早餐/经典/控卡/省钱/回血/兑换，结果必须是合法代号
    res = P.score(["a"] * 6)
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
