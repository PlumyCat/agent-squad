/* ============================================================
   Claude Squad — TicketPanel + modals  →  window
   ============================================================ */

function ModalShell({ title, icon, onClose, children, footer, width = 480 }) {
  return (
    <React.Fragment>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(3px)', zIndex: 80 }}></div>
      <div className="fade-up" style={{
        position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', zIndex: 90,
        width: 'calc(100% - 40px)', maxWidth: width, background: 'var(--surface-container)',
        border: '1px solid var(--border-hairline)', borderRadius: 'var(--radius-2xl)', boxShadow: 'var(--shadow-2xl)', overflow: 'hidden'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '15px 18px', borderBottom: '1px solid var(--border-hairline)' }}>
          <Icon name={icon} size={19} className="fg-3" />
          <span className="font-headline fg-1" style={{ fontSize: 15, fontWeight: 700, flex: 1 }}>{title}</span>
          <button className="btn btn-icon" onClick={onClose}><Icon name="close" size={17} /></button>
        </div>
        <div style={{ padding: 18 }}>{children}</div>
        {footer ? <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 9, padding: '13px 18px', borderTop: '1px solid var(--border-hairline)', background: 'var(--surface-container-low)' }}>{footer}</div> : null}
      </div>
    </React.Fragment>
  );
}

function Field({ label, children }) {
  return (
    <label style={{ display: 'block', marginBottom: 14 }}>
      <span className="eyebrow" style={{ display: 'block', marginBottom: 6 }}>{label}</span>
      {children}
    </label>
  );
}

function CreateTicketModal({ onClose, onSubmit }) {
  const [title, setTitle] = React.useState('');
  const [body, setBody] = React.useState('');
  const [priority, setPriority] = React.useState('medium');
  const [labels, setLabels] = React.useState('');
  return (
    <ModalShell title="Créer un ticket" icon="add_task" onClose={onClose} width={520}
      footer={<React.Fragment>
        <button className="btn" onClick={onClose}>Annuler</button>
        <button className="btn btn-primary" disabled={!title.trim()} onClick={() => onSubmit({ title: title.trim(), body: body.trim(), priority, labels: labels.split(',').map(s => s.trim()).filter(Boolean) })}><Icon name="add" size={16} /> Créer</button>
      </React.Fragment>}>
      <Field label="Titre"><input className="input" autoFocus value={title} onChange={e => setTitle(e.target.value)} placeholder="Ex. Migrer le schéma des sessions" /></Field>
      <Field label="Description"><textarea className="input scroll" rows={4} value={body} onChange={e => setBody(e.target.value)} placeholder="Contexte, critères d'acceptation…" style={{ resize: 'vertical', fontFamily: 'var(--font-body)' }} /></Field>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Field label="Priorité">
          <div style={{ display: 'flex', gap: 6 }}>
            {['low', 'medium', 'high'].map(p => (
              <button key={p} onClick={() => setPriority(p)} className={'chip' + (priority === p ? ' on' : '')} style={{ flex: 1, justifyContent: 'center' }}>{{ low: 'Basse', medium: 'Moyenne', high: 'Haute' }[p]}</button>
            ))}
          </div>
        </Field>
        <Field label="Labels (séparés par ,)"><input className="input" value={labels} onChange={e => setLabels(e.target.value)} placeholder="backend, migration" /></Field>
      </div>
    </ModalShell>
  );
}

function AssignModal({ ticket, workers, onClose, onSubmit }) {
  const idle = workers.filter(w => ['running', 'exited', 'done', 'unknown'].includes(w.status));
  const [sel, setSel] = React.useState(null);
  return (
    <ModalShell title={'Assigner ' + ticket.id} icon="person_add" onClose={onClose}
      footer={<React.Fragment>
        <button className="btn" onClick={onClose}>Annuler</button>
        <button className="btn btn-primary" disabled={!sel} onClick={() => onSubmit(ticket, sel)}><Icon name="check" size={16} /> Assigner</button>
      </React.Fragment>}>
      <p className="font-body fg-3" style={{ fontSize: 13, margin: '0 0 14px', lineHeight: 1.5 }}>Rattacher un worker existant au ticket, ou lancer une nouvelle session.</p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 14 }}>
        {workers.map(w => (
          <button key={w.id} onClick={() => setSel(w.name)} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '9px 11px', borderRadius: 'var(--radius-md)', cursor: 'pointer', textAlign: 'left',
            background: sel === w.name ? 'color-mix(in srgb, var(--primary) 10%, transparent)' : 'var(--surface-container-high)',
            border: '1px solid ' + (sel === w.name ? 'var(--border-accent)' : 'var(--border-hairline)')
          }}>
            <AgentChip agent={w.agent} />
            <span style={{ flex: 1 }}>
              <div className="font-headline fg-1" style={{ fontSize: 13, fontWeight: 600 }}>{w.name}</div>
              <div className="font-mono fg-4" style={{ fontSize: 10.5 }}>{w.session}</div>
            </span>
            <StatusBadge kind={w.status} />
          </button>
        ))}
      </div>
      <button className="btn" style={{ width: '100%' }} onClick={() => onSubmit(ticket, '__new__')}><Icon name="add" size={16} /> Lancer un nouveau worker</button>
    </ModalShell>
  );
}

function TimelineRow({ item, last }) {
  return (
    <div style={{ display: 'flex', gap: 11 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 'none' }}>
        <span className="dot" style={{ background: 'var(--fg-4)', width: 7, height: 7, marginTop: 5 }}></span>
        {!last ? <span style={{ flex: 1, width: 1, background: 'var(--border-subtle)', marginTop: 3 }}></span> : null}
      </div>
      <div style={{ paddingBottom: last ? 0 : 13, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 7 }}>
          <span className="font-label fg-2" style={{ fontSize: 12, fontWeight: 600 }}>{item.who}</span>
          <span className="font-mono fg-4" style={{ fontSize: 10 }}>{window.CSQ.fmtRel(item.t)}</span>
        </div>
        <div className="font-body fg-3" style={{ fontSize: 12.5, lineHeight: 1.5, marginTop: 2 }}>{item.text}</div>
      </div>
    </div>
  );
}

function TicketPanel({ ticket, workers, onClose, onOpenWorker, onAction, onAssign }) {
  const tk = ticket;
  if (!tk) return null;
  const w = workerByName(workers, tk.assigned_to);
  const active = isWorkerActive(w);
  const statuses = ['open', 'in-progress', 'waiting', 'blocked', 'done'];

  return (
    <React.Fragment>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(2px)', zIndex: 60 }}></div>
      <div className="slide-over scroll" style={{
        position: 'fixed', top: 0, right: 0, height: '100%', width: '100%', maxWidth: 560, zIndex: 70, overflowY: 'auto',
        background: 'var(--surface-container-lowest)', borderLeft: '1px solid var(--border-hairline)', boxShadow: 'var(--shadow-2xl)'
      }}>
        {/* Header */}
        <div style={{ position: 'sticky', top: 0, zIndex: 2, padding: '14px 18px', borderBottom: '1px solid var(--border-hairline)', background: 'var(--surface-container-lowest)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 9, flexWrap: 'wrap' }}>
            <TicketId tk={tk} />
            {tk.linear_url ? <a href={tk.linear_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} title="Ouvrir dans Linear" style={{ display: 'inline-flex', alignItems: 'center', color: 'var(--fg-4)' }}><Icon name="open_in_new" size={13} /></a> : null}
            <StatusBadge kind={tk.status} type="ticket" />
            <PriorityTag level={tk.priority} />
            {(tk.blocked_by || []).length ? <BlockedByBadge ids={tk.blocked_by} /> : null}
            <div style={{ flex: 1 }}></div>
            <button className="btn btn-icon" onClick={onClose}><Icon name="close" size={18} /></button>
          </div>
          <h2 className="font-headline fg-1" style={{ fontSize: 19, fontWeight: 700, margin: 0, lineHeight: 1.3, letterSpacing: '-0.01em' }}>{tk.title}</h2>
        </div>

        <div style={{ padding: 18 }}>
          {/* status changer */}
          <div className="eyebrow" style={{ marginBottom: 8 }}>Statut</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 18 }}>
            {statuses.map(s => {
              const meta = window.CSQ.TICKET_STATUS[s];
              const on = tk.status === s;
              return (
                <button key={s} onClick={() => onAction('set-status', { ticket: tk, status: s })} className={'badge ' + meta.cls}
                  style={{ cursor: 'pointer', opacity: on ? 1 : 0.5, outline: on ? '1px solid color-mix(in srgb, var(--sc) 50%, transparent)' : 'none', padding: '5px 10px' }}>
                  <Icon name={meta.icon} size={12} fill />{meta.label}
                </button>
              );
            })}
          </div>

          {/* description */}
          <div className="eyebrow" style={{ marginBottom: 8 }}>Description</div>
          <p className="font-body fg-2" style={{ fontSize: 13.5, lineHeight: 1.65, margin: '0 0 14px' }}>{tk.body}</p>
          {(tk.labels || []).length ? <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 18 }}>{tk.labels.map(l => <LabelChip key={l} text={l} />)}</div> : null}

          {/* assigned worker */}
          <div className="eyebrow" style={{ marginBottom: 8 }}>Worker assigné</div>
          {w ? (
            <button onClick={() => onOpenWorker(w)} style={{
              display: 'flex', alignItems: 'center', gap: 11, width: '100%', textAlign: 'left', padding: '11px 13px', marginBottom: 18,
              borderRadius: 'var(--radius-lg)', background: 'var(--surface-container)', border: '1px solid var(--border-hairline)', cursor: 'pointer'
            }}>
              <AgentChip agent={w.agent} size={34} />
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="font-headline fg-1" style={{ fontSize: 14, fontWeight: 600 }}>{w.name}</span>
                  <WDot kind={w.status} pulse={w.status === 'running'} />
                  <StatusBadge kind={w.status} />
                </span>
                <span className="font-mono fg-4" style={{ fontSize: 11 }}>{w.session} · {w.role}</span>
              </span>
              <Icon name="open_in_full" size={15} className="fg-4" />
            </button>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '13px', marginBottom: 18, borderRadius: 'var(--radius-lg)', border: '1px dashed var(--border-subtle)', background: 'color-mix(in srgb, var(--warn) 5%, transparent)' }}>
              <Icon name="person_off" size={20} className="fg-4" />
              <span className="font-body fg-3" style={{ fontSize: 12.5, flex: 1 }}>{tk.status === 'done' ? 'Aucun worker actif — ticket terminé.' : 'Aucun worker actif sur ce ticket.'}</span>
              {tk.status !== 'done' ? <button className="btn btn-warn btn-sm" onClick={() => onAssign(tk)}><Icon name="person_add" size={14} /> Assigner</button> : null}
            </div>
          )}

          {/* comments */}
          {(tk.comments || []).length ? (
            <React.Fragment>
              <div className="eyebrow" style={{ marginBottom: 8 }}>Échanges</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 18 }}>
                {tk.comments.map((c, i) => (
                  <div key={i} style={{ padding: '10px 12px', borderRadius: 'var(--radius-md)', background: 'var(--surface-container)', borderLeft: '2px solid ' + (c.agent ? 'var(--primary)' : 'var(--fg-4)') }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 7, marginBottom: 3 }}>
                      <span className="font-label fg-2" style={{ fontSize: 11.5, fontWeight: 700 }}>{c.who}</span>
                      {c.agent ? <span className="font-mono fg-4" style={{ fontSize: 9.5 }}>agent</span> : null}
                      <span className="font-mono fg-4" style={{ fontSize: 9.5 }}>{window.CSQ.fmtRel(c.t)}</span>
                    </div>
                    <div className="font-body fg-2" style={{ fontSize: 12.5, lineHeight: 1.5 }}>{c.text}</div>
                  </div>
                ))}
              </div>
            </React.Fragment>
          ) : null}

          {/* history */}
          <div className="eyebrow" style={{ marginBottom: 10 }}>Historique</div>
          <div>
            {[...(tk.history || [])].reverse().map((h, i, arr) => <TimelineRow key={i} item={h} last={i === arr.length - 1} />)}
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}

Object.assign(window, { TicketPanel, CreateTicketModal, AssignModal, ModalShell, Field, TimelineRow });
