// 吸收写进引擎内部（worldStep 内、移动之后），外部只调原版 worldStep —— 与 play6 逐项一致，唯独吸收位置不同
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

vm.runInThisContext(fs.readFileSync(__dirname + '/core-fleet.engine.collect.js', 'utf8'));
const G = globalThis.__CF__;
const DIRS = ['up', 'down', 'left', 'right'];

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

const SEED = 20261017, MAX = Number(process.argv[2] || 900);
console.log('=== 引擎内部吸收（移动 → 吸收 → 射击 → 敌方）｜cap=8 吞吐=2 回血=满 ===');
console.log('（对照：play6 外部吸收、回合末 = 694 回合 / 峰值 16384 / T680 达成 2048）\n');

let q = G.initial(SEED);
let apUsed = 0, peak = 2, peakTurn = 0, first2048 = null, maxMembers = 0;
const t0 = Date.now();
for (let step = 0; step < MAX; step++) {
  if (q.dead || q.settled) break;
  apUsed += spendAP(q, 12);
  const pick = chooseDir(q);
  let r = null, dir = null;
  if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
  if (!r) {
    for (const d of DIRS) { if (d === dir) continue; r = G.worldStep(q, d); if (r) { dir = d; break; } }
  }
  if (!r) break;
  const members = q.g.filter((t) => t && t.side === 'p' && !t.support).length;
  if (members > maxMembers) maxMembers = members;
  const best = Math.max(2, ...q.g.filter((t) => t && t.side === 'p' && !t.support).map((t) => t.n));
  if (best > peak) { peak = best; peakTurn = q.turn; }
  if (first2048 === null && best >= 2048) first2048 = q.turn;
  if (q.turn % 100 === 0) {
    console.log(`  T${String(q.turn).padStart(4)} 最高${String(best).padStart(5)} 成员${String(members).padStart(3)} 共享core${String(G.sharedCore(q)).padStart(4)} 中立${String(q.g.filter((t) => t && t.side === 'n').length).padStart(5)} AP${q.ap}`);
  }
}
console.log(`\n结束 ${q.turn} 回合 ${q.dead ? '阵亡' : '存活'} · 峰值 ${peak}(T${peakTurn}) · 首达2048 ${first2048 ?? '未达成'} · 成员峰值 ${maxMembers} · AP ${apUsed} · ${((Date.now() - t0) / 1000).toFixed(0)}s`);
