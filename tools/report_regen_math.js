// Reference numbers behind the two Step 3 deviations.
//
//   node tools/report_regen_math.js
//
// Uses the engine's own formulas so the figures are not hand-derived:
//   cap    = 3^log2(n) * log2(core)          (rescale)
//   damage = n * log2(core)                  (damage)
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
global.document = makeStub();
global.window = makeStub();
global.requestAnimationFrame = () => 0;
const store = new Map();
global.localStorage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };
vm.runInThisContext(fs.readFileSync('D:\\2048\\build\\engine.js', 'utf8'));
const G = globalThis.__CF__;

const lvl = G.lvl;
const capOf = (n, core) => 3 ** lvl(n) * lvl(core);
const dmgOf = (n, core) => n * lvl(core);

const FLAT = 2;                                          // was signed: shared TP budget = 2
const scaled = (cap) => Math.max(2, Math.ceil(cap * 0.1)); // implemented: REGEN_FRAC = 0.1

const pad = (v, w) => String(v).padStart(w);

console.log('cap = 3^lvl(n) * lvl(core)      damage = n * lvl(core)');
console.log('FLAT   = 2 hp/turn   (the signed "shared TP budget" reading)');
console.log('SCALED = max(2, ceil(cap*0.1)) hp/turn   (what is implemented)\n');

for (const core of [8, 32, 128]) {
  console.log(`=== sharedCore = ${core}  (lvl = ${lvl(core)}) ===`);
  console.log(pad('n', 5) + pad('cap', 9) + pad('hit', 9) + pad('FLAT to full', 15) + pad('SCALED to full', 17));
  for (const n of [2, 4, 8, 16, 32, 64]) {
    const cap = capOf(n, core);
    const hit = dmgOf(n, core);
    const f = Math.ceil((cap - 1) / FLAT);
    const s = Math.ceil((cap - 1) / scaled(cap));
    console.log(pad(n, 5) + pad(cap, 9) + pad(hit, 9) + pad(f + ' turns', 15) + pad(s + ' turns', 17));
  }
  console.log();
}

console.log('=== recovery after ONE hit from an equal-value enemy (sharedCore = 8) ===');
console.log(pad('n', 5) + pad('cap', 9) + pad('damage', 9) + pad('hp lost', 10) + pad('FLAT', 12) + pad('SCALED', 12));
for (const n of [8, 16, 32, 64]) {
  const cap = capOf(n, 8);
  const dmg = dmgOf(n, 8);
  const lost = Math.max(0, dmg);
  console.log(pad(n, 5) + pad(cap, 9) + pad(dmg, 9) + pad(lost, 10)
    + pad(Math.ceil(lost / FLAT) + ' turns', 12)
    + pad(Math.ceil(lost / scaled(cap)) + ' turns', 12));
}
