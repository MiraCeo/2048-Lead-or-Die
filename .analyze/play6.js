// 底层改动试验：方块级自动收集（≤cap 的己方方块吸收相邻中立，累积到阈值翻倍）
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
const OFF = [[-1, 0], [1, 0], [0, -1], [0, 1]];

// ---- 自动收集：n < cap 的己方方块，吸收四向相邻中立（n<=cap），累积到阈值翻倍 ----
function autoCollect(q, cap, throughput) {
  let grown = 0, eaten = 0;
  if (!cap) return { grown, eaten };
  const lvCore = G.lvl(G.sharedCore(q));
  for (let i = 0; i < 10000; i++) {
    let t = q.g[i];
    if (!t || t.side !== 'p' || t.support || t.n >= cap) continue;
    let used = 0;
    const r = Math.floor(i / 100), c = i % 100;
    for (const [dr, dc] of OFF) {
      if (used >= throughput) break;
      if (t.n >= cap) break;
      const rr = r + dr, cc = c + dc;
      if (rr < 0 || rr >= 100 || cc < 0 || cc >= 100) continue;
      const j = rr * 100 + cc;
      const u = q.g[j];
      if (!u || u.side !== 'n' || u.n > cap) continue;
      t.payload = (t.payload || 0) + u.n;
      q.g[j] = null;
      eaten++; used++;
      while (t.payload >= t.n && t.n * 2 <= cap) {
        t.payload -= t.n;
        t.n *= 2;
        t.cap = 3 ** G.lvl(t.n) * lvCore;
        t.hp = t.cap;
        grown++;
      }
      if (t.payload < t.n) break;
    }
  }
  return { grown, eaten };
}

function spendAP(q, budget) {
  let used = 0;
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
    used++;
  }
  return used;
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

function run({ cap, throughput, seed, maxTurns, label }) {
  let q = G.initial(seed);
  let totalGrown = 0, totalEaten = 0, apUsed = 0;
  let peak = 2, peakTurn = 0, first2048 = null, maxNeutral = 0;
  const t0 = Date.now();
  for (let step = 0; step < maxTurns; step++) {
    if (q.dead || q.settled) break;
    apUsed += spendAP(q, 12);
    const pick = chooseDir(q);
    let r = null, dir = null;
    if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
    if (!r) {
      for (const d of DIRS) { if (d === dir) continue; r = G.worldStep(q, d); if (r) { dir = d; break; } }
    }
    if (!r) break;
    const a = autoCollect(q, cap, throughput);
    totalGrown += a.grown; totalEaten += a.eaten;
    const best = Math.max(2, ...q.g.filter((t) => t && t.side === 'p' && !t.support).map((t) => t.n));
    if (best > peak) { peak = best; peakTurn = q.turn; }
    if (first2048 === null && best >= 2048) first2048 = q.turn;
    const nl = q.g.filter((t) => t && t.side === 'n').length;
    if (nl > maxNeutral) maxNeutral = nl;
    if (q.turn % 100 === 0) {
      const core = G.sharedCore(q);
      console.log(`  [${label}] T${String(q.turn).padStart(4)} 最高${String(best).padStart(5)} 共享core${String(core).padStart(4)} 中立${String(nl).padStart(5)} 吸收累计${totalGrown}/吃${totalEaten} AP${q.ap}`);
    }
  }
  const ms = Date.now() - t0;
  console.log(`  [${label}] 结束：${q.turn} 回合 ${q.dead ? '阵亡' : '存活'} · 峰值 ${peak}（T${peakTurn}）· 首达2048 ${first2048 ?? '未达成'} · 吸收升级 ${totalGrown} 次 / 吃掉中立 ${totalEaten} 块 · 中立峰值 ${maxNeutral} · AP用 ${apUsed} · ${(ms / 1000).toFixed(0)}s`);
  return { label, turns: q.turn, dead: q.dead, peak, peakTurn, first2048, totalGrown, totalEaten, apUsed };
}

const SEED = 20261017;
const MAX = Number(process.argv[2] || 900);
console.log('### 基线（无自动收集）参见此前数据：546 回合阵亡，峰值 1024（T501），AP 用 277');
console.log(`\n### cap=8 吞吐2`);
run({ cap: 8, throughput: 2, seed: SEED, maxTurns: MAX, label: 'cap8' });
console.log(`\n### cap=16 吞吐2`);
run({ cap: 16, throughput: 2, seed: SEED, maxTurns: MAX, label: 'cap16' });
