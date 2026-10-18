// ==== 95-input ====
// 来源: main.script.js 第 149–160 行（阶段 3 改过：移除旧档导入，见项目文档 §16）
// 指针/键盘/对话框接线、教程与介绍
  const tutorialHTML = new TextDecoder('utf-8').decode(
    Uint8Array.from(atob('__TUTORIAL_B64__'), (c) => c.charCodeAt(0)),
  );
  let tutorialLoaded = false,
    tutorialMemory = null;
  function closeTutorial() {
    if ($('tutorialDialog').open) $('tutorialDialog').close();
    canvas.focus({ preventScroll: true });
  }
  $('showTutorial').onclick = () => {
    if (drag) cancelDrag();
    clearPreview();
    save();
    if (!tutorialLoaded) {
      let stored = tutorialMemory;
      try {
        stored = localStorage.getItem('core-tutorial-v1') || stored;
      } catch {}
      const seed = stored
        ? btoa(Array.from(new TextEncoder().encode(stored), (b) => String.fromCharCode(b)).join(''))
        : '';
      $('tutorialFrame').srcdoc = tutorialHTML.replace('__TUTORIAL_SAVE_SEED__', seed);
      tutorialLoaded = true;
    }
    $('tutorialDialog').showModal();
  };
  $('closeTutorial').onclick = closeTutorial;
  window.addEventListener('message', (e) => {
    if (e.source !== $('tutorialFrame').contentWindow) return;
    const msg = e.data;
    if (msg?.type === 'core-tutorial-return') {
      closeTutorial();
      return;
    }
    if (msg?.type !== 'core-tutorial-save' || typeof msg.value !== 'string' || msg.value.length > 12000000) return;
    try {
      const data = JSON.parse(msg.value);
      if (!valid(data.s) || !Number.isInteger(data.s.lesson) || data.s.lesson < 0 || data.s.lesson > 6) return;
      tutorialMemory = msg.value;
      try {
        localStorage.setItem('core-tutorial-v1', msg.value);
      } catch {}
    } catch {}
  });
  $('showGuide').onclick = () => {
    clearPreview();
    $('guideFrame').srcdoc = guideHTML;
    $('guideDialog').showModal();
  };
  $('closeGuide').onclick = () => $('guideDialog').close();
  $('continueGoal').onclick = () => {
    s.goalChoice = 'continue';
    s.settled = false;
    $('goalDialog').close();
    save();
    ui();
    say('2048只是起点，继续挑战！');
  };
  $('settleGoal').onclick = () => {
    s.goalChoice = 'settle';
    s.settled = true;
    $('goalDialog').close();
    save();
    ui();
  };
  $('goalDialog').addEventListener('cancel', (e) => e.preventDefault());
  $('resume').onclick = () => {
    s.settled = false;
    s.goalChoice = 'continue';
    save();
    ui();
  };
  $('undo').onclick = undo;
  $('endUndo').onclick = undo;
  const restart = () => {
    clearPreview();
    $('dialog').showModal();
  };
  $('restart').onclick = restart;
  $('endRestart').onclick = restart;
  $('cancel').onclick = () => $('dialog').close();
  $('confirm').onclick = () => {
    $('dialog').close();
    reset();
  };
  window.addEventListener('keydown', (e) => {
    if (
      $('dialog').open ||
      $('goalDialog').open ||
      $('guideDialog').open ||
      $('tutorialDialog').open ||
      $('techDialog').open ||
      e.ctrlKey ||
      e.altKey ||
      e.metaKey
    )
      return;
    const k = e.key.toLowerCase(),
      d = {
        w: 'up',
        arrowup: 'up',
        s: 'down',
        arrowdown: 'down',
        a: 'left',
        arrowleft: 'left',
        d: 'right',
        arrowright: 'right',
      }[k];
    if (d || ['escape', 'z'].includes(k)) {
      e.preventDefault();
      if (e.repeat) return;
      if (drag) {
        if (k === 'escape') {
          cancelDrag();
          setMode('main');
        }
        return;
      }
      if (d) {
        if (e.shiftKey && mode === 'main') showPreview(d);
        else act(d);
      } else if (k === 'z') undo();
      else {
        selected = null;
        setMode('main');
      }
    }
  });
  window.addEventListener('keyup', (e) => {
    if (e.key === 'Shift' && preview) clearPreview();
  });
  window.addEventListener('blur', () => {
    if (drag) cancelDrag();
    if (preview) clearPreview();
  });
  function valid(q) {
    return (
      q &&
      Array.isArray(q.g) &&
      q.g.length === N * N &&
      q.g.every(
        (t) =>
          !t ||
          (Number.isFinite(t.n) &&
            t.n >= 2 &&
            Number.isInteger(Math.log2(t.n)) &&
            ['p', 'e', 'n'].includes(t.side) &&
            Number.isFinite(t.hp) &&
            t.hp > 0 &&
            t.hp <= t.cap),
      ) &&
      Array.isArray(q.logs) &&
      Number.isInteger(q.ap) &&
      q.ap >= 0 &&
      (q.dead || q.g.some((t) => t?.core && t.side === 'p' && t.id === q.active))
    );
  }
  try {
    const current = localStorage.getItem(KEY),
      data = JSON.parse(current);
    if (data && valid(data.s)) {
      s = data.s;
      history = decodeHistory(data);
      neutralClusters(s);
      for (const prior of history) neutralClusters(prior);
      ui();
      say('已恢复远征存档。');
    } else reset();
  } catch {
    reset();
  }
  function frame() {
    if (effects.length) draw();
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
