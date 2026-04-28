// ============================================================================
//  Tax Sathi — API integration layer
//  All functions call the real FastAPI backend at localhost:8000.
// ============================================================================

const API = (() => {
  // ─── Config ────────────────────────────────────────────────────────────────
  const BASE_URL = "http://localhost:8000";
  // ───────────────────────────────────────────────────────────────────────────

  const TOKEN_KEY = "ts_token";
  const getToken  = () => localStorage.getItem(TOKEN_KEY);
  const setToken  = (t) => t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY);

  // Generic fetch wrapper — attaches Bearer token automatically.
  const request = async (path, opts = {}) => {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
        ...(opts.headers || {}),
      },
    });
    if (res.status === 401) {
      setToken(null);
      throw new Error("401 Unauthorized");
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `${res.status} ${res.statusText}`);
    }
    return res.json();
  };

  // ─── Profile shape ─────────────────────────────────────────────────────────
  const EMPTY_PROFILE = {
    identity: {
      fullName: "",
      email: "",
      ntn: "",
      cnic: "",
      phone: "",
      filerStatus: "Non-filer",
      residencyStatus: "Resident",
      city: "",
      province: "",
    },
    income: [],
    deductions: {
      zakat: 0,
      section61Donations: 0,
      section60CHousingFinance: 0,
      pensionContribution: 0,
    },
    preferences: {
      taxYear: "2025-2026",
      category: "",
      language: "en",
      reminders: true,
    },
  };

  const FBR_CATEGORIES = [
    { id: "salaried",           label: "Salaried Individual",               hint: "Employment income from an employer" },
    { id: "small_business",     label: "Small Business / Sole Proprietor",  hint: "Shopkeeper, trader, small enterprise" },
    { id: "freelancer",         label: "Freelancer / Professional Services", hint: "IT exports, consultants, designers" },
    { id: "aop",                label: "Association of Persons (AOP)",      hint: "Partnership or joint venture" },
    { id: "company",            label: "Company",                           hint: "Private or public limited" },
    { id: "non_resident",       label: "Non-Resident Pakistani",            hint: "Overseas Pakistanis filing in PK" },
    { id: "retailer_t1",        label: "Retailer — Tier-1",                 hint: "POS-integrated retail chain" },
    { id: "retailer_t2",        label: "Retailer — Tier-2 / other",         hint: "Non-Tier-1 retail" },
    { id: "manufacturer",       label: "Manufacturer",                      hint: "Industrial undertaking" },
    { id: "importer_exporter",  label: "Importer / Exporter",               hint: "Commercial import or export" },
    { id: "property_income",    label: "Property Income",                   hint: "Rental / immovable property" },
    { id: "agriculturist",      label: "Agriculturist",                     hint: "Agricultural income" },
    { id: "pensioner",          label: "Pensioner",                         hint: "Retired, pension income" },
    { id: "other",              label: "Other",                             hint: "None of the above" },
  ];

  const mergeProfile = (base, patch) => {
    const out = { ...base };
    for (const k of Object.keys(patch || {})) {
      if (patch[k] && typeof patch[k] === "object" && !Array.isArray(patch[k])) {
        out[k] = { ...base[k], ...patch[k] };
      } else {
        out[k] = patch[k];
      }
    }
    return out;
  };

  // ─── Auth ──────────────────────────────────────────────────────────────────
  const login = async (email, password) => {
    const data = await request("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.token);
    const profile = await getProfile().catch(() => null);
    return {
      token: data.token,
      user: { email: data.email, name: data.full_name, id: data.user_id },
      profile,
      hasProfile: !!profile,
    };
  };

  const signup = async (email, password, name) => {
    const data = await request("/api/v1/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: name }),
    });
    setToken(data.token);
    return {
      token: data.token,
      user: { email: data.email, name: data.full_name, id: data.user_id },
      profile: null,
      hasProfile: false,
    };
  };

  const socialAuth = async (provider) => {
    throw new Error("Social auth is not yet supported. Please use email and password.");
  };

  const logout = async () => {
    setToken(null);
  };

  const getCurrentUser = async () => {
    return request("/api/v1/auth/me");
  };

  // ─── Profile ───────────────────────────────────────────────────────────────
  // DB stores identity fields. Income / deductions / preferences live in
  // localStorage so the full profile shape is always available client-side.
  const getProfile = async () => {
    try {
      const db = await request("/api/v1/profile/");
      const ext = loadLocal("profile_extended") || {};
      return {
        identity: {
          fullName: db.full_name || "",
          email: db.email || "",
          ntn: db.ntn || "",
          cnic: db.cnic || "",
          phone: db.phone || "",
          filerStatus: ext.filerStatus || "Non-filer",
          residencyStatus: ext.residencyStatus || "Resident",
          city: db.city || "",
          province: db.province || "",
        },
        income: ext.income || [],
        deductions: ext.deductions || { zakat: 0, section61Donations: 0, section60CHousingFinance: 0, pensionContribution: 0 },
        preferences: ext.preferences || { taxYear: db.tax_year || "2025-2026", category: "", language: "en", reminders: true },
      };
    } catch {
      return null;
    }
  };

  const saveProfile = async (profile) => {
    await request("/api/v1/profile/", {
      method: "PUT",
      body: JSON.stringify({
        full_name: profile.identity?.fullName || undefined,
        phone:     profile.identity?.phone    || undefined,
        cnic:      profile.identity?.cnic     || undefined,
        ntn:       profile.identity?.ntn      || undefined,
        city:      profile.identity?.city     || undefined,
        province:  profile.identity?.province || undefined,
        tax_year:  profile.preferences?.taxYear || undefined,
      }),
    });
    saveLocal("profile_extended", {
      filerStatus:     profile.identity?.filerStatus,
      residencyStatus: profile.identity?.residencyStatus,
      income:          profile.income,
      deductions:      profile.deductions,
      preferences:     profile.preferences,
    });
    return profile;
  };

  const updateProfile = async (patch) => {
    const current = (await getProfile()) || EMPTY_PROFILE;
    return saveProfile(mergeProfile(current, patch));
  };

  // ─── Sessions ──────────────────────────────────────────────────────────────
  const getSessions = async () => {
    return request("/api/v1/sessions/");
  };

  const createSession = async (title = "New Chat") => {
    return request("/api/v1/sessions/", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  };

  const getSession = async (sessionId) => {
    return request(`/api/v1/sessions/${sessionId}`);
  };

  const deleteSession = async (sessionId) => {
    return request(`/api/v1/sessions/${sessionId}`, { method: "DELETE" });
  };

  const updateSessionTitle = async (sessionId, title) => {
    return request(`/api/v1/sessions/${sessionId}`, {
      method: "PUT",
      body: JSON.stringify({ title }),
    });
  };

  // ─── Send message ──────────────────────────────────────────────────────────
  const sendMessage = async (sessionId, message, conversationHistory = [], profileContext = null) => {
    return request("/api/v1/pipeline/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        message,
        conversation_history: conversationHistory,
        profile_context: profileContext || undefined,
      }),
    });
  };

  // ─── Format profile as context string for the extractor ────────────────────
  const formatProfileContext = (profile) => {
    if (!profile) return null;
    const lines = [];
    const id = profile.identity || {};
    if (id.filerStatus) lines.push(`Filer Status: ${id.filerStatus === "Filer" ? "filer" : "non_filer"}`);
    if (id.residencyStatus) lines.push(`Residency Status: ${id.residencyStatus === "Resident" ? "resident" : "non_resident"}`);
    if (profile.preferences?.taxYear) lines.push(`Tax Year: ${profile.preferences.taxYear}`);
    if (id.fullName) lines.push(`Taxpayer Name: ${id.fullName}`);

    const income = profile.income || [];
    if (income.length > 0) {
      lines.push("Income Sources:");
      for (const inc of income) {
        if (inc.type === "salary") lines.push(`  - Salary: PKR ${Number(inc.annualAmount || 0).toLocaleString()} annual`);
        else if (inc.type === "business") lines.push(`  - Business income: PKR ${Number(inc.annualAmount || 0).toLocaleString()}`);
        else if (inc.type === "rental") lines.push(`  - Rental income: PKR ${Number(inc.annualAmount || 0).toLocaleString()}`);
        else if (inc.type === "freelance") lines.push(`  - Freelance income: PKR ${Number(inc.annualAmount || 0).toLocaleString()}`);
        else if (inc.annualAmount) lines.push(`  - ${inc.type}: PKR ${Number(inc.annualAmount).toLocaleString()}`);
      }
    }

    const ded = profile.deductions || {};
    const dedLines = [];
    if (ded.zakat > 0) dedLines.push(`Zakat PKR ${Number(ded.zakat).toLocaleString()}`);
    if (ded.section61Donations > 0) dedLines.push(`Section 61 donations PKR ${Number(ded.section61Donations).toLocaleString()}`);
    if (ded.pensionContribution > 0) dedLines.push(`Pension PKR ${Number(ded.pensionContribution).toLocaleString()}`);
    if (dedLines.length > 0) lines.push(`Deductions: ${dedLines.join(", ")}`);

    return lines.length > 0 ? lines.join("\n") : null;
  };

  // ─── Kept for calendar (data.jsx still populates window.CALENDAR)  ─────────
  const getCalendar = async () => ({ events: window.CALENDAR || [] });

  // ─── Export / Share ────────────────────────────────────────────────────────
  const exportPDF    = async () => ({ url: "#" });
  const shareAnswer  = async () => ({ url: "#" });

  // ─── localStorage helpers ──────────────────────────────────────────────────
  function loadLocal(key) {
    try { return JSON.parse(localStorage.getItem("ts_" + key) || "null"); } catch { return null; }
  }
  function saveLocal(key, value) {
    if (value === null) localStorage.removeItem("ts_" + key);
    else localStorage.setItem("ts_" + key, JSON.stringify(value));
  }

  return {
    EMPTY_PROFILE,
    FBR_CATEGORIES,
    login, signup, socialAuth, logout, getCurrentUser,
    getProfile, saveProfile, updateProfile,
    getSessions, createSession, getSession, deleteSession, updateSessionTitle,
    sendMessage, formatProfileContext,
    getCalendar,
    exportPDF, shareAnswer,
    getToken,
    _mergeProfile: mergeProfile,
  };
})();

window.API = API;
