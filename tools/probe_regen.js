// 探针：回血到底有没有在对局中真正发生？
// 若 regen 从不生效，则任何改回血规则的变异都无法被差异测试察觉 —— 那是安全网的盲区。
const fs = require('fs'), vm = require('vm');

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
    set() { return true; }, apply() { return makeStub(); }, construct() { return makeStub(); },
  });
}
global.document = makeStub(); global.window = makeStub(); global.requestAnimationFrame = () => 0;
const store = new Map();
global.localStorage = { getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k) };

const ENGINE = process.argv[2] || 'build/engine.js';
const SEEDS = Number(process.argv[3] || 3);
const TURNS = Number(process.argv[4] || 300);
vm.runInThisContext(fs.readFileSync(ENGINE, 'utf8'));
const G = globalThis.__CF__;
const DIRS = ['up', 'down', 'left', 'right'];

function spendAP(q, budget) {
  let used = 0;
  for (let k = 0; k < budget; k++) {
    if (q.ap < 1) break;
    const ids = q.g.filter(t => t && t.side === 'p' && !t.core && !t.support).map(t => t.id);
    let found = null;
    for (const id of ids) {
      for (const d of DIRS) {
        const draft = G.copy(q); const r = G.extraStep(draft, id, d);
        if (r.error) continue;
        if (draft.g.filter(Boolean).length < q.g.filter(Boolean).length) { found = draft; break; }
      }
      if (found) break;
    }
    if (!found) break;
    Object.assign(q, found); used++;
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
    const draft = G.copy(q); const r = G.moveMain(draft, d);
    if (!r) continue;
    const di = draft.g.findIndex(t => t && t.core && t.id === draft.active);
    const dist = di >= 0 ? Math.min(...targets.map(t => Math.sqrt(G.dist2(di, t)))) : 99;
    const score = r.merges * 10 + r.recruited * 4 - dist * 0.6 + (r.contacts || 0);
    if (!pick || score > pick.score) pick = { d, score };
  }
  return pick;
}

console.log(`引擎: ${ENGINE}`);
for (let s = 0; s < SEEDS; s++) {
  const seed = (20261017 + s * 7919) >>> 0;
  store.clear();
  const q = G.initial(seed);
  let regenEvents = 0, turnHasRegen = 0, damageTurns = 0, hpSeen = 0;
  // 通过 worldStep 返回值里的 fx 抓 regen 事件（引擎自带的事件通道）
  for (let step = 0; step < TURNS; step++) {
    if (q.dead || q.settled) break;
    spendAP(q, 12);
    const pick = chooseDir(q);
    let r = null, dir = null;
    if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
    if (!r) { for (const d of DIRS) { if (d === dir) continue; r = G.worldStep(q, d); if (r) { dir = d; break; } } }
    if (!r) break;
    const fx = r.fx || [];
    const pIds = new Set(q.g.filter(t => t && t.side === 'p').map(t => t.id));
    const heal = fx.filter(f => f.kind === 'regen' && pIds.has(q.g[f.at]?.id)).length;
    if (heal > 0) { regenEvents += heal; turnHasRegen++; }
    if (fx.some(f => f.kind === 'hit')) damageTurns++;
    // 统计当前有多少己方方块不满血（回血的候选者）
    hpSeen += q.g.filter(t => t && t.side === 'p' && !t.support && t.hp < t.cap).length;
  }
  console.log(`  seed ${String(seed).padStart(10)}  endTurn ${String(q.turn).padStart(4)}  ` +
    `regen 事件 ${String(regenEvents).padStart(5)} 次 (${turnHasRegen} 个回合)  ` +
    `受击回合 ${String(damageTurns).padStart(4)}  受伤方块·回合累计 ${hpSeen}`);
}
console.log('\n判读: regen 事件为 0 则回血在整局中从未生效 —— 改回血规则的变异无法被差异测试察觉。');
