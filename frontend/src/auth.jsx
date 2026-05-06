// Split-screen auth: brand on left, form on right
const AuthScreen = ({ onAuth }) => {
  const [mode, setMode] = React.useState("login");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [name, setName] = React.useState("");
  const [ntn, setNtn] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  // Password visibility toggles
  const [showPassword, setShowPassword] = React.useState(false);
  const [showCnicPassword, setShowCnicPassword] = React.useState(false);

  // CNIC mini-form state
  const [showCnic, setShowCnic] = React.useState(false);
  const [cnic, setCnic] = React.useState("");
  const [cnicPassword, setCnicPassword] = React.useState("");
  const [cnicError, setCnicError] = React.useState("");

  // Forgot password state
  const [showForgot, setShowForgot] = React.useState(false);
  const [forgotEmail, setForgotEmail] = React.useState("");
  const [forgotStatus, setForgotStatus] = React.useState(null); // { type: "success"|"error", message: string }
  const [forgotLoading, setForgotLoading] = React.useState(false);

  const CNIC_PATTERN = /^\d{5}-\d{7}-\d$/;

  const switchMode = (m) => {
    setMode(m);
    setShowForgot(false);
    setForgotStatus(null);
  };

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

  const submitCnic = async (e) => {
    e.preventDefault();
    setCnicError("");
    if (!CNIC_PATTERN.test(cnic)) {
      setCnicError("CNIC must be in format XXXXX-XXXXXXX-X (e.g. 12345-1234567-1)");
      return;
    }
    setLoading(true);
    try {
      const res = await window.API.cnicLogin(cnic, cnicPassword);
      const hasExtendedProfile = !!window.API.loadLocal("profile_extended");
      await onAuth(res, { isSignup: false, forceSetup: !hasExtendedProfile });
    } catch (err) {
      setCnicError(err.message || "Invalid CNIC or password");
    } finally { setLoading(false); }
  };

  const submitForgot = async (e) => {
    e.preventDefault();
    setForgotStatus(null);
    setForgotLoading(true);
    try {
      await window.API.forgotPassword(forgotEmail);
      setForgotStatus({ type: "success", message: "If that email is registered, a reset link has been sent. Check your inbox." });
    } catch (err) {
      setForgotStatus({ type: "error", message: err.message || "Request failed. Please try again." });
    } finally {
      setForgotLoading(false);
    }
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
            <button className={mode === "login" ? "active" : ""} onClick={() => switchMode("login")}>Log in</button>
            <button className={mode === "signup" ? "active" : ""} onClick={() => switchMode("signup")}>Sign up</button>
          </div>

          <div key={mode} className="auth-mode-content">
          {mode === "login" && showForgot ? (
            <div>
              <a
                style={{cursor:"pointer", color:"var(--forest)", fontSize:13, display:"inline-block", marginBottom:16}}
                onClick={() => { setShowForgot(false); setForgotStatus(null); }}
              >← Back to login</a>
              <h1>Forgot your password?</h1>
              <p className="sub">Enter your account email and we'll send you a reset link.</p>
              <form onSubmit={submitForgot} style={{display:"flex", flexDirection:"column", gap:8}}>
                <div className="field">
                  <label>Email</label>
                  <input
                    type="email"
                    value={forgotEmail}
                    onChange={e => setForgotEmail(e.target.value)}
                    placeholder="you@domain.com"
                    required
                  />
                </div>
                {forgotStatus && (
                  <div style={{fontSize:13, color: forgotStatus.type === "success" ? "var(--forest)" : "var(--rose)", padding:"4px 0", lineHeight:1.5}}>
                    {forgotStatus.message}
                  </div>
                )}
                <button className="btn block" type="submit" disabled={forgotLoading} style={{marginTop:4}}>
                  {forgotLoading ? "Sending…" : "Send Reset Link"}
                  {!forgotLoading && <Icon name="arrow" size={14} />}
                </button>
              </form>
            </div>
          ) : (
            <>
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
              <div style={{position:"relative"}}>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  style={{paddingRight: 36, width:"100%", boxSizing:"border-box"}}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  style={{position:"absolute", right:8, top:"50%", transform:"translateY(-50%)", background:"none", border:"none", cursor:"pointer", color:"var(--ink-3)", padding:0, display:"flex", alignItems:"center"}}
                  tabIndex={-1}
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  <Icon name={showPassword ? "eyeOff" : "eye"} size={16}/>
                </button>
              </div>
              {mode === "login" && (
                <div style={{textAlign:"right", marginTop:4}}>
                  <a className="hint" style={{color:"var(--forest)", cursor:"pointer"}} onClick={() => { setShowForgot(true); setForgotStatus(null); setForgotEmail(""); }}>Forgot?</a>
                </div>
              )}
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
            </>
          )}
          </div>

          <div className="auth-divider">or continue with</div>
          <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap: 10}}>
            <button className="btn ghost" onClick={() => window.API.googleLogin()}>Google</button>
            <button className="btn ghost" onClick={() => { setShowCnic(v => !v); setCnicError(""); }}>
              CNIC / NADRA
            </button>
          </div>

          {showCnic && (
            <form onSubmit={submitCnic} style={{marginTop: 12, display:"flex", flexDirection:"column", gap: 8}}>
              <div className="field" style={{marginBottom: 0}}>
                <label>CNIC</label>
                <input
                  value={cnic}
                  onChange={e => { setCnic(e.target.value); setCnicError(""); }}
                  placeholder="XXXXX-XXXXXXX-X"
                  required
                />
              </div>
              <div className="field" style={{marginBottom: 0}}>
                <label>Password</label>
                <div style={{position:"relative"}}>
                  <input
                    type={showCnicPassword ? "text" : "password"}
                    value={cnicPassword}
                    onChange={e => setCnicPassword(e.target.value)}
                    required
                    style={{paddingRight: 36, width:"100%", boxSizing:"border-box"}}
                  />
                  <button
                    type="button"
                    onClick={() => setShowCnicPassword(v => !v)}
                    style={{position:"absolute", right:8, top:"50%", transform:"translateY(-50%)", background:"none", border:"none", cursor:"pointer", color:"var(--ink-3)", padding:0, display:"flex", alignItems:"center"}}
                    tabIndex={-1}
                    title={showCnicPassword ? "Hide password" : "Show password"}
                  >
                    <Icon name={showCnicPassword ? "eyeOff" : "eye"} size={16}/>
                  </button>
                </div>
              </div>
              {cnicError && (
                <div style={{fontSize: 12, color: "var(--rose)", padding: "4px 0"}}>{cnicError}</div>
              )}
              <button className="btn block" type="submit" disabled={loading}>
                {loading ? "Signing you in…" : "Login with CNIC"}
              </button>
            </form>
          )}

          <div className="auth-foot">
            {mode === "login" ? (
              <>New to Tax Sathi? <a onClick={() => switchMode("signup")}>Create an account</a></>
            ) : (
              <>Already a filer? <a onClick={() => switchMode("login")}>Log in</a></>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
window.AuthScreen = AuthScreen;


// Reset password screen — shown when ?reset_token= is present in the URL
const ResetPasswordScreen = ({ resetToken, onDone }) => {
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [showNew, setShowNew] = React.useState(false);
  const [showConfirm, setShowConfirm] = React.useState(false);
  const [error, setError] = React.useState("");
  const [success, setSuccess] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await window.API.resetPassword(resetToken, newPassword);
      setSuccess(true);
      setTimeout(() => onDone(), 2000);
    } catch (err) {
      setError(err.message || "Reset failed. The link may have expired.");
    } finally {
      setLoading(false);
    }
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
          </p>
        </div>
      </aside>

      <section className="auth-form-wrap">
        <div className="auth-form">
          <div className="auth-mode-content">
            <h1>Set a new password.</h1>
            <p className="sub">Choose a strong password of at least 8 characters.</p>

            {success ? (
              <div style={{color:"var(--forest)", fontSize:14, padding:"12px 0", lineHeight:1.6}}>
                Password updated successfully. Redirecting to login…
              </div>
            ) : (
              <form onSubmit={submit} style={{display:"flex", flexDirection:"column", gap:8}}>
                <div className="field">
                  <label>New Password</label>
                  <div style={{position:"relative"}}>
                    <input
                      type={showNew ? "text" : "password"}
                      value={newPassword}
                      onChange={e => setNewPassword(e.target.value)}
                      required
                      style={{paddingRight:36, width:"100%", boxSizing:"border-box"}}
                    />
                    <button
                      type="button"
                      onClick={() => setShowNew(v => !v)}
                      style={{position:"absolute", right:8, top:"50%", transform:"translateY(-50%)", background:"none", border:"none", cursor:"pointer", color:"var(--ink-3)", padding:0, display:"flex", alignItems:"center"}}
                      tabIndex={-1}
                      title={showNew ? "Hide password" : "Show password"}
                    >
                      <Icon name={showNew ? "eyeOff" : "eye"} size={16}/>
                    </button>
                  </div>
                </div>

                <div className="field">
                  <label>Confirm Password</label>
                  <div style={{position:"relative"}}>
                    <input
                      type={showConfirm ? "text" : "password"}
                      value={confirmPassword}
                      onChange={e => setConfirmPassword(e.target.value)}
                      required
                      style={{paddingRight:36, width:"100%", boxSizing:"border-box"}}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm(v => !v)}
                      style={{position:"absolute", right:8, top:"50%", transform:"translateY(-50%)", background:"none", border:"none", cursor:"pointer", color:"var(--ink-3)", padding:0, display:"flex", alignItems:"center"}}
                      tabIndex={-1}
                      title={showConfirm ? "Hide password" : "Show password"}
                    >
                      <Icon name={showConfirm ? "eyeOff" : "eye"} size={16}/>
                    </button>
                  </div>
                </div>

                {error && (
                  <div style={{fontSize:13, color:"var(--rose)", padding:"4px 0", lineHeight:1.5}}>
                    {error}
                  </div>
                )}

                <button className="btn block" type="submit" disabled={loading} style={{marginTop:4}}>
                  {loading ? "Updating…" : "Update Password"}
                  {!loading && <Icon name="arrow" size={14} />}
                </button>
              </form>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
window.ResetPasswordScreen = ResetPasswordScreen;
