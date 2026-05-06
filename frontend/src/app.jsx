const { useState, useEffect, useRef } = React;

const App = () => {
  const [bootState, setBootState] = useState("boot"); // boot | auth | setup | app | reset_password
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [resetToken, setResetToken] = useState(null);

  // Sessions & chat state
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [activeCanvas, setActiveCanvas] = useState(null);

  const [streaming, setStreaming] = useState(false);
  const [streamLabel, setStreamLabel] = useState("");
  const [pendingQuestions, setPendingQuestions] = useState(null); // clarification questions from last response
  const [activeNav, setActiveNav] = useState("chat");
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState(null);

  const [tweaks, setTweaks] = useState(window.__TS_TWEAKS);
  const [tweaksVisible, setTweaksVisible] = useState(false);

  useEffect(() => { document.documentElement.setAttribute("data-theme", tweaks.theme); }, [tweaks.theme]);

  // ── Boot — validate existing token ────────────────────────────────────────
  useEffect(() => {
    (async () => {
      // Check for OAuth token injected via URL query param (Google OAuth callback)
      const urlParams = new URLSearchParams(window.location.search);

      // Password reset link takes priority — show reset form immediately
      const urlResetToken = urlParams.get("reset_token");
      if (urlResetToken) {
        window.history.replaceState({}, "", "/");
        setResetToken(urlResetToken);
        setBootState("reset_password");
        return;
      }

      const urlToken = urlParams.get("token");
      const isNewGoogleUser = urlParams.get("is_new") === "1";
      if (urlToken) {
        localStorage.setItem("ts_token", urlToken);
        window.history.replaceState({}, "", "/");
      }

      const token = window.API.getToken();
      if (!token) { setBootState("auth"); return; }
      try {
        await window.API.getCurrentUser();
        const p = await window.API.getProfile();
        if (!p) { setBootState("auth"); return; }
        setProfile(p);
        setUser({ name: p.identity.fullName || "User", email: p.identity.email });
        const sessionList = await window.API.getSessions().catch(() => []);
        setSessions(sessionList);
        // New Google users go to profile setup just like new email signups
        setBootState(isNewGoogleUser ? "setup" : "app");
      } catch {
        setBootState("auth");
      }
    })();
  }, []);

  // ── Tweaks protocol ───────────────────────────────────────────────────────
  useEffect(() => {
    const onMsg = (e) => {
      if (!e.data || typeof e.data !== "object") return;
      if (e.data.type === "__activate_edit_mode") setTweaksVisible(true);
      if (e.data.type === "__deactivate_edit_mode") setTweaksVisible(false);
    };
    window.addEventListener("message", onMsg);
    window.parent.postMessage({type: "__edit_mode_available"}, "*");
    return () => window.removeEventListener("message", onMsg);
  }, []);

  const updateTweak = (patch) => {
    setTweaks(prev => {
      const next = {...prev, ...patch};
      window.parent.postMessage({type: "__edit_mode_set_keys", edits: patch}, "*");
      return next;
    });
  };

  const showToast = (t) => { setToast(t); setTimeout(() => setToast(null), 2200); };

  // ── Auth callback ─────────────────────────────────────────────────────────
  const onAuth = async (res, opts = {}) => {
    setUser(res.user);
    setProfile(res.profile);
    const sessionList = await window.API.getSessions().catch(() => []);
    setSessions(sessionList);
    if ((opts.isSignup && !res.hasProfile) || opts.forceSetup) setBootState("setup");
    else {
      if (!res.profile) setProfile(window.API.EMPTY_PROFILE);
      setBootState("app");
    }
  };

  const onSetupDone = (p) => { setProfile(p); setBootState("app"); showToast("Profile saved"); };
  const onSetupSkip = () => { setProfile(window.API.EMPTY_PROFILE); setBootState("app"); };

  const onLogout = async () => {
    await window.API.logout();
    setUser(null); setProfile(null);
    setSessions([]); setCurrentSessionId(null);
    setMessages([]); setActiveCanvas(null);
    setBootState("auth");
    showToast("Logged out");
  };

  // ── Send message ──────────────────────────────────────────────────────────
  // profileToUse: the profile object if "Use Profile" is on, or null
  // imageContext: plain-text extracted from an uploaded image, or null
  const onSendMessage = async (text, profileToUse = null, imageContext = null) => {
    let sessionId = currentSessionId;

    // Create session lazily on first message
    if (!sessionId) {
      try {
        const session = await window.API.createSession();
        sessionId = session.id;
        setCurrentSessionId(sessionId);
        setSessions(prev => [session, ...prev]);
      } catch (err) {
        showToast("Failed to create session: " + err.message);
        return;
      }
    }

    // Optimistic user message
    const userMsg = {
      id: "tmp-u-" + Date.now(),
      role: "user",
      content: text,
      canvas_data: null,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setPendingQuestions(null); // clear previous clarification questions
    setStreaming(true);
    setStreamLabel("Processing…");
    setActiveCanvas(null);

    try {
      const conversationHistory = messages.map(m => ({ role: m.role, content: m.content }));
      const profileContext = profileToUse ? window.API.formatProfileContext(profileToUse) : null;
      const res = await window.API.sendMessage(sessionId, text, conversationHistory, profileContext, imageContext);

      const assistantMsg = {
        id: "tmp-a-" + Date.now(),
        role: "assistant",
        content: res.assistant_message,
        canvas_data: res.canvas,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMsg]);
      setActiveCanvas(res.canvas);

      // Surface clarification questions so the Workspace can render them
      if (res.stage === "clarification_needed" && res.questions?.length > 0) {
        setPendingQuestions(res.questions);
      } else {
        setPendingQuestions(null);
      }

      // Update title in sidebar for new sessions
      setSessions(prev => prev.map(s => {
        if (s.id !== sessionId) return s;
        const title = s.title === "New Chat" ? text.slice(0, 50) : s.title;
        return {...s, title, updated_at: new Date().toISOString(), last_message_preview: text.slice(0, 100)};
      }));
    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== userMsg.id));
      showToast("Error: " + (err.message || "Something went wrong"));
    } finally {
      setStreaming(false);
      setStreamLabel("");
    }
  };

  // ── Session navigation ────────────────────────────────────────────────────
  const onSelectSession = async (id) => {
    setCurrentSessionId(id);
    setStreaming(false);
    setActiveCanvas(null);
    setActiveNav("chat");
    try {
      const session = await window.API.getSession(id);
      setMessages(session.messages);
      const lastAssistant = [...session.messages].reverse().find(m => m.role === "assistant" && m.canvas_data);
      setActiveCanvas(lastAssistant?.canvas_data || null);
    } catch {
      showToast("Failed to load session");
    }
  };

  const onNew = () => {
    setMessages([]);
    setCurrentSessionId(null);
    setActiveCanvas(null);
    setStreaming(false);
    setPendingQuestions(null);
    setActiveNav("chat");
  };

  const onDeleteSession = async (id) => {
    try {
      await window.API.deleteSession(id);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (currentSessionId === id) onNew();
    } catch {
      showToast("Failed to delete session");
    }
  };

  const onNav = (n) => {
    setActiveNav(n);
    if (n === "calendar") setModal("calendar");
    else if (n === "profile") setModal("profile");
  };

  const onExport = async (kind) => {
    if (kind === "copy") { showToast("Copied to clipboard"); return; }
    if (kind === "pdf") { showToast("PDF export coming soon"); return; }
    if (kind === "share") { showToast("Share link coming soon"); }
  };

  const onProfileSaved = (p) => { setProfile(p); showToast("Profile updated"); };

  // ── Render ────────────────────────────────────────────────────────────────
  if (bootState === "boot") return (
    <div style={{display:"grid", placeItems:"center", height:"100vh", color:"var(--ink-3)"}}>Loading…</div>
  );

  if (bootState === "reset_password") return (
    <>
      <ResetPasswordScreen resetToken={resetToken} onDone={() => setBootState("auth")}/>
      <Tweaks visible={tweaksVisible} values={tweaks} onChange={updateTweak}/>
      {toast && <div className="toast">{toast}</div>}
    </>
  );

  if (bootState === "auth") return (
    <>
      <AuthScreen onAuth={onAuth}/>
      <Tweaks visible={tweaksVisible} values={tweaks} onChange={updateTweak}/>
      {toast && <div className="toast">{toast}</div>}
    </>
  );

  if (bootState === "setup") return (
    <>
      <ProfileSetup user={user} onComplete={onSetupDone} onSkip={onSetupSkip}/>
      <Tweaks visible={tweaksVisible} values={tweaks} onChange={updateTweak}/>
      {toast && <div className="toast">{toast}</div>}
    </>
  );

  const shellUser = {
    name: profile?.identity?.fullName || user.name,
    email: profile?.identity?.email || user.email,
    initials: (profile?.identity?.fullName || user.name || "U U").split(" ").map(s=>s[0]).slice(0,2).join(""),
    ntn: profile?.identity?.ntn || "—",
    filerStatus: profile?.identity?.filerStatus || "Non-filer",
  };

  return (
    <>
      <div className="app" data-screen-label="Main">
        <Sidebar
          user={shellUser}
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelectSession={onSelectSession}
          onDeleteSession={onDeleteSession}
          onNew={onNew}
          onNav={onNav}
          activeNav={activeNav}
          onLogout={onLogout}
          onProfile={() => setModal("profile")}
        />
        <div style={{display:"flex", overflow:"hidden", minWidth:0, flex:1}}>
          <Workspace
            user={shellUser}
            profile={profile}
            messages={messages}
            onSendMessage={onSendMessage}
            streaming={streaming}
            streamLabel={streamLabel}
            activeCanvas={activeCanvas}
            layout={tweaks.layout}
            onExport={onExport}
            pendingQuestions={pendingQuestions}
          />
        </div>
      </div>

      {modal === "calendar" && <CalendarModal onClose={() => { setModal(null); setActiveNav("chat"); }}/>}
      {modal === "profile" && <ProfileModal user={shellUser} onClose={() => { setModal(null); setActiveNav("chat"); }} onSaved={onProfileSaved}/>}

      <Tweaks visible={tweaksVisible} values={tweaks} onChange={updateTweak}/>
      {toast && <div className="toast">{toast}</div>}
    </>
  );
};

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App/>);
