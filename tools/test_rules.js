// 规则功能验收：吸收阈值 · 受伤可升级 · 回血 · 敌方天花板。
//
//   node tools/test_rules.js
//
// 这些是你锁定的规格，逐条断言。
const fs = require('fs');
const vm = require('vm');

let failures = 0;
function check(ok, label, detail) {
  if (!ok) { failures++; console.log(`  失败  ${label}${detail ? '  -- ' + detail : ''}`); }
  else console.log(`  通过  ${label}${detail ? '  -- ' + detail : ''}`);
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

vm.runInThisContext(fs.readFileSync('D:\\2048\\build\\engine.js', 'utf8'));
const G = globalThis.__CF__;
const P = (r, c) => r * 100 + c;
const CAP = (n) => 3 ** G.lvl(n) * G.lvl(8);

function mkState(tiles) {
  const q = G.initial(12345);
  q.g = Array(10000).fill(null);
  Object.assign(q, { dead: false, settled: false, primaryLost: false, playerCore: 8, primary: 1, active: 1, serial: 5000, score: 0, kills: 0, logs: [], turn: 0, combat: null });
  const add = (t) => {
    const cap = CAP(t.n);
    q.g[t.i] = { id: t.id ?? q.serial++, n: t.n, side: t.side, core: !!t.core, team: t.team ?? 1, hp: t.hp ?? cap, cap, kind: t.kind, payload: t.payload };
    return q.g[t.i];
  };
  add({ i: P(40, 40), n: 8, side: 'p', core: true, id: 1, team: 1 });
  for (const t of tiles) add(t);
  return q;
}
const lvCore = (q) => G.lvl(G.sharedCore(q));
const combat = (q, team, turn) => { q.combat = q.combat || {}; q.combat[team] = turn; };

// =====================================================================
console.log('\n=== A. 准入放宽：数字等于阈值也能吸收 ===');
{
  const q = mkState([{ i: P(50, 50), n: 4, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);
  G.autoCollect(q);
  check(q.g[P(50, 51)] === null, '阈值为 4 时，n=4 的方块（正好等于阈值）把中立吸走了');
}

// =====================================================================
console.log('\n=== B. 进度继承：升级后仍不超过阈值，多出的进度保留 ===');
{
  // 阈值 4 时，继承只可能发生在 2 -> 4 这一步
  const q = mkState([{ i: P(50, 50), n: 2, side: 'p', payload: 3 }]);
  G.settleTiles(q, lvCore(q));
  const t = q.g[P(50, 50)];
  check(t.n === 4, '2 升到 4', `n=${t.n}`);
  check(t.payload === 1, '多出的 1 点进度被继承（3-2=1）', `进度=${t.payload}`);
}

// =====================================================================
console.log('\n=== C. 超过阈值则进度清零 ===');
{
  const q = mkState([{ i: P(50, 50), n: 4, side: 'p', payload: 4 }]);
  G.settleTiles(q, lvCore(q));
  const t = q.g[P(50, 50)];
  check(t.n === 8, '4 升到 8（越过阈值 4）', `n=${t.n}`);
  check(t.payload === 0, '进度清零', `进度=${t.payload}`);
}

// =====================================================================
console.log('\n=== D. 不变量：数字超过阈值的方块，进度必为 0 ===');
{
  // 手动合并出来的 16（超过阈值）被塞了一段进度
  const q = mkState([{ i: P(50, 50), n: 16, side: 'p', payload: 5 }]);
  G.settleTiles(q, lvCore(q));
  check(q.g[P(50, 50)].payload === 0, '超过阈值的方块进度被强制清零', `进度=${q.g[P(50, 50)].payload}`);
  const q2 = mkState([{ i: P(50, 50), n: 8, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);
  G.autoCollect(q2);
  check(q2.g[P(50, 51)] !== null, '超过阈值的方块（8 大于阈值 4）不再吸收', '中立仍在');
}

// =====================================================================
console.log('\n=== E. 阈值曲线：8 / 16 / 32，自动可达两倍 ===');
{
  check(G.absorbThresholdAt(0) === 4, '0 级阈值 4（基础）', `${G.absorbThresholdAt(0)}`);
  check(G.absorbThresholdAt(1) === 8, '1 级阈值 8', `${G.absorbThresholdAt(1)}`);
  check(G.absorbThresholdAt(2) === 16, '2 级阈值 16', `${G.absorbThresholdAt(2)}`);
  check(G.absorbThresholdAt(3) === 32, '3 级阈值 32（上限）', `${G.absorbThresholdAt(3)}`);
  // 阈值升到 16 时，n=16 本身也能吸收
  const q = mkState([{ i: P(50, 50), n: 16, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);
  q.upThreshold = 2;
  G.autoCollect(q);
  check(q.g[P(50, 51)] === null, '阈值 16 时，n=16 的方块可以吸收');
}

// =====================================================================
console.log('\n=== F. 乙：受伤也能升级 ===');
{
  const q = mkState([{ i: P(50, 50), n: 4, side: 'p', hp: Math.floor(CAP(4) / 2), payload: 4 }]);
  G.settleTiles(q, lvCore(q));
  check(q.g[P(50, 50)].n === 8, '半血的 4 依然升级到 8', `n=${q.g[P(50, 50)].n}`);
}

// =====================================================================
console.log('\n=== G. 升级只等比例继承血量，不回满 ===');
{
  const oldCap = CAP(4), newCap = CAP(8);
  const q = mkState([{ i: P(50, 50), n: 4, side: 'p', hp: Math.floor(oldCap / 2), payload: 4 }]);
  G.settleTiles(q, lvCore(q));
  const t = q.g[P(50, 50)];
  const want = Math.max(1, Math.min(newCap, Math.round(Math.floor(oldCap / 2) * newCap / oldCap)));
  check(t.hp < t.cap, '没有回满血', `血量 ${t.hp}/${t.cap}`);
  check(t.hp === want, '按比例继承', `实际 ${t.hp}，预期 ${want}`);
}

// =====================================================================
console.log('\n=== H. 回血：门槛 10 回合，未满不回 ===');
{
  const q = mkState([{ i: P(50, 50), n: 8, side: 'p', hp: 10 }]);
  q.turn = 100; combat(q, 1, 100);
  G.regenTiles(q);
  check(q.g[P(50, 50)].hp === 10, '刚受伤（差 0 回合）不回血', `血量=${q.g[P(50, 50)].hp}`);
  q.turn = 109; G.regenTiles(q);
  check(q.g[P(50, 50)].hp === 10, '脱离战斗 9 回合仍不回', `血量=${q.g[P(50, 50)].hp}`);
}

// =====================================================================
console.log('\n=== I. 回血：满 10 回合后每回合回上限的 5% ===');
{
  const q = mkState([{ i: P(50, 50), n: 8, side: 'p', hp: 10 }]);
  const cap = q.g[P(50, 50)].cap;
  const want = Math.max(1, Math.ceil(cap * 0.05));
  q.turn = 110; combat(q, 1, 100);
  G.regenTiles(q);
  check(q.g[P(50, 50)].hp === 10 + want, `回血 ${want}（上限 ${cap} 的 5%）`, `血量=${q.g[P(50, 50)].hp}`);
  // 满血后不再溢出
  q.g[P(50, 50)].hp = cap;
  G.regenTiles(q);
  check(q.g[P(50, 50)].hp === cap, '满血不溢出', `血量=${q.g[P(50, 50)].hp}`);
}

// =====================================================================
console.log('\n=== J. 每个核心独立计数 ===');
{
  const q = mkState([
    { i: P(50, 50), n: 8, side: 'p', hp: 10, team: 1 },        // 本队刚刚受伤
    { i: P(60, 60), n: 8, side: 'p', hp: 10, team: 77 },       // 另一队长期无战斗
  ]);
  q.g[P(60, 60)].core = true;
  q.turn = 110;
  combat(q, 1, 110);              // 1 队刚受伤
  combat(q, 77, 0);               // 77 队早就脱离了
  G.regenTiles(q);
  check(q.g[P(50, 50)].hp === 10, '刚受伤的那支队伍不回血', `血量=${q.g[P(50, 50)].hp}`);
  check(q.g[P(60, 60)].hp > 10, '已脱离战斗的那支队伍在回血', `血量=${q.g[P(60, 60)].hp}`);
}

// =====================================================================
console.log('\n=== K. 敌方回血默认关闭（参数为 0） ===');
{
  const q = mkState([{ i: P(50, 51), n: 8, side: 'e', hp: 10 }]);
  q.turn = 999;
  combat(q, 1, 0);
  G.regenTiles(q);
  check(q.g[P(50, 51)].hp === 10, '敌方不回血', `血量=${q.g[P(50, 51)].hp}`);
}

// =====================================================================
console.log('\n=== L. 受伤会重置计数 ===');
{
  const q = mkState([{ i: P(50, 50), n: 8, side: 'p', hp: 10 }]);
  q.turn = 500;
  combat(q, 1, 0);                // 看似早就脱离
  G.markCombat(q, q.g[P(50, 50)]); // 但这一回合又挨打了
  G.regenTiles(q);
  check(q.g[P(50, 50)].hp === 10, '挨打当回合不回血', `血量=${q.g[P(50, 50)].hp}`);
}

// =====================================================================
console.log('\n=== M. 敌方采集机天花板与玩家同形态（可达两倍） ===');
{
  check(G.aiAbsorbCeiling({}) === 4, '敌方天花板默认跟随基础值 4', `${G.aiAbsorbCeiling({})}`);
  // 采集机 4 级、半血、进度堆到很大，旁边放一个中立让它真的走进升级循环
  const q = mkState([
    { i: P(50, 51), n: 4, side: 'e', core: true, id: 9, team: 9, kind: 'collector', hp: 10 },
    { i: P(50, 52), n: 2, side: 'n' },
  ]);
  const c = q.g[P(50, 51)];
  c.payload = 100;
  const consumed = G.collect(q, 9);
  check(consumed === true, '采集机真的执行了吸收（走到了升级路径）', `返回=${consumed}`);
  check(q.g[P(50, 52)] === null, '相邻中立被吃掉');
  check(c.n === 8, '停在天花板的两倍（8），不再更高', `n=${c.n}`);
  check(c.payload === 0, '越过天花板后进度清零', `进度=${c.payload}`);
  check(c.hp < c.cap, '升级没有回满血（等比例继承）', `血量 ${c.hp}/${c.cap}`);
}

// =====================================================================
console.log('\n=== N. 整局不变量 ===');
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
  check(!threw, '80 回合无异常', threw ? threw.message : `回合=${turns}`);
  check(G.valid(q), 'valid() 通过');
  const th = G.absorbThreshold(q);
  const bad = q.g.filter((t) => t && t.side === 'p' && !t.support && t.n > th && (t.payload || 0) > 0);
  check(bad.length === 0, '不存在"超过阈值却留着进度"的方块', `违例=${bad.length}`);
  const badN = q.g.filter((t) => t && !Number.isInteger(Math.log2(t.n)));
  check(badN.length === 0, '所有数字仍是 2 的幂', `违例=${badN.length}`);
  const overHeal = q.g.filter((t) => t && t.hp > t.cap);
  check(overHeal.length === 0, '没有方块血量超过上限', `违例=${overHeal.length}`);
  const negProgress = q.g.filter((t) => t && (t.payload || 0) < 0);
  check(negProgress.length === 0, '没有方块进度为负', `违例=${negProgress.length}`);
}

console.log(`\n${failures} 项失败`);
process.exit(failures ? 1 : 0);
