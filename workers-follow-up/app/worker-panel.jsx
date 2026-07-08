/* ============================================================
   Claude Squad — WorkerPanel (drill-in slide-over)  →  window
   ============================================================ */

function MetaItem({ label, children }) {
  return (
    <div style={{ minWidth: 0 }}>
      <div className="eyebrow" style={{ fontSize: 9, marginBottom: 3 }}>{label}</div>
      <div className="font-label fg-2" style={{ fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{children}</div>
    </div>
  );
}

function WorkerPanel({ worker, logs, ticket, onClose, onAction, onOpenTicket }) {
  const [tailing, setTailing] = React.useState(true);
  const [captureN, setCaptureN] = React.useState(500);
  const [search, setSearch] = React.useState('');
  const [draft, setDraft] = React.useState('');
  const w = worker;
  if (!w) return null;
  const isWaiting = w.status === 'waiting';
  const isBlocked = w.status === 'blocked';
  const running = w.status === 'running' || isWaiting;
  const canMessage = ['running', 'waiting', 'blocked'].includes(w.status);
  // killable is set by the backend (providers/worker_actions.can_kill): true only
  // for split-panes tmux workers. In-process Agent Teams teammates have no pane
  // to kill, so the button is disabled with an explanatory tooltip. Tolerant by
  // design: an absent field (current payload, pre-integration) stays enabled, so
  // the front can ship before the backend without breaking the legacy path.
  const canKill = w.killable !== false;

  function submit() {
    const text = draft.trim();
    if (!text) return;
    onAction(isWaiting ? 'respond' : 'send', { worker: w, text });
    setDraft('');
  }

  return (
    <React.Fragment>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(2px)', zIndex: 60 }}></div>
      <div className="slide-over" style={{
        position: 'fixed', top: 0, right: 0, height: '100%', width: '100%', maxWidth: 680, zIndex: 70,
        background: 'var(--surface-container-lowest)', borderLeft: '1px solid var(--border-hairline)',
        display: 'flex', flexDirection: 'column', boxShadow: 'var(--shadow-2xl)'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px', borderBottom: '1px solid var(--border-hairline)', flex: 'none' }}>
          <AgentChip agent={w.agent} size={36} />
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
              <span className="font-headline fg-1" style={{ fontSize: 17, fontWeight: 700 }}>{w.name}</span>
              <WDot kind={w.status} pulse={running} />
              <StatusBadge kind={w.status} />
            </div>
            <div className="font-mono fg-4" style={{ fontSize: 11, marginTop: 2 }}>{window.CSQ.AGENTS[w.agent]} · {w.session}</div>
          </div>
          <button className="btn btn-icon" onClick={onClose}><Icon name="close" size={18} /></button>
        </div>

        {/* Meta strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, padding: '12px 16px', borderBottom: '1px solid var(--border-hairline)', flex: 'none' }}>
          <MetaItem label="Rôle">{w.role || '—'}</MetaItem>
          <MetaItem label="Ticket">
            <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              {w.ticket_id ? <span className="linkish font-mono" onClick={() => onOpenTicket(w.ticket_id)} style={{ fontSize: 12 }}>{w.ticket_id}</span> : <span className="fg-4">sans ticket</span>}
              {w.linear_issue ? <LinearLink id={w.linear_issue} /> : null}
            </span>
          </MetaItem>
          <MetaItem label="Démarré">{window.CSQ.fmtDuration(w.created_at)} </MetaItem>
          <MetaItem label="Activité"><RelTime date={w.last_activity_at} /></MetaItem>
        </div>

        {/* worker-without-ticket affordance */}
        {!w.ticket_id && canMessage ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', borderBottom: '1px solid var(--border-hairline)', background: 'color-mix(in srgb, var(--warn) 6%, transparent)' }}>
            <Icon name="link_off" size={16} style={{ color: 'var(--warn)' }} />
            <span className="font-label fg-2" style={{ fontSize: 12, flex: 1 }}>Ce worker n'est rattaché à aucun ticket.</span>
            <button className="btn btn-warn btn-sm" onClick={() => onAction('attach', { worker: w })}><Icon name="add_link" size={14} /> Associer un ticket</button>
          </div>
        ) : null}

        {/* blocked banner */}
        {isBlocked ? (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '11px 16px', borderBottom: '1px solid var(--border-hairline)', background: 'color-mix(in srgb, var(--danger) 8%, transparent)' }}>
            <Icon name="block" size={16} style={{ color: 'var(--danger)', marginTop: 1 }} fill />
            <span className="font-body" style={{ fontSize: 12.5, lineHeight: 1.5, color: 'var(--fg-2)' }}>{w.output}</span>
          </div>
        ) : null}

        {/* Terminal */}
        <div style={{ flex: 1, minHeight: 0, padding: '12px 16px', display: 'flex' }}>
          <LogTerminal lines={logs} tailing={tailing} onToggleTail={() => setTailing(t => !t)}
            captureN={captureN} onCapture={setCaptureN} search={search} onSearch={setSearch}
            height="100%" running={running} worker={w} />
        </div>

        {/* Composer + actions */}
        <div style={{ borderTop: '1px solid var(--border-hairline)', padding: 14, flex: 'none', background: 'var(--surface-container)' }}>
          {isWaiting ? (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 10, padding: '9px 11px', borderRadius: 'var(--radius-md)', background: 'color-mix(in srgb, var(--warn) 9%, transparent)', border: '1px solid color-mix(in srgb, var(--warn) 28%, transparent)' }}>
              <Icon name="help" size={15} style={{ color: 'var(--warn)', marginTop: 1 }} fill />
              <span className="font-body" style={{ fontSize: 12.5, lineHeight: 1.5, color: 'var(--fg-1)' }}>{w.waiting_question || w.output}</span>
            </div>
          ) : null}
          {canMessage ? (
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
              <textarea className="input scroll" value={draft} onChange={e => setDraft(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit(); }}
                placeholder={isWaiting ? 'Répondre au worker…' : 'Envoyer un message au worker…'}
                rows={2} style={{ resize: 'none', fontFamily: 'var(--font-body)', flex: 1 }} />
              <button className={'btn ' + (isWaiting ? 'btn-warn' : 'btn-primary')} onClick={submit} disabled={!draft.trim()} style={{ height: 38 }}>
                <Icon name={isWaiting ? 'reply' : 'send'} size={16} /> {isWaiting ? 'Répondre' : 'Envoyer'}
              </button>
            </div>
          ) : (
            <div className="font-label fg-4" style={{ fontSize: 12, textAlign: 'center', padding: '6px 0' }}>
              {w.status === 'done' ? 'Worker terminé · code de sortie 0' : w.status === 'exited' ? 'Worker sorti · code ' + w.exit_code : 'Session inactive'}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 11, flexWrap: 'wrap' }}>
            {w.ticket_id ? (
              <React.Fragment>
                <button className="btn btn-success btn-sm" onClick={() => onAction('ticket-status', { worker: w, status: 'done' })}><Icon name="check_circle" size={14} /> Marquer terminé</button>
                <button className="btn btn-warn btn-sm" onClick={() => onAction('ticket-status', { worker: w, status: 'waiting' })}><Icon name="pending" size={14} /> En attente</button>
                <button className="btn btn-danger btn-sm" onClick={() => onAction('ticket-status', { worker: w, status: 'blocked' })}><Icon name="block" size={14} /> Bloqué</button>
              </React.Fragment>
            ) : null}
            <div style={{ flex: 1 }}></div>
            {canMessage
              ? <button
                  className="btn btn-danger btn-sm"
                  onClick={() => canKill && onAction('kill', { worker: w })}
                  disabled={!canKill}
                  title={canKill ? 'Tuer la session du worker' : 'Worker in-process (Agent Teams) — pas de session tmux à tuer'}
                  style={canKill ? undefined : { opacity: 0.5, cursor: 'not-allowed' }}
                ><Icon name="stop_circle" size={14} /> Tuer</button>
              : <button className="btn btn-primary btn-sm" onClick={() => onAction('restart', { worker: w })}><Icon name="restart_alt" size={14} /> Relancer</button>}
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}

Object.assign(window, { WorkerPanel, MetaItem });
