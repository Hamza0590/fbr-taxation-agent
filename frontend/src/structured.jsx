// StructuredModal
// ----------------
// A guided, CSV-style form for users who aren't sure *what* data to provide.
// Required fields are marked with a red * and block submission.
// Optional fields are grouped below.
// Transactions (purchases / sales) are a repeatable row grid.
// Can also be seeded from a CSV file or exported as a CSV template.

const StructuredModal = ({ profile, category, onClose, onSubmit }) => {
  // Category-aware field sets (FBR-aligned)
  const SCHEMA = React.useMemo(() => buildSchema(category), [category]);

  const [data, setData] = React.useState(() => seedFromProfile(SCHEMA, profile));
  const [txns, setTxns] = React.useState([emptyTxn()]);
  const [showErrors, setShowErrors] = React.useState(false);
  const [tab, setTab] = React.useState("fields"); // fields | transactions

  const fileRef = React.useRef(null);

  const set = (k, v) => setData(d => ({ ...d, [k]: v }));

  const addTxn = () => setTxns(t => [...t, emptyTxn()]);
  const delTxn = (i) => setTxns(t => t.filter((_, idx) => idx !== i));
  const updTxn = (i, patch) => setTxns(t => t.map((r, idx) => idx === i ? { ...r, ...patch } : r));

  const missingRequired = SCHEMA.required.filter(f => {
    const v = data[f.id];
    return v === "" || v === null || v === undefined;
  });

  const submit = () => {
    if (missingRequired.length) { setShowErrors(true); setTab("fields"); return; }
    const validTxns = txns.filter(t => t.kind && t.description);
    onSubmit({
      category,
      fields: data,
      transactions: validTxns,
      schemaVersion: SCHEMA.version,
    });
  };

  const downloadTemplate = () => {
    const rows = [];
    rows.push(["# Tax Sathi — structured input template"]);
    rows.push([`# Category: ${category || "—"}`]);
    rows.push(["# Required rows are marked with *. Fill the 'value' column."]);
    rows.push([]);
    rows.push(["field_id", "label", "required", "value", "notes"]);
    for (const f of SCHEMA.required) rows.push([f.id, f.label, "yes", "", f.hint || ""]);
    for (const f of SCHEMA.optional) rows.push([f.id, f.label, "no", "", f.hint || ""]);
    rows.push([]);
    rows.push(["# Transactions — one row per purchase / sale / investment"]);
    rows.push(["transaction_kind", "date", "description", "amount_pkr", "counterparty", "invoice_no"]);
    rows.push(["purchase", "YYYY-MM-DD", "", "0", "", ""]);
    const csv = rows.map(r => r.map(csvEscape).join(",")).join("\n");
    downloadBlob(csv, `tax-sathi-${category || "template"}.csv`, "text/csv");
  };

  const onUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = parseCSV(String(reader.result));
        const { fields, transactions } = interpretCSV(parsed, SCHEMA);
        setData(d => ({ ...d, ...fields }));
        if (transactions.length) setTxns(transactions);
      } catch (err) {
        alert("Couldn't read CSV: " + err.message);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal structured-modal" onClick={e => e.stopPropagation()} role="dialog" aria-label="Structured input">
        <div className="modal-head">
          <div style={{flex:1}}>
            <h2 style={{margin:0, fontSize:22}}>Structured input</h2>
            <p style={{margin:"4px 0 0", fontSize:12, color:"var(--ink-muted)"}}>
              Fill only what you have. Required fields are marked <span style={{color:"var(--rose)"}}>*</span>.
              {category ? <> Tailored for <strong>{categoryLabel(category)}</strong>.</> : <> Set your category in profile for a tailored form.</>}
            </p>
          </div>
          <button className="close-x" onClick={onClose}><Icon name="x" size={14}/></button>
        </div>

        <div className="struct-tabs">
          <button className={`struct-tab ${tab==='fields'?'active':''}`} onClick={() => setTab("fields")}>
            Fields
            {showErrors && missingRequired.length > 0 && <span className="struct-badge">{missingRequired.length}</span>}
          </button>
          <button className={`struct-tab ${tab==='transactions'?'active':''}`} onClick={() => setTab("transactions")}>
            Transactions <span className="struct-count">{txns.filter(t=>t.kind && t.description).length}</span>
          </button>
          <div style={{flex:1}}/>
          <button className="btn ghost xs" onClick={downloadTemplate}><Icon name="download" size={12}/> CSV template</button>
          <button className="btn ghost xs" onClick={() => fileRef.current?.click()}><Icon name="upload" size={12}/> Upload CSV</button>
          <input ref={fileRef} type="file" accept=".csv,text/csv" style={{display:"none"}} onChange={onUpload}/>
        </div>

        <div className="modal-body structured-body">
          {tab === "fields" && (
            <>
              <div className="struct-section">
                <div className="struct-section-head">
                  <h4>Required</h4>
                  <span className="struct-muted">Must be filled before submit.</span>
                </div>
                <div className="struct-grid">
                  {SCHEMA.required.map(f => (
                    <Field key={f.id} f={f} required value={data[f.id]} onChange={v => set(f.id, v)} invalid={showErrors && isEmpty(data[f.id])}/>
                  ))}
                </div>
              </div>

              <div className="struct-section">
                <div className="struct-section-head">
                  <h4>Optional</h4>
                  <span className="struct-muted">Improves accuracy of the answer when provided.</span>
                </div>
                <div className="struct-grid">
                  {SCHEMA.optional.map(f => (
                    <Field key={f.id} f={f} value={data[f.id]} onChange={v => set(f.id, v)}/>
                  ))}
                </div>
              </div>
            </>
          )}

          {tab === "transactions" && (
            <div className="struct-section">
              <div className="struct-section-head">
                <h4>Purchases &amp; sales</h4>
                <span className="struct-muted">Capital goods, inventory, investments, assets. Leave blank if none apply.</span>
              </div>
              <div className="struct-txn-grid">
                <div className="struct-txn-head">
                  <div>Kind</div>
                  <div>Date</div>
                  <div>Description</div>
                  <div>Amount (PKR)</div>
                  <div>Counterparty</div>
                  <div>Invoice #</div>
                  <div aria-hidden/>
                </div>
                {txns.map((t, i) => (
                  <div className="struct-txn-row" key={i}>
                    <select value={t.kind} onChange={e => updTxn(i, {kind: e.target.value})}>
                      <option value="">—</option>
                      <option value="purchase">Purchase</option>
                      <option value="sale">Sale</option>
                      <option value="asset_buy">Asset bought</option>
                      <option value="asset_sell">Asset sold</option>
                      <option value="investment">Investment</option>
                      <option value="expense">Expense</option>
                    </select>
                    <input type="date" value={t.date} onChange={e => updTxn(i, {date: e.target.value})}/>
                    <input placeholder="e.g. Laptop, 5kg sugar, 100 Engro shares" value={t.description} onChange={e => updTxn(i, {description: e.target.value})}/>
                    <input inputMode="numeric" placeholder="0" value={t.amount} onChange={e => updTxn(i, {amount: digits(e.target.value)})}/>
                    <input placeholder="Vendor / buyer" value={t.counterparty} onChange={e => updTxn(i, {counterparty: e.target.value})}/>
                    <input placeholder="INV-…" value={t.invoice} onChange={e => updTxn(i, {invoice: e.target.value})}/>
                    <button className="icon-btn" onClick={() => delTxn(i)} title="Remove row"><Icon name="x" size={12}/></button>
                  </div>
                ))}
              </div>
              <button className="btn ghost sm" onClick={addTxn} style={{marginTop:12}}>+ Add transaction row</button>
            </div>
          )}
        </div>

        <div className="modal-foot">
          <span style={{fontSize:11, color:"var(--ink-4)", fontFamily:"var(--mono)"}}>
            {showErrors && missingRequired.length
              ? `${missingRequired.length} required field${missingRequired.length>1?'s':''} missing`
              : "Sent as structured JSON with your prompt."}
          </span>
          <div style={{flex:1}}/>
          <button className="btn ghost sm" onClick={onClose}>Cancel</button>
          <button className="btn sm" onClick={submit}>Attach &amp; ask</button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Field renderer
// ---------------------------------------------------------------------------
const Field = ({ f, value, onChange, required, invalid }) => {
  const style = invalid ? {borderColor:"var(--rose)"} : undefined;
  return (
    <div className="field">
      <label>
        {f.label} {required && <span style={{color:"var(--rose)"}}>*</span>}
        {f.unit && <span className="struct-unit">({f.unit})</span>}
      </label>
      {f.type === "select" ? (
        <select value={value || ""} onChange={e => onChange(e.target.value)} style={style}>
          <option value="" disabled>Select…</option>
          {f.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      ) : f.type === "textarea" ? (
        <textarea rows={2} value={value || ""} onChange={e => onChange(e.target.value)} style={style} placeholder={f.placeholder}/>
      ) : f.type === "number" ? (
        <input inputMode="numeric" value={value || ""} onChange={e => onChange(digits(e.target.value))} style={style} placeholder={f.placeholder || "0"}/>
      ) : (
        <input value={value || ""} onChange={e => onChange(e.target.value)} style={style} placeholder={f.placeholder}/>
      )}
      {f.hint && <div className="struct-hint">{f.hint}</div>}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Schema — category-aware
// ---------------------------------------------------------------------------
function buildSchema(category) {
  const common = {
    required: [
      { id: "tax_year", label: "Tax year", type: "select", options: [{value:"2025",label:"2025"},{value:"2024",label:"2024"},{value:"2023",label:"2023"}], hint: "FBR tax year this data relates to" },
      { id: "cnic", label: "CNIC", type: "text", placeholder: "00000-0000000-0" },
      { id: "ntn", label: "NTN", type: "text", placeholder: "0000000-0", hint: "National Tax Number" },
      { id: "filer_status", label: "Filer status", type: "select", options: [{value:"filer",label:"Filer"},{value:"non_filer",label:"Non-filer"}] },
    ],
    optional: [
      { id: "address", label: "Address", type: "text" },
      { id: "phone", label: "Phone", type: "text", placeholder: "+92 …" },
      { id: "bank_account", label: "Bank account (last 4)", type: "text" },
      { id: "zakat_paid", label: "Zakat paid", type: "number", unit: "PKR" },
      { id: "donations_sec61", label: "Sec 61 donations", type: "number", unit: "PKR" },
    ],
  };

  const byCat = {
    salaried: {
      required: [
        { id: "annual_salary", label: "Annual gross salary", type: "number", unit: "PKR", hint: "Before deductions" },
        { id: "employer_name", label: "Employer name", type: "text" },
        { id: "tax_withheld", label: "Tax deducted by employer", type: "number", unit: "PKR", hint: "From your salary slip total" },
      ],
      optional: [
        { id: "bonus", label: "Bonus / commission", type: "number", unit: "PKR" },
        { id: "provident_fund", label: "Provident fund contribution", type: "number", unit: "PKR" },
        { id: "medical_allowance", label: "Medical allowance (exempt)", type: "number", unit: "PKR" },
        { id: "rent_paid", label: "Annual rent paid", type: "number", unit: "PKR" },
      ],
    },
    small_business: {
      required: [
        { id: "business_name", label: "Business name", type: "text" },
        { id: "business_nature", label: "Nature of business", type: "text", placeholder: "e.g. retail, trading" },
        { id: "annual_turnover", label: "Annual turnover", type: "number", unit: "PKR", hint: "Total sales for the year" },
        { id: "annual_expenses", label: "Allowable expenses", type: "number", unit: "PKR" },
      ],
      optional: [
        { id: "opening_stock", label: "Opening stock", type: "number", unit: "PKR" },
        { id: "closing_stock", label: "Closing stock", type: "number", unit: "PKR" },
        { id: "employees", label: "Employees", type: "number" },
        { id: "sales_tax_reg", label: "Sales tax registered", type: "select", options: [{value:"yes",label:"Yes"},{value:"no",label:"No"}] },
      ],
    },
    freelancer: {
      required: [
        { id: "service_type", label: "Service type", type: "text", placeholder: "e.g. software dev, design" },
        { id: "annual_receipts_pkr", label: "Annual receipts (PKR)", type: "number", unit: "PKR" },
        { id: "annual_receipts_usd", label: "Annual receipts (USD)", type: "number", unit: "USD", hint: "If paid in foreign currency" },
        { id: "export_proceeds_certificate", label: "Export proceeds certificate?", type: "select", options: [{value:"yes",label:"Yes"},{value:"no",label:"No"}], hint: "From your bank — qualifies IT-export concessional rate" },
      ],
      optional: [
        { id: "psw_registered", label: "PSEB registered", type: "select", options: [{value:"yes",label:"Yes"},{value:"no",label:"No"}] },
        { id: "business_expenses", label: "Business expenses", type: "number", unit: "PKR" },
        { id: "withholding_deducted", label: "Withholding already deducted", type: "number", unit: "PKR" },
      ],
    },
    aop: {
      required: [
        { id: "aop_name", label: "AOP name", type: "text" },
        { id: "partners_count", label: "Number of partners", type: "number" },
        { id: "annual_turnover", label: "Annual turnover", type: "number", unit: "PKR" },
        { id: "net_profit", label: "Net profit", type: "number", unit: "PKR" },
      ],
      optional: [
        { id: "partner_shares", label: "Partner profit shares", type: "textarea", placeholder: "Name — %; Name — %" },
      ],
    },
    company: {
      required: [
        { id: "company_name", label: "Company name", type: "text" },
        { id: "company_type", label: "Company type", type: "select", options: [{value:"private",label:"Private Ltd"},{value:"public",label:"Public Ltd"},{value:"smc",label:"SMC"}] },
        { id: "annual_turnover", label: "Annual turnover", type: "number", unit: "PKR" },
        { id: "taxable_income", label: "Taxable income", type: "number", unit: "PKR" },
      ],
      optional: [
        { id: "paid_up_capital", label: "Paid-up capital", type: "number", unit: "PKR" },
        { id: "listed", label: "Listed on PSX", type: "select", options: [{value:"yes",label:"Yes"},{value:"no",label:"No"}] },
      ],
    },
    non_resident: {
      required: [
        { id: "country_of_residence", label: "Country of residence", type: "text" },
        { id: "days_in_pakistan", label: "Days in Pakistan this year", type: "number" },
        { id: "pakistan_source_income", label: "Pakistan-source income", type: "number", unit: "PKR" },
      ],
      optional: [
        { id: "overseas_income", label: "Overseas income (informational)", type: "number", unit: "PKR" },
        { id: "dtaa_country", label: "DTAA with country?", type: "select", options: [{value:"yes",label:"Yes"},{value:"no",label:"No"},{value:"unknown",label:"Unsure"}] },
      ],
    },
    retailer_t1: {
      required: [
        { id: "shop_name", label: "Shop / outlet name", type: "text" },
        { id: "annual_turnover", label: "Annual turnover", type: "number", unit: "PKR" },
        { id: "pos_integrated", label: "POS integrated with FBR", type: "select", options: [{value:"yes",label:"Yes"},{value:"no",label:"No"}] },
      ],
      optional: [
        { id: "outlets", label: "Number of outlets", type: "number" },
        { id: "floor_area", label: "Total floor area (sqft)", type: "number" },
      ],
    },
    retailer_t2: {
      required: [
        { id: "shop_name", label: "Shop / outlet name", type: "text" },
        { id: "annual_turnover", label: "Annual turnover", type: "number", unit: "PKR" },
      ],
      optional: [
        { id: "electricity_bill_monthly", label: "Avg monthly electricity bill", type: "number", unit: "PKR" },
      ],
    },
    manufacturer: {
      required: [
        { id: "factory_name", label: "Factory / unit name", type: "text" },
        { id: "annual_turnover", label: "Annual turnover", type: "number", unit: "PKR" },
        { id: "cost_of_goods_sold", label: "Cost of goods sold", type: "number", unit: "PKR" },
      ],
      optional: [
        { id: "sales_tax_reg", label: "Sales tax registered", type: "select", options: [{value:"yes",label:"Yes"},{value:"no",label:"No"}] },
        { id: "industrial_zone", label: "Industrial zone", type: "text" },
      ],
    },
    importer_exporter: {
      required: [
        { id: "trade_type", label: "Importer / Exporter / Both", type: "select", options: [{value:"importer",label:"Importer"},{value:"exporter",label:"Exporter"},{value:"both",label:"Both"}] },
        { id: "annual_fob_usd", label: "Annual FOB value (USD)", type: "number", unit: "USD" },
      ],
      optional: [
        { id: "hs_codes", label: "Main HS codes", type: "text" },
        { id: "weboc_id", label: "WeBOC ID", type: "text" },
      ],
    },
    property_income: {
      required: [
        { id: "property_type", label: "Property type", type: "select", options: [{value:"residential",label:"Residential"},{value:"commercial",label:"Commercial"}] },
        { id: "annual_rent", label: "Annual rent received", type: "number", unit: "PKR" },
        { id: "property_address", label: "Property address", type: "text" },
      ],
      optional: [
        { id: "property_cost", label: "Acquisition cost", type: "number", unit: "PKR" },
        { id: "repair_costs", label: "Repair / maintenance", type: "number", unit: "PKR" },
      ],
    },
    agriculturist: {
      required: [
        { id: "land_holding_acres", label: "Land holding (acres)", type: "number" },
        { id: "crop_type", label: "Primary crop(s)", type: "text" },
        { id: "agri_income", label: "Annual agricultural income", type: "number", unit: "PKR" },
      ],
      optional: [
        { id: "non_agri_income", label: "Non-agri income", type: "number", unit: "PKR" },
      ],
    },
    pensioner: {
      required: [
        { id: "annual_pension", label: "Annual pension", type: "number", unit: "PKR" },
        { id: "pension_source", label: "Pension source", type: "text", placeholder: "e.g. Government, EOBI" },
      ],
      optional: [
        { id: "other_income", label: "Other income", type: "number", unit: "PKR" },
        { id: "age", label: "Age", type: "number" },
      ],
    },
    other: {
      required: [
        { id: "description", label: "Describe your situation", type: "textarea", placeholder: "What kind of income or activity?" },
        { id: "annual_income", label: "Total annual income", type: "number", unit: "PKR" },
      ],
      optional: [],
    },
  };

  const cat = byCat[category] || byCat.other;
  return {
    version: "1.0",
    required: [...common.required, ...cat.required],
    optional: [...cat.optional, ...common.optional],
  };
}

function categoryLabel(id) {
  return window.API.FBR_CATEGORIES.find(c => c.id === id)?.label || id;
}

function seedFromProfile(schema, profile) {
  const out = {};
  for (const f of [...schema.required, ...schema.optional]) out[f.id] = "";
  if (!profile) return out;
  // Pre-fill from profile where possible
  const map = {
    cnic: profile.identity?.cnic,
    ntn: profile.identity?.ntn,
    filer_status: profile.identity?.filerStatus === "Filer" ? "filer" : profile.identity?.filerStatus === "Non-filer" ? "non_filer" : "",
    address: profile.identity?.address,
    phone: profile.identity?.phone,
    tax_year: profile.preferences?.taxYear,
    zakat_paid: profile.deductions?.zakat,
    donations_sec61: profile.deductions?.section61Donations,
  };
  for (const [k, v] of Object.entries(map)) {
    if (v !== undefined && v !== null && v !== "") out[k] = String(v);
  }
  // Try to pull the first salary income if salaried
  const salary = profile.income?.find(i => i.type === "salary");
  if (salary) out.annual_salary = String(salary.annualAmount || "");
  return out;
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
const emptyTxn = () => ({ kind: "", date: "", description: "", amount: "", counterparty: "", invoice: "" });
const digits = (s) => String(s).replace(/[^\d]/g, "");
const isEmpty = (v) => v === "" || v === null || v === undefined;
const csvEscape = (v) => {
  const s = String(v ?? "");
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function parseCSV(text) {
  // Minimal CSV parser — handles quoted fields and embedded commas/newlines
  const rows = []; let row = []; let field = ""; let inQuote = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i], n = text[i+1];
    if (inQuote) {
      if (c === '"' && n === '"') { field += '"'; i++; }
      else if (c === '"') { inQuote = false; }
      else { field += c; }
    } else {
      if (c === '"') inQuote = true;
      else if (c === ",") { row.push(field); field = ""; }
      else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
      else if (c === "\r") { /* skip */ }
      else field += c;
    }
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function interpretCSV(rows, schema) {
  const fields = {};
  const transactions = [];
  let mode = null; // null | "fields" | "txns"
  let fieldHeader = null;
  let txnHeader = null;
  for (const r of rows) {
    if (!r.length || r.every(c => !c)) continue;
    if (r[0]?.startsWith("#")) continue;
    if (r[0] === "field_id") { mode = "fields"; fieldHeader = r; continue; }
    if (r[0] === "transaction_kind") { mode = "txns"; txnHeader = r; continue; }
    if (mode === "fields" && fieldHeader) {
      const [id, , , value] = r;
      if (id && value) fields[id] = value;
    } else if (mode === "txns" && txnHeader) {
      const [kind, date, description, amount, counterparty, invoice] = r;
      if (kind || description) transactions.push({ kind, date, description, amount: digits(amount || ""), counterparty, invoice });
    }
  }
  return { fields, transactions };
}

window.StructuredModal = StructuredModal;
