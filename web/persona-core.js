/* ============================================================
 *  mcctl · 麦门人格测试内核（McPersona core）
 *  纯逻辑、无 DOM —— 浏览器与 Node 均可加载。
 *  题库与计分规则必须与 src/mcctl/data/personas.json 逐字一致，
 *  由 tests/test_persona_parity.py 对 512 种作答做端到端一致性校验。
 * ============================================================ */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.McPersona = api;
})(typeof self !== "undefined" ? self : null, function () {
  "use strict";

  // ---- 命定套餐 code → 展示名（与 mock_data 一致）----
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

  // ---- 答案特点维度 ----
  const DIM_LABELS = {
    decisive: "决策果断",
    explore: "爱做功课",
    efficiency: "效率优先",
    saving: "省钱倾向",
    classic: "经典偏好",
    novelty: "尝鲜偏好",
    social: "社交主导",
    easygoing: "随和跟随",
    adventurous: "冒险精神",
    steady: "求稳保守",
    indulgence: "满足优先",
    value: "性价比优先",
    loyal: "认准不变",
    variety: "喜欢变化",
  };

  // ---- 8 型人格（顺序即图鉴顺序，平局时按此顺序定夺）----
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
      cta: "mcctl party --people 6",
      meal: ["BUR_BIGMAC", "BUR_MALA_CHICKEN", "SIDE_NUGGETS_10", "SIDE_FRIES_L", "DRK_COLA_M", "DRK_COLA_ZERO"] },
    { code: "LOYT", emoji: "🪙", name: "麦门省钱主教", title: "麦麦省首席领券官 · 积分套利大祭司",
      motto: "没有券的订单是不完整的，省到就是赚到。", color: ["#8A6410", "#FFE9A8"],
      traits: ["券王", "积分精算", "极致性价比"],
      desc: "把每次下单当作小型套利，到手价是你唯一的信仰。",
      cta: "mcctl save", meal: ["BUR_DOUBLE_CHEESE", "SIDE_FRIES_M", "DRK_COLA_ZERO"] },
  ];

  /* ---- 8 道题：前 7 题二选一（a/b），第 8 题终局四选一（a/b/c/d）
   * text：选项文案；score：人格加分；dim：答案特点维度（结果页解释用） ---- */
  const QUESTIONS = [
    { id: 1, q: "你到店/打开点餐页后，通常是？",
      a: { text: "秒选熟悉套餐，不纠结（果断）", score: { BIGS: 2, EARL: 1 }, dim: "decisive" },
      b: { text: "研究菜单很久，来回对比（探索）", score: { SPCY: 2, SWEET: 1 }, dim: "explore" } },
    { id: 2, q: "下单前，你会先研究优惠券吗？",
      a: { text: "直接下单，省时间（效率）", score: { NITE: 2, EARL: 1 }, dim: "efficiency" },
      b: { text: "先把优惠券全部研究一遍（省钱）", score: { LOYT: 2, FITA: 1 }, dim: "saving" } },
    { id: 3, q: "你点餐更偏爱？",
      a: { text: "固定搭配，次次都差不多（稳定）", score: { EARL: 2, FITA: 1 }, dim: "classic" },
      b: { text: "每次都试新组合（尝鲜）", score: { SWEET: 2, SPCY: 1 }, dim: "novelty" } },
    { id: 4, q: "朋友聚餐时，你通常是？",
      a: { text: "拍板、算预算、张罗的人（主导）", score: { SQUAD: 2, LOYT: 1 }, dim: "social" },
      b: { text: "跟着大家选，吃啥都行（跟随）", score: { FITA: 2, SWEET: 1 }, dim: "easygoing" } },
    { id: 5, q: "面对新品，你会？",
      a: { text: "立刻尝试，怕错过（冒险）", score: { SPCY: 2, SQUAD: 1 }, dim: "adventurous" },
      b: { text: "继续买熟悉的，稳妥（稳妥）", score: { BIGS: 2, FITA: 1 }, dim: "steady" } },
    { id: 6, q: "你更在意？",
      a: { text: "吃得满足、分量够、开心（满足）", score: { SWEET: 2, SQUAD: 1 }, dim: "indulgence" },
      b: { text: "每一块钱都花得划算（价值）", score: { LOYT: 2, NITE: 1 }, dim: "value" } },
    { id: 7, q: "你有固定的必点款吗？",
      a: { text: "有，认准了就一直点（忠诚）", score: { EARL: 2, BIGS: 1 }, dim: "loyal" },
      b: { text: "没有，喜欢不断更换（变化）", score: { NITE: 2, SQUAD: 1 }, dim: "variety" } },
    { id: 8, final: true, q: "如果今天的麦门之旅只能选一个结局，你选？",
      a: { text: "极致省钱（券王结局）", score: { LOYT: 1 }, dim: "saving" },
      b: { text: "快乐尝鲜（新品结局）", score: { SPCY: 1 }, dim: "novelty" },
      c: { text: "稳定满足（经典结局）", score: { BIGS: 1 }, dim: "classic" },
      d: { text: "朋友全员满意（团长结局）", score: { SQUAD: 1 }, dim: "social" } },
  ];

  const OPTIONS = ["a", "b", "c", "d"];

  /** 该题实际提供的选项字母 */
  function optionsOf(q) {
    return OPTIONS.filter((k) => q && q[k]);
  }

  function normalize(answers) {
    return answers.map((raw, i) => {
      if (i >= QUESTIONS.length) return null;
      const valid = optionsOf(QUESTIONS[i]);
      const ch = String(raw == null ? "" : raw).toLowerCase();
      return valid.indexOf(ch) >= 0 ? ch : "a";
    }).filter((x) => x !== null);
  }

  /** 统计答案特点（维度出现次数，取前 3） */
  function traitsOf(norm) {
    const counts = {};
    norm.forEach((ch, i) => {
      const dim = QUESTIONS[i][ch].dim;
      if (dim) counts[dim] = (counts[dim] || 0) + 1;
    });
    return Object.keys(counts)
      .sort((a, b) => (counts[b] - counts[a]) || (a < b ? -1 : 1))
      .slice(0, 3)
      .map((k) => ({ key: k, label: DIM_LABELS[k] || k, count: counts[k] }));
  }

  /**
   * 计算人格结果。
   * 同分裁决（与 Python 引擎一致）：
   *   1. 终局题（最后一题且 final=true）指向的人格若在并列集合中，取之；
   *   2. 否则按图鉴顺序取并列中最靠前者。
   */
  function scoreAll(answers) {
    const norm = normalize(answers || []);
    const scores = {};
    PERSONAS.forEach((p) => (scores[p.code] = 0));
    const picks = [];
    norm.forEach((ch, i) => {
      const picked = QUESTIONS[i][ch].score;
      picks.push({ index: i, choice: ch, score: picked });
      Object.keys(picked).forEach((c) => (scores[c] = (scores[c] || 0) + picked[c]));
    });

    const order = PERSONAS.map((p) => p.code);
    const rank = {};
    order.forEach((c, i) => (rank[c] = i));
    const top = Math.max.apply(null, order.map((c) => scores[c]));
    const tied = order.filter((c) => scores[c] === top);
    let winner = tied[0];
    const tie = tied.length > 1;
    let tieBrokenBy = null;

    if (tie) {
      if (picks.length) {
        const last = picks[picks.length - 1];
        if (QUESTIONS[last.index].final) {
          const cand = tied.filter((c) => (last.score[c] || 0) > 0);
          if (cand.length) { winner = cand[0]; tieBrokenBy = "final"; }
        }
      }
      if (!tieBrokenBy) tieBrokenBy = "index";
    }

    let runnerUp = null;
    if (tie) {
      runnerUp = tied.filter((c) => c !== winner)[0] || null;
    } else {
      const rest = order.filter((c) => c !== winner)
        .sort((a, b) => (scores[b] - scores[a]) || (rank[a] - rank[b]));
      runnerUp = rest[0] || null;
    }
    const second = runnerUp ? scores[runnerUp] : 0;
    const persona = PERSONAS.find((p) => p.code === winner);
    const runnerUpPersona = runnerUp ? PERSONAS.find((p) => p.code === runnerUp) : null;

    const keyQuestions = picks
      .map((x) => {
        const w = x.score[winner] || 0;
        const r = runnerUp ? (x.score[runnerUp] || 0) : 0;
        return { id: QUESTIONS[x.index].id, q: QUESTIONS[x.index].q, choice: x.choice,
                 text: QUESTIONS[x.index][x.choice].text, delta: w - r, winnerPoints: w };
      })
      .sort((a, b) => (b.delta - a.delta) || (b.winnerPoints - a.winnerPoints) || (a.id - b.id))
      .slice(0, 2);

    const explanation = { traits: traitsOf(norm), keyQuestions, topScore: top, runnerUpScore: second };
    const lines = [];
    if (explanation.traits.length) {
      lines.push("你的答案特点：" + explanation.traits.map((t) => `${t.label}（${t.count}）`).join("、"));
    }
    keyQuestions.forEach((k) => {
      lines.push(`第 ${k.id} 题「${k.q}」你选了 ${k.choice.toUpperCase()}：${k.text}`);
    });
    if (tie && runnerUpPersona) {
      lines.push(`提示：你与 ${runnerUpPersona.name}（${runnerUp}）同分，按` +
                 (tieBrokenBy === "final" ? "终局题" : "图鉴顺序") + "定夺。");
    }

    return {
      code: winner, persona, scores,
      margin: top - second,
      runnerUp, runnerUpPersona,
      tie, tieBrokenBy,
      explanation, explainLines: lines,
    };
  }

  /** 按每题实际选项数随机作答 */
  function randomAnswers(rng) {
    const r = rng || Math.random;
    return QUESTIONS.map((q) => {
      const opts = optionsOf(q);
      return opts[Math.floor(r() * opts.length) % opts.length];
    });
  }

  return {
    MEALS, PERSONAS, QUESTIONS, DIM_LABELS, OPTIONS,
    optionsOf, normalize, traitsOf, scoreAll, randomAnswers,
  };
});
