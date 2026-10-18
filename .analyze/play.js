// 在 Node 里用真实引擎跑一局「核心群岛」
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
if (!G) { console.error('engine not exported'); process.exit(1); }

const state = (q) => {
  const coresP = q.g.filter((t) => t && t.side === 'p' && t.core);
  const coresE = q.g.filter((t) => t && t.side === 'e' && t.core);
  const neutral = q.g.filter((t) => t && t.side === 'n');
  const groups = new Set(neutral.filter((t) => t.ng).map((t) => t.ng));
  const best = Math.max(2, ...q.g.filter((t) => t && t.side === 'p' && !t.support).map((t) => t.n));
  return {
    turn: q.turn, ap: q.ap, coresP: coresP.length, coresE: coresE.length,
    neutral: neutral.length, groups: groups.size, best, score: q.score,
    kills: q.kills, highest: q.highestN, dead: q.dead, settled: q.settled,
  };
};

// 玩家策略：向最近的“已成形中立组”推进（没有组则向最近的敌方核心 / 散落中立）
function pickDir(q) {
  const targets = [];
  q.g.forEach((t, i) => { if (t && t.side === 'n' && t.ng) targets.push(i); });
  if (!targets.length) q.g.forEach((t, i) => { if (t && t.side === 'e' && t.core) targets.push(i); });
  if (!targets.length) q.g.forEach((t, i) => { if (t && t.side === 'n') targets.push(i); });
  if (!targets.length) return null;

  let best = null;
  for (const d of ['up', 'down', 'left', 'right']) {
    const draft = G.copy(q);
    const r = G.moveMain(draft, d);
    if (!r) continue;
    const di = draft.g.findIndex((t) => t && t.core && t.id === draft.active);
    const dist = di >= 0 ? Math.min(...targets.map((t) => Math.sqrt(G.dist2(di, t)))) : 999;
    const score = r.merges * 6 + r.recruited * 3 - dist * 2 + (r.contacts || 0);
    if (!best || score > best.score) best = { d, score, r };
  }
  return best;
}

const seed = Number(process.argv[2] || 20261017);
const maxTurns = Number(process.argv[3] || 200);
let q = G.initial(seed);

const supplyTot = { inside: 0, outside: 0 };
const events = [];
let stuck = 0;
const t0 = Date.now();

console.log('=== 开局 ===', JSON.stringify(state(q)));
console.log('初始非空格数 =', q.g.filter(Boolean).length);

for (let step = 0; step < maxTurns; step++) {
  if (q.dead || q.settled) break;
  const before = new Set(q.logs);
  const pick = pickDir(q);
  let r = null, dir = null;
  if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
  if (!r) {
    for (const d of ['up', 'down', 'left', 'right']) {
      if (d === dir) continue;
      r = G.worldStep(q, d);
      if (r) { dir = d; break; }
    }
  }
  if (!r) { stuck++; if (stuck > 3) { console.log('!! 连续无有效主移动，对局终止于回合', q.turn); break; } continue; }
  stuck = 0;

  supplyTot.inside += r.supply.inside;
  supplyTot.outside += r.supply.outside;

  for (const t of q.logs) {
    if (before.has(t)) break;
    if (/成组|分化|核心|增援|碉堡|2048|收编|升级|成长|上限/.test(t)) events.push(`[T${q.turn}] ${t}`);
  }

  if (q.turn % 20 === 0) {
    const st = state(q);
    console.log(`T${String(st.turn).padStart(3)} dir=${dir} ap=${st.ap} 己核=${st.coresP} 敌核=${st.coresE} 中立=${st.neutral}(${st.groups}组) 最高=${st.best} 分=${st.score} 击破=${st.kills} | 本回合补给 内${r.supply.inside}/外${r.supply.outside} 射${r.playerShots}/${r.enemyShots} AP+${r.earned}`);
  }
}

const ms = Date.now() - t0;
console.log('\n=== 结束 ===', JSON.stringify(state(q)));
console.log(`跑了 ${q.turn} 回合，耗时 ${ms}ms（${(ms / Math.max(1, q.turn)).toFixed(1)}ms/回合）`);
console.log('累计补给：内', supplyTot.inside, '/ 外', supplyTot.outside);
console.log('\n=== 关键事件（尾部 40 条）===');
console.log(events.slice(-40).join('\n'));
console.log('\n=== 最后 12 条战报 ===');
console.log(q.logs.join('\n'));
