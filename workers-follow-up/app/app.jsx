/* ============================================================
   Claude Squad — App root (state, simulation, routing)  →  #root
   ============================================================ */
const { useState, useEffect, useRef, useCallback } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#8686d4",
  "density": "comfortable",
  "ticketLayout": "board",
  "liveData": true,
  "refreshSeconds": 2,
  "glow": true
}/*EDITMODE-END*/;

function Toasts({ items, onDismiss }) {
  return (
    <div style={{ position: 'fixed', bottom: 18, right: 18, zIndex: 120, display: 'flex', flexDirection: 'column', gap: 8 }}>
      {items.map(t => (
        <div key={t.id} className="fade-up" style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', minWidth: 240, maxWidth: 360,
          borderRadius: 'var(--radius-lg)', background: 'var(--surface-container-high)', border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-lg)'
        }}>
          <Icon name={t.icon || 'check_circle'} size={18} style={{ color: t.tone || 'var(--success)' }} fill />
          <span className="font-body fg-1" style={{ fontSize: 12.5, flex: 1, lineHeight: 1.4 }}>{t.text}</span>
          <button className="btn btn-icon" style={{ width: 24, height: 24, border: 'none' }} onClick={() => onDismiss(t.id)}><Icon name="close" size={14} /></button>
        </div>
      ))}
    </div>
  );
}

function AttachModal({ worker, tickets, onClose, onSubmit }) {
  const open = tickets.filter(t => ['open', 'in-progress'].includes(t.status) && !window.isWorkerActive(window.workerByName(window.CSQ.workers, t.assigned_to)));
  const [sel, setSel] = useState(null);
  return (
    <ModalShell title={'Associer un ticket à ' + worker.name} icon="add_link" onClose={onClose}
      footer={<React.Fragment><button className="btn" onClick={onClose}>Annuler</button>
        <button className="btn btn-primary" disabled={!sel} onClick={() => onSubmit(worker, sel)}><Icon name="check" size={16} /> Associer</button></React.Fragment>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {open.length === 0 ? <p className="font-body fg-3" style={{ fontSize: 13 }}>Aucun ticket disponible.</p> : open.map(t => (
          <button key={t.id} onClick={() => setSel(t.id)} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 'var(--radius-md)', cursor: 'pointer', textAlign: 'left',
            background: sel === t.id ? 'color-mix(in srgb, var(--primary) 10%, transparent)' : 'var(--surface-container-high)',
            border: '1px solid ' + (sel === t.id ? 'var(--border-accent)' : 'var(--border-hairline)')
          }}>
            <span className="font-mono fg-4" style={{ fontSize: 11 }}>{t.id}</span>
            <span className="font-body fg-1" style={{ fontSize: 13, flex: 1 }}>{t.title}</span>
            <StatusBadge kind={t.status} type="ticket" />
          </button>
        ))}
      </div>
    </ModalShell>
  );
}

function toDate(value) {
  return value instanceof Date ? value : new Date(value || Date.now());
}

function hydrateWorker(worker) {
  return {
    ...worker,
    created_at: toDate(worker.created_at),
    last_activity_at: toDate(worker.last_activity_at),
  };
}

function hydrateTicket(ticket) {
  return {
    ...ticket,
    created_at: toDate(ticket.created_at),
    updated_at: toDate(ticket.updated_at),
    history: (ticket.history || []).map(item => ({ ...item, t: toDate(item.t || item.timestamp) })),
    comments: (ticket.comments || []).map(item => ({ ...item, t: toDate(item.t || item.timestamp) })),
    labels: ticket.labels || [],
  };
}

function hydrateLogsMap(logs) {
  const out = {};
  Object.entries(logs || {}).forEach(([id, lines]) => {
    out[id] = (lines || []).map(line => ({ ...line, time: toDate(line.time) }));
  });
  return out;
}

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [theme, setTheme] = useState(() => localStorage.getItem('csq-theme') || 'dark');
  const [view, setView] = useState('dashboard');
  const [workers, setWorkers] = useState(() => window.CSQ.workers.map(w => ({ ...w })));
  const [tickets, setTickets] = useState(() => window.CSQ.tickets.map(tk => ({ ...tk })));
  const [logsMap, setLogsMap] = useState(() => {
    const m = {};
    window.CSQ.workers.forEach(w => { m[w.id] = window.CSQ.seedLogs(w); });
    return m;
  });
  const [openWorkerId, setOpenWorkerId] = useState(null);
  const [openTicketId, setOpenTicketId] = useState(null);
  const [modal, setModal] = useState(null);
  const [selLogId, setSelLogId] = useState('w_nova');
  const [toasts, setToasts] = useState([]);
  const [, setTick] = useState(0);
  const [lastRefresh, setLastRefresh] = useState('Maj ' + window.CSQ.fmtClock(new Date()));
  const [apiConnected, setApiConnected] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(() => localStorage.getItem('csq-notifications') === '1' && 'Notification' in window && Notification.permission === 'granted');
  const refreshInFlight = useRef(false);
  const previousWorkerStatuses = useRef(new Map());
  const apiLoadedOnce = useRef(false);
  const lineId = useRef(1000);
  const mountAt = useRef(Date.now());
  const firedRef = useRef({});

  // theme
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.documentElement.classList.toggle('light', theme === 'light');
    localStorage.setItem('csq-theme', theme);
  }, [theme]);

  // accent override
  useEffect(() => {
    if (t.accent) document.documentElement.style.setProperty('--primary', t.accent);
  }, [t.accent]);

  // toast helper
  const toast = useCallback((text, icon, tone) => {
    const id = Math.random().toString(36).slice(2);
    setToasts(ts => [...ts, { id, text, icon, tone }]);
    setTimeout(() => setToasts(ts => ts.filter(x => x.id !== id)), 3600);
  }, []);

  const notifyWorkerDone = useCallback((worker) => {
    const ok = worker.status === 'done';
    const title = ok ? 'Worker terminé' : 'Worker sorti';
    const detail = worker.ticket_id ? `${worker.name} · ${worker.ticket_id}` : worker.name;
    toast(`${title} : ${detail}`, ok ? 'check_circle' : 'logout', ok ? 'var(--success)' : 'var(--warn)');

    if (!notificationsEnabled || !('Notification' in window) || Notification.permission !== 'granted') return;
    const petIcon = new URL('/assets/claude-pet-icon.png', window.location.origin).href;
    const notification = new Notification(title, {
      body: detail,
      icon: petIcon,
      badge: petIcon,
      tag: `claude-squad-${worker.id}-${worker.status}`,
      silent: false,
    });
    notification.onclick = () => {
      window.focus();
      setOpenWorkerId(worker.id);
      setOpenTicketId(null);
      notification.close();
    };
  }, [notificationsEnabled, toast]);

  const notifyWorkerWaiting = useCallback((worker) => {
    const detail = worker.ticket_id ? `${worker.name} · ${worker.ticket_id}` : worker.name;
    const rawQuestion = worker.waiting_question || worker.output || '';
    // Cap the notification body so a long question doesn't run on (the OS
    // truncates silently anyway, but a clean ellipsis reads better).
    const question = rawQuestion.length > 120 ? rawQuestion.slice(0, 119).trimEnd() + '…' : rawQuestion;
    toast(`Worker en attente : ${detail}`, 'pending', 'var(--warn)');

    if (!notificationsEnabled || !('Notification' in window) || Notification.permission !== 'granted') return;
    const petIcon = new URL('/assets/claude-pet-icon.png', window.location.origin).href;
    const notification = new Notification('Worker en attente', {
      body: question ? `${detail} — ${question}` : detail,
      icon: petIcon,
      badge: petIcon,
      tag: `claude-squad-${worker.id}-waiting`,
      silent: false,
    });
    notification.onclick = () => {
      window.focus();
      setOpenWorkerId(worker.id);
      setOpenTicketId(null);
      notification.close();
    };
  }, [notificationsEnabled, toast]);

  const trackWorkerTransitions = useCallback((nextWorkers) => {
    const previous = previousWorkerStatuses.current;
    const finalStatuses = new Set(['done', 'exited']);
    const activeStatuses = new Set(['running', 'waiting', 'blocked']);

    if (apiLoadedOnce.current) {
      nextWorkers.forEach(worker => {
        const oldStatus = previous.get(worker.id);
        if (oldStatus && activeStatuses.has(oldStatus) && finalStatuses.has(worker.status)) {
          notifyWorkerDone(worker);
        }
        // A worker entering "waiting" needs the lead's attention -> notify.
        if (oldStatus && oldStatus !== 'waiting' && worker.status === 'waiting') {
          notifyWorkerWaiting(worker);
        }
      });
    }

    previousWorkerStatuses.current = new Map(nextWorkers.map(worker => [worker.id, worker.status]));
    apiLoadedOnce.current = true;
  }, [notifyWorkerDone, notifyWorkerWaiting]);

  async function enableNotifications() {
    if (!('Notification' in window)) {
      toast('Notifications navigateur non disponibles', 'block', 'var(--warn)');
      return;
    }
    if (Notification.permission === 'granted') {
      localStorage.setItem('csq-notifications', '1');
      setNotificationsEnabled(true);
      toast('Notifications activées', 'notifications_active', 'var(--success)');
      return;
    }
    const permission = await Notification.requestPermission();
    const enabled = permission === 'granted';
    localStorage.setItem('csq-notifications', enabled ? '1' : '0');
    setNotificationsEnabled(enabled);
    toast(enabled ? 'Notifications activées' : 'Notifications refusées', enabled ? 'notifications_active' : 'block', enabled ? 'var(--success)' : 'var(--warn)');
  }

  const loadApiState = useCallback(async ({ quiet = false } = {}) => {
    if (refreshInFlight.current) return false;
    refreshInFlight.current = true;
    try {
      const res = await fetch('/api/state', { cache: 'no-store' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const payload = await res.json();
      const nextWorkers = (payload.workers || []).map(hydrateWorker);
      const nextTickets = (payload.tickets || []).map(hydrateTicket);
      const nextLogs = hydrateLogsMap(payload.logs || {});
      trackWorkerTransitions(nextWorkers);
      setWorkers(nextWorkers);
      setTickets(nextTickets);
      setLogsMap(nextLogs);
      setApiConnected(true);
      setLastRefresh('Maj ' + window.CSQ.fmtClock(new Date(payload.generated_at || Date.now())));
      if (!quiet) toast('Données locales rafraîchies', 'refresh', 'var(--primary)');
      return true;
    } catch (err) {
      setApiConnected(false);
      if (!quiet) toast('API locale indisponible, données mockées conservées', 'cloud_off', 'var(--warn)');
      return false;
    } finally {
      refreshInFlight.current = false;
    }
  }, [toast, trackWorkerTransitions]);

  const appendLog = useCallback((wid, entries) => {
    setLogsMap(m => {
      const cur = m[wid] || [];
      const add = entries.map(e => ({ id: 'l' + (lineId.current++), time: new Date(), kind: e[0], text: e[1] }));
      const next = [...cur, ...add];
      return { ...m, [wid]: next.length > 600 ? next.slice(next.length - 600) : next };
    });
  }, []);

  // 1s clock tick (refresh relative times)
  useEffect(() => {
    const iv = setInterval(() => setTick(x => x + 1), 1000);
    return () => clearInterval(iv);
  }, []);

  // load real local data when served by workers-follow-up/server.py
  useEffect(() => {
    loadApiState({ quiet: true });
  }, [loadApiState]);

  useEffect(() => {
    if (!apiConnected || !t.liveData) return;
    const intervalMs = Math.max(1000, Number(t.refreshSeconds || 2) * 1000);
    const iv = setInterval(() => loadApiState({ quiet: true }), intervalMs);
    return () => clearInterval(iv);
  }, [apiConnected, t.liveData, t.refreshSeconds, loadApiState]);

  useEffect(() => {
    if (!apiConnected || !t.liveData) return;
    const onVisible = () => {
      if (document.visibilityState === 'visible') loadApiState({ quiet: true });
    };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', onVisible);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', onVisible);
    };
  }, [apiConnected, t.liveData, loadApiState]);

  // live simulation
  useEffect(() => {
    if (!t.liveData || apiConnected) return;
    const iv = setInterval(() => {
      const elapsed = (Date.now() - mountAt.current) / 1000;

      // scripted: a waiting worker appears (~16s) — vega asks a question
      if (elapsed > 16 && !firedRef.current.vegaWait) {
        firedRef.current.vegaWait = true;
        setWorkers(prev => prev.map(w => w.id === 'w_vega' ? {
          ...w, status: 'waiting', last_activity_at: new Date(),
          output: 'Dois-je supprimer les usages de legacy_token maintenant, ou créer un ticket dédié ?',
          waiting_question: 'Retirer legacy_token dans cette session, ou ouvrir un ticket de tech-debt séparé ?'
        } : w));
        appendLog('w_vega', [['warn', '⏸  Question à l\'orchestrateur : retirer legacy_token ou ouvrir un ticket ?']]);
        toast('vega attend une réponse', 'pending', 'var(--warn)');
      }

      // stream lines into running workers + bump activity
      setWorkers(prev => prev.map(w => {
        if (w.status !== 'running') return w;
        const line = window.CSQ.nextStreamLine(w);
        appendLog(w.id, [[line.kind, line.text]]);
        return { ...w, last_activity_at: new Date(), output: line.text };
      }));
    }, 2400);
    return () => clearInterval(iv);
  }, [t.liveData, apiConnected, appendLog, toast]);

  // ── Actions ───────────────────────────────────────────────
  const openWorker = (w) => { setOpenWorkerId(w.id); setOpenTicketId(null); };
  const openTicket = (id) => { setOpenTicketId(id); setOpenWorkerId(null); };

  async function handleWorkerAction(type, p) {
    const w = p.worker;
    if (type === 'respond') {
      appendLog(w.id, [['cmd', '> ' + p.text], ['ok', '✓ Réponse reçue, reprise du traitement…']]);
      setWorkers(prev => prev.map(x => x.id === w.id ? { ...x, status: 'running', last_activity_at: new Date(), output: 'Reprise après réponse : ' + p.text.slice(0, 48) } : x));
      if (w.ticket_id) setTickets(prev => prev.map(tk => tk.id === w.ticket_id ? { ...tk, status: 'in-progress', updated_at: new Date(), history: [...tk.history, { t: new Date(), who: 'eric', text: 'Réponse fournie au worker. Statut → En cours.' }] } : tk));
      toast('Réponse envoyée à ' + w.name, 'reply', 'var(--primary)');
    } else if (type === 'send') {
      appendLog(w.id, [['cmd', '> ' + p.text]]);
      toast('Message envoyé à ' + w.name, 'send', 'var(--primary)');
    } else if (type === 'kill') {
      // In-process Agent Teams workers (killable === false) have no tmux pane to
      // kill; short-circuit before hitting the API. Absent field stays killable
      // so the legacy tmux path is unaffected pre-integration.
      if (w.killable === false) {
        toast(w.name + ' tourne in-process (Agent Teams) — pas de session à tuer', 'block', 'var(--warn)');
        return;
      }
      try {
        const res = await fetch('/api/workers/' + encodeURIComponent(w.session || w.name) + '/kill', { method: 'POST' });
        const payload = await res.json().catch(() => ({}));
        if (!res.ok || !payload.ok) throw new Error(payload.error || 'kill failed');
        appendLog(w.id, [['err', '✕ SIGTERM — session terminée par l\'orchestrateur.']]);
        setWorkers(prev => prev.filter(x => x.id !== w.id));
        setOpenWorkerId(null);
        toast(w.name + ' arrêté', 'stop_circle', 'var(--danger)');
        loadApiState({ quiet: true });
      } catch (err) {
        toast('Impossible de tuer ' + w.name + ' : ' + (err.message || err), 'block', 'var(--danger)');
      }
    } else if (type === 'restart') {
      appendLog(w.id, [['cmd', '$ tmux respawn ' + w.session], ['info', 'Session relancée.']]);
      setWorkers(prev => prev.map(x => x.id === w.id ? { ...x, status: 'running', exit_code: null, last_activity_at: new Date(), output: 'Session relancée.' } : x));
      toast(w.name + ' relancé', 'restart_alt', 'var(--success)');
    } else if (type === 'ticket-status') {
      setTickets(prev => prev.map(tk => tk.id === w.ticket_id ? { ...tk, status: p.status, updated_at: new Date(), history: [...tk.history, { t: new Date(), who: w.name, text: 'Statut → ' + window.CSQ.TICKET_STATUS[p.status].label }] } : tk));
      toast(w.ticket_id + ' → ' + window.CSQ.TICKET_STATUS[p.status].label, window.CSQ.TICKET_STATUS[p.status].icon);
    } else if (type === 'attach') {
      setModal({ type: 'attach', worker: w });
    }
  }

  function handleTicketAction(type, p) {
    if (type === 'set-status') {
      setTickets(prev => prev.map(tk => tk.id === p.ticket.id ? { ...tk, status: p.status, updated_at: new Date(), history: [...tk.history, { t: new Date(), who: 'eric', text: 'Statut → ' + window.CSQ.TICKET_STATUS[p.status].label }] } : tk));
      toast(p.ticket.id + ' → ' + window.CSQ.TICKET_STATUS[p.status].label, window.CSQ.TICKET_STATUS[p.status].icon);
    }
  }

  function createTicket(data) {
    const num = Math.max(...tickets.map(t => parseInt(t.id.split('-')[1]))) + 1;
    const id = 'CSQ-' + num;
    const tk = { id, title: data.title, body: data.body || 'Aucune description.', status: 'open', assigned_to: null, priority: data.priority, labels: data.labels, created_at: new Date(), updated_at: new Date(), history: [{ t: new Date(), who: 'eric', text: 'Ticket créé.' }], comments: [] };
    setTickets(prev => [tk, ...prev]);
    setModal(null); setView('tickets');
    toast(id + ' créé', 'add_task');
  }

  function assignTicket(ticket, workerName) {
    if (workerName === '__new__') {
      const n = 'agent-' + Math.random().toString(36).slice(2, 5);
      const nw = { id: 'w_' + n, name: n, agent: Math.random() > 0.5 ? 'codex' : 'claude', session: 'csq:' + n, status: 'running', role: 'Auto', ticket_id: ticket.id, created_at: new Date(), last_activity_at: new Date(), exit_code: null, output: 'Worker démarré sur ' + ticket.id };
      setWorkers(prev => [...prev, nw]);
      setLogsMap(m => ({ ...m, [nw.id]: window.CSQ.seedLogs(nw) }));
      setTickets(prev => prev.map(tk => tk.id === ticket.id ? { ...tk, status: 'in-progress', assigned_to: n, updated_at: new Date(), history: [...tk.history, { t: new Date(), who: 'eric', text: 'Nouveau worker ' + n + ' lancé.' }] } : tk));
      toast('Worker ' + n + ' lancé sur ' + ticket.id, 'rocket_launch');
    } else {
      setWorkers(prev => prev.map(w => w.name === workerName ? { ...w, ticket_id: ticket.id, status: 'running', last_activity_at: new Date() } : w));
      setTickets(prev => prev.map(tk => tk.id === ticket.id ? { ...tk, status: 'in-progress', assigned_to: workerName, updated_at: new Date(), history: [...tk.history, { t: new Date(), who: 'eric', text: workerName + ' assigné au ticket.' }] } : tk));
      toast(workerName + ' assigné à ' + ticket.id, 'person_add');
    }
    setModal(null);
  }

  function attachTicketToWorker(worker, ticketId) {
    setWorkers(prev => prev.map(w => w.id === worker.id ? { ...w, ticket_id: ticketId } : w));
    setTickets(prev => prev.map(tk => tk.id === ticketId ? { ...tk, status: 'in-progress', assigned_to: worker.name, updated_at: new Date(), history: [...tk.history, { t: new Date(), who: 'eric', text: worker.name + ' associé au ticket.' }] } : tk));
    setModal(null);
    toast(ticketId + ' associé à ' + worker.name, 'add_link');
  }

  function respondTo(w) { openWorker(w); }
  function refresh() {
    if (!apiConnected) {
      loadApiState();
      return;
    }
    loadApiState();
  }

  // counts for sidebar
  const counts = {
    waiting: workers.filter(w => w.status === 'waiting').length,
    blocked: workers.filter(w => w.status === 'blocked').length,
    activeWorkers: workers.filter(w => ['running', 'waiting', 'blocked'].includes(w.status)).length,
    totalWorkers: workers.length,
    openTickets: tickets.filter(t => t.status !== 'done').length,
  };
  const online = workers.filter(w => ['running', 'waiting', 'blocked'].includes(w.status)).length;
  const openWorker_ = workers.find(w => w.id === openWorkerId) || null;
  const openTicket_ = tickets.find(tk => tk.id === openTicketId) || null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <TopNav clock={lastRefresh} online={online} theme={theme} onToggleTheme={() => setTheme(th => th === 'dark' ? 'light' : 'dark')} onRefresh={refresh} lastRefresh={lastRefresh} live={apiConnected && t.liveData} refreshSeconds={t.refreshSeconds || 2} notificationsEnabled={notificationsEnabled} onEnableNotifications={enableNotifications} />
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <Sidebar view={view} setView={setView} counts={counts} onCreate={() => setModal({ type: 'create' })} />
        <main className="scroll app-bg" style={{ flex: 1, minWidth: 0, overflowY: 'auto', position: 'relative' }}>
          {t.glow ? <div className="glow" style={{ top: -180, right: -120 }}></div> : null}
          <div style={{ position: 'relative', zIndex: 1, padding: '22px 26px 40px', maxWidth: 1480, margin: '0 auto' }}>
            {view === 'dashboard' && <Dashboard workers={workers} tickets={tickets} onOpenWorker={openWorker} onRespond={respondTo} onOpenTicket={openTicket} density={t.density} setView={setView} />}
            {view === 'workers' && <WorkersView workers={workers} tickets={tickets} onOpenWorker={openWorker} onRespond={respondTo} onOpenTicket={openTicket} density={t.density} />}
            {view === 'tickets' && <TicketsView tickets={tickets} workers={workers} onOpen={openTicket} onAssign={(tk) => setModal({ type: 'assign', ticket: tk })} onCreate={() => setModal({ type: 'create' })} density={t.density} ticketLayout={t.ticketLayout} />}
            {view === 'logs' && <LogsView workers={workers} logsMap={logsMap} selectedId={selLogId} onSelect={setSelLogId} onOpenWorker={openWorker} />}
          </div>
        </main>
      </div>

      {openWorker_ && <WorkerPanel worker={openWorker_} logs={logsMap[openWorker_.id] || []} ticket={tickets.find(tk => tk.id === openWorker_.ticket_id)} onClose={() => setOpenWorkerId(null)} onAction={handleWorkerAction} onOpenTicket={openTicket} />}
      {openTicket_ && <TicketPanel ticket={openTicket_} workers={workers} onClose={() => setOpenTicketId(null)} onOpenWorker={openWorker} onAction={handleTicketAction} onAssign={(tk) => setModal({ type: 'assign', ticket: tk })} />}

      {modal && modal.type === 'create' && <CreateTicketModal onClose={() => setModal(null)} onSubmit={createTicket} />}
      {modal && modal.type === 'assign' && <AssignModal ticket={modal.ticket} workers={workers} onClose={() => setModal(null)} onSubmit={assignTicket} />}
      {modal && modal.type === 'attach' && <AttachModal worker={modal.worker} tickets={tickets} onClose={() => setModal(null)} onSubmit={attachTicketToWorker} />}

      <Toasts items={toasts} onDismiss={(id) => setToasts(ts => ts.filter(x => x.id !== id))} />

      <TweaksPanel>
        <TweakSection label="Apparence" />
        <TweakColor label="Couleur d'accent" value={t.accent} options={['#8686d4', '#7dd3a4', '#ff8b67', '#fcb214', '#6ea8fe']} onChange={(v) => setTweak('accent', v)} />
        <TweakRadio label="Densité" value={t.density} options={['compact', 'comfortable']} onChange={(v) => setTweak('density', v)} />
        <TweakToggle label="Halo ambiant" value={t.glow} onChange={(v) => setTweak('glow', v)} />
        <TweakSection label="Tickets" />
        <TweakRadio label="Vue par défaut" value={t.ticketLayout} options={['board', 'table']} onChange={(v) => setTweak('ticketLayout', v)} />
        <TweakSection label="Simulation" />
        <TweakToggle label="Données en direct" value={t.liveData} onChange={(v) => setTweak('liveData', v)} />
        <TweakRadio label="Fréquence" value={String(t.refreshSeconds || 2)} options={['1', '2', '5']} onChange={(v) => setTweak('refreshSeconds', Number(v))} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
