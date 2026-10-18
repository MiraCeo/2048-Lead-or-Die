// 展示层与战报的验证。
//
//   node tools/test_display.js
//
// canvas 画出来的东西无头环境看不到，所以分两层验：
//   1. 运行层：新绘制路径不抛错；战报行为（跑若干回合后是否还有例行行）
//   2. 源码层：关键公式在场、旧实现已消失（防止被悄悄改回去）
const fs = require('fs');
const path = require('path');
// 仓库根从脚本位置推导（tools/ 的上一级），不再写死盘符
const ROOT = path.resolve(__dirname, '..');
const { DELIVERABLE } = require('./_root.js');
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

vm.runInThisContext(ENGINE);
const G = globalThis.__CF__;
const HTML = fs.readFileSync(path.join(ROOT, DELIVERABLE), 'utf8');

const tile = (hp, cap, n, payload) => ({ hp, cap, n, payload, side: 'p', support: false, core: false });

console.log('\n=== 运行层：绘制路径 ===');
{
  check(typeof G.tileBody === 'function', 'tileBody 已导出');
  for (const [name, hp, cap] of [['半血', 50, 100], ['残血', 1, 2187], ['满血', 100, 100], ['空血', 0, 81]]) {
    let threw = null;
    try { G.tileBody({ x: 100, y: 100 }, 14, 28, 4, '#abcdef', '#123456', tile(hp, cap, 4, 2)); }
    catch (e) { threw = e; }
    check(!threw, `tileBody ${name}不抛错`, threw ? threw.message : '');
  }
  let threw = null;
  try { G.draw(); } catch (e) { threw = e; }
  check(!threw, 'draw() 整帧不抛错', threw ? threw.message : '');
}

console.log('\n=== 源码层：棋盘编码 ===');
{
  check(has(ENGINE, 'ctx.clip()'), '填充改用画布裁剪（低血圆角缺口消失）');
  check(notHas(ENGINE, 'Math.min(rad,Math.floor(h/2))'), '旧的"按高度夹圆角"写法已移除');
  check(has(ENGINE, 'bx=p.x-11,by=p.y+8,bw=22,bh=4'), '进度条加大到 22×4');
  check(has(ENGINE, "'#7f8f7f'"), '不可吸收画明显更亮的满格灰');
  check(notHas(ENGINE, "'#4a5a4a'"), '旧的暗灰满格条已移除（原来和空条撞色）');
  check(has(ENGINE, "'#0d1512'"), '轨道改成更深的底色（提高与填充的对比）');
  check(notHas(ENGINE, 'if(t.n<=8)for(let k=1;k<t.n;k++)'), '档位刻度已取消');
  check(notHas(ENGINE, 'strokeText'), '描边已取消');
  check(notHas(ENGINE, "'#f2f7e8'"), '数字不再带描边色');
  check(has(ENGINE, "if(t.side==='p'&&!t.core&&t.hp<t.cap)"),
        '掉血的我方方块按比例变色，且核心已排除（核心保持原色）');
  check(has(ENGINE, 'hr>HP_HURT?HP_COL_OK:hr>HP_CRIT?HP_COL_HURT:HP_COL_CRIT'),
        '三档阈值：绿(>2/3) / 黄(>1/3) / 红(其余)');
  check(has(ENGINE, "'#8fd98a'") && has(ENGINE, "'#e8cf72'") && has(ENGINE, "'#e07a6a'"),
        '绿/黄/红三色都在场');
  check(has(ENGINE, 'let fill='), 'fill 改为可覆盖（否则无法按血量改色）');
  check(has(ENGINE, 'size*Math.max(0,Math.min(1,t.hp/t.cap))'), '血量仍是背景高度');
  check(notHas(ENGINE, '20*t.hp/t.cap'), '旧的血条代码已不在');
}

console.log('\n=== 战报：只留重要事件 ===');
{
  check(has(ENGINE, 'q.logs.slice(0,30)'), '战报上限提升到 30');
  check(notHas(ENGINE, '· 补给内${supply.inside}/外'), '例行回合行已从引擎移除');
  check(notHas(ENGINE, "log(q,info+' · 行动点 −1，时间冻结')"), '额外操作行已移除');
  check(notHas(ENGINE, '两块位置互换 · 行动点 −1 · 分化'), '置换的例行行已移除');
  check(has(ENGINE, 'if(splits)log(q,'), '置换改为只在触发分化时记');

  const q = G.initial(20261017);
  const DIRS = ['up', 'down', 'left', 'right'];
  let turns = 0;
  for (let i = 0; i < 60 && !q.dead && !q.settled; i++) {
    for (const d of DIRS) {
      const draft = G.copy(q);
      if (G.moveMain(draft, d)) { G.worldStep(q, d); turns++; break; }
    }
  }
  const routine = q.logs.filter((l) => l.startsWith('回合 '));
  check(routine.length === 0, `跑 ${turns} 回合后战报里没有例行行`, `例行行=${routine.length}`);
  check(q.logs.length > 0, '战报仍有内容（重要事件）', `条数=${q.logs.length}`);
  console.log('  info  战报前三条：');
  q.logs.slice(0, 3).forEach((l) => console.log(`        · ${l}`));
}

console.log('\n=== 交付物一致性 ===');
{
  check(has(HTML, 'tileBody'), '交付文件里含 tileBody');
  check(notHas(HTML, '20*t.hp/t.cap'), '交付文件里已无旧血条');
  const n = (HTML.match(/id="techTree"/g) || []).length;
  check(n === 1, '科技面板仍在', `#techTree=${n}`);
}

console.log(`\n${failures} 项失败`);
process.exit(failures ? 1 : 0);
