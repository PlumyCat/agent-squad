/* ============================================================
   Claude Squad — Dashboard view  →  window
   ============================================================ */

function AlertStrip({ workers, onOpenWorker, onRespond, onOpenTicket }) {
  const waiting = workers.filter(w => w.status === 'waiting');
  const blocked = workers.filter(w => w.status === 'blocked');
  if (waiting.length === 0 && blocked.length === 0) return null;
  return (
    <div className="fade-up" style={{
      borderRadius: 'var(--radius-xl)', overflow: 'hidden', marginBottom: 18,
      border: '1px solid color-mix(in srgb, var(--warn) 30%, transparent)',
      background: 'color-mix(in srgb, var(--warn) 7%, transparent)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', borderBottom: '1px solid var(--border-hairline)' }}>
        <Icon name="notifications_active" size={18} style={{ color: 'var(--warn)' }} fill />
        <span className="font-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.04em', color: 'var(--fg-1)' }}>
          Intervention requise
        </span>
        <span className="font-label fg-4" style={{ fontSize: 11 }}>
          {waiting.length} en attente · {blocked.length} bloqué{blocked.length > 1 ? 's' : ''}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 1, background: 'var(--border-hairline)' }}>
        {[...waiting, ...blocked].map(w => {
          const isWaiting = w.status === 'waiting';
          const tone = isWaiting ? 'var(--warn)' : 'var(--danger)';
          return (
            <div key={w.id} style={{ background: 'var(--surface-container)', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 9 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                <AgentChip agent={w.agent} />
                <button className="font-headline" onClick={() => onOpenWorker(w)} style={{ fontSize: 14, fontWeight: 700, color: 'var(--fg-1)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>{w.name}</button>
                <StatusBadge kind={w.status} />
                {w.ticket_id ? <button className="linkish font-mono" onClick={() => onOpenTicket(w.ticket_id)} style={{ fontSize: 11, background: 'none', border: 'none', marginLeft: 'auto' }}>{w.ticket_id}</button> : <span className="font-mono fg-4" style={{ fontSize: 11, marginLeft: 'auto' }}>sans ticket</span>}
              </div>
              <p className="font-body" style={{ fontSize: 12.5, lineHeight: 1.5, color: 'var(--fg-2)', margin: 0,
                borderLeft: `2px solid ${tone}`, paddingLeft: 10, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {isWaiting ? (w.waiting_question || w.output) : w.output}
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                {isWaiting
                  ? <button className="btn btn-warn btn-sm" onClick={() => onRespond(w)}><Icon name="reply" size={14} /> Répondre</button>
                  : <button className="btn btn-danger btn-sm" onClick={() => onOpenWorker(w)}><Icon name="build" size={14} /> Débloquer</button>}
                <button className="btn btn-sm" onClick={() => onOpenWorker(w)}><Icon name="terminal" size={14} /> Logs</button>
                <span className="font-mono fg-4" style={{ fontSize: 10.5, marginLeft: 'auto' }}><RelTime date={w.last_activity_at} /></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const WORKER_STATUS_ORDER = { waiting: 0, blocked: 1, running: 2, idle: 3, unknown: 4, done: 5, exited: 6 };

function sortWorkers(list) {
  return [...list].sort((a, b) => (WORKER_STATUS_ORDER[a.status] - WORKER_STATUS_ORDER[b.status]) || (b.last_activity_at - a.last_activity_at));
}

/* One worker row. Extracted so both the flat and team-grouped layouts reuse it. */
function WorkerRow({ w, pad, onOpenWorker, onRespond, onOpenTicket, showActionsCol }) {
  const attn = w.status === 'waiting' ? 'row-attn-waiting' : w.status === 'blocked' ? 'row-attn-blocked' : '';
  const isRunning = w.status === 'running';
  return (
    <tr className={attn} onClick={() => onOpenWorker(w)}>
      <td style={{ padding: pad }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <WDot kind={w.status} pulse={isRunning} />
          <StatusBadge kind={w.status} />
        </span>
      </td>
      <td style={{ padding: pad }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <AgentChip agent={w.agent} />
          <span style={{ minWidth: 0 }}>
            <div className="font-headline fg-1" style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.2 }}>{w.name}</div>
            <div className="font-mono fg-4" style={{ fontSize: 10.5 }}>{w.session}</div>
          </span>
        </span>
      </td>
      <td style={{ padding: pad }}>
        {w.ticket_id
          ? <button className="linkish font-mono" onClick={(e) => { e.stopPropagation(); onOpenTicket(w.ticket_id); }} style={{ fontSize: 12, background: 'none', border: 'none', padding: 0 }}>{w.ticket_id}</button>
          : <span className="badge" style={{ '--sc': 'var(--fg-4)' }}><Icon name="link_off" size={11} /> sans ticket</span>}
      </td>
      <td style={{ padding: pad }}><span className="font-label fg-2" style={{ fontSize: 12 }}>{w.role || '—'}</span></td>
      <td style={{ padding: pad }}><span className="font-mono fg-3" style={{ fontSize: 11.5 }}><RelTime date={w.last_activity_at} /></span></td>
      <td style={{ padding: pad, maxWidth: 280 }}>
        <span className="font-mono fg-3" style={{ fontSize: 11.5, display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 280 }}>{w.output}</span>
      </td>
      {showActionsCol ? (
        <td style={{ padding: pad }} onClick={(e) => e.stopPropagation()}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, justifyContent: 'flex-end' }}>
            {w.status === 'waiting'
              ? <button className="btn btn-warn btn-sm" onClick={() => onRespond(w)}><Icon name="reply" size={14} /></button>
              : null}
            <button className="btn btn-icon btn-sm" style={{ width: 28, height: 28 }} title="Ouvrir" onClick={() => onOpenWorker(w)}><Icon name="open_in_full" size={14} /></button>
          </span>
        </td>
      ) : null}
    </tr>
  );
}

/* Group workers by their `team` field, preserving status sort within each group.
   Returns [[teamName, sortedWorkers], ...] ordered by team name. */
function groupWorkersByTeam(workers) {
  const groups = new Map();
  for (const w of workers) {
    const team = w.team || '—';
    if (!groups.has(team)) groups.set(team, []);
    groups.get(team).push(w);
  }
  return [...groups.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([team, list]) => [team, sortWorkers(list)]);
}

/* Count workers per status within a team group, ordered by attention priority.
   Returns [[status, count], ...] for the statuses actually present. */
function teamStatusCounts(rows) {
  const counts = {};
  for (const w of rows) counts[w.status] = (counts[w.status] || 0) + 1;
  return Object.keys(WORKER_STATUS_ORDER)
    .filter(k => counts[k])
    .map(k => [k, counts[k]]);
}

function WorkerTable({ workers, tickets, onOpenWorker, onRespond, onOpenTicket, density, showActionsCol = true, groupByTeam }) {
  const pad = density === 'compact' ? '7px 16px' : '11px 16px';
  const colCount = showActionsCol ? 7 : 6;
  const rowProps = { pad, onOpenWorker, onRespond, onOpenTicket, showActionsCol };
  // Auto-group when workers span more than one team (multi-team aggregated view),
  // unless explicitly overridden. A single team renders flat as before.
  const teams = new Set(workers.map(w => w.team || '—'));
  const grouped = groupByTeam ?? (teams.size > 1);

  return (
    <div className="panel" style={{ overflow: 'hidden' }}>
      <div className="scroll" style={{ overflowX: 'auto' }}>
        <table className="tbl">
          <thead>
            <tr>
              <th style={{ width: 132 }}>Statut</th>
              <th>Worker</th>
              <th>Ticket</th>
              <th style={{ width: 120 }}>Rôle</th>
              <th style={{ width: 150 }}>Dernière activité</th>
              <th>Sortie récente</th>
              {showActionsCol ? <th style={{ width: 110 }}></th> : null}
            </tr>
          </thead>
          <tbody>
            {grouped
              ? groupWorkersByTeam(workers).map(([team, rows]) => (
                  <React.Fragment key={team}>
                    <tr className="team-group-head">
                      <td colSpan={colCount} style={{ padding: '8px 16px', background: 'var(--surface-container)', borderTop: '1px solid var(--outline-variant)' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                          <Icon name="groups" size={14} />
                          <span className="font-label fg-2" style={{ fontSize: 12, fontWeight: 600, letterSpacing: 0.2 }}>{team}</span>
                          <span className="font-mono fg-4" style={{ fontSize: 11 }}>{rows.length} worker{rows.length > 1 ? 's' : ''}</span>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                            {teamStatusCounts(rows).map(([kind, n]) => (
                              <span key={kind} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }} title={(window.CSQ.WORKER_STATUS[kind] || {}).label || kind}>
                                <WDot kind={kind} />
                                <span className="font-mono fg-3" style={{ fontSize: 11 }}>{n}</span>
                              </span>
                            ))}
                          </span>
                        </span>
                      </td>
                    </tr>
                    {rows.map(w => <WorkerRow key={w.id} w={w} {...rowProps} />)}
                  </React.Fragment>
                ))
              : sortWorkers(workers).map(w => <WorkerRow key={w.id} w={w} {...rowProps} />)}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ActivityRail({ workers, tickets, onOpenWorker, onOpenTicket }) {
  // build a recent activity feed from worker last_activity + ticket history
  const feed = [];
  workers.forEach(w => feed.push({ t: w.last_activity_at, kind: w.status, who: w.name, agent: w.agent, text: w.output, worker: w }));
  tickets.forEach(tk => (tk.history || []).slice(-1).forEach(h => feed.push({ t: h.t, kind: 'ticket', who: tk.id, text: h.text, ticket: tk.id })));
  feed.sort((a, b) => new Date(b.t) - new Date(a.t));
  const top = feed.slice(0, 9);
  const iconFor = (k) => ({ running: 'bolt', waiting: 'pending', blocked: 'block', done: 'check_circle', exited: 'logout', ticket: 'sell', unknown: 'help' }[k] || 'circle');
  const colFor = (k) => ({ running: 'var(--success)', waiting: 'var(--warn)', blocked: 'var(--danger)', done: 'var(--fg-3)', exited: 'var(--fg-4)', ticket: 'var(--primary)' }[k] || 'var(--fg-4)');
  return (
    <div className="panel" style={{ padding: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '13px 16px', borderBottom: '1px solid var(--border-hairline)', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Icon name="monitoring" size={17} className="fg-3" />
        <span className="font-headline fg-1" style={{ fontSize: 14, fontWeight: 700 }}>Activité récente</span>
      </div>
      <div className="scroll" style={{ overflowY: 'auto', padding: '6px 8px', maxHeight: 'none' }}>
        {top.map((f, i) => (
          <button key={i} onClick={() => f.worker ? onOpenWorker(f.worker) : onOpenTicket(f.ticket)} style={{
            display: 'flex', gap: 10, width: '100%', textAlign: 'left', padding: '9px 9px', borderRadius: 'var(--radius-md)',
            background: 'none', border: 'none', cursor: 'pointer', transition: 'background var(--dur-fast)'
          }} onMouseEnter={e => e.currentTarget.style.background = 'var(--row-hover)'} onMouseLeave={e => e.currentTarget.style.background = 'none'}>
            <Icon name={iconFor(f.kind)} size={16} style={{ color: colFor(f.kind), marginTop: 1, flex: 'none' }} fill />
            <span style={{ minWidth: 0, flex: 1 }}>
              <span style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span className="font-headline fg-1" style={{ fontSize: 12.5, fontWeight: 600 }}>{f.who}</span>
                <span className="font-mono fg-4" style={{ fontSize: 10 }}><RelTime date={f.t} /></span>
              </span>
              <span className="font-body fg-3" style={{ fontSize: 11.5, lineHeight: 1.45, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{f.text}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Dashboard({ workers, tickets, onOpenWorker, onRespond, onOpenTicket, density, setView }) {
  const active = workers.filter(w => ['running', 'waiting', 'blocked'].includes(w.status));
  const waiting = workers.filter(w => w.status === 'waiting').length;
  const blocked = workers.filter(w => w.status === 'blocked').length;
  const running = workers.filter(w => w.status === 'running').length;
  const ticketsInProgress = tickets.filter(t => t.status === 'in-progress').length;
  const ticketsDone = tickets.filter(t => t.status === 'done').length;

  if (active.length === 0) {
    return (
      <div style={{ paddingTop: 40 }}>
        <EmptyState icon="bedtime" title="Aucun worker actif"
          body="Aucune session tmux en cours. Lancez un worker depuis votre terminal ou relancez un ticket en attente."
          action={<button className="btn btn-primary" onClick={() => setView('tickets')}><Icon name="view_kanban" size={16} /> Voir les tickets</button>} />
      </div>
    );
  }

  return (
    <div>
      <AlertStrip workers={workers} onOpenWorker={onOpenWorker} onRespond={onRespond} onOpenTicket={onOpenTicket} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 18 }}>
        <StatTile label="Actifs" value={running + waiting + blocked} sub="workers" icon="bolt" tone="primary" />
        <StatTile label="En attente" value={waiting} sub="réponse" icon="pending" tone="warn" onClick={() => setView('dashboard')} active={waiting > 0} />
        <StatTile label="Bloqués" value={blocked} sub="intervention" icon="block" tone="danger" active={blocked > 0} />
        <StatTile label="Tickets en cours" value={ticketsInProgress} sub="assignés" icon="autorenew" tone="secondary" onClick={() => setView('tickets')} />
        <StatTile label="Terminés" value={ticketsDone} sub="aujourd'hui" icon="check_circle" tone="success" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 16, alignItems: 'start' }}>
        <div>
          <SectionHead icon="memory" title="Workers" eyebrow="Sessions tmux en direct"
            right={<button className="btn btn-sm" onClick={() => setView('workers')}>Tout voir <Icon name="arrow_forward" size={14} /></button>} />
          <WorkerTable workers={workers} tickets={tickets} onOpenWorker={onOpenWorker} onRespond={onRespond} onOpenTicket={onOpenTicket} density={density} />
        </div>
        <div style={{ position: 'sticky', top: 0 }}>
          <ActivityRail workers={workers} tickets={tickets} onOpenWorker={onOpenWorker} onOpenTicket={onOpenTicket} />
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Dashboard, AlertStrip, WorkerTable, ActivityRail });
