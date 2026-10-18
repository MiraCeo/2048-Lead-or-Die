// Per-turn trace, for locating the FIRST turn where two absorption positions diverge.
//
//   node tools/trace.js <engine.js> <position> <seed> <maxTurns> <outfile.jsonl>
//
// Same greedy agent as tools/harness.js, but instead of printing progress it
// writes one JSON line per turn with a digest of the world state. Comparing two
// traces tells us the exact turn the trajectories split, which is where the
// causal mechanism has to live.
const fs = require('fs');
const vm = require('vm');

const ENGINE = process.argv[2];
const POS = process.argv[3] || 'end';
const SEED = Number(process.argv[4] || 20261017);
const MAX = Number(process.argv[5] || 150);
const OUT = process.argv[6] || 'build/traces/trace.jsonl';

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

vm.runInThisContext(fs.readFileSync(ENGINE, 'utf8'));
const G = globalThis.__CF__;
const DIRS = ['up', 'down', 'left', 'right'];
const callExternally = (POS === 'end' || POS === 'external');

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

// Order-sensitive digest of the whole board (occupancy, side, n, team, flags).
function gridHash(q) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < q.g.length; i++) {
    const t = q.g[i];
    if (!t) continue;
    const s = t.side + t.n + '|' + (t.team || '') + (t.core ? 'c' : '') +
              (t.support ? 's' : '') + (t.ng || '') + (t.kind || '');
    for (let k = 0; k < s.length; k++) { h ^= s.charCodeAt(k); h = Math.imul(h, 16777619) >>> 0; }
    h ^= i; h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

const lines = [];
function snap(q, note) {
  const ci = (() => { const i = q.g.findIndex((t) => t && t.core && t.id === q.active); return i; })();
  lines.push(JSON.stringify({
    turn: q.turn,
    note,
    ap: q.ap,
    sharedCore: G.sharedCore(q),
    mainN: ci >= 0 ? q.g[ci].n : null,
    mainHp: ci >= 0 ? q.g[ci].hp : null,
    mainCap: ci >= 0 ? q.g[ci].cap : null,
    pCores: q.g.filter((t) => t && t.core && t.side === 'p').length,
    nPlayer: q.g.filter((t) => t && t.side === 'p' && !t.support).length,
    nNeutral: q.g.filter((t) => t && t.side === 'n').length,
    nEnemy: q.g.filter((t) => t && t.side === 'e').length,
    nSupport: q.g.filter((t) => t && t.support).length,
    empty: q.g.filter((t) => !t).length,
    kills: q.kills,
    rng: q.seed,
    hash: gridHash(q),
  }));
}

const q = G.initial(SEED);
snap(q, 'init');
for (let step = 0; step < MAX; step++) {
  if (q.dead || q.settled) break;
  spendAP(q, 12);
  const pick = chooseDir(q);
  let r = null, dir = null;
  if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
  if (!r) {
    for (const d of DIRS) { if (d === dir) continue; r = G.worldStep(q, d); if (r) { dir = d; break; } }
  }
  if (!r) break;
  if (callExternally) G.__autoCollect(q);
  snap(q, dir || 'none');
}

fs.mkdirSync(require('path').dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, lines.join('\n') + '\n');
console.log(`[${POS}] wrote ${lines.length} turns -> ${OUT}  (final turn ${q.turn}, sharedCore ${G.sharedCore(q)}, peak-n ${Math.max(...q.g.filter((t) => t && t.side === 'p' && !t.support).map((t) => t.n))})`);
