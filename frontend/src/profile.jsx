// Editable profile modal — reads from API, saves via API
const ProfileModal = ({ user, onClose, onSaved }) => {
  const [profile, setProfile] = React.useState(null);
  const [saving, setSaving] = React.useState(false);
  const [dirty, setDirty] = React.useState(false);
  const [tab, setTab] = React.useState("identity");

  React.useEffect(() => {
    window.API.getProfile().then(p => setProfile(p || window.API.EMPTY_PROFILE));
  }, []);

  if (!profile) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal" onClick={e => e.stopPropagation()}>
          <div className="modal-body" style={{padding:40, textAlign:"center", color:"var(--ink-3)"}}>Loading profile…</div>
        </div>
      </div>
    );
  }

  const upd = (section, patch) => { setProfile(p => ({...p, [section]: {...p[section], ...patch}})); setDirty(true); };
  const addIncome = (inc) => { setProfile(p => ({...p, income: [...p.income, inc]})); setDirty(true); };
  const removeIncome = (i) => { setProfile(p => ({...p, income: p.income.filter((_, idx) => idx !== i)})); setDirty(true); };

  const save = async () => {
    setSaving(true);
    const saved = await window.API.saveProfile(profile);
    setSaving(false);
    setDirty(false);
    onSaved && onSaved(saved);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Profile & tax context</h2>
          {dirty && <span className="chip" style={{marginRight:10, color:"var(--amber)"}}><span className="dot" style={{background:"var(--amber)"}}/>Unsaved</span>}
          <button className="close-x" onClick={onClose}><Icon name="close" size={16}/></button>
        </div>

        <div className="profile-tabs">
          {["identity","income","deductions","preferences"].map(t => (
            <button key={t} className={`profile-tab ${tab===t?'active':''}`} onClick={() => setTab(t)}>
              {t[0].toUpperCase()+t.slice(1)}
            </button>
          ))}
        </div>

        <div className="modal-body">
          {tab === "identity" && (
            <div>
              <div className="field"><label>Full name</label><input value={profile.identity.fullName} onChange={e => upd('identity',{fullName:e.target.value})}/></div>
              <div className="field"><label>Email</label><input value={profile.identity.email} onChange={e => upd('identity',{email:e.target.value})}/></div>
              <div className="grid-2">
                <div className="field"><label>CNIC</label><input value={profile.identity.cnic} onChange={e => upd('identity',{cnic:e.target.value})} placeholder="00000-0000000-0"/></div>
                <div className="field"><label>NTN</label><input value={profile.identity.ntn} onChange={e => upd('identity',{ntn:e.target.value})}/></div>
              </div>
              <div className="grid-2">
                <div className="field"><label>Filer status</label>
                  <select value={profile.identity.filerStatus} onChange={e => upd('identity',{filerStatus:e.target.value})}>
                    <option>Filer</option><option>Non-filer</option>
                  </select>
                </div>
                <div className="field"><label>Residency</label>
                  <select value={profile.identity.residencyStatus} onChange={e => upd('identity',{residencyStatus:e.target.value})}>
                    <option>Resident</option><option>Non-resident</option>
                  </select>
                </div>
              </div>
              <div className="field"><label>City</label><input value={profile.identity.city} onChange={e => upd('identity',{city:e.target.value})}/></div>
            </div>
          )}

          {tab === "income" && <IncomeEditor profile={profile} addIncome={addIncome} removeIncome={removeIncome}/>}

          {tab === "deductions" && (
            <div>
              <div className="grid-2">
                <div className="field"><label>Zakat (PKR)</label><input value={profile.deductions.zakat} onChange={e => upd('deductions',{zakat:+e.target.value.replace(/\D/g,'')||0})}/></div>
                <div className="field"><label>Sec 61 donations</label><input value={profile.deductions.section61Donations} onChange={e => upd('deductions',{section61Donations:+e.target.value.replace(/\D/g,'')||0})}/></div>
              </div>
              <div className="grid-2">
                <div className="field"><label>Sec 60C housing</label><input value={profile.deductions.section60CHousingFinance} onChange={e => upd('deductions',{section60CHousingFinance:+e.target.value.replace(/\D/g,'')||0})}/></div>
                <div className="field"><label>Pension</label><input value={profile.deductions.pensionContribution} onChange={e => upd('deductions',{pensionContribution:+e.target.value.replace(/\D/g,'')||0})}/></div>
              </div>
            </div>
          )}

          {tab === "preferences" && (
            <div>
              <div className="grid-2">
                <div className="field"><label>Tax year</label>
                  <select value={profile.preferences.taxYear} onChange={e => upd('preferences',{taxYear:e.target.value})}>
                    <option>2025</option><option>2024</option><option>2023</option>
                  </select>
                </div>
                <div className="field"><label>Category <span style={{color:"var(--rose)"}}>*</span></label>
                  <select
                    value={profile.preferences.category || ""}
                    onChange={e => upd('preferences',{category:e.target.value})}
                    style={!profile.preferences.category ? {borderColor:"var(--rose)"} : undefined}
                  >
                    <option value="" disabled>Select category…</option>
                    {window.API.FBR_CATEGORIES.map(c => (
                      <option key={c.id} value={c.id}>{c.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="field"><label>Language</label>
                <select value={profile.preferences.language} onChange={e => upd('preferences',{language:e.target.value})}>
                  <option value="en">English</option>
                  <option value="ur">اردو (Urdu)</option>
                  <option value="roman-ur">Roman Urdu</option>
                </select>
              </div>
              <div style={{display:"flex",alignItems:"center",gap:10,padding:"12px 0"}}>
                <div className={`switch ${profile.preferences.reminders?'on':''}`} onClick={() => upd('preferences',{reminders:!profile.preferences.reminders})}/>
                <span style={{fontSize:13}}>Email me FBR deadline reminders</span>
              </div>
            </div>
          )}
        </div>

        <div className="modal-foot">
          <span style={{fontSize:11, color:"var(--ink-4)", fontFamily:"var(--mono)"}}>This data is sent as JSON with every prompt when "Use my profile" is on.</span>
          <div style={{flex:1}}/>
          <button className="btn ghost sm" onClick={onClose}>Cancel</button>
          <button className="btn sm" onClick={save} disabled={!dirty || saving}>{saving ? "Saving…" : "Save changes"}</button>
        </div>
      </div>
    </div>
  );
};

const IncomeEditor = ({ profile, addIncome, removeIncome }) => {
  const [t, setT] = React.useState("salary");
  const [a, setA] = React.useState("");
  const [s, setS] = React.useState("");
  const types = [
    { id: "salary", label: "Salary" },
    { id: "freelance", label: "Freelance" },
    { id: "business", label: "Business / AOP" },
    { id: "rental", label: "Rental" },
    { id: "capital_gains", label: "Capital gains" },
  ];
  return (
    <div>
      <div className="grid-income">
        <div className="field"><label>Type</label>
          <select value={t} onChange={e => setT(e.target.value)}>{types.map(x => <option key={x.id} value={x.id}>{x.label}</option>)}</select>
        </div>
        <div className="field"><label>Annual (PKR)</label><input value={a} onChange={e => setA(e.target.value.replace(/\D/g,''))}/></div>
        <div className="field"><label>Source</label><input value={s} onChange={e => setS(e.target.value)}/></div>
        <button className="btn sm" onClick={() => { if(a){addIncome({type:t, annualAmount:+a, source:s}); setA(''); setS('');} }}>Add</button>
      </div>
      <div className="income-list">
        {profile.income.length === 0 && <div className="income-empty">No income sources yet.</div>}
        {profile.income.map((inc, i) => (
          <div key={i} className="income-row">
            <span className="t">{(types.find(x=>x.id===inc.type)||{}).label || inc.type}</span>
            <span className="s muted">{inc.source||"—"}</span>
            <span className="a mono">PKR {Number(inc.annualAmount).toLocaleString()}</span>
            <button className="icon-btn" onClick={() => removeIncome(i)}><Icon name="close" size={12}/></button>
          </div>
        ))}
      </div>
    </div>
  );
};

window.ProfileModal = ProfileModal;
