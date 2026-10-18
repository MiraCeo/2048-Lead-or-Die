// ==== 70-turn ====
// 溯源: 阶段 2 的压缩文本 main.script.js 第 94–105 行（此后经阶段 3 改名、阶段 4 格式化）
// worldStep 回合循环、camera/屏幕映射
  function techInfoAt(line, lv) {
    if (line === 'tp') return '每块每回合吸收 ' + absorbTpAt(lv) + ' 个';
    if (line === 'radius') {
      const r = siteRadiusAt(lv);
      return '覆盖 ' + ((2 * r + 1) * (2 * r + 1) - 1) + ' 格 · 站点吞吐 ' + siteBudgetAt(lv) + '/回合';
    }
    return '阈值 ' + absorbThresholdAt(lv) + ' · 可自动长到 ' + 2 * absorbThresholdAt(lv);
  }
  function techUI() {
    const t = $('tech');
    if (t) t.textContent = (s.tech || 0) + ' 点';
    const cb = $('convertScore');
    if (cb) cb.onclick = techConvert;
    const box = $('techTree');
    if (!box) return;
    const mk = (line, label) => {
      const lv = techLevel(s, line),
        max = techMax(line);
      const row = document.createElement('div');
      row.className = 'tech-row';
      const info = document.createElement('div');
      info.className = 'tech-info';
      const name = document.createElement('strong');
      name.textContent = label + ' ' + lv + ' / ' + max;
      const eff = document.createElement('span');
      const b = document.createElement('button');
      if (lv >= max) {
        eff.textContent = techInfoAt(line, lv) + '（已满级）';
        b.textContent = '已满级';
        b.disabled = true;
      } else {
        const cost = techCost(line, lv);
        eff.textContent = techInfoAt(line, lv) + ' → ' + techInfoAt(line, lv + 1);
        b.textContent = '升级 ' + cost + ' 点';
        b.disabled = (s.tech || 0) < cost;
      }
      info.appendChild(name);
      info.appendChild(eff);
      b.onclick = () => techBuy(line);
      row.appendChild(info);
      row.appendChild(b);
      return row;
    };
    box.replaceChildren(mk('threshold', '自动合成阈值'), mk('tp', '吸收吞吐'), mk('radius', '收集半径'));
  }
  function openTech() {
    const d = $('techDialog');
    if (d) d.showModal();
  }
  function closeTech() {
    const d = $('techDialog');
    if (d) d.close();
    if (canvas) canvas.focus({ preventScroll: true });
  }
  $('openTech') && ($('openTech').onclick = openTech);
  $('closeTech') && ($('closeTech').onclick = closeTech);
  function growFighters(q) {
    let count = 0,
      top = 0;
    for (const t of q.g) {
      if (!t?.core || t.side !== 'e' || t.kind !== 'fighter') continue;
      if (t.nextGrowth === undefined) t.nextGrowth = q.turn + 40;
      if (q.turn >= t.nextGrowth) {
        t.n *= 2;
        t.nextGrowth += 40;
        count++;
        if (t.n > top) top = t.n;
      }
    }
    if (count) {
      log(q, `敌机成长 · ${count} 架核心翻倍（最高 ${fmt(top)}）`);
      rescale(q);
    }
    return count;
  }
  function swapStep(q, first, second) {
    if (q.dead || q.settled) return { error: '本局已停止，请撤销或继续挑战。' };
    if (q.ap < 1) return { error: '行动点不足，置换需要1点。' };
    if (first === second) return { error: '请选两个不同的方块。' };
    const a = q.g.findIndex((t) => t?.id === first),
      b = q.g.findIndex((t) => t?.id === second),
      cam = camera(q);
    if (a < 0 || b < 0 || !visible(a, cam) || !visible(b, cam)) return { error: '只能置换当前视野内的方块。' };
    if ([q.g[a], q.g[b]].some((t) => t.side !== 'p' || t.core || t.support))
      return { error: '只能置换两个己方非核心方块。' };
    [q.g[a], q.g[b]] = [q.g[b], q.g[a]];
    q.ap--;
    const splits = normalize(q);
    rescale(q);
    checkGoal(q);
    if (splits) log(q, `两块位置互换触发分化 · ${splits} 个新核心`);
    return { splits };
  }
  function performSwap(first, second) {
    const q = copy(s),
      r = swapStep(q, first, second);
    if (r.error) {
      say(r.error);
      draw();
      return false;
    }
    remember();
    s = q;
    selected = null;
    mode = 'main';
    preview = null;
    effects = [];
    save();
    ui();
    say('拖动置换完成 · 行动点 −1 · 已返回主体操作，世界时间不变。');
    return true;
  }
  function worldStep(q, dir) {
    if (q.dead || q.settled) return null;
    const fx = [];
    const r = moveMain(q, dir, q.active, fx);
    if (!r) return null;
    q.turn++;
    const earned = q.turn % 2 === 0 ? 1 : 0;
    q.ap += earned;
    if (!q.dead) autoCollect(q, fx);
    if (!q.dead) growFighters(q);
    const playerShots = fire(q, 'p', fx);
    let enemyShots = 0,
      enemyMoves = 0;
    if (!q.dead && q.turn % 2 === 0) enemyMoves = ai(q);
    if (!q.dead) enemyShots = fire(q, 'e', fx, (t) => q.turn % 2 === 0 || teamCore(q, t.team)?.kind === 'bunker');
    let supply = { inside: 0, outside: 0 };
    if (!q.dead) {
      normalize(q);
      if (q.turn % 10 === 0) replenish(q);
      if (q.turn === q.nextWave) reinforce(q);
      if (q.turn >= (q.nextSupport ?? 20)) {
        spawnSupport(q);
        q.nextSupport = q.turn + 20;
      }
      if (q.nextWave - q.turn === 5) {
        const spec = waveSpec(q.wave + 1);
        log(q, `增援预告：5回合后，${Math.min(spec.count, enemySlots(q))} 个单位（最多6队），core=${spec.n}`);
      }
      supply = spawn(q);
      q.lastFocus = coreIndex(q) >= 0 ? coreIndex(q) : q.lastFocus;
    }
    if (q.dead) log(q, '所有己方核心已失去，远征结束。');
    return { ...r, earned, fx, playerShots, enemyShots, enemyMoves, supply };
  }
  function camera(q) {
    const i = coreIndex(q) >= 0 ? coreIndex(q) : q.lastFocus;
    return {
      r: Math.max(0, Math.min(N - V, Math.floor(i / N) - Math.floor(V / 2))),
      c: Math.max(0, Math.min(N - V, (i % N) - Math.floor(V / 2))),
    };
  }
  function screenPoint(i, cam) {
    return { x: X + ((i % N) - cam.c) * C + C / 2, y: Y + (Math.floor(i / N) - cam.r) * C + C / 2 };
  }
  function visible(i, cam) {
    return Math.floor(i / N) >= cam.r && Math.floor(i / N) < cam.r + V && i % N >= cam.c && i % N < cam.c + V;
  }
