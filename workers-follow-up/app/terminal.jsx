/* ============================================================
   Claude Squad — LogTerminal (shared monospace output)  →  window
   ============================================================ */

function LogTerminal({ lines, tailing, onToggleTail, captureN, onCapture, search, onSearch, height, running, worker }) {
  const scrollRef = React.useRef(null);
  const atBottomRef = React.useRef(true);

  const filtered = (search ? lines.filter(l => l.text.toLowerCase().includes(search.toLowerCase())) : lines);

  React.useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (tailing && atBottomRef.current) el.scrollTop = el.scrollHeight;
  }, [lines.length, tailing]);

  function onScroll() {
    const el = scrollRef.current;
    if (!el) return;
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  }

  return (
    <div className="terminal" style={{ display: 'flex', flexDirection: 'column', height: height || 'auto', minHeight: 0, overflow: 'hidden' }}>
      {/* terminal toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderBottom: '1px solid var(--border-subtle)', flex: 'none' }}>
        <span style={{ display: 'flex', gap: 5 }}>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ff5f57' }}></span>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#febc2e' }}></span>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#28c840' }}></span>
        </span>
        <span className="font-mono" style={{ fontSize: 11, color: 'var(--fg-3)', marginLeft: 4 }}>{worker ? worker.session : 'tmux'}</span>
        <div style={{ flex: 1 }}></div>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Icon name="search" size={14} style={{ position: 'absolute', left: 7, color: 'var(--fg-4)' }} />
          <input className="input" value={search} onChange={e => onSearch(e.target.value)} placeholder="Filtrer…"
            style={{ width: 130, padding: '5px 8px 5px 26px', fontSize: 11, background: 'rgba(255,255,255,0.04)', fontFamily: 'var(--font-mono)' }} />
        </div>
        <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: 'var(--radius-sm)', padding: 2 }}>
          {[100, 500, 1000].map(n => (
            <button key={n} onClick={() => onCapture(n)} className="font-mono" style={{
              fontSize: 10.5, padding: '3px 7px', borderRadius: 'var(--radius-xs)', border: 'none', cursor: 'pointer',
              background: captureN === n ? 'var(--primary)' : 'transparent', color: captureN === n ? 'var(--on-primary)' : 'var(--fg-3)'
            }}>{n}</button>
          ))}
        </div>
        <button onClick={onToggleTail} className="btn btn-sm" style={{
          padding: '4px 9px', borderColor: tailing ? 'color-mix(in srgb, var(--success) 40%, transparent)' : 'var(--border-subtle)',
          color: tailing ? 'var(--success)' : 'var(--fg-3)', background: tailing ? 'color-mix(in srgb, var(--success) 12%, transparent)' : 'transparent'
        }} title="Suivre la sortie en direct">
          <Icon name={tailing ? 'pause' : 'play_arrow'} size={14} /> {tailing ? 'Tail' : 'Figé'}
        </button>
      </div>

      {/* terminal body */}
      <div ref={scrollRef} onScroll={onScroll} className="scroll" style={{ flex: 1, overflowY: 'auto', padding: '10px 14px', minHeight: 0 }}>
        {filtered.length === 0
          ? <div className="font-mono term-dim" style={{ fontSize: 12, padding: 8 }}>{search ? 'Aucune ligne ne correspond.' : 'En attente de sortie…'}</div>
          : filtered.map(l => (
            <div key={l.id} className="term-line">
              <span className="term-ts">{window.CSQ.ts(l.time)}  </span>
              <span className={'term-' + l.kind}>{l.text}</span>
            </div>
          ))}
        {running && tailing && !search ? <div className="term-line"><span className="term-ts">{window.CSQ.ts(new Date())}  </span><span className="term-cursor"></span></div> : null}
      </div>

      {/* footer status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 12px', borderTop: '1px solid var(--border-subtle)', flex: 'none' }}>
        <span className="font-mono" style={{ fontSize: 10, color: 'var(--fg-4)' }}>{filtered.length} lignes{search ? ' filtrées' : ''} · capture {captureN}</span>
        <div style={{ flex: 1 }}></div>
        {running ? <span className="font-mono" style={{ fontSize: 10, color: 'var(--success)', display: 'inline-flex', alignItems: 'center', gap: 5 }}><span className="dot st-running dot-pulse"></span> flux actif</span>
          : <span className="font-mono" style={{ fontSize: 10, color: 'var(--fg-4)' }}>flux inactif</span>}
      </div>
    </div>
  );
}

Object.assign(window, { LogTerminal });
