// 核对科技树当前的常量与全线成本（文档 §10 的速查表可能已经过时）。
//
//   node tools/report_tech_cost.js
const fs = require('fs');
const path = require('path');
// 仓库根从脚本位置推导（tools/ 的上一级），不再写死盘符
const ROOT = path.resolve(__dirname, '..');
const vm = require('vm');

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
vm.runInThisContext(fs.readFileSync(path.join(ROOT, 'build', 'engine.js'), 'utf8'));
const G = globalThis.__CF__;

const LINES = [['threshold', '自动合成阈值'], ['tp', '吸收吞吐'], ['radius', '收集半径']];
let total = 0;
console.log('线          等级  1级 2级 3级   本线合计  各级后效果');
for (const [line, name] of LINES) {
  const max = G.techMax(line);
  const costs = [];
  for (let lv = 0; lv < max; lv++) costs.push(G.techCost(line, lv));
  const sum = costs.reduce((a, b) => a + b, 0);
  total += sum;
  const eff = [];
  for (let lv = 0; lv <= max; lv++) eff.push(G.techInfoAt(line, lv));
  console.log(`${name.padEnd(8)} ${String(max).padStart(3)}  ${costs.map((c) => String(c).padStart(3)).join(' ')}` +
              `   ${String(sum).padStart(6)}   ${eff.join(' → ')}`);
}
console.log('\n全线合计：' + total + ' 点');

// 顺带把当前的关键常量打出来，供文档速查表对齐
const src = fs.readFileSync(path.join(ROOT, 'src', 'main.script.js'), 'utf8');
const m = src.match(/const ABSORB_CAP=[^\n]*;/);
console.log('\n常量行：\n  ' + (m ? m[0] : '?'));
const m2 = src.match(/const SCORE_PER_TECH=[^\n]*;/);
console.log('  ' + (m2 ? m2[0] : '?'));
