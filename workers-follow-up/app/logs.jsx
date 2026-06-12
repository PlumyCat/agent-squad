/* ============================================================
   Claude Squad — Logs view + Workers view  →  window
   ============================================================ */

function LogsView({ workers, logsMap, selectedId, onSelect, onOpenWorker }) {
  const [tailing, setTailing] = React.useState(true);
  const [captureN, setCaptureN] = React.useState(500);
  const [search, setSearch] = React.useState('');
  const sel = workers.find(w => w.id === selectedId) || workers[0];
  const order = { waiting: 0, blocked: 1, running: 2, done: 3, exited: 4, unknown: 5 };
  const list = [...workers].sort((a, b) => order[a.status] - order[b.status]);
  const lines = sel ? (logsMap[sel.id] || []) : [];
  const running = sel && (sel.status === 'running' || sel.status === 'waiting');

  return (
    <div>
      <SectionHead icon="terminal" title="Logs" eyebrow="Sortie des sessions tmux" />
      <div style={{ display: 'grid', gridTemplateColumns: '236px minmax(0,1fr)', gap: 16, height: 'calc(100vh - 188px)' }}>
        {/* worker rail */}
        <div className="panel scroll" style={{ overflowY: 'auto', padding: 8 }}>
          {list.map(w => (
            <button key={w.id} onClick={() => onSelect(w.id)} style={{
              display: 'flex', alignItems: 'center', gap: 9, width: '100%', textAlign: 'left', padding: '9px 10px', marginBottom: 3,
              borderRadius: 'var(--radius-md)', cursor: 'pointer',
              background: sel && sel.id === w.id ? 'color-mix(in srgb, var(--primary) 10%, transparent)' : 'transparent',
              border: '1px solid ' + (sel && sel.id === w.id ? 'var(--border-accent)' : 'transparent')
            }}>
              <WDot kind={w.status} pulse={w.status === 'running'} />
              <span style={{ flex: 1, minWidth: 0 }}>
                <div className="font-headline fg-1" style={{ fontSize: 12.5, fontWeight: 600 }}>{w.name}</div>
                <div className="font-mono fg-4" style={{ fontSize: 10 }}>{w.session}</div>
              </span>
              <AgentChip agent={w.agent} size={22} />
            </button>
          ))}
        </div>
        {/* terminal */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          {sel ? (
            <React.Fragment>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                <AgentChip agent={sel.agent} />
                <span className="font-headline fg-1" style={{ fontSize: 14, fontWeight: 700 }}>{sel.name}</span>
                <StatusBadge kind={sel.status} />
                {sel.ticket_id ? <span className="font-mono fg-4" style={{ fontSize: 11 }}>{sel.ticket_id}</span> : null}
                <div style={{ flex: 1 }}></div>
                <button className="btn btn-sm" onClick={() => onOpenWorker(sel)}><Icon name="open_in_full" size={14} /> Ouvrir le worker</button>
              </div>
              <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
                <LogTerminal lines={lines} tailing={tailing} onToggleTail={() => setTailing(t => !t)}
                  captureN={captureN} onCapture={setCaptureN} search={search} onSearch={setSearch}
                  height="100%" running={running} worker={sel} />
              </div>
            </React.Fragment>
          ) : <EmptyState icon="terminal" title="Aucune session" body="Aucun worker à afficher." />}
        </div>
      </div>
    </div>
  );
}

function WorkersView({ workers, tickets, onOpenWorker, onRespond, onOpenTicket, density }) {
  const [filter, setFilter] = React.useState('all');
  const filters = [
    { id: 'all', label: 'Tous' },
    { id: 'active', label: 'Actifs' },
    { id: 'waiting', label: 'En attente' },
    { id: 'blocked', label: 'Bloqués' },
    { id: 'done', label: 'Terminés' },
    { id: 'no-ticket', label: 'Sans ticket' },
  ];
  let shown = workers;
  if (filter === 'active') shown = workers.filter(w => ['running', 'waiting', 'blocked'].includes(w.status));
  else if (filter === 'no-ticket') shown = workers.filter(w => !w.ticket_id);
  else if (filter !== 'all') shown = workers.filter(w => w.status === filter);

  return (
    <div>
      <SectionHead icon="memory" title="Workers" eyebrow="Toutes les sessions"
        right={<div style={{ display: 'flex', gap: 6 }}>{filters.map(f => {
          const n = f.id === 'all' ? workers.length : f.id === 'active' ? workers.filter(w => ['running', 'waiting', 'blocked'].includes(w.status)).length : f.id === 'no-ticket' ? workers.filter(w => !w.ticket_id).length : workers.filter(w => w.status === f.id).length;
          return <button key={f.id} className={'chip' + (filter === f.id ? ' on' : '')} onClick={() => setFilter(f.id)}>{f.label} <span className="font-mono" style={{ opacity: 0.7 }}>{n}</span></button>;
        })}</div>} />
      {shown.length === 0
        ? <div className="panel" style={{ padding: 0 }}><EmptyState icon="filter_alt_off" title="Aucun worker" body="Aucune session ne correspond à ce filtre." /></div>
        : <WorkerTable workers={shown} tickets={tickets} onOpenWorker={onOpenWorker} onRespond={onRespond} onOpenTicket={onOpenTicket} density={density} />}
    </div>
  );
}

Object.assign(window, { LogsView, WorkersView });
