/* ============================================================
   Claude Squad — shared components  →  window
   ============================================================ */
const ICON_FALLBACKS = {
  add: '+',
  add_link: '+',
  add_task: '+',
  arrow_forward: '>',
  autorenew: '~',
  bedtime: 'o',
  block: '!',
  bolt: '*',
  build: '!',
  check: '✓',
  check_circle: '✓',
  close: '×',
  dark_mode: '◐',
  filter_alt_off: '×',
  groups: '▒',
  help: '?',
  hub: '◇',
  light_mode: '○',
  link_off: '×',
  logout: '→',
  memory: '▣',
  monitoring: '▥',
  notifications_active: '!',
  notifications_off: '!',
  open_in_full: '↗',
  pause_circle: '⏸',
  pending: '…',
  person_add: '+',
  radio_button_unchecked: '○',
  refresh: '↻',
  reply: '↩',
  restart_alt: '↻',
  rocket_launch: '↑',
  sell: '#',
  send: '→',
  space_dashboard: '▦',
  stop_circle: '■',
  table_rows: '≡',
  terminal: '›',
  view_kanban: '▤',
};

function Icon({ name, size = 18, fill = false, className = '', style = {} }) {
  const glyph = ICON_FALLBACKS[name] || '•';
  return (
    <span
      className={'local-icon' + (fill ? ' fill' : '') + (className ? ' ' + className : '')}
      aria-hidden="true"
      style={{ width: size + 'px', height: size + 'px', fontSize: Math.max(10, Math.round(size * 0.78)) + 'px', ...style }}
    >{glyph}</span>
  );
}

/* live-updating relative time */
function RelTime({ date, tick }) {
  return <span>{window.CSQ.fmtRel(date)}</span>;
}

function StatusBadge({ kind, type = 'worker', size }) {
  const dict = type === 'worker' ? window.CSQ.WORKER_STATUS : window.CSQ.TICKET_STATUS;
  const s = dict[kind] || dict.unknown || { label: kind, cls: 'st-unknown', icon: 'help' };
  return (
    <span className={'badge ' + s.cls} style={size ? { fontSize: size } : null}>
      <Icon name={s.icon} size={12} fill />
      {s.label}
    </span>
  );
}

function WDot({ kind, type = 'worker', pulse = false }) {
  const dict = type === 'worker' ? window.CSQ.WORKER_STATUS : window.CSQ.TICKET_STATUS;
  const s = dict[kind] || { cls: 'st-unknown' };
  return <span className={'dot ' + s.cls + (pulse ? ' dot-pulse' : '')}></span>;
}

function AgentChip({ agent, size }) {
  const isCodex = agent === 'codex';
  return (
    <span className={'agent-chip ' + (isCodex ? 'agent-codex' : 'agent-claude')}
          style={size ? { width: size, height: size } : null}
          title={window.CSQ.AGENTS[agent]}>
      <Icon name={isCodex ? 'terminal' : 'smart_toy'} size={16} />
    </span>
  );
}

function Avatar({ name, size = 24 }) {
  const initial = (name || '?').slice(0, 2);
  return (
    <span className="agent-chip" style={{
      width: size, height: size, fontSize: size * 0.4,
      background: 'var(--surface-container-highest)', color: 'var(--fg-2)',
      textTransform: 'uppercase', borderRadius: 'var(--radius-pill)'
    }}>{initial}</span>
  );
}

/* compact KPI tile */
function StatTile({ label, value, sub, icon, tone = 'primary', onClick, active }) {
  const toneVar = { primary: 'var(--primary)', warn: 'var(--warn)', danger: 'var(--danger)', success: 'var(--success)', secondary: 'var(--secondary)' }[tone];
  return (
    <button
      onClick={onClick}
      className="glass fade-up"
      style={{
        textAlign: 'left', padding: '16px 18px', borderRadius: 'var(--radius-xl)',
        cursor: onClick ? 'pointer' : 'default', position: 'relative', overflow: 'hidden',
        borderColor: active ? `color-mix(in srgb, ${toneVar} 45%, transparent)` : undefined,
        transition: 'border-color var(--dur-fast)',
      }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span className="eyebrow">{label}</span>
        <span style={{
          width: 30, height: 30, borderRadius: 'var(--radius-md)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: `color-mix(in srgb, ${toneVar} 14%, transparent)`, color: toneVar
        }}><Icon name={icon} size={17} fill /></span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span className="font-headline" style={{ fontSize: 30, fontWeight: 700, lineHeight: 1, color: tone === 'primary' ? 'var(--fg-1)' : toneVar }}>{value}</span>
        {sub ? <span className="font-label fg-4" style={{ fontSize: 11 }}>{sub}</span> : null}
      </div>
    </button>
  );
}

function SectionHead({ eyebrow, title, right, icon }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, marginBottom: 14 }}>
      <div>
        {eyebrow ? <div className="eyebrow" style={{ marginBottom: 5 }}>{eyebrow}</div> : null}
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          {icon ? <Icon name={icon} size={19} className="fg-3" /> : null}
          <h2 className="font-headline fg-1" style={{ fontSize: 18, fontWeight: 700, margin: 0, letterSpacing: '-0.01em' }}>{title}</h2>
        </div>
      </div>
      {right}
    </div>
  );
}

function EmptyState({ icon, title, body, action }) {
  return (
    <div className="fade-up" style={{ textAlign: 'center', padding: '56px 24px', maxWidth: 420, margin: '0 auto' }}>
      <div style={{
        width: 60, height: 60, borderRadius: 'var(--radius-xl)', margin: '0 auto 16px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--surface-container-high)', border: '1px solid var(--border-hairline)'
      }}>
        <Icon name={icon} size={30} className="fg-4" />
      </div>
      <h3 className="font-headline fg-2" style={{ fontSize: 16, fontWeight: 700, margin: '0 0 7px' }}>{title}</h3>
      <p className="font-body fg-4" style={{ fontSize: 13, lineHeight: 1.6, margin: '0 auto 18px' }}>{body}</p>
      {action}
    </div>
  );
}

/* ── Top navigation bar ───────────────────────────────────── */
function TopNav({ clock, online, onToggleTheme, theme, onRefresh, lastRefresh, live, refreshSeconds, notificationsEnabled, onEnableNotifications }) {
  return (
    <nav style={{
      height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 20px 0 18px', borderBottom: '1px solid var(--border-hairline)',
      background: 'var(--surface-container-lowest)', position: 'relative', zIndex: 30, flex: 'none'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{
          width: 30, height: 30, borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'color-mix(in srgb, var(--primary) 16%, transparent)', color: 'var(--primary)'
        }}><Icon name="hub" size={18} fill /></span>
        <span className="font-headline fg-1" style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.02em' }}>
          {window.CSQ_IS_CODEX_PAGE ? 'Codex Squad' : 'Claude Squad'}
        </span>
        <span className="font-mono fg-4" style={{ fontSize: 10, padding: '2px 7px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border-hairline)' }}>local</span>
        <a href={window.CSQ_IS_CODEX_PAGE ? '/' : '/codex'} className="font-label fg-3"
          title={window.CSQ_IS_CODEX_PAGE ? 'Voir les workers Claude Agent Teams' : 'Voir les workers codex/tmux'}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '4px 10px', textDecoration: 'none',
            fontSize: 10.5, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
            borderRadius: 'var(--radius-pill)', border: '1px solid var(--border-hairline)',
            background: 'var(--surface-container-high)'
          }}>
          <Icon name="swap_horiz" size={14} />
          {window.CSQ_IS_CODEX_PAGE ? 'Claude' : 'Codex'}
        </a>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 7, padding: '5px 9px', borderRadius: 'var(--radius-pill)',
          background: live ? 'color-mix(in srgb, var(--success) 10%, transparent)' : 'var(--surface-container-high)',
          border: '1px solid ' + (live ? 'color-mix(in srgb, var(--success) 30%, transparent)' : 'var(--border-hairline)')
        }}>
          <span className={'dot st-running' + (live ? ' dot-pulse' : '')}></span>
          <span className="font-label" style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: live ? 'var(--success)' : 'var(--fg-4)' }}>
            {live ? `live ${refreshSeconds}s` : 'manuel'}
          </span>
        </div>
        <span className="font-mono fg-4" style={{ fontSize: 11 }}>{lastRefresh}</span>
        <button className="btn btn-icon" onClick={onEnableNotifications} title={notificationsEnabled ? 'Notifications activées' : 'Activer les notifications'}
          style={notificationsEnabled ? { color: 'var(--success)', borderColor: 'color-mix(in srgb, var(--success) 30%, transparent)' } : null}>
          <Icon name={notificationsEnabled ? 'notifications_active' : 'notifications_off'} size={17} />
        </button>
        <button className="btn btn-icon" onClick={onRefresh} title="Rafraîchir"><Icon name="refresh" size={17} /></button>
        <button className="btn btn-icon" onClick={onToggleTheme} title="Thème">
          <Icon name={theme === 'dark' ? 'light_mode' : 'dark_mode'} size={17} />
        </button>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 7, padding: '5px 11px', borderRadius: 'var(--radius-pill)',
          background: 'var(--surface-container-high)', border: '1px solid var(--border-hairline)'
        }}>
          <span className="dot st-running dot-pulse"></span>
          <span className="font-label" style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--fg-2)' }}>{online} actifs</span>
        </div>
      </div>
    </nav>
  );
}

/* ── Left sidebar ─────────────────────────────────────────── */
function Sidebar({ view, setView, counts, onCreate }) {
  const items = [
    { id: 'dashboard', label: 'Vue d\'ensemble', icon: 'space_dashboard' },
    { id: 'workers', label: 'Workers', icon: 'memory', badge: counts.activeWorkers },
    { id: 'tickets', label: 'Tickets', icon: 'view_kanban', badge: counts.openTickets },
    { id: 'logs', label: 'Logs', icon: 'terminal' },
  ];
  const attn = counts.waiting + counts.blocked;
  return (
    <aside style={{
      width: 232, flex: 'none', display: 'flex', flexDirection: 'column',
      background: 'var(--surface-container-lowest)', borderRight: '1px solid var(--border-hairline)'
    }}>
      <div style={{ padding: '16px 14px 10px' }}>
        <div className="eyebrow" style={{ padding: '0 10px 8px' }}>Supervision</div>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {items.map(it => (
            <button key={it.id} className={'nav-item' + (view === it.id ? ' active' : '')} onClick={() => setView(it.id)}>
              <Icon name={it.icon} size={20} />
              <span style={{ flex: 1 }}>{it.label}</span>
              {it.badge ? <span className="font-mono" style={{ fontSize: 10, color: 'var(--fg-4)' }}>{it.badge}</span> : null}
            </button>
          ))}
        </nav>
      </div>

      <div className="divider" style={{ margin: '6px 14px' }}></div>

      {/* Signals block */}
      <div style={{ padding: '8px 14px' }}>
        <div className="eyebrow" style={{ padding: '0 10px 8px' }}>Signaux</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '0 4px' }}>
          <SignalRow tone="warn" icon="pending" label="En attente" n={counts.waiting} onClick={() => setView('dashboard')} />
          <SignalRow tone="danger" icon="block" label="Bloqués" n={counts.blocked} onClick={() => setView('dashboard')} />
        </div>
      </div>

      <div style={{ flex: 1 }}></div>

      <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 4px' }}>
          <span className="font-mono fg-4" style={{ fontSize: 10 }}>tmux · {counts.totalWorkers} sessions</span>
        </div>
      </div>
    </aside>
  );
}

function SignalRow({ tone, icon, label, n, onClick }) {
  const v = { warn: 'var(--warn)', danger: 'var(--danger)' }[tone];
  const muted = n === 0;
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 9, width: '100%', textAlign: 'left',
      padding: '7px 9px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
      background: muted ? 'transparent' : `color-mix(in srgb, ${v} 9%, transparent)`,
      border: '1px solid ' + (muted ? 'var(--border-hairline)' : `color-mix(in srgb, ${v} 26%, transparent)`),
      transition: 'all var(--dur-fast)'
    }}>
      <Icon name={icon} size={16} style={{ color: muted ? 'var(--fg-4)' : v }} fill={!muted} />
      <span className="font-label" style={{ fontSize: 12, flex: 1, color: muted ? 'var(--fg-4)' : 'var(--fg-2)' }}>{label}</span>
      <span className="font-headline" style={{ fontSize: 14, fontWeight: 700, color: muted ? 'var(--fg-4)' : v }}>{n}</span>
    </button>
  );
}

Object.assign(window, { Icon, RelTime, StatusBadge, WDot, AgentChip, Avatar, StatTile, SectionHead, EmptyState, TopNav, Sidebar, SignalRow });
