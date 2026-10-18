// Step 4 (engine) functional checks: tech points and the TP / radius lines.
//
//   node tools/test_step4.js
const fs = require('fs');
const path = require('path');
// 仓库根从脚本位置推导（tools/ 的上一级），不再写死盘符
const ROOT = path.resolve(__dirname, '..');
const { DELIVERABLE } = require('./_root.js');
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
for (const fn of ['survey', 'convertScore', 'buyTech', 'absorbTp', 'siteRadius', 'techCost']) {
  check(typeof G[fn] === 'function', `${fn} exported`);
}

const P = (r, c) => r * 100 + c;
const CAP = (n) => 3 ** G.lvl(n) * G.lvl(8);

function mkState(tiles) {
  const q = G.initial(12345);
  q.g = Array(10000).fill(null);
  Object.assign(q, { dead: false, settled: false, primaryLost: false, playerCore: 8, primary: 1, active: 1, serial: 5000, score: 0, kills: 0, logs: [], turn: 0 });
  const add = (t) => {
    const cap = CAP(t.n);
    q.g[t.i] = { id: t.id ?? q.serial++, n: t.n, side: t.side, core: !!t.core, team: t.team ?? 1, hp: t.hp ?? cap, cap, kind: t.kind };
    return q.g[t.i];
  };
  add({ i: P(40, 40), n: 8, side: 'p', core: true, id: 1, team: 1 });
  for (const t of tiles) add(t);
  return q;
}

// ---------------------------------------------------------------------------
console.log('\n=== A. fresh state carries the tech fields ===');
{
  const q = G.initial(20261017);
  check(q.tech === 0 && q.upTp === 0 && q.upRadius === 0,
        'tech / upTp / upRadius start at 0', `tech=${q.tech} tp=${q.upTp} r=${q.upRadius}`);
  check(G.absorbTp(q) === 2 && G.siteRadius(q) === 1,
        'baselines: TP 2, radius 1', `tp=${G.absorbTp(q)} r=${G.siteRadius(q)}`);
}

// ---------------------------------------------------------------------------
console.log('\n=== B. score converts to points, and it COSTS score ===');
{
  const q = mkState([]);
  q.score = 250;
  const got = G.convertScore(q);
  check(got === 2, 'floor(250/100) = 2 points', `got=${got}`);
  check(q.score === 50, 'score was deducted (tradeoff is real)', `score=${q.score}`);
  check(q.tech === 2, 'points landed', `tech=${q.tech}`);
  check(G.convertScore(q) === 0, 'no conversion below one unit of score', `score=${q.score}`);
  check(q.score === 50, 'a failed conversion changes nothing', `score=${q.score}`);
}

// ---------------------------------------------------------------------------
console.log('\n=== C. only MEANINGFUL kills pay: enemy cores and bunkers ===');
{
  // an ordinary enemy member: still counted as a kill, but pays nothing
  const plain = mkState([{ i: P(50, 51), n: 4, side: 'e' }]);
  G.kill(plain, P(50, 51));
  check(plain.kills === 1, 'member kill still counted as a kill', `kills=${plain.kills}`);
  check(plain.tech === 0, 'member kill pays NO tech point', `tech=${plain.tech}`);

  // an enemy core (squad leader / fighter / collector)
  const core = mkState([{ i: P(50, 51), n: 8, side: 'e', core: true, id: 77, team: 77 }]);
  G.kill(core, P(50, 51));
  check(core.kills === 1 && core.tech === 1, 'core kill -> +1 tech point',
        `kills=${core.kills} tech=${core.tech}`);

  // a bunker: kind lives on its core tile
  const bunk = mkState([{ i: P(50, 51), n: 8, side: 'e', core: true, id: 88, team: 88, kind: 'bunker' }]);
  G.kill(bunk, P(50, 51));
  check(bunk.kills === 1 && bunk.tech === 1, 'bunker kill -> +1 tech point',
        `kills=${bunk.kills} tech=${bunk.tech}`);
}

// ---------------------------------------------------------------------------
console.log('\n=== D. exploration pays once per 10x10 block ===');
{
  const q = mkState([{ i: P(50, 50), n: 4, side: 'p' }]);
  const first = G.survey(q);
  const second = G.survey(q);
  check(first > 0, 'first survey finds new blocks', `found=${first}`);
  check(second === 0, 're-surveying the same place pays nothing', `found=${second}`);
  check(q.tech === first, 'points equal newly found blocks', `tech=${q.tech}`);
  // walk far away -> new block -> pays again
  q.g[P(50, 50)] = null;
  q.g[P(90, 90)] = { id: 9001, n: 4, side: 'p', core: false, team: 1, hp: CAP(4), cap: CAP(4) };
  const third = G.survey(q);
  check(third > 0, 'entering a far block pays again', `found=${third}`);
}

// ---------------------------------------------------------------------------
console.log('\n=== E. the tree: cost, gating, and effect ===');
{
  const q = mkState([]);
  q.tech = 0;
  const poor = G.buyTech(q, 'tp');
  check(!!poor.error, 'cannot buy with 0 points', poor.error);
  check(G.techCost('tp', 0) === 8, 'level 1 costs 8', `cost=${G.techCost('tp', 0)}`);

  q.tech = 8;
  const one = G.buyTech(q, 'tp');
  check(!one.error && one.level === 1, 'bought TP level 1', JSON.stringify(one));
  check(q.tech === 0, 'points were spent', `tech=${q.tech}`);
  check(G.absorbTp(q) === 3, 'TP line now feeds autoCollect (2 + 1)', `tp=${G.absorbTp(q)}`);

  q.tech = 99;
  G.buyTech(q, 'tp');
  const over = G.buyTech(q, 'tp');
  check(!!over.error, 'TP line is capped', over.error);
  check(G.absorbTp(q) === 4, 'TP topped out at 2 + 2', `tp=${G.absorbTp(q)}`);

  G.buyTech(q, 'radius');
  check(G.siteRadius(q) === 2, 'radius line feeds the site ring (1 + 1)', `r=${G.siteRadius(q)}`);
}

// ---------------------------------------------------------------------------
console.log('\n=== F. the TP line really absorbs more per turn ===');
{
  const mk = () => mkState([
    { i: P(50, 50), n: 2, side: 'p' },
    { i: P(49, 50), n: 2, side: 'n' },
    { i: P(51, 50), n: 2, side: 'n' },
    { i: P(50, 49), n: 2, side: 'n' },
    { i: P(50, 51), n: 2, side: 'n' },
  ]);
  const base = mk();
  G.autoCollect(base);
  const baseLeft = base.g.filter((t) => t && t.side === 'n').length;

  const up = mk();
  up.upTp = 2;
  G.autoCollect(up);
  const upLeft = up.g.filter((t) => t && t.side === 'n').length;

  check(baseLeft === 2, 'base TP=2 absorbs exactly 2 of the 4 neighbours', `left=${baseLeft}`);
  check(upLeft === 0, 'TP=4 absorbs all 4', `left=${upLeft}`);
}

// ---------------------------------------------------------------------------
console.log('\n=== G. the radius line really extends reach ===');
{
  // core at (40,40) is the ring provider; receiver 4 at (40,41); neutral at (38,38)
  // is Chebyshev distance 2 from the core -- reachable only at radius 2, and not
  // 4-adjacent to any friendly tile.
  const mk = () => mkState([
    { i: P(40, 41), n: 4, side: 'p' },
    { i: P(38, 38), n: 4, side: 'n' },
  ]);
  const r1 = mk();
  G.autoCollect(r1);
  check(r1.g[P(38, 38)] !== null, 'radius 1 does NOT reach a distance-2 neutral');

  const r2 = mk();
  r2.upRadius = 1;
  G.autoCollect(r2);
  check(r2.g[P(38, 38)] === null, 'radius 2 DOES reach it');
  check(r2.g[P(40, 41)].n === 8, 'and it fed the nearest under-cap friendly tile',
        `n=${r2.g[P(40, 41)].n}`);
}

// ---------------------------------------------------------------------------
console.log('\n=== H. invariants over a full game ===');
{
  const q = G.initial(20261017);
  const DIRS = ['up', 'down', 'left', 'right'];
  let turns = 0, threw = null;
  try {
    for (let i = 0; i < 80 && !q.dead && !q.settled; i++) {
      for (const d of DIRS) {
        const draft = G.copy(q);
        if (G.moveMain(draft, d)) { G.worldStep(q, d); turns++; break; }
      }
    }
  } catch (e) { threw = e; }
  check(!threw, '80 turns ran without throwing', threw ? threw.message : `turns=${turns}`);
  check(G.valid(q), 'state passes valid()');
  check(q.tech > 0, 'exploration/kills earned tech points while playing', `tech=${q.tech}`);
  const blocks = q.visited ? Object.keys(q.visited).length : 0;
  check(blocks > 0, 'explored blocks were recorded', `blocks=${blocks}`);
  const badN = q.g.filter((t) => t && !Number.isInteger(Math.log2(t.n)));
  check(badN.length === 0, 'every tile value is still a power of two', `bad=${badN.length}`);
  console.log(`  info  after ${turns} turns: tech=${q.tech}, kills=${q.kills}, blocks=${blocks}, score=${q.score}`);
}

// ---------------------------------------------------------------------------
console.log('\n=== I. the tech panel is wired into the deliverable and is safe ===');
{
  const html = fs.readFileSync(path.join(ROOT, DELIVERABLE), 'utf8');
  for (const id of ['tech', 'techTree', 'convertScore']) {
    const n = (html.match(new RegExp('id="' + id + '"', 'g')) || []).length;
    check(n === 1, `deliverable has #${id} exactly once`, `count=${n}`);
  }
  for (const fn of ['techUI', 'techBuy', 'techConvert']) {
    check(typeof G[fn] === 'function', `${fn} exported`);
  }
  // headless: every element is a stub, so these must simply not throw
  let threw = null;
  try { G.techUI(); } catch (e) { threw = e; }
  check(!threw, 'techUI() renders without throwing (stubbed DOM)', threw ? threw.message : '');
  threw = null;
  try { G.techBuy('tp'); } catch (e) { threw = e; }
  check(!threw, 'techBuy() without points fails softly', threw ? threw.message : '');
  threw = null;
  try { G.techConvert(); } catch (e) { threw = e; }
  check(!threw, 'techConvert() without score fails softly', threw ? threw.message : '');
}

// ---------------------------------------------------------------------------
console.log('\n=== J. the radius line buys throughput as well as reach (bug fix) ===');
{
  // Mirrors tools/report_radius_throughput.js: 15 neutrals parked at Chebyshev
  // distance 2 from the only site, unreachable by tile adjacency. Before the fix
  // the site pulled a fixed SITE_TP=4 no matter how wide the ring got.
  const core = P(40, 40), receiver = P(40, 41);
  const ring2 = [];
  for (let dr = -2; dr <= 2; dr++) {
    for (let dc = -2; dc <= 2; dc++) {
      if (Math.max(Math.abs(dr), Math.abs(dc)) !== 2) continue;
      const i = P(40 + dr, 40 + dc);
      if (i === receiver || i === core) continue;
      if (Math.abs(dr) + Math.abs(dc - 1) === 1) continue;   // not 4-adjacent to the receiver
      ring2.push(i);
    }
  }
  const count = (up) => {
    const q = mkState([{ i: receiver, n: 2, side: 'p' }]);
    for (const i of ring2) {
      q.g[i] = { id: q.serial++, n: 2, side: 'n', core: false, team: null, hp: CAP(2), cap: CAP(2) };
    }
    q.upRadius = up;
    const before = q.g.filter((t) => t && t.side === 'n').length;
    G.autoCollect(q);
    return before - q.g.filter((t) => t && t.side === 'n').length;
  };
  const at1 = count(0), at2 = count(1);
  check(at1 === 0, 'radius 1 cannot reach the distance-2 ring at all', `absorbed=${at1}`);
  check(at2 > 4, 'radius 2 absorbs MORE than the old fixed SITE_TP=4', `absorbed=${at2} (was 4)`);
  check(G.siteBudgetAt(0) === 4 && G.siteBudgetAt(1) === 8,
        'site budget scales with the radius line', `${G.siteBudgetAt(0)} -> ${G.siteBudgetAt(1)}`);
}

console.log(`\n${failures} FAILURE(S)`);
process.exit(failures ? 1 : 0);
