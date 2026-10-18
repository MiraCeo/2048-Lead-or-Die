// 变异探针 v2：把变异限制在**玩家侧**，并选一个必然改变数值的参数。
//
// v1 用 REGEN_RATE=0.05→0.051 做探针，结果差异测试报"一致"。查清原因后确认
// 那是**等效变异**而非工具盲区：回血公式是 max(1, ceil(cap*rate))，而多数 cap
// （81/324 等）下 ceil(81*0.05) == ceil(81*0.051) == 5，取整把差异吃掉了。
//
// v2 改为 REGEN_DELAY=10→9（脱离战斗的门槛），并只统计**己方方块**的回血
// —— 因为 REGEN_RATE 对敌方恒为 0（AI_REGEN_RATE=0），而 REGEN_DELAY 会同时
// 影响敌方，那会引入一个与本探针目的无关的差异源。
const fs = require('fs');

const [, , ENGINE, OUT, MODE] = process.argv;
if (!ENGINE || !OUT) {
  console.error('用法: node tools/mutate.js <engine.js> <out.js> [mode]');
  console.error('  mode: delay (默认) | rate');
  process.exit(2);
}
const kind = MODE || 'delay';

let src = fs.readFileSync(ENGINE, 'utf8');
const edits = [];

// --- 1. 回血门槛 10 → 9（必然改变行为：更早开始回血） ---
const NEEDLE_DELAY = 'REGEN_DELAY=10';
const atD = src.indexOf(NEEDLE_DELAY);
if (atD < 0) { console.error(`变异点未找到: ${NEEDLE_DELAY}`); process.exit(2); }
if (kind === 'delay' || kind === 'both') {
  src = src.slice(0, atD) + 'REGEN_DELAY=9' + src.slice(atD + NEEDLE_DELAY.length);
  edits.push(`${NEEDLE_DELAY} -> REGEN_DELAY=9`);
}

// --- 2. 只改玩家侧回血比例，绕过 ceil 把差异吃掉的问题 ---
// 注意：这会同时把 REGEN_RATE 与 AI_REGEN_RATE 分开，所以必须精确定位
// 三元表达式 `t.side==='p'?REGEN_RATE:AI_REGEN_RATE`（敌方恒为 0，不受影响）。
if (kind === 'rate') {
  const NEEDLE_RATE = "const rate=t.side==='p'?REGEN_RATE:AI_REGEN_RATE;";
  const atR = src.indexOf(NEEDLE_RATE);
  if (atR < 0) { console.error(`变异点未找到: ${NEEDLE_RATE}`); process.exit(2); }
  src = src.slice(0, atR) + "const rate=t.side==='p'?0.02:AI_REGEN_RATE;" + src.slice(atR + NEEDLE_RATE.length);
  edits.push(`${NEEDLE_RATE} -> 玩家侧硬编码 0.02`);
}

fs.writeFileSync(OUT, src);
console.log(`模式: ${kind}`);
for (const e of edits) console.log(`  变异: ${e}`);
console.log(`注入: ${OUT}`);
