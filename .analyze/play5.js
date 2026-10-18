// 定位崩盘：跑到指定回合后逐回合打印态势
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

const SEED = 20261017;
const WATCH_FROM = 470;
let q = G.initial(SEED);
let turn = 0;

const line = (q, tag) => {
  const coresP = q.g.filter((t) => t && t.side === 'p' && t.core).map((t) => `${t.n}(${t.hp}/${t.cap})`);
  const coresE = q.g.filter((t) => t && t.side === 'e' && t.core);
  const ci = q.g.findIndex((t) => t && t.core && t.id === q.active);
  const eDist = coresE.map((t) => {
    const i = q.g.findIndex((x) => x && x.id === t.id);
    return `${t.n}@${ci >= 0 && i >= 0 ? Math.round(Math.sqrt(G.dist2(ci, i))) : '?'}`;
  });
  const own = q.g.filter((t) => t && t.side === 'p' && !t.support);
  const ownHp = own.reduce((a, t) => a + t.hp, 0);
  const best = Math.max(2, ...own.map((t) => t.n));
  const eUnits = q.g.filter((t) => t && t.side === 'e').length;
  console.log(`${tag} T${q.turn} 己核[${coresP.join(' ')}] 己员${own.length}(最高${best}) 总血${Math.round(ownHp)} AP${q.ap} | 敌核[${eDist.join(' ')}] 敌员${eUnits}`);
};

while (turn < 700 && !q.dead && !q.settled) {
  spendAP(q, 12);
  const pick = chooseDir(q);
  let r = null, dir = null;
  if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
  if (!r) {
    for (const d of DIRS) { if (d === dir) continue; r = G.worldStep(q, d); if (r) { dir = d; break; } }
  }
  if (!r) break;
  turn++;
  if (q.turn >= WATCH_FROM) {
    const fresh = [];
    for (const t of q.logs) { fresh.push(t); if (fresh.length >= 2) break; }
    line(q, '  ');
    for (const t of fresh.slice(0, 1)) console.log('        └ ' + t);
  }
}
console.log('\n最终:', q.turn, '回合', q.dead ? '阵亡' : '存活');
