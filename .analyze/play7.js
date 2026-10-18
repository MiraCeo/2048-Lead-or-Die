// 当前这一步：吸收前置 + 取消整组，对比“升级回满血 / 按比例保留血量”
const fs = require('fs');
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
function bootEngine(disableGroups) {
  let js = fs.readFileSync(__dirname + '/core-fleet.engine.js', 'utf8');
  if (disableGroups) {
    const start = js.indexOf('function neutralGroups(q){');
    let i = js.indexOf('{', start), depth = 0, end = -1;
    for (let k = i; k < js.length; k++) {
      if (js[k] === '{') depth++;
      else if (js[k] === '}') { depth--; if (depth === 0) { end = k; break; } }
    }
    js = js.slice(0, start) + 'function neutralGroups(q){return 0;}' + js.slice(end + 1);
  }
  const sandbox = {
    document: makeStub(), window: makeStub(), requestAnimationFrame: () => 0,
    TextDecoder, atob, btoa, console, performance,
  };
  const store = new Map();
  sandbox.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(js, sandbox);
  return sandbox.__CF__;
}

const DIRS = ['up', 'down', 'left', 'right'];
const OFF = [[-1, 0], [1, 0], [0, -1], [0, 1]];
const CAP = 8, TP = 2;

function autoCollect(G, q, heal) {
  let grown = 0, eaten = 0;
  const lvCore = G.lvl(G.sharedCore(q));
  for (let i = 0; i < 10000; i++) {
    const t = q.g[i];
    if (!t || t.side !== 'p' || t.support || t.n >= CAP) continue;
    let used = 0;
    const r = Math.floor(i / 100), c = i % 100;
    for (const [dr, dc] of OFF) {
      if (used >= TP || t.n >= CAP) break;
      const rr = r + dr, cc = c + dc;
      if (rr < 0 || rr >= 100 || cc < 0 || cc >= 100) continue;
      const j = rr * 100 + cc, u = q.g[j];
      if (!u || u.side !== 'n' || u.n > CAP) continue;
      const before = t.hp, beforeCap = t.cap;
      t.payload = (t.payload || 0) + u.n;
      q.g[j] = null; eaten++; used++;
      while (t.payload >= t.n && t.n * 2 <= CAP) {
        t.payload -= t.n;
        t.n *= 2;
        t.cap = 3 ** G.lvl(t.n) * lvCore;
        t.hp = heal ? t.cap : Math.max(1, Math.ceil(before / Math.max(1, beforeCap) * t.cap));
        grown++;
      }
      if (t.payload < t.n) break;
    }
  }
  return { grown, eaten };
}

function spendAP(G, q, budget) {
  let used = 0;
  for (let k = 0; k < budget; k++) {
    if (q.ap < 1) break;
    const ids = q.g.filter((t) => t && t.side === 'p' && !t.core && !t.support).map((t) => t.id);
    let found = null;
    for (const id of ids) {
      for (const d of DIRS) {
        const draft = G.copy(q);
        const r = G.extraStep(draft, id, d);
        if (r.error) continue;
        if (draft.g.filter(Boolean).length < q.g.filter(Boolean).length) { found = draft; break; }
      }
      if (found) break;
    }
    if (!found) break;
    Object.assign(q, found);
    used++;
  }
  return used;
}

function chooseDir(G, q) {
  const targets = [];
  q.g.forEach((t, i) => { if (t && t.side === 'n') targets.push(i); });
  q.g.forEach((t, i) => { if (t && t.side === 'e') targets.push(i); });
  if (!targets.length) return null;
  let pick = null;
  for (const d of DIRS) {
    const draft = G.copy(q);
    const r = G.moveMain(draft, d);
    if (!r) continue;
    const di = draft.g.findIndex((t) => t && t.core && t.id === draft.active);
    const dist = di >= 0 ? Math.min(...targets.map((t) => Math.sqrt(G.dist2(di, t)))) : 99;
    const score = r.merges * 10 + r.recruited * 4 - dist * 0.6 + (r.contacts || 0);
    if (!pick || score > pick.score) pick = { d, score };
  }
  return pick;
}

function run({ heal, seed, maxTurns, label }) {
  const G = bootEngine(true);          // 取消整组
  let q = G.initial(seed);
  let grown = 0, eaten = 0, apUsed = 0;
  let peak = 2, peakTurn = 0, first2048 = null, maxMembers = 0;
  const t0 = Date.now();
  for (let step = 0; step < maxTurns; step++) {
    if (q.dead || q.settled) break;
    apUsed += spendAP(G, q, 12);
    const a = autoCollect(G, q, heal);   // 先吸收
    grown += a.grown; eaten += a.eaten;
    const pick = chooseDir(G, q);
    let r = null, dir = null;
    if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
    if (!r) {
      for (const d of DIRS) { if (d === dir) continue; r = G.worldStep(q, d); if (r) { dir = d; break; } }
    }
    if (!r) break;
    const members = q.g.filter((t) => t && t.side === 'p' && !t.support).length;
    if (members > maxMembers) maxMembers = members;
    const best = Math.max(2, ...q.g.filter((t) => t && t.side === 'p' && !t.support).map((t) => t.n));
    if (best > peak) { peak = best; peakTurn = q.turn; }
    if (first2048 === null && best >= 2048) first2048 = q.turn;
    if (q.turn % 100 === 0) {
      console.log(`  [${label}] T${String(q.turn).padStart(4)} 最高${String(best).padStart(5)} 成员${String(members).padStart(3)} 共享core${String(G.sharedCore(q)).padStart(4)} 吸收${grown}/${eaten} AP${q.ap}`);
    }
  }
  const ms = Date.now() - t0;
  console.log(`  [${label}] 结束 ${q.turn} 回合 ${q.dead ? '阵亡' : '存活'} · 峰值 ${peak}(T${peakTurn}) · 首达2048 ${first2048 ?? '未达成'} · 成员峰值 ${maxMembers} · 吸收 ${grown}/${eaten} · AP ${apUsed} · ${(ms / 1000).toFixed(0)}s`);
}

const SEED = 20261017, MAX = Number(process.argv[2] || 700);
console.log('=== 吸收前置 + 取消整组 ===');
console.log('（对照：play6 的后置吸收+保留整组 cap8 = 694 回合、峰值 16384、T680 达成）\n');
console.log('### A 升级回满血');
run({ heal: true, seed: SEED, maxTurns: MAX, label: 'heal' });
console.log('\n### B 升级按比例保留血量');
run({ heal: false, seed: SEED, maxTurns: MAX, label: 'keep' });
