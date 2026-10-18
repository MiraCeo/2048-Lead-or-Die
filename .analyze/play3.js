// 策略 C：主移动 + 用行动点做“时间冻结”的合并整理
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

const DIRS = ['up', 'down', 'left', 'right'];
const best = (q) => Math.max(2, ...q.g.filter((t) => t && t.side === 'p' && !t.support).map((t) => t.n));

// 用行动点做即刻合并（时间冻结，不推进回合、不触发射击与补给）
function spendAP(q, budget) {
  let used = 0, merged = 0;
  for (let k = 0; k < budget; k++) {
    if (q.ap < 1) break;
    const ids = q.g.filter((t) => t && t.side === 'p' && !t.core && !t.support).map((t) => t.id);
    let found = null;
    for (const id of ids) {
      for (const d of DIRS) {
        const draft = G.copy(q);
        const r = G.extraStep(draft, id, d);
        if (r.error) continue;
        if (draft.g.filter(Boolean).length < q.g.filter(Boolean).length) { found = draft; break; }
      }
      if (found) break;
    }
    if (!found) break;
    Object.assign(q, found);
    used++; merged++;
  }
  return { used, merged };
}

function chooseDir(q) {
  const targets = [];
  q.g.forEach((t, i) => { if (t && t.side === 'n') targets.push(i); });
  q.g.forEach((t, i) => { if (t && t.side === 'e') targets.push(i); });
  if (!targets.length) return null;
  let pick = null;
  for (const d of DIRS) {
    const draft = G.copy(q);
    const r = G.moveMain(draft, d);
    if (!r) continue;
    const di = draft.g.findIndex((t) => t && t.core && t.id === draft.active);
    const dist = di >= 0 ? Math.min(...targets.map((t) => Math.sqrt(G.dist2(di, t)))) : 99;
    const score = r.merges * 10 + r.recruited * 4 - dist * 0.6 + (r.contacts || 0);
    if (!pick || score > pick.score) pick = { d, score };
  }
  return pick;
}

function run(seed, maxTurns, verbose) {
  let q = G.initial(seed);
  const sup = { inside: 0, outside: 0 };
  let apUsed = 0, apMerged = 0, peakBest = 2, peakAt = { turn: 0 };
  const t0 = Date.now();
  for (let step = 0; step < maxTurns; step++) {
    if (q.dead || q.settled) break;
    const a = spendAP(q, 12);
    apUsed += a.used; apMerged += a.merged;
    const pick = chooseDir(q);
    let r = null, dir = null;
    if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
    if (!r) {
      for (const d of DIRS) { if (d === dir) continue; r = G.worldStep(q, d); if (r) { dir = d; break; } }
    }
    if (!r) break;
    sup.inside += r.supply.inside; sup.outside += r.supply.outside;
    const b = best(q);
    if (b > peakBest) { peakBest = b; peakAt.turn = q.turn; }
    if (verbose && q.turn % 20 === 0) {
      const e = q.g.filter((t) => t && t.side === 'e' && t.core).length;
      const nl = q.g.filter((t) => t && t.side === 'n').length;
      console.log(`  T${String(q.turn).padStart(3)} 己核${q.g.filter((t) => t && t.side === 'p' && t.core).length} 敌核${e} 中立${nl} 最高${b} 分${q.score} 击破${q.kills} AP${q.ap}｜AP已用${apUsed}`);
    }
  }
  const ms = Date.now() - t0;
  return { seed, turns: q.turn, dead: q.dead, best: best(q), peakBest, peakAtTurn: peakAt.turn,
    score: q.score, kills: q.kills, sup, apUsed, apMerged, ms };
}

const ARGV_SEED = process.argv[2] ? Number(process.argv[2]) : null;
const ARGV_TURNS = process.argv[3] ? Number(process.argv[3]) : 400;
const JOBS = ARGV_SEED ? [[ARGV_SEED, true]] : [[20261017, true], [777, false], [4242, false]];

for (const [seed, v] of JOBS) {
  console.log(`\n### 策略 C · seed ${seed}`);
  const r = run(seed, ARGV_TURNS, v);
  console.log(`  ${r.turns} 回合 · ${r.dead ? '阵亡' : '存活'} · 最终最高 ${r.best} · 峰值 ${r.peakBest}（T${r.peakAtTurn}）· 得分 ${r.score} · 击破 ${r.kills}`);
  console.log(`  补给 内${r.sup.inside}/外${r.sup.outside} · AP 使用 ${r.apUsed} 次（其中合并 ${r.apMerged} 次）· 耗时 ${(r.ms / 1000).toFixed(1)}s`);
}
