// 差异测试：证明「纯重构没有改变任何行为」。
//
//   node tools/difftest.js --engine <engine.js> --seeds 6 --turns 300 --out build/difftest/base
//   node tools/difftest.js --engine <engine.js> --seeds 6 --turns 300 --out build/difftest/new \
//                        --assert-same build/difftest/base
//
// 为什么需要它：模块化/域重写会大面积改动引擎源码，而「看起来等价」不等于等价。
// 本工具用固定种子 + 固定确定性智能体把完整对局跑成一条轨迹，逐回合对**全部方块字段**
// 与**全部计数器**求摘要。任何语义漂移都会在某回合的第一个分歧处暴露。
//
// 相比既有的 tools/trace.js（§6 相位诊断用），本工具补了三个关键缺口：
//   1. trace.js 的 gridHash 只覆盖 side/n/team/core/support/kind，且仍在哈希早已删除的
//      t.ng —— 完全没覆盖 hp / cap / payload / nc / supportCore / coreCache / nextGrowth，
//      而这些正是重构最可能碰坏的状态。
//   2. trace.js 不比对 q.seed（RNG 状态）。若重构改变了 rand() 的调用顺序或次数，
//      世界会静默分叉而摘要看不出来。这里把 seed 纳入逐回合摘要。
//   3. 这里做的是「同一引擎两次运行必须逐位相同」的自比对，结论比跨配置数值对比硬。
//
// 一个进程只加载一份引擎：同一进程内加载两份会互相覆盖 globalThis.__CF__
// （项目文档 §14.7 记录的坑）。所以比较基线走 --assert-same 读取文件，不双载。
const fs = require('fs');
const path = require('path');

// 智能体与引擎加载从共享模块取 —— 不再各写一份。
// 平衡基准 tools/balance.js 用的是同一份实现，所以两个工具测的是"同一个玩家"。
const { loadEngine, clearStorage, spendAP, chooseDir, DIRS: HARNESS_DIRS } = require('./_harness.js');

// ---- 参数 -----------------------------------------------------------------
function argOf(name, dflt) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : dflt;
}
const ENGINE = argOf('engine', 'build/engine.js');
const SEEDS = Number(argOf('seeds', 6));
const TURNS = Number(argOf('turns', 300));
const OUT = argOf('out', 'build/difftest/run');
const ASSERT_SAME = argOf('assert-same', null);
const AP_BUDGET = Number(argOf('ap-budget', 12));
const VERBOSE = process.argv.includes('--verbose');

if (!fs.existsSync(ENGINE)) {
  console.error('找不到引擎: ' + ENGINE + '\n  先跑: python tools/build_engine.py --out build/engine.js');
  process.exit(2);
}

const G = loadEngine(ENGINE);
const DIRS = HARNESS_DIRS;

// ---- 规范化 ----------------------------------------------------------------
// 方块对象按**键名排序**后逐键输出：既能捕获「字段增删」，又不受键的插入顺序影响。
// 未定义的字段不输出 —— 这样「字段从 0 变成 undefined」这类差异不会被误报，
// 但「字段消失」仍然会体现为键集合变化。
const TILE_KEY_ORDER = [
  'id', 'n', 'side', 'core', 'team', 'hp', 'cap', 'payload', 'nc', 'kind',
  'structure', 'support', 'supportCore', 'coreCache', 'nextGrowth',
];

function normNum(v) {
  if (v === undefined) return undefined;
  if (v === null) return null;
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) return String(v);           // NaN / Infinity
    return v;                                            // JSON 对有限数保精度
  }
  return v;
}

function normTile(t) {
  if (!t) return null;
  const out = {};
  const keys = Object.keys(t).sort();
  for (const k of keys) {
    const v = normNum(t[k]);
    if (v !== undefined) out[k] = v;
  }
  // 记录是否出现 TILE_KEY_ORDER 之外的字段（新字段必须被显式知晓）
  for (const k of keys) if (!TILE_KEY_ORDER.includes(k)) out['~extra:' + k] = out[k];
  return out;
}

function normVisited(v) {
  if (!v) return null;
  const keys = Object.keys(v).sort();
  const out = {};
  for (const k of keys) out[k] = v[k];
  return out;
}

function normCombat(c) {
  if (!c) return null;
  const keys = Object.keys(c).sort();
  const out = {};
  for (const k of keys) out[k] = c[k];
  return out;
}

function snapshot(q) {
  return {
    turn: q.turn,
    seed: q.seed >>> 0,             // RNG 状态：rand() 调用顺序变了这里立刻暴露
    ap: q.ap,
    active: q.active,
    primary: q.primary,
    playerCore: q.playerCore,
    primaryLost: !!q.primaryLost,
    wave: q.wave,
    nextWave: q.nextWave,
    nextSupport: q.nextSupport,
    serial: q.serial,               // 决定新方块 id 与 loose-<n> 团队名
    score: q.score,
    shots: q.shots,
    kills: q.kills,
    tech: q.tech,
    upTp: q.upTp, upRadius: q.upRadius, upThreshold: q.upThreshold,
    highestN: q.highestN,
    lastFocus: q.lastFocus,
    dead: !!q.dead, settled: !!q.settled,
    goalReached: !!q.goalReached,
    goalChoice: q.goalChoice === undefined ? null : q.goalChoice,
    goalTurn: q.goalTurn === undefined ? null : q.goalTurn,
    visited: normVisited(q.visited),
    combat: normCombat(q.combat),
    logs: q.logs.length,            // 只记条数（文案不是语义）
    g: q.g.map(normTile),
  };
}

// FNV-1a 32 位，对规范化 JSON 求摘要
function hashStr(s) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h.toString(16).padStart(8, '0');
}

// ---- 跑一局 -----------------------------------------------------------------
const SEED_BASE = 20261017;
function seedFor(i) { return (SEED_BASE + i * 7919) >>> 0; }

function playOne(seed) {
  clearStorage();
  const q = G.initial(seed);
  const turns = [];
  let snap0 = JSON.stringify(snapshot(q));
  turns.push({ turn: q.turn, dir: 'init', hash: hashStr(snap0), json: snap0 });

  for (let step = 0; step < TURNS; step++) {
    if (q.dead || q.settled) break;
    spendAP(G, q, AP_BUDGET);
    const pick = chooseDir(G, q);
    let r = null, dir = null;
    if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
    if (!r) {
      for (const d of DIRS) { if (d === dir) continue; r = G.worldStep(q, d); if (r) { dir = d; break; } }
    }
    if (!r) break;
    const json = JSON.stringify(snapshot(q));
    turns.push({ turn: q.turn, dir, hash: hashStr(json), json });
  }

  const last = turns[turns.length - 1];
  return {
    seed,
    turns: turns.length - 1,
    endTurn: q.turn,
    dead: !!q.dead,
    settled: !!q.settled,
    perTurn: turns.map((t) => t.hash),
    trajectory: hashStr(turns.map((t) => t.hash).join(',')),
    lastJson: last.json,
  };
}

// ---- 主流程 -----------------------------------------------------------------
fs.mkdirSync(path.dirname(OUT), { recursive: true });
const results = [];
const t0 = Date.now();
for (let i = 0; i < SEEDS; i++) {
  const r = playOne(seedFor(i));
  results.push(r);
  if (VERBOSE) {
    console.log(`  seed ${r.seed}  回合 ${String(r.endTurn).padStart(4)}  ${r.dead ? '阵亡' : '存活'}  轨迹 ${r.trajectory}`);
  }
}

const manifest = {
  engine: ENGINE,
  engineSha256: require('crypto').createHash('sha256').update(fs.readFileSync(ENGINE)).digest('hex'),
  seeds: SEEDS, turns: TURNS, apBudget: AP_BUDGET, seedBase: SEED_BASE,
  runs: results.map((r) => ({
    seed: r.seed, turns: r.turns, endTurn: r.endTurn, dead: r.dead, settled: r.settled,
    trajectory: r.trajectory,
  })),
  overall: hashStr(results.map((r) => r.trajectory).join('|')),
};

fs.writeFileSync(OUT + '.manifest.json', JSON.stringify(manifest, null, 2));
// 逐回合摘要（可定位第一个分歧回合）
fs.writeFileSync(OUT + '.turns.jsonl',
  results.map((r) => JSON.stringify({ seed: r.seed, perTurn: r.perTurn })).join('\n') + '\n');

const secs = ((Date.now() - t0) / 1000).toFixed(1);
console.log(`引擎      : ${ENGINE}`);
console.log(`           sha256 ${manifest.engineSha256.slice(0, 16)}…`);
console.log(`对局      : ${SEEDS} 局 × 最多 ${TURNS} 回合（AP 预算 ${AP_BUDGET}）`);
for (const r of manifest.runs) {
  console.log(`  seed ${String(r.seed).padStart(10)}  ${String(r.endTurn).padStart(4)} 回合  ${r.dead ? '阵亡' : '存活'}  轨迹 ${r.trajectory}`);
}
console.log(`总轨迹摘要: ${manifest.overall}`);
console.log(`输出      : ${OUT}.manifest.json  /  ${OUT}.turns.jsonl   (${secs}s)`);

// ---- 自比对 -----------------------------------------------------------------
if (ASSERT_SAME) {
  const refPath = ASSERT_SAME.endsWith('.json') ? ASSERT_SAME : ASSERT_SAME + '.manifest.json';
  if (!fs.existsSync(refPath)) { console.error(`\n基线不存在: ${refPath}`); process.exit(2); }
  const ref = JSON.parse(fs.readFileSync(refPath, 'utf8'));

  // 逐回合摘要不在 manifest 里（它在 .turns.jsonl），定位分歧回合必须把它读回来。
  function loadTurns(p) {
    const jl = p.replace(/\.manifest\.json$/, '').replace(/\.json$/, '') + '.turns.jsonl';
    if (!fs.existsSync(jl)) return new Map();
    const m = new Map();
    for (const line of fs.readFileSync(jl, 'utf8').split('\n')) {
      if (!line.trim()) continue;
      try { const o = JSON.parse(line); m.set(o.seed, o.perTurn); } catch {}
    }
    return m;
  }
  const refTurns = loadTurns(refPath);
  const curTurns = loadTurns(OUT + '.manifest.json');

  console.log(`\n=== 与基线比对: ${refPath} ===`);
  console.log(`基线引擎  : ${ref.engine}  (${String(ref.engineSha256).slice(0, 16)}…)`);
  if (ref.seeds !== manifest.seeds || ref.turns !== manifest.turns || ref.apBudget !== manifest.apBudget) {
    console.log(`⚠️  参数不同（基线 seeds=${ref.seeds} turns=${ref.turns} ap=${ref.apBudget}）—— 比对可能不成立`);
  }

  let bad = 0;
  for (let i = 0; i < Math.max(ref.runs.length, manifest.runs.length); i++) {
    const a = ref.runs[i], b = manifest.runs[i];
    if (!a || !b) { console.log(`  !! 第 ${i} 局数量不一致`); bad++; continue; }
    if (a.trajectory === b.trajectory) continue;
    bad++;
    console.log(`\n  !! seed ${a.seed}: 轨迹不同  (基线 ${a.trajectory} vs 当前 ${b.trajectory})`);
    console.log(`     结束回合 基线 ${a.endTurn}(${a.dead ? '阵亡' : '存活'}) vs 当前 ${b.endTurn}(${b.dead ? '阵亡' : '存活'})`);
    const rt = refTurns.get(a.seed) || a.perTurn || [];
    const ct = curTurns.get(b.seed) || b.perTurn || [];
    const n = Math.min(rt.length, ct.length);
    let found = false;
    for (let k = 0; k < n; k++) {
      if (rt[k] !== ct[k]) {
        console.log(`     第一个分歧: 第 ${k} 个快照（含 init，对应第 ${k} 次快照后）`);
        console.log(`       基线 ${rt[k]}  vs  当前 ${ct[k]}`);
        found = true;
        break;
      }
    }
    if (!found) console.log(`     前 ${n} 个快照全部相同 —— 分歧发生在之后（长度 ${rt.length} vs ${ct.length}）`);
  }

  if (manifest.overall === ref.overall) {
    console.log(`\n结果: 逐回合逐位一致 ✅  总摘要 ${manifest.overall}`);
    console.log(`      ${manifest.runs.length} 局全部相同 —— 重构未改变任何行为`);
    process.exit(0);
  }
  console.log(`\n结果: 存在分歧 ❌  ${bad} 局不同`);
  console.log(`      基线总摘要 ${ref.overall}  vs  当前 ${manifest.overall}`);
  process.exit(1);
}
