// Mock data for Tax Sathi — Pakistan tax context
const SAMPLE_USER = {
  name: "Ayesha Khan",
  email: "ayesha.khan@gmail.com",
  initials: "AK",
  ntn: "3740187-2",
  filerStatus: "Filer",
  taxYear: "2025"
};

const SUGGESTIONS = [
  { k: "Calculate", t: "How much tax do I owe on PKR 3,800,000 salary with 15,000/mo rent paid?" },
  { k: "Explain", t: "What changed in FBR withholding tax on banking transactions for tax year 2025?" },
  { k: "Compare", t: "Should I register as AOP or sole proprietorship for my freelance income?" },
  { k: "Deadline", t: "When is the last date to file ITR for salaried individuals this year?" },
];

const HISTORY = [
  { group: "Today", items: [
    { id: "h1", t: "Tax liability on PKR 3.8M salary — old vs new rates", m: "2m ago" },
    { id: "h2", t: "Section 149 withholding by employer", m: "42m ago" },
  ]},
  { group: "This week", items: [
    { id: "h3", t: "Freelance income via SWIFT — export proceeds rules", m: "Mon" },
    { id: "h4", t: "How to claim Zakat deduction on filing", m: "Mon" },
    { id: "h5", t: "Property rental income tax treatment", m: "Sun" },
  ]},
  { group: "TY 2024", items: [
    { id: "h6", t: "Late filing surcharge calculation", m: "Sep 12" },
    { id: "h7", t: "Capital gains on PSX shares held <12mo", m: "Aug 30" },
  ]},
];

const CALENDAR = [
  { date: "30", month: "Apr", title: "Quarterly advance tax — Q4", sub: "Section 147 estimate · individuals", status: "due-soon", statusText: "in 8 days" },
  { date: "15", month: "May", title: "Sales tax return — April", sub: "Monthly STR for registered persons", status: "due-soon", statusText: "in 23 days" },
  { date: "30", month: "Sep", title: "Income tax return — TY 2025", sub: "Salaried & AOP filing deadline", status: "ok", statusText: "on track" },
  { date: "31", month: "Dec", title: "Wealth statement — TY 2025", sub: "Required for filers with NTN", status: "ok", statusText: "upcoming" },
  { date: "15", month: "Apr", title: "March sales tax return", sub: "Filed · acknowledgment #8423", status: "filed", statusText: "filed" },
];

// Canned answer for the hero prompt
const SAMPLE_ANSWER = {
  title: "Estimated tax liability on PKR 3,800,000 salary income",
  summary: "Based on FBR tax slabs for salaried individuals (Tax Year 2025) and the inputs from your profile, your estimated annual tax liability is PKR 427,500. You are above the PKR 3M bracket, so the marginal rate on income over that threshold is 25%. Rent paid doesn't directly reduce taxable salary — but if you declare it, it may affect wealth reconciliation.",
  kpis: [
    { label: "Taxable income", value: "3,800,000", unit: "PKR", delta: "after exemptions" },
    { label: "Tax liability", value: "427,500", unit: "PKR", delta: "−12% vs. TY 2024", primary: true },
    { label: "Effective rate", value: "11.2", unit: "%", delta: "marginal 25%" },
  ],
  slabs: [
    { range: "0 – 600,000", rate: "0%", on: 600000, tax: 0, pct: 16 },
    { range: "600,001 – 1,200,000", rate: "5%", on: 600000, tax: 30000, pct: 16 },
    { range: "1,200,001 – 2,200,000", rate: "15%", on: 1000000, tax: 150000, pct: 26 },
    { range: "2,200,001 – 3,200,000", rate: "25%", on: 1000000, tax: 250000, pct: 26 },
    { range: "3,200,001 – 3,800,000", rate: "25%", on: 600000, tax: 150000, pct: 16 },
  ],
  breakdown: [
    { label: "Gross salary", value: 3800000 },
    { label: "Tax on slabs", value: 580000 },
    { label: "Less: tax credit (Sec 61)", value: -12500 },
    { label: "Less: rebate (senior / disabled)", value: 0 },
  ],
  citations: [
    { ref: "[1]", t: "First Schedule, Part I, Div I — Income Tax Ordinance, 2001", m: "Salaried slabs · TY 2025" },
    { ref: "[2]", t: "Section 149 — Deduction of tax from salary", m: "Employer withholding obligations" },
    { ref: "[3]", t: "Section 61 — Charitable donations tax credit", m: "Eligible deduction cap" },
    { ref: "[4]", t: "Finance Act 2024 — amendments to Part I", m: "Rate revisions for TY25" },
  ],
  trace: {
    totalMs: 4820,
    model: "tax-sathi-v2",
    tokensIn: 1284,
    tokensOut: 612,
    toolCalls: 3,
    sources: 4,
    steps: [
      { type: "think", title: "Parse question intent", body: "Identified as a tax-calculation query with a single income figure (PKR 3,800,000) and a rent-paid detail (informational, not deductible for salaried individuals under ITO 2001).", ms: 340 },
      { type: "tool", title: "Looked up user profile", body: "Pulled filer status, prior-year return, declared NTN", code: "profile.get({ fields: ['filer_status','ntn','ty2024'] })", ms: 180 },
      { type: "source", title: "Retrieved FBR tax slabs · TY 2025", body: "Citing First Schedule, Part I, Div I.", ms: 520 },
      { type: "tool", title: "Calculated slab-by-slab tax", body: "Applied progressive rates to income brackets.", code: "calc.slabTax({ income: 3800000, schedule: 'salary_ty25' })\n→ 580,000", ms: 90 },
      { type: "tool", title: "Checked applicable credits", body: "Zakat, Sec 61 donations, Sec 60C (housing finance). Only Sec 61 from profile.", code: "credits.eligible({ user: 'u_9421', section: 'salaried' })", ms: 210 },
      { type: "think", title: "Compose structured output", body: "Generated summary, KPIs, slab table, and chart data; attached 4 citations.", ms: 880 },
    ],
  },
};

window.SAMPLE_USER = SAMPLE_USER;
window.SUGGESTIONS = SUGGESTIONS;
window.HISTORY = HISTORY;
window.CALENDAR = CALENDAR;
window.SAMPLE_ANSWER = SAMPLE_ANSWER;
