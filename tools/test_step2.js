// Step 2 functional checks for auto-collect. Hand-built scenarios, no playtesting.
//
//   node tools/test_step2.js
//
// Verifies the signed decisions:
//   - adjacency absorption accumulates into payload and upgrades by doubling
//   - n stays a power of two (payload accounting, never real addition)
//   - the cap rule applies to the ABSORBING tile and to the RECEIVER
//   - upgrading preserves hp proportionally (no full heal)
//   - a site's radius reaches neutrals that no tile is 4-adjacent to
const fs = require('fs');
const path = require('path');
// 仓库根从脚本位置推导（tools/ 的上一级），不再写死盘符
const ROOT = path.resolve(__dirname, '..');
const vm = require('vm');

let failures = 0;
function check(ok, label, detail) {
  if (!ok) { failures++; console.log(`  FAIL  ${label}${detail ? '  -- ' + detail : ''}`); }
  else console.log(`  ok    ${label}${detail ? '  -- ' + detail : ''}`);
}

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
global.localStorage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };

vm.runInThisContext(fs.readFileSync(path.join(ROOT, 'build', 'engine.js'), 'utf8'));
const G = globalThis.__CF__;
check(typeof G.autoCollect === 'function', 'autoCollect is exported');

const P = (r, c) => r * 100 + c;
const CAP = (n) => 3 ** G.lvl(n) * G.lvl(8);

// minimal valid-ish state: a primary core plus the given tiles
function mkState(tiles) {
  const q = G.initial(12345);
  q.g = Array(10000).fill(null);
  Object.assign(q, {
    dead: false, settled: false, primaryLost: false, playerCore: 8, primary: 1,
    active: 1, serial: 5000, score: 0, kills: 0, logs: [], turn: 0,
  });
  const add = (t) => {
    const value = t.side === 'p' ? 8 : 8;
    const cap = 3 ** G.lvl(t.n) * G.lvl(value);
    q.g[t.i] = {
      id: t.id ?? q.serial++, n: t.n, side: t.side, core: !!t.core,
      team: t.team ?? (t.core ? t.id ?? 1 : 1),
      hp: t.hp ?? cap, cap,
    };
    return q.g[t.i];
  };
  // primary core first so ids/teams are stable
  add({ i: P(40, 40), n: 8, side: 'p', core: true, id: 1, team: 1 });
  for (const t of tiles) add(t);
  return q;
}

const cap8 = 3 ** 3 * 3; // 3^lvl(8) * lvl(8) = 27 * 3

// ---------------------------------------------------------------------------
console.log('\n=== A. adjacency absorption accumulates and doubles ===');
{
  const q = mkState([{ i: P(50, 50), n: 4, side: 'p' }, { i: P(50, 51), n: 4, side: 'n' }]);
  const before = q.g[P(50, 50)].n;
  const grown = G.autoCollect(q);
  const t = q.g[P(50, 50)];
  check(q.g[P(50, 51)] === null, 'the adjacent neutral was consumed');
  check(t.n === 8, 'the 4 upgraded to 8', `${before} -> ${t.n}`);
  check(grown >= 1, 'upgrade counted', `grown=${grown}`);
  check(G.valid(q), 'state still passes valid()');
}

// ---------------------------------------------------------------------------
console.log('\n=== B. payload accounting: no real addition, always a power of two ===');
{
  const q = mkState([{ i: P(50, 50), n: 2, side: 'p' }, { i: P(50, 51), n: 4, side: 'n' }]);
  G.autoCollect(q);
  const t = q.g[P(50, 50)];
  check(t.n === 4, '2 absorbed a 4 and became 4 (not 6)', `n=${t.n}`);
  check(Number.isInteger(Math.log2(t.n)), 'n is still a power of two', `n=${t.n}`);
  check((t.payload || 0) === 2, 'leftover payload is 2', `payload=${t.payload}`);
  check(G.valid(q), 'state still passes valid()');
}

// ---------------------------------------------------------------------------
console.log('\n=== C. 超过阈值才停：阈值本身仍可吸收 ===');
{
  const at = mkState([{ i: P(50, 50), n: 4, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);
  G.autoCollect(at);
  check(at.g[P(50, 51)] === null, '数字等于阈值（4）的方块可以吸收');

  const over = mkState([{ i: P(50, 50), n: 8, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);
  G.autoCollect(over);
  check(over.g[P(50, 51)] !== null, '数字超过阈值（8）的方块不吸收');
}

// ---------------------------------------------------------------------------
console.log('\n=== D. 站点自身也不越权：超过阈值且无其他受方时，不吸收 ===');
{
  const q = mkState([]);
  const core = q.g[P(40, 40)];
  core.n = 16; core.cap = CAP(16); core.hp = CAP(16);   // 核心已超过阈值
  q.g[P(39, 39)] = { id: 7001, n: 2, side: 'n', core: false, team: null, hp: CAP(2), cap: CAP(2) };
  G.autoCollect(q);
  check(q.g[P(39, 39)] !== null, '核心超过阈值、环内又没有其他己方块时，中立不被吸收');
}

// ---------------------------------------------------------------------------
console.log('\n=== E. site radius reaches a neutral that no tile is 4-adjacent to ===');
{
  // core at (40,40); receiver 4 at (40,41) is in the core's ring; neutral at (39,39)
  // is ALSO in the ring but is only diagonally placed, so no tile is 4-adjacent to it.
  const q = mkState([{ i: P(40, 41), n: 4, side: 'p' }, { i: P(39, 39), n: 4, side: 'n' }]);
  const before = q.g[P(40, 41)].n;
  G.autoCollect(q);
  check(q.g[P(39, 39)] === null, 'radius-only neutral was collected');
  check(q.g[P(40, 41)].n === 8, 'it fed the nearest under-cap friendly tile', `${before} -> ${q.g[P(40, 41)].n}`);
  check(G.valid(q), 'state still passes valid()');
}

// ---------------------------------------------------------------------------
console.log('\n=== F. upgrading stays within the new cap (no over-heal) ===');
{
  // NOTE: since step 3, a tile that is BELOW full hp heals instead of upgrading,
  // so this checks the full-hp growth path only. The hurt path is covered by
  // tools/test_step3.js.
  const q = mkState([{ i: P(50, 50), n: 4, side: 'p' }, { i: P(50, 51), n: 4, side: 'n' }]);
  G.autoCollect(q);
  const after = q.g[P(50, 50)];
  check(after.n === 8, 'a healthy 4 upgraded to 8', `n=${after.n}`);
  check(after.hp === after.cap, 'hp tracks the new cap exactly', `${after.hp}/${after.cap}`);
}

// ---------------------------------------------------------------------------
console.log('\n=== G. full-game smoke: absorption runs inside worldStep ===');
{
  const q = G.initial(20261017);
  const DIRS = ['up', 'down', 'left', 'right'];
  let turns = 0, threw = null;
  try {
    for (let i = 0; i < 60 && !q.dead && !q.settled; i++) {
      for (const d of DIRS) {
        const draft = G.copy(q);
        if (G.moveMain(draft, d)) { G.worldStep(q, d); turns++; break; }
      }
    }
  } catch (e) { threw = e; }
  check(!threw, '60 turns ran without throwing', threw ? threw.message : `turns=${turns}`);
  check(G.valid(q), 'state passes valid()');
  const badN = q.g.filter((t) => t && !Number.isInteger(Math.log2(t.n)));
  check(badN.length === 0, 'every tile value is still a power of two', `bad=${badN.length}`);
  const payloads = q.g.filter((t) => t && t.side === 'p' && (t.payload || 0) > 0).length;
  console.log(`  info  player tiles carrying payload after ${turns} turns: ${payloads}`);
}

console.log(`\n${failures} FAILURE(S)`);
process.exit(failures ? 1 : 0);
