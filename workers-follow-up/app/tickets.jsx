/* ============================================================
   Claude Squad — Tickets view (board + table)  →  window
   ============================================================ */

function workerByName(workers, name) { return workers.find(w => w.name === name) || null; }
function isWorkerActive(w) { return w && ['running', 'waiting', 'blocked'].includes(w.status); }

function PriorityTag({ level }) {
  const map = { high: { c: 'var(--danger)', i: 'keyboard_double_arrow_up', l: 'Haute' }, medium: { c: 'var(--warn)', i: 'drag_handle', l: 'Moyenne' }, low: { c: 'var(--fg-4)', i: 'keyboard_arrow_down', l: 'Basse' } };
  const p = map[level] || map.low;
  return <span title={'Priorité ' + p.l} style={{ display: 'inline-flex', alignItems: 'center', color: p.c }}><Icon name={p.i} size={15} /></span>;
}

function LabelChip({ text }) {
  return <span className="font-label" style={{ fontSize: 10, fontWeight: 600, color: 'var(--fg-3)', background: 'var(--surface-container-high)', padding: '2px 7px', borderRadius: 'var(--radius-xs)', letterSpacing: '0.02em' }}>{text}</span>;
}

// Extract the Linear identifier (e.g. MYL-73) from tk.id so it can be linked.
const LINEAR_RE = /\b[A-Z]{2,}-\d+\b/;
function linearIdFrom(tk) {
  if (!tk || !tk.linear_url) return null;
  const m = (tk.linear_url.match(LINEAR_RE) || [])[0] || (String(tk.id || '').match(LINEAR_RE) || [])[0];
  return m || null;
}

// Renders the ticket id; when a Linear url is present the id becomes a link.
function TicketId({ tk, size = 12 }) {
  const lid = linearIdFrom(tk);
  if (lid && tk.linear_url) {
    return (
      <a href={tk.linear_url} target="_blank" rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className="font-mono" style={{ fontSize: size, color: 'var(--primary)', textDecoration: 'none' }}
        title={'Ouvrir ' + lid + ' dans Linear'}>{tk.id}</a>
    );
  }
  return <span className="font-mono fg-3" style={{ fontSize: size }}>{tk.id}</span>;
}

// "bloqué par #N" badge shown when the task still has open blockers.
function BlockedByBadge({ ids }) {
  const list = (ids || []).filter(Boolean);
  if (!list.length) return null;
  const label = list.length === 1 ? 'bloqué par #' + list[0] : 'bloqué par ' + list.map(i => '#' + i).join(', ');
  return (
    <span className="badge st-blocked" title={label} style={{ padding: '2px 7px' }}>
      <Icon name="block" size={11} fill />{label}
    </span>
  );
}

function TicketCard({ tk, workers, onOpen, onAssign }) {
  const w = workerByName(workers, tk.assigned_to);
  const active = isWorkerActive(w);
  const needsWorker = (tk.status === 'in-progress' || tk.status === 'open') && !active;
  return (
    <button onClick={() => onOpen(tk.id)} className="fade-up" style={{
      display: 'block', textAlign: 'left', width: '100%', padding: '12px 13px', borderRadius: 'var(--radius-lg)',
      background: 'var(--surface-container)', border: '1px solid var(--border-hairline)', cursor: 'pointer',
      transition: 'border-color var(--dur-fast)'
    }} onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-accent)'} onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-hairline)'}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 7 }}>
        <TicketId tk={tk} size={11} />
        <PriorityTag level={tk.priority} />
        <span style={{ marginLeft: 'auto', fontSize: 10 }} className="font-mono fg-4"><RelTime date={tk.updated_at} /></span>
      </div>
      <div className="font-body fg-1" style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.4, marginBottom: 10, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{tk.title}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        {(tk.labels || []).map(l => <LabelChip key={l} text={l} />)}
        {(tk.blocked_by || []).length ? <BlockedByBadge ids={tk.blocked_by} /> : null}
        <span style={{ marginLeft: 'auto' }}></span>
        {active
          ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }} title={'Worker ' + w.name + ' · ' + window.CSQ.WORKER_STATUS[w.status].label}>
              <WDot kind={w.status} pulse={w.status === 'running'} />
              <span className="font-label fg-2" style={{ fontSize: 11 }}>{w.name}</span>
              <AgentChip agent={w.agent} size={20} />
            </span>
          : needsWorker
            ? <span onClick={(e) => { e.stopPropagation(); onAssign(tk); }} className="badge" style={{ '--sc': 'var(--warn)', cursor: 'pointer' }}><Icon name="person_add" size={11} /> assigner</span>
            : w
              ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, opacity: 0.6 }}><Avatar name={w.name} size={20} /><span className="font-label fg-4" style={{ fontSize: 11 }}>{w.name}</span></span>
              : <span className="font-label fg-4" style={{ fontSize: 11 }}>non assigné</span>}
      </div>
    </button>
  );
}

function TicketBoard({ tickets, workers, onOpen, onAssign }) {
  const cols = [
    { id: 'open', tone: 'var(--primary)' },
    { id: 'in-progress', tone: 'var(--secondary)' },
    { id: 'waiting', tone: 'var(--warn)' },
    { id: 'blocked', tone: 'var(--danger)' },
    { id: 'done', tone: 'var(--fg-3)' },
  ];
  return (
    <div className="scroll" style={{ overflowX: 'auto', paddingBottom: 8 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(244px, 1fr))', gap: 12, minWidth: 1180 }}>
        {cols.map(col => {
          const items = tickets.filter(t => t.status === col.id);
          const meta = window.CSQ.TICKET_STATUS[col.id];
          return (
            <div key={col.id} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 4px 0' }}>
                <span className="dot" style={{ background: col.tone }}></span>
                <span className="font-label fg-1" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.03em' }}>{meta.label}</span>
                <span className="font-mono fg-4" style={{ fontSize: 11 }}>{items.length}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9, minHeight: 60 }}>
                {items.length === 0
                  ? <div style={{ padding: '18px 12px', borderRadius: 'var(--radius-lg)', border: '1px dashed var(--border-subtle)', textAlign: 'center' }}><span className="font-label fg-4" style={{ fontSize: 11 }}>Aucun ticket</span></div>
                  : items.map(tk => <TicketCard key={tk.id} tk={tk} workers={workers} onOpen={onOpen} onAssign={onAssign} />)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TicketTable({ tickets, workers, onOpen, onAssign, density }) {
  const order = { waiting: 0, blocked: 1, 'in-progress': 2, open: 3, done: 4 };
  const rows = [...tickets].sort((a, b) => (order[a.status] - order[b.status]) || (new Date(b.updated_at) - new Date(a.updated_at)));
  const pad = density === 'compact' ? '7px 16px' : '11px 16px';
  return (
    <div className="panel" style={{ overflow: 'hidden' }}>
      <table className="tbl">
        <thead>
          <tr>
            <th style={{ width: 96 }}>ID</th>
            <th style={{ width: 122 }}>Statut</th>
            <th>Titre</th>
            <th style={{ width: 170 }}>Worker</th>
            <th style={{ width: 60 }}>Prio</th>
            <th style={{ width: 130 }}>Mis à jour</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(tk => {
            const w = workerByName(workers, tk.assigned_to);
            const active = isWorkerActive(w);
            const attn = tk.status === 'waiting' ? 'row-attn-waiting' : tk.status === 'blocked' ? 'row-attn-blocked' : '';
            return (
              <tr key={tk.id} className={attn} onClick={() => onOpen(tk.id)}>
                <td style={{ padding: pad }}><TicketId tk={tk} /></td>
                <td style={{ padding: pad }}><StatusBadge kind={tk.status} type="ticket" /></td>
                <td style={{ padding: pad }}><span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, flexWrap: 'wrap' }}><span className="font-body fg-1" style={{ fontSize: 13 }}>{tk.title}</span>{(tk.blocked_by || []).length ? <BlockedByBadge ids={tk.blocked_by} /> : null}</span></td>
                <td style={{ padding: pad }}>
                  {active
                    ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}><WDot kind={w.status} pulse={w.status === 'running'} /><span className="font-label fg-2" style={{ fontSize: 12 }}>{w.name}</span></span>
                    : (tk.status === 'open' || tk.status === 'in-progress')
                      ? <button className="btn btn-warn btn-sm" onClick={(e) => { e.stopPropagation(); onAssign(tk); }}><Icon name="person_add" size={13} /> Assigner</button>
                      : w ? <span className="font-label fg-4" style={{ fontSize: 12 }}>{w.name}</span> : <span className="fg-4" style={{ fontSize: 12 }}>—</span>}
                </td>
                <td style={{ padding: pad }}><PriorityTag level={tk.priority} /></td>
                <td style={{ padding: pad }}><span className="font-mono fg-4" style={{ fontSize: 11.5 }}><RelTime date={tk.updated_at} /></span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TicketsView({ tickets, workers, onOpen, onAssign, onCreate, density, ticketLayout }) {
  const [mode, setMode] = React.useState(ticketLayout || 'board');
  React.useEffect(() => { if (ticketLayout) setMode(ticketLayout); }, [ticketLayout]);
  const [filter, setFilter] = React.useState('all');
  const counts = {
    all: tickets.length,
    active: tickets.filter(t => ['in-progress', 'waiting', 'blocked'].includes(t.status)).length,
    attn: tickets.filter(t => ['waiting', 'blocked'].includes(t.status)).length,
    unassigned: tickets.filter(t => !isWorkerActive(workerByName(workers, t.assigned_to)) && t.status !== 'done').length,
  };
  let shown = tickets;
  if (filter === 'active') shown = tickets.filter(t => ['in-progress', 'waiting', 'blocked'].includes(t.status));
  if (filter === 'attn') shown = tickets.filter(t => ['waiting', 'blocked'].includes(t.status));
  if (filter === 'unassigned') shown = tickets.filter(t => !isWorkerActive(workerByName(workers, t.assigned_to)) && t.status !== 'done');

  return (
    <div>
      <SectionHead icon="view_kanban" title="Tickets" eyebrow="Backlog & travail en cours"
        right={
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className={'chip' + (filter === 'all' ? ' on' : '')} onClick={() => setFilter('all')}>Tous <span className="font-mono" style={{ opacity: 0.7 }}>{counts.all}</span></button>
              <button className={'chip' + (filter === 'active' ? ' on' : '')} onClick={() => setFilter('active')}>Actifs {counts.active}</button>
              <button className={'chip' + (filter === 'attn' ? ' on' : '')} onClick={() => setFilter('attn')}>Attention {counts.attn}</button>
              <button className={'chip' + (filter === 'unassigned' ? ' on' : '')} onClick={() => setFilter('unassigned')}>Sans worker {counts.unassigned}</button>
            </div>
            <div style={{ display: 'flex', background: 'var(--surface-container-high)', borderRadius: 'var(--radius-md)', padding: 2, border: '1px solid var(--border-hairline)' }}>
              <button className="btn btn-icon btn-sm" style={{ width: 30, height: 28, border: 'none', background: mode === 'board' ? 'var(--surface-container-highest)' : 'transparent', color: mode === 'board' ? 'var(--fg-1)' : 'var(--fg-4)' }} onClick={() => setMode('board')} title="Tableau"><Icon name="view_kanban" size={16} /></button>
              <button className="btn btn-icon btn-sm" style={{ width: 30, height: 28, border: 'none', background: mode === 'table' ? 'var(--surface-container-highest)' : 'transparent', color: mode === 'table' ? 'var(--fg-1)' : 'var(--fg-4)' }} onClick={() => setMode('table')} title="Liste"><Icon name="table_rows" size={16} /></button>
            </div>
          </div>
        } />
      {mode === 'board'
        ? <TicketBoard tickets={shown} workers={workers} onOpen={onOpen} onAssign={onAssign} />
        : <TicketTable tickets={shown} workers={workers} onOpen={onOpen} onAssign={onAssign} density={density} />}
    </div>
  );
}

Object.assign(window, { TicketsView, TicketBoard, TicketTable, TicketCard, workerByName, isWorkerActive, PriorityTag, LabelChip, TicketId, BlockedByBadge });
