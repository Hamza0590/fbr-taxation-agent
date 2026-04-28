// Split-screen auth: brand on left, form on right
const AuthScreen = ({ onAuth }) => {
  const [mode, setMode] = React.useState("login");
  const [email, setEmail] = React.useState("ayesha.khan@gmail.com");
  const [password, setPassword] = React.useState("••••••••");
  const [name, setName] = React.useState("");
  const [ntn, setNtn] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = mode === "login"
        ? await window.API.login(email, password)
        : await window.API.signup(email, password, name || "New User");
      await onAuth(res, { isSignup: mode === "signup" });
    } catch (err) {
      alert(err.message || "Authentication failed");
    } finally { setLoading(false); }
  };

  const social = async (provider) => {
    setLoading(true);
    try {
      const res = await window.API.socialAuth(provider);
      await onAuth(res, { isSignup: false });
    } catch (err) {
      alert(err.message || "Social auth failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="auth">
      <aside className="auth-brand">
        <div className="auth-brand-logo">
          <div className="lm">TS</div>
          <span>Tax Sathi</span>
        </div>

        <div className="auth-brand-hero">
          <div className="auth-brand-kicker">Pakistan · FBR compliant</div>
          <h1 className="auth-brand-headline">
            Your tax <em>saathi</em>,<br/>one prompt away.
          </h1>
          <p className="auth-brand-sub">
            Ask anything about ITO 2001, FBR slabs, withholding, or your own return — in plain Urdu or English.
            Get structured answers with the reasoning, sources, and calculations shown in full.
          </p>
        </div>

        <div className="auth-brand-proof">
          <div><strong>842k</strong><span>Questions answered</span></div>
          <div><strong>FBR</strong><span>Live slab data</span></div>
          <div><strong>Audit</strong><span>trail per answer</span></div>
        </div>
      </aside>

      <section className="auth-form-wrap">
        <div className="auth-form">
          <div className="auth-tabs" data-mode={mode}>
            <span className="tab-pill" aria-hidden="true"/>
            <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Log in</button>
            <button className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")}>Sign up</button>
          </div>

          <div key={mode} className="auth-mode-content">
          <h1>{mode === "login" ? "Welcome back." : "Create your account."}</h1>
          <p className="sub">{mode === "login" ? "Pick up where you left off with your tax queries." : "Takes 30 seconds. NTN is optional — add it later."}</p>

          <form onSubmit={submit}>
            {mode === "signup" && (
              <div className="field">
                <label>Full name</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="As per your CNIC" required />
              </div>
            )}
            <div className="field">
              <label>Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@domain.com" required />
            </div>
            <div className="field">
              <label>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
              {mode === "login" && <div style={{textAlign:"right", marginTop:4}}><a className="hint" style={{color:"var(--forest)", cursor:"pointer"}}>Forgot?</a></div>}
            </div>
            {mode === "signup" && (
              <div className="field">
                <label>NTN <span className="muted">(optional)</span></label>
                <input value={ntn} onChange={e => setNtn(e.target.value)} placeholder="e.g. 3740187-2" />
                <div className="hint">We'll use it to pre-fill your tax context. You can skip and add later.</div>
              </div>
            )}

            <button className="btn block" type="submit" disabled={loading} style={{marginTop: 10}}>
              {loading ? "Signing you in…" : mode === "login" ? "Log in" : "Create account"}
              {!loading && <Icon name="arrow" size={14} />}
            </button>
          </form>
          </div>

          <div className="auth-divider">or continue with</div>
          <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap: 10}}>
            <button className="btn ghost" onClick={() => social('google')}>Google</button>
            <button className="btn ghost" onClick={() => social('nadra')}>CNIC / NADRA</button>
          </div>

          <div className="auth-foot">
            {mode === "login" ? (
              <>New to Tax Sathi? <a onClick={() => setMode("signup")}>Create an account</a></>
            ) : (
              <>Already a filer? <a onClick={() => setMode("login")}>Log in</a></>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
window.AuthScreen = AuthScreen;
