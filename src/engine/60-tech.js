// ==== 60-tech ====
// 溯源: 阶段 2 的压缩文本 main.script.js 第 75–93 行（此后经阶段 3 改名、阶段 4 格式化）
// 科技树 UI 与购买、飞行器成长、置换
  function checkGoal(q, turn = q.turn) {
    const best = Math.max(2, ...q.g.filter((t) => t?.side === 'p' && !t.support).map((t) => t.n));
    q.highestN = Math.max(q.highestN || 2, best);
    if (!q.goalReached && best >= 2048) {
      q.goalReached = true;
      q.goalTurn = turn;
      log(q, '阶段目标达成：2048！可结算远征或继续挑战。');
    }
  }
  const ABSORB_CAP = 4,
    ABSORB_TP = 2,
    ABSORB_RADIUS = 1,
    SITE_TP = 4,
    REGEN_RATE = 0.05,
    REGEN_DELAY = 10,
    AI_REGEN_RATE = 0,
    AI_ABSORB_CEILING = 4;
  function ringCells(i, R) {
    const out = [],
      r = Math.floor(i / N),
      c = i % N;
    for (let dr = -R; dr <= R; dr++)
      for (let dc = -R; dc <= R; dc++) {
        if (!dr && !dc) continue;
        const rr = r + dr,
          cc = c + dc;
        if (rr < 0 || rr >= N || cc < 0 || cc >= N) continue;
        out.push(rr * N + cc);
      }
    return out;
  }
  function absorbValue(q, t, value) {
    if (!t || t.side !== 'p' || t.support) return 0;
    t.payload = (t.payload || 0) + value;
    return 0;
  }
  function markCombat(q, t) {
    if (!t || t.side === 'n') return;
    q.combat = q.combat || {};
    q.combat[t.team] = q.turn;
  }
  function regenTiles(q, fx) {
    let healed = 0;
    q.combat = q.combat || {};
    for (let i = 0; i < N * N; i++) {
      const t = q.g[i];
      if (!t || t.support || t.side === 'n') continue;
      if (t.hp >= t.cap) continue;
      const rate = t.side === 'p' ? REGEN_RATE : AI_REGEN_RATE;
      if (!(rate > 0)) continue;
      const last = q.combat[t.team];
      if (last !== undefined && q.turn - last < REGEN_DELAY) continue;
      const amt = Math.max(1, Math.ceil(t.cap * rate));
      t.hp = Math.min(t.cap, t.hp + amt);
      healed++;
      if (t.hp >= t.cap && fx) fx.push({ kind: 'regen', at: i });
    }
    return healed;
  }
  function settleTiles(q, lvCore, fx) {
    const th = absorbThreshold(q);
    let grown = 0;
    for (let i = 0; i < N * N; i++) {
      const t = q.g[i];
      if (!t || t.side !== 'p' || t.support) continue;
      if (t.n > th) {
        if (t.payload) t.payload = 0;
        continue;
      }
      let pay = t.payload || 0;
      if (pay <= 0) continue;
      while (pay >= t.n) {
        pay -= t.n;
        const oldCap = t.cap || 1,
          oldHp = t.hp ?? oldCap;
        t.n *= 2;
        t.cap = 3 ** lvl(t.n) * lvCore;
        t.hp = Math.max(1, Math.min(t.cap, Math.round((oldHp * t.cap) / oldCap)));
        grown++;
        if (fx) fx.push({ kind: 'pulse', at: i });
        if (t.n > th) {
          pay = 0;
          break;
        }
      }
      t.payload = pay;
    }
    return grown;
  }
  function autoCollect(q, fx) {
    const lvCore = lvl(sharedCore(q));
    let grown = 0,
      absorbed = 0;
    const tps = absorbTp(q),
      th = absorbThreshold(q);
    survey(q);
    for (let s = 0; s < N * N; s++) {
      const site = q.g[s];
      if (!site || site.side !== 'p' || !(site.core || site.support)) continue;
      const R = site.collectRadius ?? siteRadius(q),
        ring = ringCells(s, R);
      const receivers = ring.filter((i) => {
        const t = q.g[i];
        return !!t && t.side === 'p' && !t.support && t.n <= th;
      });
      let budget = siteBudget(q);
      const cands = ring
        .filter((j) => {
          const u = q.g[j];
          return !!u && u.side === 'n' && u.n <= th;
        })
        .sort((a, b) => dist2(s, a) - dist2(s, b) || a - b);
      for (const j of cands) {
        if (budget <= 0) break;
        const u = q.g[j];
        if (!u || u.side !== 'n') continue;
        let recv = -1,
          bestD = Infinity;
        for (const i of receivers) {
          const d = dist2(i, j);
          if (d < bestD || (d === bestD && i < recv)) {
            bestD = d;
            recv = i;
          }
        }
        if (recv < 0 && !site.support && site.n <= th) recv = s;
        if (recv < 0) continue;
        const v = u.n;
        q.g[j] = null;
        absorbed++;
        budget--;
        if (fx) fx.push({ kind: 'absorb', from: j, to: recv });
        grown += absorbValue(q, q.g[recv], v, lvCore);
      }
    }
    for (let i = 0; i < N * N; i++) {
      const t = q.g[i];
      if (!t || t.side !== 'p' || t.support || t.n > th) continue;
      let used = 0;
      for (const d in dirs) {
        if (used >= tps || t.n > th) break;
        const j = neighbor(i, d);
        if (j < 0) continue;
        const u = q.g[j];
        if (!u || u.side !== 'n' || u.n > th) continue;
        const v = u.n;
        q.g[j] = null;
        absorbed++;
        used++;
        if (fx) fx.push({ kind: 'absorb', from: j, to: i });
        grown += absorbValue(q, t, v, lvCore);
      }
    }
    grown += settleTiles(q, lvCore, fx);
    regenTiles(q, fx);
    if (grown || absorbed) rescale(q);
    return grown;
  }
  const SCORE_PER_TECH = 100,
    TECH_TP_MAX = 2,
    TECH_RADIUS_MAX = 2,
    TECH_THRESHOLD_MAX = 3;
  function absorbTpAt(lv) {
    return ABSORB_TP + (lv || 0);
  }
  function absorbTp(q) {
    return absorbTpAt(q.upTp || 0);
  }
  function absorbThresholdAt(lv) {
    return ABSORB_CAP * 2 ** (lv || 0);
  }
  function absorbThreshold(q) {
    return absorbThresholdAt(q.upThreshold || 0);
  }
  function aiAbsorbCeiling(q) {
    return AI_ABSORB_CEILING;
  }
  function siteRadiusAt(lv) {
    return ABSORB_RADIUS + (lv || 0);
  }
  function siteBudgetAt(lv) {
    return SITE_TP + 4 * (lv || 0);
  }
  function siteRadius(q) {
    return siteRadiusAt(q.upRadius || 0);
  }
  function siteBudget(q) {
    return siteBudgetAt(q.upRadius || 0);
  }
  function techLevel(q, line) {
    return line === 'tp' ? q.upTp || 0 : line === 'radius' ? q.upRadius || 0 : q.upThreshold || 0;
  }
  function techMax(line) {
    return line === 'tp' ? TECH_TP_MAX : line === 'radius' ? TECH_RADIUS_MAX : TECH_THRESHOLD_MAX;
  }
  function techCost(line, level) {
    return 8 + 8 * level;
  }
  function survey(q) {
    q.visited = q.visited || {};
    let found = 0;
    for (let i = 0; i < N * N; i++) {
      const t = q.g[i];
      if (!t || t.side !== 'p' || t.support) continue;
      const b = Math.floor(i / N / 10) * 10 + Math.floor((i % N) / 10);
      if (!q.visited[b]) {
        q.visited[b] = 1;
        found++;
      }
    }
    if (found) q.tech = (q.tech || 0) + found;
    return found;
  }
  function convertScore(q) {
    const pts = Math.floor((q.score || 0) / SCORE_PER_TECH);
    if (pts <= 0) return 0;
    q.score -= pts * SCORE_PER_TECH;
    q.tech = (q.tech || 0) + pts;
    return pts;
  }
  function buyTech(q, line) {
    const lv = techLevel(q, line);
    if (lv >= techMax(line)) return { error: '这条线已经满级。' };
    const cost = techCost(line, lv);
    if ((q.tech || 0) < cost) return { error: '科技点不足：需要 ' + cost + '，现有 ' + (q.tech || 0) + '。' };
    q.tech -= cost;
    if (line === 'tp') q.upTp = lv + 1;
    else if (line === 'radius') q.upRadius = lv + 1;
    else q.upThreshold = lv + 1;
    return { line, level: lv + 1, cost, left: q.tech };
  }
  function techBuy(line) {
    const q = copy(s),
      r = buyTech(q, line);
    if (r.error) {
      say(r.error);
      draw();
      return;
    }
    remember();
    s = q;
    save();
    ui();
    say('科技树：' + (line === 'tp' ? '吞吐' : '收集半径') + ' 升到 ' + r.level + ' 级，消耗 ' + r.cost + ' 点。');
  }
  function techConvert() {
    const q = copy(s),
      got = convertScore(q);
    if (!got) {
      say('积分不足 ' + SCORE_PER_TECH + '，无法兑换。');
      draw();
      return;
    }
    remember();
    s = q;
    save();
    ui();
    say('兑换 ' + got + ' 点科技点，消耗 ' + got * SCORE_PER_TECH + ' 积分。');
  }
