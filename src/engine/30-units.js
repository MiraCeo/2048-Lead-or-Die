// ==== 30-units ====
// 来源: main.script.js 第 26–48 行（原样搬移，未改一字符）
// 存档编码、敌方编成、初始盘面
  function paintOutlines(q, cam) {
    const cells = [];
    for (let r = cam.r; r < cam.r + V; r++) for (let c = cam.c; c < cam.c + V; c++) cells.push(r * N + c);
    const edges = boundaryEdges(q, cells);
    ctx.save();
    ctx.beginPath();
    ctx.rect(X, Y, V * C, V * C);
    ctx.clip();
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (const e of edges) {
      const p = screenPoint(e.i, cam),
        t = q.g[e.i];
      const color =
        t.side === 'n' ? '#ffe0a0' : t.side === 'e' ? '#ff927c' : t.team === q.active ? '#d0fa93' : '#91e0f4';
      const x = p.x - C / 2,
        y = p.y - C / 2;
      const pair =
        e.d === 'up'
          ? [x, y, x + C, y]
          : e.d === 'down'
            ? [x, y + C, x + C, y + C]
            : e.d === 'left'
              ? [x, y, x, y + C]
              : [x + C, y, x + C, y + C];
      ctx.beginPath();
      ctx.moveTo(pair[0], pair[1]);
      ctx.lineTo(pair[2], pair[3]);
      ctx.strokeStyle = '#101a14';
      ctx.lineWidth = 6;
      ctx.stroke();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.6;
      ctx.stroke();
    }
    ctx.restore();
  }
  function capture(q, t, team, side) {
    if (t.support) {
      if (side !== 'p') return 0;
      const old = t.team;
      let count = 0;
      for (const u of q.g)
        if (u?.support && u.team === old) {
          delete u.support;
          delete u.structure;
          delete u.supportCore;
          u.side = 'p';
          u.team = team;
          u.core = false;
          count++;
        }
      log(q, `吞并友方碉堡 · ${count}块解除固定，纳入己方主体`);
      rescale(q);
      return count;
    }
    if (t.side !== side && t.side !== 'n') return 0;
    if (t.side === side && t.team === team) return 0;
    if (t.core) {
      const old = t.team;
      if (side === 'p' && t.id === q.primary && !q.primaryLost) {
        q.primary = team;
      }
      let count = 0;
      for (const u of q.g)
        if (u?.team === old && u.side === side) {
          u.team = team;
          u.core = false;
          count++;
        }
      return count;
    }
    t.side = side;
    t.team = team;
    delete t.nc;
    return 1;
  }
  // Snapshot objects are immutable; cache only history, never the live state.
  const historyEncoding = new WeakMap(),
    snapshotIds = new WeakMap();
  let nextSnapshotId = 1;
  function snapshotId(q) {
    if (!snapshotIds.has(q)) snapshotIds.set(q, nextSnapshotId++);
    return snapshotIds.get(q);
  }
  function sameTile(a, b) {
    if (a === b) return true;
    if (!a || !b) return false;
    const keys = Object.keys(a);
    return keys.length === Object.keys(b).length && keys.every((k) => a[k] === b[k]);
  }
  function encodeHistory(list) {
    if (!list.length) return { base: 'null', deltas: [] };
    let entry = historyEncoding.get(list[0]);
    if (!entry) {
      entry = {};
      historyEncoding.set(list[0], entry);
    }
    if (!entry.full) entry.full = JSON.stringify(list[0]);
    const base = entry.full,
      deltas = [];
    for (let k = 1; k < list.length; k++) {
      const q = list[k],
        prev = list[k - 1];
      let e = historyEncoding.get(q);
      if (!e) {
        e = {};
        historyEncoding.set(q, e);
      }
      if (e.prevId !== snapshotId(prev)) {
        const changes = [];
        for (let i = 0; i < N * N; i++) if (!sameTile(q.g[i], prev.g[i])) changes.push([i, q.g[i]]);
        const { g, ...meta } = q;
        e.delta = JSON.stringify({ meta, changes });
        e.prevId = snapshotId(prev);
      }
      deltas.push(e.delta);
    }
    return { base, deltas };
  }
  function decodeHistory(data) {
    if (data.historyFormat !== 'delta-v1')
      return Array.isArray(data.history) ? data.history.filter(valid).slice(-50) : [];
    if (!data.historyBase) return [];
    if (!valid(data.historyBase) || !Array.isArray(data.historyDeltas) || data.historyDeltas.length > 49) return [];
    const list = [data.historyBase];
    for (const patch of data.historyDeltas) {
      if (!patch || !patch.meta || !Array.isArray(patch.changes)) return [];
      const q = { ...patch.meta, g: copy(list[list.length - 1]).g };
      for (const pair of patch.changes) {
        if (!Array.isArray(pair) || !Number.isInteger(pair[0]) || pair[0] < 0 || pair[0] >= N * N) return [];
        q.g[pair[0]] = pair[1] ? { ...pair[1] } : null;
      }
      if (!valid(q)) return [];
      list.push(q);
    }
    return list;
  }
  function save() {
    const current = JSON.stringify(s);
    for (const keep of [50, 5, 0]) {
      try {
        const packed = encodeHistory(keep ? history.slice(-keep) : []);
        localStorage.setItem(
          KEY,
          '{"s":' +
            current +
            ',"historyFormat":"delta-v1","historyBase":' +
            packed.base +
            ',"historyDeltas":[' +
            packed.deltas.join(',') +
            ']}',
        );
        return;
      } catch {}
    }
  }
  function neutralMultiplier(q) {
    return 2 ** Math.max(0, Math.floor((lvl(sharedCore(q)) - 3) / 2));
  }
  function enemySlots(q) {
    return Math.max(0, 6 - cores(q, 'e').length);
  }
  function addNeutral(q, i) {
    const n = (rand(q) < 0.85 ? 2 : 4) * neutralMultiplier(q),
      cap = 3 ** lvl(n);
    q.g[i] = { id: q.serial++, n, side: 'n', core: false, team: null, hp: cap, cap };
  }
  function spawn(q) {
    const cam = camera(q),
      inside = [],
      outside = [];
    q.g.forEach((t, i) => {
      if (!t) (visible(i, cam) ? inside : outside).push(i);
    });
    let result = { inside: 0, outside: 0 };
    for (const [list, key, count] of [
      [inside, 'inside', q.turn % 2 === 0 ? 1 : 0],
      [outside, 'outside', 3],
    ])
      for (let n = 0; n < count && list.length; n++) {
        const at = Math.floor(rand(q) * list.length),
          i = list.splice(at, 1)[0];
        addNeutral(q, i);
        result[key]++;
      }
    neutralClusters(q);
    return result;
  }
  function waveSpec(wave) {
    const tier = Math.floor((wave - 1) / 3),
      n = 2 ** (3 + tier),
      count = Math.min(3, 1 + tier);
    return { tier: tier + 1, n, count };
  }
  function desiredSize(core) {
    const m = lvl(Math.max(8, core.n));
    return ((m + 1) * m) / 2;
  }
  function memberValue(core, ordinal) {
    const m = lvl(Math.max(8, core.n)),
      levels = [Math.max(1, m - 2), Math.max(2, m - 1), Math.max(1, m - 2), Math.max(2, m - 1), m];
    return 2 ** levels[ordinal % levels.length];
  }
  function fillEnemy(q, id, budget = Infinity) {
    const ci = coreIndex(q, id),
      core = q.g[ci];
    if (!core || core.side !== 'e') return 0;
    let count = q.g.filter((t) => t?.side === 'e' && t.team === core.team).length,
      added = 0;
    const target = desiredSize(core),
      radius = Math.min(N - 1, Math.max(2, Math.ceil((Math.sqrt(target) + 1) / 2)));
    while (count < target && added < budget) {
      const body = [...connected(q, id)],
        slots = new Set();
      for (const i of body)
        for (const d in dirs) {
          const j = neighbor(i, d);
          if (
            j >= 0 &&
            !q.g[j] &&
            Math.abs(Math.floor(j / N) - Math.floor(ci / N)) <= radius &&
            Math.abs((j % N) - (ci % N)) <= radius
          )
            slots.add(j);
        }
      if (!slots.size) break;
      const ordered = [...slots].sort((a, b) => dist2(a, ci) - dist2(b, ci) || a - b),
        i = ordered[0],
        memberN = memberValue(core, count - 1),
        cap = 3 ** lvl(memberN) * lvl(core.n);
      q.g[i] = { id: q.serial++, n: memberN, side: 'e', core: false, team: core.team, hp: cap, cap, coreCache: core.n };
      count++;
      added++;
    }
    return added;
  }
  function replenish(q) {
    let added = 0;
    for (const t of cores(q, 'e')) added += fillEnemy(q, t.id, 2);
    if (added) log(q, `敌方补员 +${added} · 各编队最多补2块`);
    return added;
  }
  function uniformEmpty(q) {
    const slots = [];
    q.g.forEach((t, i) => {
      if (!t) slots.push(i);
    });
    return slots.length ? slots[Math.floor(rand(q) * slots.length)] : -1;
  }
  function reinforce(q) {
    q.wave++;
    const spec = waveSpec(q.wave);
    let added = 0;
    for (let k = 0; k < spec.count && enemySlots(q) > 0; k++) {
      const i = uniformEmpty(q);
      if (i < 0) break;
      const kind =
          q.wave === 1
            ? 'fighter'
            : q.wave === 2
              ? 'bunker'
              : q.wave === 3
                ? 'collector'
                : ['fighter', 'bunker', 'collector'][(q.wave + k - 1) % 3],
        id = q.serial++;
      q.g[i] = {
        id,
        n: spec.n,
        side: 'e',
        core: true,
        team: id,
        kind,
        hp: 3 ** lvl(spec.n) * lvl(spec.n),
        cap: 3 ** lvl(spec.n) * lvl(spec.n),
        payload: 0,
        nextGrowth: q.turn + 40,
      };
      const body = fillEnemy(q, id);
      added++;
      log(q, `全图增援：${kindName[kind]} core=${spec.n} · ${body + 1}块，${Math.floor(i / N) + 1}行${(i % N) + 1}列`);
    }
    if (!added)
      log(
        q,
        enemySlots(q) === 0
          ? '敌方已达6单位上限，本批增援跳过（已有超限单位保留）。'
          : '全地图没有空位，本批增援跳过。',
      );
    q.nextWave += 20;
    rescale(q);
    return added;
  }
  function spawnSupport(q) {
    const i = uniformEmpty(q);
    if (i < 0) {
      log(q, '全地图无空位，本次友方碉堡支援跳过。');
      return 0;
    }
    const batch = Math.max(1, Math.floor(q.turn / 20)),
      n = Math.max(4, waveSpec(batch).n / 2),
      id = q.serial++,
      team = 'support-' + id,
      cap = 3 ** lvl(n) * lvl(n);
    q.g[i] = { id, n, side: 'p', team, core: false, support: true, structure: true, supportCore: n, hp: cap, cap };
    const m = lvl(n),
      target = ((m + 1) * m) / 2;
    let count = 1;
    while (count < target) {
      const slots = new Set();
      for (let k = 0; k < N * N; k++)
        if (q.g[k]?.support && q.g[k].team === team)
          for (const d in dirs) {
            const j = neighbor(k, d);
            if (j >= 0 && !q.g[j]) slots.add(j);
          }
      if (!slots.size) break;
      const chosen = [...slots].sort((a, b) => dist2(a, i) - dist2(b, i) || a - b)[0],
        values = [
          2 ** Math.max(1, m - 2),
          2 ** Math.max(1, m - 1),
          2 ** Math.max(1, m - 2),
          2 ** Math.max(1, m - 1),
          n,
        ],
        value = values[(count - 1) % 5],
        hp = 3 ** lvl(value) * m;
      q.g[chosen] = {
        id: q.serial++,
        n: value,
        side: 'p',
        team,
        core: false,
        support: true,
        structure: false,
        supportCore: n,
        hp,
        cap: hp,
      };
      count++;
    }
    log(q, `友方碉堡部署：core=${n}，${count}块，位于 ${Math.floor(i / N) + 1}行${(i % N) + 1}列`);
    return count;
  }
  function initial(seed = Date.now()) {
    const q = {
      g: Array(N * N).fill(null),
      seed: seed >>> 0,
      turn: 0,
      ap: 5,
      active: 1,
      primary: 1,
      playerCore: 8,
      primaryLost: false,
      wave: 0,
      nextWave: 20,
      nextSupport: 20,
      serial: 1,
      score: 0,
      shots: 0,
      kills: 0,
      tech: 0,
      upTp: 0,
      upRadius: 0,
      upThreshold: 0,
      visited: null,
      combat: null,
      logs: [],
      dead: false,
      goalReached: false,
      goalChoice: null,
      goalTurn: null,
      settled: false,
      highestN: 2,
      lastFocus: 50 * N + 50,
    };
    function add(r, c, n, side = 'n', core = false, team = null) {
      const id = q.serial++,
        cap = 3 ** lvl(n);
      q.g[(r + 25) * N + c + 25] = { id, n, side, core, team: core ? id : team, hp: cap, cap };
      return id;
    }
    const p = add(25, 25, 8, 'p', true);
    q.active = p;
    add(24, 25, 2, 'p', false, p);
    add(26, 25, 4, 'p', false, p);
    add(25, 24, 2, 'p', false, p);
    add(25, 26, 4, 'p', false, p);
    add(26, 26, 2, 'p', false, p);
    add(20, 20, 4, 'p', false, 'loose-start');
    add(20, 21, 2, 'p', false, 'loose-start');
    for (const [r, c, n] of [
      [24, 26, 4],
      [25, 23, 2],
      [25, 27, 4],
      [27, 25, 4],
      [23, 25, 2],
      [23, 24, 8],
      [27, 24, 2],
      [28, 26, 8],
      [22, 21, 4],
      [22, 22, 4],
    ])
      add(r, c, n);
    for (const [r, c, n] of [
      [22, 29, 2],
      [22, 30, 4],
      [22, 31, 2],
      [23, 29, 4],
      [23, 30, 8],
      [23, 31, 2],
    ])
      add(r, c, n);
