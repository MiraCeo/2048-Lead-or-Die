// ==== 20-board ====
// 溯源: 阶段 2 的压缩文本 main.script.js 第 14–25 行（此后经阶段 3 改名、阶段 4 格式化）
// core 取值、rescale、连通、分化、中性密集区、轮廓
  function sharedCore(q) {
    const main = q.g.find((t) => t?.side === 'p' && t.core && t.id === q.primary);
    if (main && !q.primaryLost) q.playerCore = main.n;
    return q.playerCore || 8;
  }
  function coreValue(q, t) {
    if (t.support) return t.supportCore;
    if (t.side === 'p') return sharedCore(q);
    if (t.side === 'n') return 2;
    const core = t.core ? t : teamCore(q, t.team);
    if (core) t.coreCache = core.n;
    return core?.n || t.coreCache || 2;
  }
  function damage(q, t) {
    return t.n * lvl(coreValue(q, t));
  }
  function rescale(q) {
    for (const t of q.g) if (t?.side === 'e' && t.core && t.n < 8) t.n = 8;
    sharedCore(q);
    const values = new Map(q.g.filter((t) => t?.core).map((t) => [t.team, t.n]));
    for (const t of q.g) {
      if (!t || t.hp <= 0) continue;
      const value = t.support
        ? t.supportCore
        : t.side === 'p'
          ? q.playerCore
          : t.side === 'e'
            ? values.get(t.team) || t.coreCache || 2
            : 2;
      if (t.side === 'e') t.coreCache = value;
      const cap = 3 ** lvl(t.n) * lvl(value),
        old = t.cap || cap;
      t.hp = Math.max(1, Math.min(cap, Math.ceil(((t.hp ?? cap) / old) * cap)));
      t.cap = cap;
    }
  }
  function flood(q, start, team) {
    const found = new Set([start]),
      queue = [start];
    for (let k = 0; k < queue.length; k++)
      for (const d in dirs) {
        const j = neighbor(queue[k], d);
        if (j >= 0 && q.g[j] && q.g[j].side !== 'n' && q.g[j].team === team && !found.has(j)) {
          found.add(j);
          queue.push(j);
        }
      }
    return found;
  }
  function connected(q, id = q.active) {
    const i = coreIndex(q, id);
    return i < 0 ? new Set() : flood(q, i, q.g[i].team);
  }
  function teamCore(q, team) {
    return q.g.find((t) => t?.core && t.team === team);
  }
  function normalize(q) {
    let created = 0;
    const teams = [...new Set(q.g.filter((t) => t && t.side !== 'n' && !t.support).map((t) => t.team))];
    for (const team of teams) {
      const members = q.g
          .map((t, i) => (t && t.side !== 'n' && !t.support && t.team === team ? i : -1))
          .filter((i) => i >= 0),
        remaining = new Set(members),
        ci = members.find((i) => q.g[i].core);
      if (ci !== undefined) for (const i of flood(q, ci, team)) remaining.delete(i);
      while (remaining.size) {
        const start = remaining.values().next().value,
          part = [...flood(q, start, team)];
        for (const i of part) remaining.delete(i);
        let newTeam = ci !== undefined || remaining.size ? 'loose-' + q.serial++ : team;
        if (part.length >= 4 && (q.g[start].side !== 'e' || enemySlots(q) > 0)) {
          const large = part.reduce((a, i) => (q.g[i].n > q.g[a].n ? i : a), part[0]);
          q.g[large].core = true;
          if (q.g[large].side === 'e') q.g[large].n = Math.max(8, q.g[large].n);
          newTeam = q.g[large].id;
          created++;
          log(q, `${q.g[large].side === 'p' ? '己方' : '敌方'}离体小队分化 · ${q.g[large].n} 核心`);
        }
        for (const i of part) q.g[i].team = newTeam;
      }
    }
    if (coreIndex(q) < 0 || q.g[coreIndex(q)]?.side !== 'p') q.active = cores(q, 'p')[0]?.id ?? null;
    if (created) rescale(q);
    return created;
  }
  function neutralClusters(q) {
    const CLUSTER_MIN = 3;
    const visited = new Set();
    let dense = 0;
    for (let start = 0; start < N * N; start++) {
      if (q.g[start]?.side !== 'n' || visited.has(start)) continue;
      const component = [start];
      visited.add(start);
      for (let k = 0; k < component.length; k++)
        for (const d in dirs) {
          const j = neighbor(component[k], d);
          if (j >= 0 && q.g[j]?.side === 'n' && !visited.has(j)) {
            visited.add(j);
            component.push(j);
          }
        }
      if (component.length >= CLUSTER_MIN) {
        const key = 'dense-' + q.serial++;
        for (const i of component) q.g[i].nc = key;
        dense++;
      } else for (const i of component) delete q.g[i].nc;
    }
    return dense;
  }
  function outlineKey(t) {
    return !t ? null : t.side === 'n' ? (t.nc ? 'n:' + t.nc : null) : t.side + ':' + t.team;
  }
  function boundaryEdges(q, indices) {
    const segments = [];
    for (const i of indices) {
      const key = outlineKey(q.g[i]);
      if (!key) continue;
      for (const d in dirs) {
        const j = neighbor(i, d);
        if (j < 0 || outlineKey(q.g[j]) !== key) segments.push({ i, d, key });
      }
    }
    return segments;
  }
