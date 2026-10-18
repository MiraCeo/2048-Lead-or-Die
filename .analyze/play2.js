// 多策略对照：用真实引擎连续跑对局
const fs = require('fs');
const vm = require('vm');

function makeStub() {
  const f = function () {};
  return new Proxy(f, {
    get(t, k) {
      if (k === 'then') return undefined;
      if (k === Symbol.toPrimitive) return () => '';
      if (k === Symbol.iterator) return function* () {};
      if (k === 'toString' || k === 'valueOf') return () => '';
      if (k === 'length') return 0;
      if (!(k in t)) t[k] = makeStub();
      return t[k];
    },
    set() { return true; },
    apply() { return makeStub(); },
    construct() { return makeStub(); },
  });
}
global.document = makeStub();
global.window = makeStub();
global.requestAnimationFrame = () => 0;
const store = new Map();
global.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};

vm.runInThisContext(fs.readFileSync(__dirname + '/core-fleet.engine.js', 'utf8'));
const G = globalThis.__CF__;

const scan = (q) => {
  const neutral = q.g.filter((t) => t && t.side === 'n');
  const grouped = neutral.filter((t) => t.ng);
  const sizes = new Map();
  grouped.forEach((t) => sizes.set(t.ng, (sizes.get(t.ng) || 0) + 1));
  return {
    coresP: q.g.filter((t) => t && t.side === 'p' && t.core).length,
    coresE: q.g.filter((t) => t && t.side === 'e' && t.core).length,
    neutral: neutral.length,
    groups: sizes.size,
    maxGroup: sizes.size ? Math.max(...sizes.values()) : 0,
    best: Math.max(2, ...q.g.filter((t) => t && t.side === 'p' && !t.support).map((t) => t.n)),
  };
};

// 策略 A：追中立组 / 敌核 / 散落中立（上一局用的）
function chaseGroup(q) {
  const targets = [];
  q.g.forEach((t, i) => { if (t && t.side === 'n' && t.ng) targets.push(i); });
  if (!targets.length) q.g.forEach((t, i) => { if (t && t.side === 'e' && t.core) targets.push(i); });
  if (!targets.length) q.g.forEach((t, i) => { if (t && t.side === 'n') targets.push(i); });
  return targets;
}

// 策略 B：就近吃 + 优先合并（限制活动半径，不长途奔波）
function nearby(q) {
  const ci = q.g.findIndex((t) => t && t.core && t.id === q.active);
  if (ci < 0) return [];
  const R = 14;
  const out = [];
  q.g.forEach((t, i) => {
    if (!t) return;
    if (t.side === 'n') out.push([i, 1]);
    else if (t.side === 'e') out.push([i, t.core ? 3 : 2]);
  });
  const near = out.filter(([i]) => Math.sqrt(G.dist2(ci, i)) <= R);
  return (near.length ? near : out).map(([i]) => i);
}

function pickDir(q, mode) {
  const targets = mode === 'A' ? chaseGroup(q) : nearby(q);
  if (!targets.length) return null;
  let best = null;
  for (const d of ['up', 'down', 'left', 'right']) {
    const draft = G.copy(q);
    const r = G.moveMain(draft, d);
    if (!r) continue;
    const di = draft.g.findIndex((t) => t && t.core && t.id === draft.active);
    const dist = di >= 0 ? Math.min(...targets.map((t) => Math.sqrt(G.dist2(di, t)))) : 99;
    const w = mode === 'A' ? { m: 6, rec: 3, dist: 2 } : { m: 10, rec: 4, dist: 0.6 };
    const score = r.merges * w.m + r.recruited * w.rec - dist * w.dist + (r.contacts || 0);
    if (!best || score > best.score) best = { d, score };
  }
  return best;
}

function run(mode, seed, maxTurns, verbose) {
  let q = G.initial(seed);
  const sup = { inside: 0, outside: 0 };
  const curve = [];
  let groupPicks = 0, dissolutions = 0, coreBreaks = 0, peaks = { coresE: 0, neutral: 0, maxGroup: 0 };
  const t0 = Date.now();

  for (let step = 0; step < maxTurns; step++) {
    if (q.dead || q.settled) break;
    const before = new Set(q.logs);
    const pick = pickDir(q, mode);
    let r = null, dir = null;
    if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
    if (!r) {
      for (const d of ['up', 'down', 'left', 'right']) {
        if (d === dir) continue;
        r = G.worldStep(q, d);
        if (r) { dir = d; break; }
      }
    }
    if (!r) break;
    sup.inside += r.supply.inside;
    sup.outside += r.supply.outside;
    for (const t of q.logs) {
      if (before.has(t)) break;
      if (/整组收编/.test(t)) groupPicks++;
      if (/分化/.test(t)) dissolutions++;
      if (/核心 .* 被摧毁/.test(t)) coreBreaks++;
    }
    const sc = scan(q);
    peaks.coresE = Math.max(peaks.coresE, sc.coresE);
    peaks.neutral = Math.max(peaks.neutral, sc.neutral);
    peaks.maxGroup = Math.max(peaks.maxGroup, sc.maxGroup);
    if (q.turn % 20 === 0) {
      curve.push({ t: q.turn, ...sc, ap: q.ap, score: q.score, kills: q.kills });
      if (verbose) console.log(`  T${String(q.turn).padStart(3)} 己核${sc.coresP} 敌核${sc.coresE} 中立${sc.neutral}(组${sc.groups}/最大${sc.maxGroup}) 最高${sc.best} 分${q.score} 击破${q.kills} AP${q.ap}`);
    }
  }
  const ms = Date.now() - t0;
  const fin = scan(q);
  return { mode, seed, turns: q.turn, dead: q.dead, fin, sup, groupPicks, dissolutions, coreBreaks, peaks, curve, ms };
}

const results = [];
for (const [mode, seed, verbose] of [['A', 20261017, false], ['B', 20261017, true], ['B', 777, false]]) {
  console.log(`\n### 策略 ${mode} · seed ${seed}`);
  const r = run(mode, seed, 400, verbose);
  results.push(r);
  console.log(`  结果：${r.turns} 回合，${r.dead ? '阵亡' : '存活'}，最高数字 ${r.fin.best}，得分 ${r.fin.score}，击破 ${r.fin.kills}，耗时 ${(r.ms / 1000).toFixed(1)}s`);
  console.log(`  补给累计：内 ${r.sup.inside} / 外 ${r.sup.outside}（比 ${(r.sup.outside / Math.max(1, r.sup.inside)).toFixed(1)}:1）`);
  console.log(`  整组收编 ${r.groupPicks} 次 · 分化 ${r.dissolutions} 次 · 核心摧毁 ${r.coreBreaks} 次`);
  console.log(`  峰值：敌核 ${r.peaks.coresE} · 中立 ${r.peaks.neutral} · 中立组最大 ${r.peaks.maxGroup} 块`);
}
