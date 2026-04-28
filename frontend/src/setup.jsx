// Post-signup profile setup wizard — 4 steps
const ProfileSetup = ({ user, onComplete, onSkip }) => {
  const [step, setStep] = React.useState(0);
  const [saving, setSaving] = React.useState(false);
  const [showErrors, setShowErrors] = React.useState(false);
  const [profile, setProfile] = React.useState(() => ({
    ...window.API.EMPTY_PROFILE,
    identity: { ...window.API.EMPTY_PROFILE.identity, fullName: user.name || "", email: user.email || "" },
  }));

  const update = (section, patch) => setProfile(p => ({ ...p, [section]: { ...p[section], ...patch } }));
  const addIncome = (inc) => setProfile(p => ({ ...p, income: [...p.income, inc] }));
  const removeIncome = (i) => setProfile(p => ({ ...p, income: p.income.filter((_, idx) => idx !== i) }));

  const steps = ["Identity", "Income", "Deductions", "Preferences"];

  const finish = async () => {
    if (!profile.preferences.category) {
      setShowErrors(true);
      return;
    }
    setSaving(true);
    await window.API.saveProfile(profile);
    setSaving(false);
    onComplete(profile);
  };

  return (
    <div className="setup-wrap">
      <div className="setup-card">
        <div className="setup-head">
          <div className="setup-brand">
            <div className="lm-sm">TS</div>
            <span>Set up your tax profile</span>
          </div>
          <div className="setup-steps">
            {steps.map((s, i) => (
              <div key={s} className={`setup-step ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
                <span className="n">{i + 1}</span>
                <span className="lbl">{s}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="setup-body">
          {step === 0 && <StepIdentity profile={profile} update={update}/>}
          {step === 1 && <StepIncome profile={profile} addIncome={addIncome} removeIncome={removeIncome}/>}
          {step === 2 && <StepDeductions profile={profile} update={update}/>}
          {step === 3 && <StepPrefs profile={profile} update={update} showErrors={showErrors}/>}
        </div>

        <div className="setup-foot">
          <button className="btn ghost sm" onClick={onSkip}>Skip for now</button>
          <div style={{flex:1}}/>
          {step > 0 && <button className="btn ghost sm" onClick={() => setStep(s => s - 1)}>Back</button>}
          {step < 3 && <button className="btn sm" onClick={() => setStep(s => s + 1)}>Continue</button>}
          {step === 3 && <button className="btn sm" onClick={finish} disabled={saving}>{saving ? "Saving…" : "Finish setup"}</button>}
        </div>
      </div>
    </div>
  );
};

const StepIdentity = ({ profile, update }) => (
  <div className="setup-grid">
    <div className="setup-intro">
      <h2>Let's get your basics.</h2>
      <p>We use this to tailor answers to your tax situation. Only the fields you mark as usable are sent with prompts.</p>
    </div>
    <div>
      <div className="field"><label>Full name</label><input value={profile.identity.fullName} onChange={e => update('identity', {fullName: e.target.value})}/></div>
      <div className="grid-2">
        <div className="field"><label>CNIC</label><input value={profile.identity.cnic} onChange={e => update('identity', {cnic: e.target.value})} placeholder="00000-0000000-0"/></div>
        <div className="field"><label>NTN</label><input value={profile.identity.ntn} onChange={e => update('identity', {ntn: e.target.value})} placeholder="0000000-0"/></div>
      </div>
      <div className="grid-2">
        <div className="field"><label>Filer status</label>
          <select value={profile.identity.filerStatus} onChange={e => update('identity', {filerStatus: e.target.value})}>
            <option>Filer</option><option>Non-filer</option>
          </select>
        </div>
        <div className="field"><label>Residency</label>
          <select value={profile.identity.residencyStatus} onChange={e => update('identity', {residencyStatus: e.target.value})}>
            <option>Resident</option><option>Non-resident</option>
          </select>
        </div>
      </div>
      <div className="field"><label>City</label><input value={profile.identity.city} onChange={e => update('identity', {city: e.target.value})} placeholder="Karachi, Lahore, Islamabad…"/></div>
    </div>
  </div>
);

const INCOME_TYPES = [
  { id: "salary", label: "Salary" },
  { id: "freelance", label: "Freelance / contract" },
  { id: "business", label: "Business / AOP" },
  { id: "rental", label: "Rental" },
  { id: "capital_gains", label: "Capital gains (PSX, property)" },
];

const StepIncome = ({ profile, addIncome, removeIncome }) => {
  const [t, setT] = React.useState("salary");
  const [a, setA] = React.useState("");
  const [s, setS] = React.useState("");

  return (
    <div className="setup-grid">
      <div className="setup-intro">
        <h2>Your income sources.</h2>
        <p>Add every stream — annual amounts in PKR. You can edit these anytime from Profile.</p>
      </div>
      <div>
        <div className="grid-income">
          <div className="field"><label>Type</label>
            <select value={t} onChange={e => setT(e.target.value)}>
              {INCOME_TYPES.map(x => <option key={x.id} value={x.id}>{x.label}</option>)}
            </select>
          </div>
          <div className="field"><label>Annual (PKR)</label><input value={a} onChange={e => setA(e.target.value.replace(/\D/g,''))} placeholder="3800000"/></div>
          <div className="field"><label>Source (optional)</label><input value={s} onChange={e => setS(e.target.value)} placeholder="Employer / client"/></div>
          <button className="btn sm" onClick={() => { if(a){addIncome({type:t, annualAmount:+a, source:s}); setA(''); setS('');} }}>Add</button>
        </div>

        <div className="income-list">
          {profile.income.length === 0 && <div className="income-empty">No income sources added yet.</div>}
          {profile.income.map((inc, i) => (
            <div key={i} className="income-row">
              <span className="t">{(INCOME_TYPES.find(x => x.id === inc.type) || {}).label || inc.type}</span>
              <span className="s muted">{inc.source || "—"}</span>
              <span className="a mono">PKR {Number(inc.annualAmount).toLocaleString()}</span>
              <button className="icon-btn" onClick={() => removeIncome(i)}><Icon name="close" size={12}/></button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const StepDeductions = ({ profile, update }) => (
  <div className="setup-grid">
    <div className="setup-intro">
      <h2>Deductions & credits.</h2>
      <p>Optional — leave 0 if not applicable. Annual amounts in PKR.</p>
    </div>
    <div>
      <div className="grid-2">
        <div className="field"><label>Zakat paid</label><input value={profile.deductions.zakat} onChange={e => update('deductions', {zakat: +e.target.value.replace(/\D/g,'') || 0})}/></div>
        <div className="field"><label>Section 61 donations</label><input value={profile.deductions.section61Donations} onChange={e => update('deductions', {section61Donations: +e.target.value.replace(/\D/g,'') || 0})}/></div>
      </div>
      <div className="grid-2">
        <div className="field"><label>Sec 60C housing finance</label><input value={profile.deductions.section60CHousingFinance} onChange={e => update('deductions', {section60CHousingFinance: +e.target.value.replace(/\D/g,'') || 0})}/></div>
        <div className="field"><label>Pension contribution</label><input value={profile.deductions.pensionContribution} onChange={e => update('deductions', {pensionContribution: +e.target.value.replace(/\D/g,'') || 0})}/></div>
      </div>
    </div>
  </div>
);

const StepPrefs = ({ profile, update, showErrors }) => (
  <div className="setup-grid">
    <div className="setup-intro">
      <h2>Preferences.</h2>
      <p>Default settings for how Tax Sathi works with you. <strong>Category</strong> determines which FBR rules apply to your returns.</p>
    </div>
    <div>
      <div className="field"><label>Active tax year</label>
        <select value={profile.preferences.taxYear} onChange={e => update('preferences', {taxYear: e.target.value})}>
          <option>2025</option><option>2024</option><option>2023</option>
        </select>
      </div>
      <div className="field">
        <label>Category <span style={{color:"var(--rose)"}}>*</span></label>
        <select
          value={profile.preferences.category}
          onChange={e => update('preferences', {category: e.target.value})}
          style={showErrors && !profile.preferences.category ? {borderColor:"var(--rose)"} : undefined}
        >
          <option value="" disabled>Select your FBR taxpayer category…</option>
          {window.API.FBR_CATEGORIES.map(c => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>
        {profile.preferences.category ? (
          <div style={{fontSize:12, color:"var(--ink-muted)", marginTop:6}}>
            {window.API.FBR_CATEGORIES.find(c => c.id === profile.preferences.category)?.hint}
          </div>
        ) : showErrors ? (
          <div style={{fontSize:12, color:"var(--rose)", marginTop:6}}>Required — this is sent with every tax calculation.</div>
        ) : null}
      </div>
      <div className="field"><label>Language</label>
        <select value={profile.preferences.language} onChange={e => update('preferences', {language: e.target.value})}>
          <option value="en">English</option>
          <option value="ur">اردو (Urdu)</option>
          <option value="roman-ur">Roman Urdu</option>
        </select>
      </div>
      <div style={{display:"flex", alignItems:"center", gap:10, padding:"10px 0"}}>
        <div className={`switch ${profile.preferences.reminders ? 'on' : ''}`} onClick={() => update('preferences', {reminders: !profile.preferences.reminders})}/>
        <span style={{fontSize:13}}>Email me FBR deadline reminders</span>
      </div>
    </div>
  </div>
);

window.ProfileSetup = ProfileSetup;
