// 平衡基准：用固定种子 + 固定智能体测「引擎改动的难度影响」。
//
//   node tools/balance.js --engine build/engine.js --seeds 12 --turns 400 --out build/balance/base
//   node tools/balance.js --engine build/engine.js --seeds 12 --turns 400 \
//        --out build/balance/after --compare build/balance/base
//
// 与 difftest.js 的分工（两者共用 tools/_harness.js 里的同一份智能体，所以是"同一个玩家"）：
//   · difftest —— 断言"行为逐位不变"，用于重构/纯搬移。
//   · balance  —— 报告"行为怎么变了"，用于**难度调整**。它不比较相等，只输出数字与差值。
//
// 为什么需要它：本项目所有历史平衡结论都基于**单 seed**，文档已两次记录它们不可信
// （§6 的"阈值反向区间"就是单 seed 结论，害得 CAP 线被错误地排除出科技树）。
// 难度调整必须能给出"12 局里存活 9→5 局、平均 362→271 回合"这种结论，
// 而不是"我觉得更难了"。
//
// 采集的指标（都是"玩家能感知到的东西"，不是内部实现细节）：
//   存活回合 · 是否阵亡/结算 · 峰值数字 · 首次达成 2048 的回合 · 击破数
//   · 峰值时的成员数 · 共享 core 轨迹（每 100 回合一次）· 科技点收入
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const { loadEngine, playGame } = require('./_harness.js');

function argOf(name, dflt) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : dflt;
}

const ENGINE = argOf('engine', 'build/engine.js');
const SEEDS = Number(argOf('seeds', 12));
const TURNS = Number(argOf('turns', 400));
const OUT = argOf('out', 'build/balance/run');
const COMPARE = argOf('compare', null);
const AP_BUDGET = Number(argOf('ap-budget', 12));
const SEED_BASE = Number(argOf('seed-base', 20261017));
const SNAPSHOT_EVERY = 100;

if (!fs.existsSync(ENGINE)) {
  console.error('找不到引擎: ' + ENGINE + '\n  先跑: python tools/build_engine.py --out build/engine.js');
  process.exit(2);
}

const G = loadEngine(ENGINE);
const ENGINE_SHA = crypto.createHash('sha256').update(fs.readFileSync(ENGINE)).digest('hex');

function seedFor(i) {
  return (SEED_BASE + i * 7919) >>> 0;
}

/** 跑一局并采集指标。 */
function runOne(seed) {
  let peak = 2;
  let peakTurn = 0;
  let first2048 = null;
  let maxMembers = 0;
  const trail = [];          // 每 SNAPSHOT_EVERY 回合记一次共享 core

  const out = playGame(G, seed, TURNS, {
    apBudget: AP_BUDGET,
    onTurn(q) {
      const best = Math.max(2, ...q.g.filter((t) => t && t.side === 'p' && !t.support).map((t) => t.n));
      if (best > peak) { peak = best; peakTurn = q.turn; }
      const members = q.g.filter((t) => t && t.side === 'p' && !t.support).length;
      if (members > maxMembers) maxMembers = members;
      if (first2048 === null && best >= 2048) first2048 = q.turn;
      if (q.turn % SNAPSHOT_EVERY === 0) trail.push({ turn: q.turn, core: G.sharedCore(q), best });
    },
  });

  const q = out.q;
  return {
    seed,
    turns: q.turn,
    dead: !!q.dead,
    settled: !!q.settled,
    peak,
    peakTurn,
    first2048,
    kills: q.kills || 0,
    tech: q.tech || 0,
    maxMembers,
    score: q.score || 0,
    trail,
  };
}

// ---- 汇总 -------------------------------------------------------------------
function bucket(n) {
  // 峰值分档：2..32 / 64..256 / 512..1024 / 2048+
  if (n < 64) return '<64';
  if (n < 512) return '64–256';
  if (n < 2048) return '512–1K';
  return '2048+';
}

function summarize(runs) {
  const turns = runs.map((r) => r.turns).sort((a, b) => a - b);
  const n = runs.length;
  const mean = turns.reduce((a, b) => a + b, 0) / n;
  const med = n % 2 ? turns[(n - 1) / 2] : Math.round((turns[n / 2 - 1] + turns[n / 2]) / 2);
  const buckets = { '<64': 0, '64–256': 0, '512–1K': 0, '2048+': 0 };
  for (const r of runs) buckets[bucket(r.peak)]++;
  const alive = runs.filter((r) => !r.dead).length;
  const got = runs.filter((r) => r.first2048 !== null).length;
  // 共享 core 轨迹均值（只统计仍有数据的回合）
  const coreAt = new Map();
  for (const r of runs) {
    for (const t of r.trail) {
      if (!coreAt.has(t.turn)) coreAt.set(t.turn, []);
      coreAt.get(t.turn).push(t.core);
    }
  }
  const coreTrail = [...coreAt.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([turn, arr]) => ({ turn, core: Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) }));

  return {
    games: n,
    survivalRate: alive / n,
    turnsMean: Math.round(mean), turnsMedian: med,
    turnsMin: turns[0], turnsMax: turns[n - 1],
    achieve2048Rate: got / n,
    peakBuckets: buckets,
    killsMean: Math.round(runs.reduce((a, r) => a + r.kills, 0) / n),
    techMean: Math.round(runs.reduce((a, r) => a + r.tech, 0) / n),
    scoreMean: Math.round(runs.reduce((a, r) => a + r.score, 0) / n),
    maxMembersMean: Math.round(runs.reduce((a, r) => a + r.maxMembers, 0) / n),
    coreTrail,
  };
}

// ---- 主流程 -----------------------------------------------------------------
const t0 = Date.now();
const runs = [];
for (let i = 0; i < SEEDS; i++) {
  const r = runOne(seedFor(i));
  runs.push(r);
  process.stdout.write(r.dead ? 'x' : '.');   // 进度点：x=阵亡 . =存活到上限
}
console.log();

// 上面那行是进度点（x=阵亡，.=跑到回合上限）。逐局明细在下面统一格式化。
// ⚠️ Node 的 console.log **不支持** `%-10s` 这类宽度修饰符（那是 Python 的 printf），
//    传进去会原样打印。所以表格用手工 padding，不用格式串。
const pad = (v, w, right) => {
  const s = String(v);
  const fill = ' '.repeat(Math.max(0, w - s.length));
  return right ? fill + s : s + fill;
};
const cjk = (s) => {
  // 中文按两个字宽算，否则列会错位
  let n = 0;
  for (const ch of String(s)) n += ch.charCodeAt(0) > 0x2e80 ? 2 : 1;
  return n;
};
const padw = (v, w, right) => {
  const s = String(v);
  const fill = ' '.repeat(Math.max(0, w - cjk(s)));
  return right ? fill + s : s + fill;
};

console.log('=== 逐局 ===');
console.log('  ' + pad('seed', 10) + padw('回合', 8, true) + padw('结局', 8, true)
  + padw('峰值', 8, true) + padw('2048@', 9, true) + padw('击破', 6, true)
  + padw('成员峰值', 10, true) + padw('科技', 6, true));
for (const r of runs) {
  console.log('  ' + pad(r.seed, 10) + pad(r.turns, 8, true)
    + padw(r.dead ? '阵亡' : (r.settled ? '已结算' : '存活'), 8, true)
    + pad(r.peak, 8, true) + pad(r.first2048 === null ? '—' : r.first2048, 9, true)
    + pad(r.kills, 6, true) + pad(r.maxMembers, 10, true) + pad(r.tech, 6, true));
}

const sum = summarize(runs);
console.log();
console.log('=== 汇总（%d 局 × 最多 %d 回合，AP 预算 %d） ===', sum.games, TURNS, AP_BUDGET);
console.log('  存活率        %d/%d = %d%%',
  Math.round(sum.survivalRate * sum.games), sum.games, Math.round(sum.survivalRate * 100));
console.log('  存活回合      平均 %d · 中位 %d · 最短 %d · 最长 %d',
  sum.turnsMean, sum.turnsMedian, sum.turnsMin, sum.turnsMax);
console.log('  达成 2048     %d/%d = %d%%',
  Math.round(sum.achieve2048Rate * sum.games), sum.games,
  Math.round(sum.achieve2048Rate * 100));
console.log('  峰值分布      %s', Object.entries(sum.peakBuckets)
  .map(([k, v]) => k + ':' + v).join('  '));
console.log('  平均击破 %d · 平均科技 %d · 平均得分 %d · 成员峰值 %d',
  sum.killsMean, sum.techMean, sum.scoreMean, sum.maxMembersMean);
console.log('  共享 core 轨迹（每 %d 回合均值）:', SNAPSHOT_EVERY);
console.log('    ' + sum.coreTrail.map((t) => 'T' + t.turn + ':' + t.core).join('  '));
console.log();
console.log('  引擎 sha256  %s…', ENGINE_SHA.slice(0, 16));
console.log('  用时         %ds', ((Date.now() - t0) / 1000).toFixed(0));

// ---- 落盘 -------------------------------------------------------------------
const manifest = {
  engine: ENGINE,
  engineSha256: ENGINE_SHA,
  seeds: SEEDS, turns: TURNS, apBudget: AP_BUDGET, seedBase: SEED_BASE,
  runs,
  summary: sum,
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT + '.json', JSON.stringify(manifest, null, 2));
console.log('  结果         %s.json', OUT);

// ---- 与基线对比 -------------------------------------------------------------
if (COMPARE) {
  const refPath = COMPARE.endsWith('.json') ? COMPARE : COMPARE + '.json';
  if (!fs.existsSync(refPath)) { console.error('\n基线不存在: ' + refPath); process.exit(2); }
  const ref = JSON.parse(fs.readFileSync(refPath, 'utf8'));
  const a = ref.summary;
  const d = (label, before, after, unit) => {
    const delta = after - before;
    const sign = delta > 0 ? '+' : '';
    const pct = before ? Math.round((delta / Math.abs(before)) * 100) : 0;
    console.log('  %-14s %8s → %-8s  %s%s%s (%s%d%%)',
      label, before + unit, after + unit, sign, delta, unit, sign, pct);
  };
  console.log();
  console.log('=== 对比基线 %s ===' % refPath);
  console.log('  基线引擎 %s…', String(ref.engineSha256).slice(0, 16));
  d('存活率', Math.round(a.survivalRate * 100), Math.round(sum.survivalRate * 100), '%');
  d('平均存活回合', a.turnsMean, sum.turnsMean, '');
  d('中位存活回合', a.turnsMedian, sum.turnsMedian, '');
  d('达成2048率', Math.round(a.achieve2048Rate * 100), Math.round(sum.achieve2048Rate * 100), '%');
  d('平均击破', a.killsMean, sum.killsMean, '');
  d('平均科技', a.techMean, sum.techMean, '');
  d('成员峰值', a.maxMembersMean, sum.maxMembersMean, '');
}
