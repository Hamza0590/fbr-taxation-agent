// ── Clarification questions panel ─────────────────────────────────────────────
const ClarificationPanel = ({ questions, onQuickReply }) => {
  if (!questions || questions.length === 0) return null;

  return (
    <div style={{
      margin: "10px 0 4px 0",
      padding: "12px 14px",
      background: "var(--surface-1)",
      border: "1px solid var(--amber)",
      borderRadius: 8,
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "var(--amber)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>
        I need a few more details
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {questions.map((q, i) => (
          <div key={i}>
            <div style={{ fontSize: 13, color: "var(--ink-1)", marginBottom: 6 }}>
              {q.priority === "required" && (
                <span style={{ color: "var(--rose)", fontSize: 11, fontWeight: 700, marginRight: 6 }}>Required</span>
              )}
              {q.question_text}
            </div>
            {q.options && q.options.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {q.options.map((opt, j) => (
                  <button
                    key={j}
                    onClick={() => onQuickReply(opt)}
                    style={{
                      padding: "4px 12px",
                      borderRadius: 16,
                      border: "1px solid var(--line-light)",
                      background: "var(--surface-0)",
                      color: "var(--ink-1)",
                      fontSize: 12,
                      cursor: "pointer",
                      transition: "all 0.15s",
                    }}
                    onMouseEnter={e => { e.target.style.background = "var(--forest)"; e.target.style.color = "#fff"; e.target.style.borderColor = "var(--forest)"; }}
                    onMouseLeave={e => { e.target.style.background = "var(--surface-0)"; e.target.style.color = "var(--ink-1)"; e.target.style.borderColor = "var(--line-light)"; }}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11, color: "var(--ink-4)", marginTop: 10 }}>
        Click an option or type your answer below and press Ask.
      </div>
    </div>
  );
};


const Workspace = ({ user, profile, messages, onSendMessage, streaming, streamLabel, activeCanvas, layout, onExport, pendingQuestions }) => {
  const [prompt, setPrompt] = React.useState("");
  const [useProfile, setUseProfile] = React.useState(true);
  const [structuredOpen, setStructuredOpen] = React.useState(false);
  const [structured, setStructured] = React.useState(null);
  const [voiceActive, setVoiceActive] = React.useState(false);
  const messagesEndRef = React.useRef(null);
  const recognitionRef = React.useRef(null);

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const speechSupported = !!SpeechRecognition;

  const toggleVoice = () => {
    if (voiceActive) {
      recognitionRef.current && recognitionRef.current.stop();
      setVoiceActive(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setPrompt(transcript);
      setVoiceActive(false);
    };
    recognition.onerror = (e) => {
      console.error("SpeechRecognition error:", e.error);
      setVoiceActive(false);
    };
    recognition.onend = () => setVoiceActive(false);
    recognitionRef.current = recognition;
    recognition.start();
    setVoiceActive(true);
  };

  React.useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streaming, pendingQuestions]);

  const submit = (text) => {
    const finalText = (text || prompt).trim();
    if (!finalText || streaming) return;
    // Pass profile when "Use Profile" is toggled on
    onSendMessage(finalText, useProfile ? profile : null);
    setPrompt("");
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  // When user clicks a quick-reply chip, fill the input (don't auto-submit so they can review)
  const onQuickReply = (text) => {
    setPrompt(prev => prev ? `${prev} ${text}` : text);
  };

  const hasMessages = messages && messages.length > 0;
  const profileLabel = useProfile && profile?.identity?.filerStatus
    ? profile.identity.filerStatus
    : null;

  return (
    <main className="workspace" style={{display:"flex", flexDirection:"column", flex:1, overflow:"hidden"}}>
      <div className="topbar">
        <div className="crumb">
          <span>Ask</span>
          <Icon name="chevR" size={12}/>
          <strong>{hasMessages ? messages[0].content.slice(0, 40) : "New question"}</strong>
        </div>
        <div className="topbar-spacer"/>
        <span className="chip"><span className="dot"/>FBR data synced · TY 2025-26</span>
        <span className="chip"><span className="dot"/>{user.filerStatus}</span>
      </div>

      <div className="ws-body split" style={{flex:1, overflow:"hidden"}}>
        {/* ── Left panel: conversation thread + input ───────────── */}
        <section className="prompt-col" style={{display:"flex", flexDirection:"column", overflow:"hidden"}}>

          {/* Welcome or conversation */}
          {!hasMessages && !streaming ? (
            <div style={{flex:1, overflowY:"auto", padding:"24px 0"}}>
              <div className="hello">
                Salaam, {user.name.split(" ")[0]}. <em>What can I untangle</em> today?
              </div>
              <div className="hello-sub">Ask in English, Urdu, or Roman Urdu.</div>
              <div className="suggest-label">Try one of these</div>
              <div className="suggest-grid">
                {(window.SUGGESTIONS || []).map((s, i) => (
                  <button key={i} className="suggest" onClick={() => setPrompt(s.t)}>
                    <span className="k">{s.k}</span>
                    <span className="t">{s.t}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="conversation" style={{flex:1, overflowY:"auto", padding:"16px 0"}}>
              {(messages || []).map((m, idx) => {
                const isUser = m.role === "user";
                const isLastAssistant = m.role === "assistant" && idx === messages.length - 1;
                const prevSameRole = idx > 0 && messages[idx - 1].role === m.role;
                return (
                  <div key={m.id} className={`conv-turn ${isUser ? 'conv-user' : 'conv-bot'}`}>
                    {!prevSameRole && (
                      <div className="msg-label">{isUser ? "You" : "Tax Sathi"}</div>
                    )}
                    <div className="msg-bubble">{m.content}</div>
                    {isLastAssistant && pendingQuestions && !streaming && (
                      <div style={{width:"100%"}}>
                        <ClarificationPanel questions={pendingQuestions} onQuickReply={onQuickReply}/>
                      </div>
                    )}
                  </div>
                );
              })}
              {streaming && (
                <div className="conv-turn conv-bot">
                  <div className="msg-label">Tax Sathi</div>
                  <div className="msg-bubble" style={{color:"var(--ink-3)"}}>{streamLabel || "Thinking…"}</div>
                </div>
              )}
              <div ref={messagesEndRef}/>
            </div>
          )}

          {/* Input */}
          <div className="prompt-card" style={{flexShrink:0}}>
            <textarea
              className="prompt-input"
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              onKeyDown={onKey}
              placeholder={hasMessages ? "Ask a follow-up or answer the question above…" : "e.g. How much tax on PKR 3.8M salary?"}
              rows={3}
              disabled={streaming}
            />
            <div className="prompt-toolbar">
              <button
                className={`tool-btn ${useProfile ? 'active' : ''}`}
                onClick={() => setUseProfile(p => !p)}
                title={useProfile ? "Profile context will be sent with your message" : "Profile context is off"}
              >
                <Icon name="user" size={14}/>
                {useProfile && profileLabel
                  ? ` ${profileLabel}`
                  : " Use my profile"}
              </button>
              <button
                className={`tool-btn ${structured ? 'active' : ''}`}
                onClick={() => setStructuredOpen(true)}
                title="Attach structured data"
              >
                <Icon name="table" size={14}/> {structured ? `Structured (${Object.values(structured.fields).filter(v=>v).length} fields)` : "Structured file"}
              </button>
              {structured && (
                <button className="tool-btn" onClick={() => setStructured(null)} style={{padding:"6px 8px"}}>
                  <Icon name="x" size={12}/>
                </button>
              )}
              {speechSupported && (
                <button
                  className={`tool-btn${voiceActive ? " voice-active" : ""}`}
                  onClick={toggleVoice}
                  title={voiceActive ? "Stop recording" : "Speak your question"}
                  disabled={streaming}
                >
                  <Icon name="mic" size={14}/>
                </button>
              )}
              <button className="send-btn" onClick={() => submit()} disabled={!prompt.trim() || streaming}>
                Ask <Icon name="send" size={12}/>
              </button>
            </div>
            {useProfile && profile && (
              <div style={{fontSize:10, color:"var(--ink-4)", padding:"2px 10px 4px", fontFamily:"var(--mono)"}}>
                Profile: {profile.identity?.filerStatus || "?"} · {profile.identity?.residencyStatus || "?"} · TY {profile.preferences?.taxYear || "2025-2026"}
              </div>
            )}
          </div>
        </section>

        {/* ── Right panel: canvas ─────────────────────────────────── */}
        <CanvasView canvas={activeCanvas} streaming={streaming} onExport={onExport}/>
      </div>

      {structuredOpen && (
        <StructuredModal
          profile={profile}
          category={profile?.preferences?.category}
          onClose={() => setStructuredOpen(false)}
          onSubmit={(data) => { setStructured(data); setStructuredOpen(false); }}
        />
      )}
    </main>
  );
};
window.Workspace = Workspace;
