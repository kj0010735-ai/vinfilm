// ON SET 런다운 자동 진행 — 연출석 화면(런다운 ?director · 촬영 진행 ?all)에서만 실행
// 1) 계획 시각이 되면 단계를 자동으로 "진행 중"으로 (앞 단계가 시간을 넘겨 아직 진행 중이면 기다림, 15분 넘으면 넘어감)
// 2) 끝내기는 사람이 누름. 다음 단계가 시작되면 겹치지 않는 앞 단계는 자동으로 끝냄
// 3) 촬영 진행에서 테이크를 고르면 그 테이크가 들어 있는 본 촬영 블록을 시작
(function () {
  if (!window.firebase || !window.DAY) return;
  const db = firebase.firestore();
  const base = new Date(DAY.date + 'T00:00:00+09:00').getTime();
  const GRACE = 15 * 60000;
  const at = hm => { const [h, m] = hm.split(':').map(Number); return base + (h * 60 + m) * 60000; };
  let items = DAY.items, ph = null, lastTake = null, busy = false;
  const main = () => items.filter(x => !x.late).map(x => ({ ...x, ps: at(x.t), pe: at(x.t) + x.d * 60000 }));
  const dayRef = db.doc('live/mv1023day');
  db.doc('live/mv1023plan').onSnapshot(s => { const d = s.data(); if (d && Array.isArray(d.items) && d.items.length) items = d.items; }, () => {});
  dayRef.onSnapshot(s => { ph = (s.data() || {}).ph || {}; }, () => {});
  function start(id, when) {
    const M = main(), x = M.find(y => y.id === id); if (!x || !ph || (ph[id] && ph[id].s)) return;
    const upd = { [id]: { s: when } };
    for (const y of M) { const q = ph[y.id]; if (q && q.s && !q.e && y.id !== id && y.pe <= x.ps) upd[y.id] = { s: q.s, e: when }; }
    busy = true; dayRef.set({ ph: upd, at: Date.now() }, { merge: true }).finally(() => { busy = false; });
  }
  function tick() {
    if (!ph || busy) return;
    const now = Date.now(), M = main();
    for (const x of M) {
      if (ph[x.id] && ph[x.id].s) continue;           // 이미 시작
      if (x.ps > now) break;                          // 아직 시간 안 됨
      const preds = M.filter(y => y.pe <= x.ps);       // 이 단계보다 먼저 끝나야 하는 단계
      const run = preds.filter(y => ph[y.id] && ph[y.id].s && !ph[y.id].e);
      // 앞 단계가 시간 초과로 진행 중이면 기다림 — 단, 15분 넘게 아무도 안 누르면 깜빡한 걸로 보고 넘어감
      if (run.length && now - x.ps < GRACE) break;
      const ends = preds.map(y => ph[y.id] && ph[y.id].e).filter(Boolean);
      start(x.id, Math.max(x.ps, ...ends, 0) > now ? now : Math.max(x.ps, ...ends));
      return;                                         // 한 번에 하나씩
    }
  }
  db.doc('live/mv1023take').onSnapshot(s => {
    const d = s.data(), tk = d && d.take || '';
    if (lastTake === null) { lastTake = tk; return; }  // 처음 불러온 값은 무시
    if (!tk) return; const d2 = { take: tk };
    if (d2.take === lastTake) return; lastTake = d2.take;
    const x = main().find(y => (y.takes || []).includes(d2.take)); if (x && ph && !(ph[x.id] && ph[x.id].s)) start(x.id, Date.now());
  }, () => {});
  setInterval(tick, 5000); setTimeout(tick, 1500);
})();
