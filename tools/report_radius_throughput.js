// Diagnostic: does the RADIUS upgrade actually buy throughput, or does SITE_TP
// strangle it?
//
//   node tools/report_radius_throughput.js
//
// autoCollect's site loop is bounded by a fixed `let budget=SITE_TP;` (SITE_TP=4)
// that does NOT scale with the radius. So a radius upgrade should widen the ring
// without letting the site pull more per turn. Setup: one core as the only site,
// one under-cap receiver, and a batch of neutrals parked at Chebyshev distance 2
// -- reachable ONLY at radius 2, and not 4-adjacent to any friendly tile, so the
// per-tile path cannot touch them.
const fs = require('fs');
const path = require('path');
// 仓库根从脚本位置推导（tools/ 的上一级），不再写死盘符
const ROOT = path.resolve(__dirname, '..');
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
global.localStorage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };
vm.runInThisContext(fs.readFileSync(path.join(ROOT, 'build', 'engine.js'), 'utf8'));
const G = globalThis.__CF__;

const P = (r, c) => r * 100 + c;
const CAP = (n) => 3 ** G.lvl(n) * G.lvl(8);
const core = P(40, 40);
const receiver = P(40, 41);

// outer ring of the 5x5 square centred on the core => Chebyshev distance exactly 2
const ring2 = [];
for (let dr = -2; dr <= 2; dr++) {
  for (let dc = -2; dc <= 2; dc++) {
    if (Math.max(Math.abs(dr), Math.abs(dc)) !== 2) continue;
    const i = P(40 + dr, 40 + dc);
    // skip cells 4-adjacent to the receiver or the core
    if (i === receiver || i === core) continue;
    if (Math.abs(40 + dr - 40) + Math.abs(40 + dc - 41) === 1) continue;
    ring2.push(i);
  }
}

function mk(upRadius) {
  const q = G.initial(12345);
  q.g = Array(10000).fill(null);
  Object.assign(q, { dead: false, settled: false, primaryLost: false, playerCore: 8, primary: 1, active: 1, serial: 5000, score: 0, kills: 0, logs: [], turn: 0 });
  const put = (i, n, side, isCore) => {
    const cap = CAP(n);
    q.g[i] = { id: q.serial++, n, side, core: !!isCore, team: 1, hp: cap, cap };
  };
  put(core, 8, 'p', true);
  put(receiver, 2, 'p', false);            // stays under the cap for a while
  for (const i of ring2) put(i, 2, 'n', false);
  q.upRadius = upRadius;
  return q;
}

console.log('neutrals parked at Chebyshev distance 2 from the core (unreachable by adjacency): ' + ring2.length);
// 注意：SITE_TP 已不再是固定值 —— siteBudgetAt(lv) = SITE_TP + 4*lv，
// 随半径线成长（修复"半径拓宽了环、站点吞吐却被写死卡住"那次改动）。
console.log('站点每回合吞吐 = SITE_TP + 4×半径等级（不是固定 4）。\n');
console.log('radius | ringReach | absorbed in ONE turn | left');
console.log('-------|-----------|----------------------|-----');
for (const [label, up] of [['1 (base)', 0], ['2 (+1 level)', 1]]) {
  const q = mk(up);
  const before = q.g.filter((t) => t && t.side === 'n').length;
  G.autoCollect(q);
  const after = q.g.filter((t) => t && t.side === 'n').length;
  console.log(
    String(label).padEnd(6) + ' | ' +
    String(G.siteRadius(q)).padEnd(9) + ' | ' +
    String(before - after).padEnd(20) + ' | ' + after
  );
}

console.log('\n期望：半径 2 能吸到的不止基础吞吐量 —— 站点吞吐随半径线一起涨，');
console.log('      所以半径买的是覆盖面，而覆盖率本身也随等级提升。');
