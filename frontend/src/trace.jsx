const TraceDrawer = ({ open, onToggle, trace, active, payload }) => {
  const [tab, setTab] = React.useState("reasoning");

  return (
    <aside className={`trace-drawer ${open ? "" : "closed"}`}>
      <div className="trace-head">
        <button className="icon-btn" onClick={onToggle} title={open ? "Collapse" : "Expand"} style={{padding:"4px 6px"}}>
          <Icon name={open ? "chevR" : "chevL"} size={14} />
        </button>
        <div className="title">Backend trace</div>
        {open && <span className="chip mono" style={{fontSize:10}}>{trace ? (trace.totalMs/1000).toFixed(2)+"s" : "idle"}</span>}
      </div>

      {open && trace && (
        <>
          <div className="trace-tabs">
            <button className={`trace-tab ${tab === 'reasoning' ? 'active' : ''}`} onClick={() => setTab('reasoning')}>Reasoning</button>
            <button className={`trace-tab ${tab === 'tools' ? 'active' : ''}`} onClick={() => setTab('tools')}>Tools</button>
            <button className={`trace-tab ${tab === 'sources' ? 'active' : ''}`} onClick={() => setTab('sources')}>Sources</button>
            <button className={`trace-tab ${tab === 'meta' ? 'active' : ''}`} onClick={() => setTab('meta')}>Meta</button>
            <button className={`trace-tab ${tab === 'payload' ? 'active' : ''}`} onClick={() => setTab('payload')}>Payload</button>
          </div>

          <div className="trace-body">
            {tab === 'reasoning' && (
              <>
                {trace.steps.map((s, i) => (
                  <div key={i} className={`trace-step ${s.type}`}>
                    <span className="dot"/>
                    <div className="step-head">
                      <span className="step-type">
                        {s.type === 'think' && 'Reasoning'}
                        {s.type === 'tool' && 'Tool call'}
                        {s.type === 'source' && 'Retrieval'}
                      </span>
                      <span className="step-time">{s.ms}ms</span>
                    </div>
                    <div className="step-title">{s.title}</div>
                    <div className="step-body">{s.body}</div>
                    {s.code && <div className="step-code">{s.code}</div>}
                  </div>
                ))}
              </>
            )}

            {tab === 'tools' && (
              <>
                {trace.steps.filter(s => s.type === 'tool').map((s, i) => (
                  <div key={i} className="trace-step tool">
                    <span className="dot"/>
                    <div className="step-head">
                      <span className="step-type">fn_call</span>
                      <span className="step-time">{s.ms}ms</span>
                    </div>
                    <div className="step-title">{s.title}</div>
                    {s.code && <div className="step-code">{s.code}</div>}
                  </div>
                ))}
              </>
            )}

            {tab === 'sources' && (
              <>
                <div style={{fontSize:11, color:"var(--ink-4)", marginBottom:10, fontFamily:"var(--mono)"}}>
                  {active ? active.citations.length : 0} sources cited
                </div>
                {active && active.citations.map((c, i) => (
                  <div key={i} className="trace-src">
                    <div className="name">{c.ref} {c.t}</div>
                    <div className="src-meta">{c.m}</div>
                  </div>
                ))}
              </>
            )}

            {tab === 'meta' && (
              <>
                <div className="trace-meta-grid">
                  <div className="trace-meta"><div className="l">Model</div><div className="v small">{trace.model}</div></div>
                  <div className="trace-meta"><div className="l">Total time</div><div className="v">{(trace.totalMs/1000).toFixed(2)}s</div></div>
                  <div className="trace-meta"><div className="l">Tokens in</div><div className="v">{trace.tokensIn.toLocaleString()}</div></div>
                  <div className="trace-meta"><div className="l">Tokens out</div><div className="v">{trace.tokensOut.toLocaleString()}</div></div>
                  <div className="trace-meta"><div className="l">Tool calls</div><div className="v">{trace.toolCalls}</div></div>
                  <div className="trace-meta"><div className="l">Sources</div><div className="v">{trace.sources}</div></div>
                </div>
                <div style={{fontSize:11, color:"var(--ink-4)", lineHeight:1.6, fontFamily:"var(--mono)", padding:"10px 0"}}>
                  Profile fields used:<br/>
                  · filer_status<br/>
                  · ntn<br/>
                  · prior_year_return<br/>
                  <br/>
                  Confidence: <span style={{color:"var(--forest)"}}>high (0.92)</span>
                </div>
              </>
            )}
            {tab === 'payload' && (
              <>
                <div style={{fontSize:11, color:"var(--ink-4)", marginBottom:10, fontFamily:"var(--mono)"}}>
                  Exact JSON sent to <code>/api/v1/ask</code>
                </div>
                <div className="step-code" style={{whiteSpace:"pre-wrap", wordBreak:"break-word"}}>{payload ? JSON.stringify(payload, null, 2) : "No payload yet."}</div>
              </>
            )}
          </div>
        </>
      )}
    </aside>
  );
};
window.TraceDrawer = TraceDrawer;
