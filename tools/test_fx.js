// 动效验证：事件通道、各类特效的产生条件、以及"模拟不产生特效"。
//
//   node tools/test_fx.js
//
// canvas 画出来的东西无头环境看不到，所以这里验的是**事件**：
// 谁在什么条件下产生哪个特效、坐标是否合法、模拟调用会不会冒出幽灵特效。
const fs = require('fs');
const path = require('path');
// 仓库根从脚本位置推导（tools/ 的上一级），不再写死盘符
const ROOT = path.resolve(__dirname, '..');
const vm = require('vm');

let failures = 0;
function check(ok, label, detail) {
  if (!ok) { failures++; console.log(`  失败  ${label}${detail ? '  -- ' + detail : ''}`); }
  else console.log(`  通过  ${label}${detail ? '  -- ' + detail : ''}`);
}

function makeStub() {
  const f = function () {};
  return new Proxy(f, { get(t, k) {
    if (k === 'then') return undefined;
    if (k === Symbol.toPrimitive) return () => '';
    if (k === Symbol.iterator) return function* () {};
    if (k === 'toString' || k === 'valueOf') return () => '';
    if (k === 'length') return 0;
    if (!(k in t)) t[k] = makeStub();
    return t[k];
  }, set() { return true; }, apply() { return makeStub(); }, construct() { return makeStub(); } });
}
global.document = makeStub();
global.window = makeStub();
global.requestAnimationFrame = () => 0;
const store = new Map();
global.localStorage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };

const ENGINE = fs.readFileSync(path.join(ROOT, 'build', 'engine.js'), 'utf8');

// 源码层断言助手：忽略**所有空白**再比对。
// 原因：断言检查的是实现约束（如"进度条 22×4"），而 prettier 会加空格，
// 用裸 includes 会因排版差异误报。归一化后断言表达的是"语义在场"，与排版无关。
const _sq = (v) => String(v).replace(/\s+/g, '');
function has(src, pat) {
  const found = _sq(src).includes(_sq(pat));
  if (!found) console.log('        [has] 未找到（归一化后）: ' + pat);
  return found;
}
function notHas(src, pat) {
  const found = _sq(src).includes(_sq(pat));
  if (found) console.log('        [notHas] 不该存在但找到了（归一化后）: ' + pat);
  return !found;
}
// 需要时用：prettier 除了加空白，还会给箭头函数参数与返回表达式**补括号**
// （`f=>x` -> `(f) => (x)`、`a||b` -> `(a || b)`）。
// 括号是结构变化，空白归一化处理不了。
//
// 实现要点：**剥括号必须按深度匹配，不能靠正则** ——
// `(DUR[f.kind || 'shot'] || 450)` 里的内层 `||` 会被 `\(([^()]*\|\|[^()]*)\)`
// 这类正则误抓。所以手写扫描器：跳过字符串、按深度找匹配右括号、
// 只在最外层剥离、递归下降。字符串内的括号（如 `'k===\'x\''`）也不能当作结构括号。
function stripParens(s) {
  const n = s.length;
  const matchClose = (openIdx) => {
    let d = 1;
    for (let k = openIdx + 1; k < n; k++) {
      const c = s[k];
      if (c === "'" || c === '"' || c === '`') {
        k++;
        while (k < n) {
          if (s[k] === '\\') { k += 2; continue; }
          if (s[k] === c) break;
          k++;
        }
        continue;
      }
      if (c === '(') d++;
      else if (c === ')') { d--; if (d === 0) return k; }
    }
    return -1;
  };
  let i = 0;
  while (i < n) {
    const c = s[i];
    if (c === "'" || c === '"' || c === '`') {
      i++;
      while (i < n) {
        if (s[i] === '\\') { i += 2; continue; }
        if (s[i] === c) { i++; break; }
        i++;
      }
      continue;
    }
    if (c === '(') {
      const j = matchClose(i);
      if (j > i) {
        const raw = s.slice(i + 1, j);
        // 只在括号内容**明显冗余**时才剥（保守白名单）。
        // 反例：`f('(a)')` 的括号是函数调用的，绝不能剥成 `f'(a)'`（自测发现的）。
        const safe = raw !== '' &&
          !raw.includes(',') && !raw.includes(';') && raw !== ')' &&
          !(raw[0] === "'" || raw[0] === '"' || raw[0] === '`');
        if (safe) {
          const inner = stripParens(raw);
          s = s.slice(0, i) + inner + s.slice(j + 1);
          i += inner.length;
          continue;
        }
      }
    }
    i++;
  }
  return s;
}
function hasLoose(src, pat) {
  // 两件事都要做：先剥掉 prettier 补的括号，再抹平空白差异。
  // 少了任何一步都会漏 —— 实测漏掉 _sq 时会因源文本里的空格而匹配失败。
  const found = _sq(stripParens(src)).includes(_sq(stripParens(pat)));
  if (!found) console.log('        [hasLoose] 未找到: ' + pat);
  return found;
}

vm.runInThisContext(ENGINE);
const G = globalThis.__CF__;
const P = (r, c) => r * 100 + c;
const CAP = (n) => 3 ** G.lvl(n) * G.lvl(8);

function mkState(tiles) {
  const q = G.initial(12345);
  q.g = Array(10000).fill(null);
  Object.assign(q, { dead: false, settled: false, primaryLost: false, playerCore: 8, primary: 1,
                     active: 1, serial: 5000, score: 0, kills: 0, logs: [], turn: 0, combat: null });
  const add = (t) => {
    const cap = CAP(t.n);
    q.g[t.i] = { id: t.id ?? q.serial++, n: t.n, side: t.side, core: !!t.core,
                 team: t.team ?? 1, hp: t.hp ?? cap, cap, kind: t.kind, payload: t.payload };
    return q.g[t.i];
  };
  add({ i: P(40, 40), n: 8, side: 'p', core: true, id: 1, team: 1 });
  for (const t of tiles) add(t);
  return q;
}
const kinds = (fx) => fx.map((f) => f.kind || 'shot');

// =====================================================================
console.log('\n=== A. 可选参数向后兼容（无头测试的旧调用方式不受影响）===');
{
  const q = mkState([{ i: P(50, 50), n: 4, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);
  let threw = null, grown = null;
  try { grown = G.autoCollect(q); } catch (e) { threw = e; }
  check(!threw, 'autoCollect(q) 不传 fx 仍可调用', threw ? threw.message : '');
  check(typeof grown === 'number', '返回值仍是数字（升级次数）', `返回=${grown}`);
}

console.log('\n=== B. 吸收特效：数量等于被吃掉的中立数 ===');
{
  const q = mkState([
    { i: P(50, 50), n: 2, side: 'p' },
    { i: P(49, 50), n: 2, side: 'n' }, { i: P(51, 50), n: 2, side: 'n' },
    { i: P(50, 49), n: 2, side: 'n' }, { i: P(50, 51), n: 2, side: 'n' },
  ]);
  const before = q.g.filter((t) => t && t.side === 'n').length;
  const fx = [];
  G.autoCollect(q, fx);
  const after = q.g.filter((t) => t && t.side === 'n').length;
  const abs = fx.filter((f) => f.kind === 'absorb');
  check(abs.length === before - after, '每个被吃掉的中立都有一个吸收特效',
        `特效=${abs.length} 中立减少=${before - after}`);
  check(abs.every((f) => f.from >= 0 && f.from < 10000 && f.at === undefined && f.to >= 0 && f.to < 10000),
        '吸收特效的坐标合法');
}

console.log('\n=== C. 升级脉冲：数量等于实际升级次数 ===');
{
  const q = mkState([{ i: P(50, 50), n: 2, side: 'p', payload: 6 }]);
  const fx = [];
  const grown = G.settleTiles(q, G.lvl(G.sharedCore(q)), fx);
  check(fx.filter((f) => f.kind === 'pulse').length === grown, '每次升级一个脉冲',
        `脉冲=${fx.filter((f) => f.kind === 'pulse').length} 升级=${grown}`);
}

console.log('\n=== D. 恢复特效：只在回满血那一刻 ===');
{
  // 满血的不出；差一点血的出；受伤但没回满的不出
  const q = mkState([
    { i: P(50, 50), n: 8, side: 'p', hp: 10, team: 1 },          // 会回满（5% 上限 81 → 每回合 5，回不满）
    { i: P(60, 60), n: 8, side: 'p', hp: 79, team: 77 },          // 差 2，会回满
  ]);
  q.g[P(60, 60)].core = true;
  q.turn = 100; q.combat = { 1: 0, 77: 0 };
  const fx = [];
  G.regenTiles(q, fx);
  const reg = fx.filter((f) => f.kind === 'regen');
  check(reg.length === 1, '只有"这一回合回满血"的方块出特效', `特效=${reg.length}`);
  check(reg[0] && reg[0].at === P(60, 60), '特效落在回满血的那一块上');
  check(!reg.some((f) => f.at === P(50, 50)), '只是回了点血、还没满的不出特效');
}

console.log('\n=== E. 摧毁与受击 ===');
{
  const q = mkState([{ i: P(50, 51), n: 4, side: 'e' }]);
  const fx = [];
  G.kill(q, P(50, 51), fx);
  check(fx.filter((f) => f.kind === 'kill').length === 1, '摧毁产生一个特效');
  check(q.g[P(50, 51)] === null, '方块确实被移除');

  const q2 = mkState([
    { i: P(50, 50), n: 8, side: 'p', core: true, id: 1, team: 1 },
    { i: P(50, 51), n: 4, side: 'e', core: true, id: 9, team: 9 },
  ]);
  const fx2 = [];
  G.contact(q2, P(50, 50), P(50, 51), fx2);
  const hits = fx2.filter((f) => f.kind === 'hit');
  check(hits.length === 2, '对碰双方各出一个受击特效', `受击=${hits.length}`);
  check(hits.every((f) => typeof f.dmg === 'number' && f.dmg > 0), '受击特效带掉血数字',
        hits.map((f) => f.dmg).join('/'));
}

console.log('\n=== F. 通道是"可选传入"：模拟调用不产生特效 ===');
{
  check(has(ENGINE, "if(fx){fx.push({kind:'hit'"), '受击事件被 if(fx) 守卫');
  check(has(ENGINE, "if(fx)fx.push({kind:'kill'"), '摧毁事件被 if(fx) 守卫');
  check(has(ENGINE, "if(fx)fx.push({kind:'absorb'"), '吸收事件被 if(fx) 守卫');
  check(notHas(ENGINE, 'fxBuf') && notHas(ENGINE, 'simDepth'),
        '没有引入全局缓冲或"是否在模拟"的标志位');

  // 同一场对碰：传 fx 有事件，不传就没有可观察的事件通道
  // 注意：mkState 默认已在 (40,40) 放了 id=1 的核心，这里围绕它摆，
  // 否则会造出第二个 id=1 的核心、受控核心就跑到别处去了。
  const mkClash = () => mkState([
    { i: P(40, 41), n: 4, side: 'p', id: 2, team: 1 },          // 与核心相连
    { i: P(40, 42), n: 2, side: 'e', core: true, id: 9, team: 9 },
  ]);
  const real = mkClash(); const realFx = [];
  const r1 = G.moveMain(real, 'right', real.active, realFx);
  const sim = mkClash();
  const r2 = G.moveMain(sim, 'right', sim.active);            // 模拟：不传 fx
  check(!!r1 && !!r2, '真实移动与模拟移动都成功');
  check(realFx.length > 0, '真实移动产生了特效', kinds(realFx).join(','));
  const realHits = realFx.filter((f) => f.kind === 'hit').length;
  check(realHits > 0, '真实对碰产生受击特效', `受击=${realHits}`);
  check(JSON.stringify(real.g.map((t) => t && t.id)) === JSON.stringify(sim.g.map((t) => t && t.id)),
        '模拟与真实得到相同的棋盘结果（模拟本身没被特效影响）');
}

console.log('\n=== G. 整局：事件种类合法、坐标合法 ===');
{
  const q = G.initial(20261017);
  const DIRS = ['up', 'down', 'left', 'right'];
  const all = [];
  let turns = 0;
  for (let i = 0; i < 60 && !q.dead && !q.settled; i++) {
    for (const d of DIRS) {
      const draft = G.copy(q);
      if (G.moveMain(draft, d)) { const r = G.worldStep(q, d); if (r && r.fx) all.push(...r.fx); turns++; break; }
    }
  }
  const set = new Set(kinds(all));
  const legal = ['shot', 'absorb', 'pulse', 'hit', 'kill', 'regen'];
  check([...set].every((k) => legal.includes(k)), '种类都在预期内', [...set].join(','));
  const bad = all.filter((f) => (f.at !== undefined && (f.at < 0 || f.at > 9999)) ||
                                 (f.from !== undefined && (f.from < 0 || f.from > 9999)) ||
                                 (f.to !== undefined && (f.to < 0 || f.to > 9999)));
  check(bad.length === 0, '所有事件坐标合法', `越界=${bad.length}`);
  check(all.length > 0, `跑了 ${turns} 回合，累计事件数非零`, `事件=${all.length}`);
  const tally = {};
  for (const k of kinds(all)) tally[k] = (tally[k] || 0) + 1;
  console.log('  info  事件分布：' + JSON.stringify(tally));
}

console.log('\n=== H. 渲染与时长表 ===');
{
  let threw = null;
  try { G.draw(); } catch (e) { threw = e; }
  check(!threw, 'draw() 不抛错', threw ? threw.message : '');
  check(has(ENGINE, 'DUR={shot:450,absorb:420,pulse:480,hit:600,kill:520,regen:640}'),
        '六类特效各有自己的时长');
  for (const k of ['absorb', 'pulse', 'regen', 'hit', 'kill']) {
    check(has(ENGINE, `k==='${k}'`), `渲染分支在场：${k}`);
  }
  check(hasLoose(ENGINE, "effects=effects.filter(f=>now-f.start<(DUR[f.kind||'shot']||450))"),
        '过期特效按各自时长清理（没有另起动画循环）');
}

console.log(`\n${failures} 项失败`);
process.exit(failures ? 1 : 0);
