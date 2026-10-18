// Step 2 tutorial checks: lesson 02 teaches auto-collect, and absorption stays
// scoped to that lesson only (it must not disturb the other lessons' boards).
//
//   node tools/test_step2_tutorial.js
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

const html = fs.readFileSync(path.join(ROOT, '2048小游戏-教程七关.html'), 'utf8');
const blobs = [...html.matchAll(/atob\('([A-Za-z0-9+/=]+)'\)/g)].map((m) => m[1]);
const tutorialHtml = Buffer.from(blobs[1], 'base64').toString('utf8');
let ts = tutorialHtml.match(/<script[^>]*>([\s\S]*?)<\/script>/)[1];

const lines = ts.split('\n');
let lastIdx = -1;
lines.forEach((l, i) => { if (l.trim()) lastIdx = i; });
check(lines[lastIdx].trim() === '})();', 'tutorial IIFE closer found');
lines[lastIdx] = 'globalThis.__TUT__={tutorialInitial,tutorialDone,tutorialUI,tutorialHighlights,worldStep,moveMain,autoCollect,valid,copy,dirs};' + lines[lastIdx];
ts = lines.join('\n');

let threw = null;
try { vm.runInThisContext(ts); } catch (e) { threw = e; }
check(!threw, 'tutorial script loads', threw ? threw.message : '');
if (threw) { console.log(`\n${failures} FAILURE(S)`); process.exit(1); }
const T = globalThis.__TUT__;

// --- all lessons instantiate -------------------------------------------------
console.log('\n=== all 7 lessons instantiate ===');
for (let lesson = 0; lesson <= 6; lesson++) {
  let err = null, q = null;
  try { q = T.tutorialInitial(lesson); } catch (e) { err = e; }
  check(!err, `lesson 0${lesson + 1}`, err ? err.message : `neutrals=${q.g.filter((t) => t && t.side === 'n').length}`);
}

// --- 教程第 02 关的盘面与弧线断言：暂时停测 ---
// 你已明确"现阶段不要管教程相关的事宜"。机制仍在变动（阈值刚改成 4），
// 第 02 关的盘面与文案要等机制冻结后再重做，所以这里不再断言它的通关路径。
// 保留的检查在下面：脚本能加载、7 关都能实例化、吸收仍只在第 02 关生效。
console.log('\n=== 教程第 02 关行为断言：已按你的要求停测 ===');

// --- absorption must NOT leak into other lessons ----------------------------
console.log('\n=== absorption stays scoped to lesson 02 ===');
{
  const DIRS = ['right', 'down', 'left', 'up'];
  for (const lesson of [0, 3, 4, 5, 6]) {
    const q = T.tutorialInitial(lesson);
    const before = q.g.filter((t) => t && t.side === 'n').map((t) => t.id).join(',');
    for (let i = 0; i < 2; i++) {
      for (const d of DIRS) {
        const draft = T.copy(q);
        if (T.moveMain(draft, d)) { T.worldStep(q, d); break; }
      }
    }
    const after = q.g.filter((t) => t && t.side === 'n').map((t) => t.id).join(',');
    // lesson 0 legitimately recruits; the point is that nothing is silently vacuumed
    const leaked = q.g.some((t) => t && t.side === 'p' && !t.core && (t.payload || 0) > 0);
    check(!leaked, `lesson 0${lesson + 1}: no tile accumulated payload from absorption`,
          `neutrals ${before} -> ${after}`);
  }
}

console.log(`\n${failures} FAILURE(S)`);
process.exit(failures ? 1 : 0);
