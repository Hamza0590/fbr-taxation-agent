// ── Collapsible block ─────────────────────────────────────────────────────────
const Collapsible = ({ label, defaultOpen = false, children }) => {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <div style={{border:"1px solid var(--line-light)", borderRadius:5, marginBottom:8, overflow:"hidden"}}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{width:"100%", background:"var(--surface-1)", border:"none", padding:"8px 12px",
                textAlign:"left", cursor:"pointer", display:"flex", justifyContent:"space-between",
                alignItems:"center", fontSize:12, fontWeight:600, color:"var(--ink-2)"}}
      >
        {label}
        <span style={{fontSize:10, color:"var(--ink-4)"}}>{open ? "▲" : "▼"}</span>
      </button>
      {open && <div style={{padding:"10px 12px"}}>{children}</div>}
    </div>
  );
};

// ── Section card (collapsible FBR section) ──────────────────────────────────
const SectionCard = ({ section }) => {
  const [expanded, setExpanded] = React.useState(false);
  return (
    <div className="section-card" style={{border:"1px solid var(--line-light)", borderRadius:6, marginBottom:8, overflow:"hidden"}}>
      <button
        className="section-header"
        onClick={() => setExpanded(v => !v)}
        style={{width:"100%", background:"none", border:"none", padding:"10px 12px", textAlign:"left", cursor:"pointer", display:"flex", justifyContent:"space-between", alignItems:"flex-start", gap:8}}
      >
        <div style={{minWidth:0}}>
          <div style={{fontSize:10, fontFamily:"var(--mono)", color:"var(--ink-4)", marginBottom:2}}>{section.section_path}</div>
          <div style={{fontSize:13, fontWeight:600, color:"var(--ink-1)"}}>{section.title}</div>
          <div style={{fontSize:12, color:"var(--ink-3)", marginTop:3}}>{section.relevance}</div>
        </div>
        <span style={{flexShrink:0, fontSize:10, color:"var(--ink-4)", paddingTop:2}}>{expanded ? "▲" : "▼"}</span>
      </button>

      <div style={{padding:"0 12px 10px", fontSize:12, color:"var(--ink-2)", lineHeight:1.6}}>
        {section.content_preview}
      </div>

      {expanded && (
        <div style={{borderTop:"1px solid var(--line-light)", padding:"10px 12px", background:"var(--surface-1)"}}>
          <div style={{fontSize:10, fontFamily:"var(--mono)", color:"var(--ink-4)", marginBottom:6}}>{section.line_range}</div>
          <pre style={{margin:0, fontSize:11, color:"var(--ink-2)", whiteSpace:"pre-wrap", fontFamily:"var(--mono)", lineHeight:1.5, maxHeight:320, overflowY:"auto"}}>
            {section.full_content}
          </pre>
        </div>
      )}
    </div>
  );
};

// ── Step status icon ──────────────────────────────────────────────────────────
const stepIcon = (status) => {
  if (status === "completed") return <span className="step-check">✓</span>;
  if (status === "failed")    return <span style={{color:"var(--rose)",   fontWeight:700}}>✗</span>;
  if (status === "skipped")   return <span style={{color:"var(--ink-4)"}}>—</span>;
  if (status === "in_progress") return <span style={{color:"var(--amber)"}}>●</span>;
  return <span style={{color:"var(--ink-4)"}}>○</span>;
};

// ── Canvas serialiser for clipboard ──────────────────────────────────────────
const serializeCanvas = (canvas) => {
  const lines = ["=== Tax Sathi Result ===", ""];
  const { extraction, retrieval, interpretation, calculation } = canvas;

  if (extraction) {
    lines.push("── Tax Data Extracted ──");
    lines.push(`Status: ${extraction.status}  Confidence: ${extraction.confidence_label} (${Math.round((extraction.confidence || 0) * 100)}%)`);
    if (extraction.extracted_fields) {
      for (const [k, v] of Object.entries(extraction.extracted_fields)) {
        lines.push(`  ${k}: ${v}`);
      }
    }
    if (extraction.assumptions?.length) lines.push("Assumptions: " + extraction.assumptions.join("; "));
    lines.push("");
  }

  if (retrieval?.selected_sections?.length) {
    lines.push("── FBR Rules Retrieved ──");
    for (const s of retrieval.selected_sections) {
      lines.push(`  [${s.section_path}] ${s.title}`);
      if (s.relevance) lines.push(`    ${s.relevance}`);
    }
    lines.push("");
  }

  if (calculation && calculation.status === "complete") {
    const fmt = (n) => `Rs. ${Number(n).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;
    lines.push("── Tax Calculation ──");
    lines.push(`Gross Income:       ${fmt(calculation.total_gross_income)}`);
    lines.push(`Taxable Income:     ${fmt(calculation.taxable_income_after_deductions)}`);
    lines.push(`Gross Liability:    ${fmt(calculation.gross_tax_liability)}`);
    lines.push(`Withholding Adj.:   ${fmt(calculation.total_adjustable_withholding)}`);
    lines.push(calculation.is_refund
      ? `REFUND DUE:         ${fmt(calculation.refund_due)}`
      : `NET TAX PAYABLE:    ${fmt(calculation.net_tax_payable)}`);
    lines.push(`Effective Rate:     ${calculation.effective_tax_rate}%`);
    lines.push("");
  }

  lines.push("Generated by Tax Sathi · FBR TY 2025-26");
  return lines.join("\n");
};

// ── PDF document builder ──────────────────────────────────────────────────────
const buildPDFHtml = (canvas) => {
  const { extraction, retrieval, interpretation, calculation } = canvas;
  const date = new Date().toLocaleDateString("en-PK", { month: "long", day: "numeric", year: "numeric" });
  const fmt = (n) => `Rs. ${Number(n).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

  let sections = "";

  // ── Extraction ──────────────────────────────────────────────────────────────
  if (extraction) {
    const pct = Math.round((extraction.confidence || 0) * 100);
    let fields = "";
    if (extraction.extracted_fields) {
      fields = Object.entries(extraction.extracted_fields).map(([k, v]) =>
        `<tr><td class="label">${k}</td><td>${v}</td></tr>`
      ).join("");
    }
    const assumptions = (extraction.assumptions || []).length
      ? `<p class="note"><strong>Assumptions:</strong> ${extraction.assumptions.join("; ")}</p>` : "";
    const missing = (extraction.missing_fields || []).length
      ? `<p class="warn"><strong>Still needed:</strong> ${extraction.missing_fields.join(", ")}</p>` : "";

    sections += `
      <section>
        <h2>01 — Tax Data Extracted</h2>
        <p><span class="badge">${extraction.status}</span> &nbsp;Confidence: <strong>${extraction.confidence_label}</strong> (${pct}%)</p>
        ${fields ? `<table class="kv">${fields}</table>` : ""}
        ${missing}${assumptions}
      </section>`;
  }

  // ── Retrieval ───────────────────────────────────────────────────────────────
  if (retrieval && retrieval.status === "complete") {
    const rows = (retrieval.selected_sections || []).map(s =>
      `<tr>
        <td class="mono">${s.section_path}</td>
        <td><strong>${s.title}</strong><br/><span class="muted">${s.relevance || ""}</span></td>
      </tr>`
    ).join("");
    const reasoning = retrieval.reasoning
      ? `<blockquote>${retrieval.reasoning}</blockquote>` : "";

    sections += `
      <section>
        <h2>03 — FBR Rules Retrieved</h2>
        <p><strong>Query:</strong> ${retrieval.query_summary}</p>
        ${reasoning}
        ${rows ? `<table class="rules">${rows}</table>` : ""}
        <p class="muted mono">${retrieval.passes_used} pass${retrieval.passes_used !== 1 ? "es" : ""} · ${(retrieval.selected_sections || []).length} sections</p>
      </section>`;
  }

  // ── Interpretation ──────────────────────────────────────────────────────────
  if (interpretation && interpretation.status === "complete") {
    let incomeRows = "";
    (interpretation.income_classifications || []).forEach(ic => {
      incomeRows += `<tr>
        <td>${ic.source_description}</td>
        <td class="mono">${ic.applicable_section}</td>
        <td><span class="badge sm">${ic.tax_regime}</span></td>
        <td>${ic.reasoning}</td>
      </tr>`;
    });

    let deductionRows = "";
    (interpretation.deductions || []).forEach(d => {
      deductionRows += `<tr>
        <td>${d.allowed ? "✓" : "✗"} ${d.type}</td>
        <td class="mono right">PKR ${(d.claimed_amount || 0).toLocaleString()}</td>
        <td>${d.cap_rule || ""}</td>
      </tr>`;
    });

    const reasoning = interpretation.overall_reasoning
      ? `<blockquote>${interpretation.overall_reasoning}</blockquote>` : "";
    const caveats = (interpretation.caveats || []).length
      ? `<div class="caveat-box"><strong>Caveats:</strong><ul>${interpretation.caveats.map(c => `<li>${c}</li>`).join("")}</ul></div>` : "";

    sections += `
      <section>
        <h2>04 — Tax Rules Interpreted</h2>
        ${incomeRows ? `<h3>Income Classification</h3><table class="data"><thead><tr><th>Source</th><th>Section</th><th>Regime</th><th>Reasoning</th></tr></thead><tbody>${incomeRows}</tbody></table>` : ""}
        ${deductionRows ? `<h3>Deductions</h3><table class="data"><thead><tr><th>Type</th><th>Amount</th><th>Cap</th></tr></thead><tbody>${deductionRows}</tbody></table>` : ""}
        ${reasoning}${caveats}
      </section>`;
  }

  // ── Calculation ─────────────────────────────────────────────────────────────
  if (calculation && calculation.status === "complete") {
    const calc = calculation;
    const isRefund = calc.is_refund;
    const netLabel = isRefund ? "REFUND DUE" : "NET TAX PAYABLE";
    const netValue = isRefund ? calc.refund_due : calc.net_tax_payable;

    let incomeRows = "";
    (calc.income_breakdowns || []).forEach(row => {
      incomeRows += `<tr>
        <td>${row.source_description}</td>
        <td style="text-transform:capitalize">${row.head.replace(/_/g, " ")}</td>
        <td class="right mono">${fmt(row.gross_income)}</td>
        <td>${row.applicable_schedule}</td>
        <td><span class="badge sm">${row.tax_regime}</span></td>
        <td class="right mono">${row.withholding_is_final ? "final WH" : fmt(row.computed_tax)}</td>
      </tr>`;
    });

    let computationNotes = "";
    if ((calc.computation_notes || []).length) {
      computationNotes = `<h3>Step-by-step computation</h3>
        <ol class="notes">${calc.computation_notes.map(n => `<li>${n}</li>`).join("")}</ol>`;
    }

    let deductionRows = "";
    (calc.deductions_applied || []).forEach(d => {
      deductionRows += `<tr>
        <td>u/s ${d.section} — ${d.type}</td>
        <td class="right mono">${fmt(d.claimed_amount)}</td>
        <td class="right mono">${fmt(d.allowed_amount)}</td>
        <td>${d.cap_rule || ""}</td>
      </tr>`;
    });

    let withholdingRows = "";
    (calc.withholding_adjustments || []).forEach(w => {
      withholdingRows += `<tr>
        <td>${w.source} (s.${w.section})</td>
        <td class="right mono">${fmt(w.amount)}</td>
        <td><span class="badge sm">${w.treatment}</span></td>
      </tr>`;
    });

    const caveats = (calc.caveats || []).length
      ? `<div class="caveat-box"><strong>Caveats:</strong><ul>${calc.caveats.map(c => `<li>${c}</li>`).join("")}</ul></div>` : "";

    sections += `
      <section>
        <h2>05 — Tax Calculation</h2>
        <div class="summary-box">
          <table class="summary-kv">
            <tr><td>Gross Income</td><td class="right mono">${fmt(calc.total_gross_income)}</td></tr>
            <tr><td>Taxable Income</td><td class="right mono">${fmt(calc.taxable_income_after_deductions)}</td></tr>
            <tr><td>Gross Liability</td><td class="right mono">${fmt(calc.gross_tax_liability)}</td></tr>
            <tr><td>Withholding Adjusted</td><td class="right mono">${fmt(calc.total_adjustable_withholding)}</td></tr>
            <tr class="net-row"><td><strong>${netLabel}</strong></td><td class="right mono net-val"><strong>${fmt(netValue)}</strong></td></tr>
          </table>
          <p class="eff-rate mono">Effective rate: ${calc.effective_tax_rate}%
            ${calc.minimum_tax_applicable && calc.minimum_tax_amount ? ` &nbsp;·&nbsp; Min tax (s.113): ${fmt(calc.minimum_tax_amount)}` : ""}
            ${calc.super_tax_applicable && calc.super_tax_amount ? ` &nbsp;·&nbsp; Super tax: ${fmt(calc.super_tax_amount)}` : ""}
          </p>
        </div>
        ${incomeRows ? `<h3>Income Breakdown</h3><table class="data"><thead><tr><th>Source</th><th>Head</th><th class="right">Amount</th><th>Schedule</th><th>Regime</th><th class="right">Tax</th></tr></thead><tbody>${incomeRows}</tbody></table>` : ""}
        ${deductionRows ? `<h3>Deductions &amp; Credits</h3><table class="data"><thead><tr><th>Item</th><th class="right">Claimed</th><th class="right">Allowed</th><th>Cap Rule</th></tr></thead><tbody>${deductionRows}</tbody></table>` : ""}
        ${withholdingRows ? `<h3>Withholding Adjustments</h3><table class="data"><thead><tr><th>Source</th><th class="right">Amount</th><th>Treatment</th></tr></thead><tbody>${withholdingRows}</tbody></table>` : ""}
        ${computationNotes}${caveats}
      </section>`;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Tax Sathi — Tax Report</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 12px; color: #1a1a1a; margin: 0; padding: 24px 32px; line-height: 1.5; }
  @page { margin: 18mm 16mm; }
  @media print { body { padding: 0; } section { page-break-inside: avoid; } }
  .doc-header { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #2d6a4f; padding-bottom: 12px; margin-bottom: 24px; }
  .doc-title { font-size: 22px; font-weight: 700; color: #2d6a4f; letter-spacing: -0.5px; }
  .doc-sub { font-size: 11px; color: #666; margin-top: 2px; }
  .doc-meta { font-size: 11px; color: #888; text-align: right; }
  section { margin-bottom: 28px; }
  h2 { font-size: 13px; font-weight: 700; color: #2d6a4f; border-bottom: 1px solid #d4e9df; padding-bottom: 5px; margin: 0 0 12px; }
  h3 { font-size: 11px; font-weight: 700; color: #444; margin: 14px 0 6px; text-transform: uppercase; letter-spacing: 0.04em; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
  table.kv td { padding: 3px 6px; font-size: 11px; vertical-align: top; }
  table.kv td.label { color: #666; width: 38%; font-weight: 600; }
  table.rules td { padding: 5px 8px; border-bottom: 1px solid #eee; vertical-align: top; font-size: 11px; }
  table.rules td.mono { color: #2d6a4f; font-family: monospace; font-size: 10px; white-space: nowrap; }
  table.data { font-size: 11px; }
  table.data th { background: #f5f5f5; padding: 5px 8px; text-align: left; font-weight: 600; color: #555; border-bottom: 1px solid #ddd; }
  table.data td { padding: 5px 8px; border-bottom: 1px solid #eee; vertical-align: top; }
  table.data td.right { text-align: right; }
  table.data td.mono { font-family: monospace; }
  .summary-box { border: 1px solid #d4e9df; border-radius: 6px; padding: 14px; margin-bottom: 12px; background: #f8fdf9; }
  table.summary-kv { width: 100%; }
  table.summary-kv td { padding: 4px 0; font-size: 12px; }
  table.summary-kv td.right { text-align: right; }
  table.summary-kv tr.net-row td { border-top: 1px solid #c8e0d0; padding-top: 8px; margin-top: 4px; }
  .net-val { color: #2d6a4f; font-size: 15px; }
  .eff-rate { font-family: monospace; font-size: 10px; color: #888; margin: 6px 0 0; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 700; background: #2d6a4f; color: #fff; }
  .badge.sm { padding: 1px 6px; font-size: 9px; }
  blockquote { margin: 8px 0; padding: 8px 12px; border-left: 3px solid #2d6a4f; background: #f8fdf9; font-style: italic; color: #444; font-size: 11px; }
  .caveat-box { border: 1px solid #f59e0b; background: #fffbea; border-radius: 5px; padding: 8px 12px; margin-top: 10px; font-size: 11px; }
  .caveat-box ul { margin: 4px 0 0; padding-left: 16px; }
  .note { font-size: 11px; color: #555; }
  .warn { font-size: 11px; color: #b45309; }
  .muted { color: #888; }
  .mono { font-family: monospace; }
  ol.notes { margin: 0; padding-left: 20px; font-family: monospace; font-size: 11px; line-height: 1.8; color: #333; }
  .footer { border-top: 1px solid #ddd; margin-top: 32px; padding-top: 10px; font-size: 10px; color: #aaa; }
</style>
</head>
<body>
<div class="doc-header">
  <div>
    <div class="doc-title">Tax Sathi</div>
    <div class="doc-sub">Pakistan Federal Board of Revenue — Tax Year 2025-26</div>
  </div>
  <div class="doc-meta">Generated on ${date}<br/>Confidential · Not for redistribution</div>
</div>
${sections}
<div class="footer">
  <strong>Disclaimer:</strong> This report is generated by Tax Sathi based on FBR TY 2025-26 data and is for informational purposes only.
  It does not constitute tax advice. Always verify figures with a licensed tax practitioner before filing.
</div>
</body>
</html>`;
};

// ── Canvas view (right panel) ─────────────────────────────────────────────────
const CanvasView = ({ canvas, streaming, onExport }) => {
  const [copyLabel, setCopyLabel] = React.useState("Copy");

  const handlePDF = () => {
    if (!canvas) return;
    const html = buildPDFHtml(canvas);
    const win = window.open("", "_blank", "width=860,height=940");
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => { win.print(); }, 600);
  };

  const handleCopy = () => {
    const text = serializeCanvas(canvas);
    const fallback = () => {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try { document.execCommand("copy"); } catch {}
      document.body.removeChild(ta);
    };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(fallback);
    } else {
      fallback();
    }
    setCopyLabel("Copied!");
    setTimeout(() => setCopyLabel("Copy"), 2000);
  };
  if (streaming && !canvas) {
    return (
      <div className="output-col">
        <div className="streaming-shell">
          <div className="streaming-label"><span className="pulse"/> Processing · consulting FBR sources…</div>
          <div className="shimmer"/>
          <div className="shimmer w80"/>
          <div className="shimmer w60"/>
          <div style={{height:18}}/>
          <div className="shimmer w40"/>
          <div className="shimmer w80"/>
          <div className="shimmer"/>
        </div>
      </div>
    );
  }

  if (!canvas) {
    return (
      <div className="output-col">
        <div className="output-empty">
          <div className="output-empty-inner">
            <div className="sig">— empty canvas —</div>
            <div>Ask a question on the left. The extraction trace and retrieved FBR sections will appear here.</div>
          </div>
        </div>
      </div>
    );
  }

  const extraction     = canvas.extraction;
  const retrieval      = canvas.retrieval;
  const interpretation = canvas.interpretation;
  const steps          = canvas.steps || [];
  const confidencePct  = extraction ? Math.round((extraction.confidence || 0) * 100) : 0;

  return (
    <div className="output-col" style={{overflowY:"auto"}}>
      <div className="out-head">
        <div className="kicker">Canvas · {new Date().toLocaleDateString("en-PK", {month:"short", day:"numeric", year:"numeric"})}</div>
        <div className="out-head-actions">
          <button className="icon-btn" onClick={handleCopy}><Icon name="copy" size={13}/> {copyLabel}</button>
          <button className="icon-btn" onClick={handlePDF}><Icon name="download" size={13}/> PDF</button>
        </div>
      </div>

      {/* ── Processing steps ─────────────────────────────────── */}
      {steps.length > 0 && (
        <div className="out-section out-section-1">
          <div className="section-label"><span className="num">01</span> Processing pipeline</div>
          <div style={{display:"flex", flexDirection:"column", gap:6}}>
            {steps.map((step, i) => (
              <div key={i} className="pipeline-step" style={{"--step-idx": i, display:"flex", alignItems:"flex-start", gap:10, padding:"8px 10px", borderRadius:5, background:"var(--surface-1)", fontSize:12}}>
                <div style={{width:18, textAlign:"center", flexShrink:0, paddingTop:1}}>{stepIcon(step.status)}</div>
                <div style={{flex:1, minWidth:0}}>
                  <div style={{fontWeight:600, color:"var(--ink-1)"}}>{step.step_name}</div>
                  {step.summary && <div style={{color:"var(--ink-3)", marginTop:2}}>{step.summary}</div>}
                </div>
                {step.duration_ms != null && (
                  <div style={{flexShrink:0, fontFamily:"var(--mono)", fontSize:10, color:"var(--ink-4)", paddingTop:2}}>{step.duration_ms}ms</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Extraction trace ─────────────────────────────────── */}
      {extraction && (
        <div className="out-section out-section-2">
          <div className="section-label"><span className="num">02</span> Tax data extracted</div>
          <div style={{background:"var(--surface-1)", borderRadius:6, padding:"12px 14px"}}>
            <div style={{display:"flex", alignItems:"center", gap:10, marginBottom:10}}>
              <span style={{
                display:"inline-block", padding:"2px 8px", borderRadius:10, fontSize:11, fontWeight:600,
                background: extraction.status === "complete" ? "var(--forest)" : extraction.status === "partial" ? "var(--amber)" : "var(--rose)",
                color:"#fff",
              }}>
                {extraction.status}
              </span>
              <span style={{fontSize:11, color:"var(--ink-3)"}}>
                Confidence: <strong style={{color:"var(--ink-1)"}}>{extraction.confidence_label}</strong> ({confidencePct}%)
              </span>
            </div>

            {extraction.extracted_fields && Object.keys(extraction.extracted_fields).length > 0 && (
              <div style={{marginBottom:10}}>
                <div style={{fontSize:11, fontWeight:600, color:"var(--ink-3)", marginBottom:5}}>Extracted fields</div>
                <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:"3px 12px"}}>
                  {Object.entries(extraction.extracted_fields).map(([k, v]) => (
                    <div key={k} style={{display:"flex", gap:6, fontSize:12}}>
                      <span style={{color:"var(--ink-4)", fontFamily:"var(--mono)", flexShrink:0}}>{k}</span>
                      <span style={{color:"var(--ink-1)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap"}}>{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {extraction.missing_fields && extraction.missing_fields.length > 0 && (
              <div style={{marginBottom:10, fontSize:12, color:"var(--amber)"}}>
                <strong>Still needed: </strong>{extraction.missing_fields.join(", ")}
              </div>
            )}

            {extraction.assumptions && extraction.assumptions.length > 0 && (
              <div style={{fontSize:12}}>
                <div style={{fontWeight:600, color:"var(--ink-3)", marginBottom:4}}>Assumptions</div>
                <ul style={{margin:0, paddingLeft:18, color:"var(--ink-2)"}}>
                  {extraction.assumptions.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Retrieval trace ──────────────────────────────────── */}
      {retrieval && retrieval.status === "complete" && (
        <div className="out-section out-section-3">
          <div className="section-label"><span className="num">03</span> FBR rules retrieved</div>
          <div style={{marginBottom:8, fontSize:12, color:"var(--ink-2)"}}>
            <strong>Query: </strong>{retrieval.query_summary}
          </div>
          {retrieval.reasoning && (
            <blockquote style={{margin:"0 0 12px 0", padding:"8px 12px", borderLeft:"3px solid var(--forest)", background:"var(--surface-1)", fontSize:12, color:"var(--ink-2)", fontStyle:"italic"}}>
              {retrieval.reasoning}
            </blockquote>
          )}
          <div>
            {(retrieval.selected_sections || []).map((sec, i) => (
              <SectionCard key={sec.node_id || i} section={sec}/>
            ))}
          </div>
          <div style={{fontSize:10, color:"var(--ink-4)", fontFamily:"var(--mono)", marginTop:6}}>
            {retrieval.passes_used} pass{retrieval.passes_used !== 1 ? "es" : ""} · {(retrieval.selected_sections || []).length} sections
          </div>
        </div>
      )}

      {retrieval && retrieval.status === "skipped" && (
        <div className="out-section">
          <div style={{fontSize:12, color:"var(--ink-4)", fontStyle:"italic"}}>
            Retrieval skipped — awaiting complete tax data before searching FBR documents.
          </div>
        </div>
      )}

      {/* ── Interpretation trace ─────────────────────────────── */}
      {interpretation && interpretation.status === "complete" && (
        <div className="out-section out-section-4">
          <div className="section-label"><span className="num">04</span> Tax rules interpreted</div>

          {/* Income classifications */}
          {interpretation.income_classifications && interpretation.income_classifications.length > 0 && (
            <div style={{marginBottom:14}}>
              <div style={{fontSize:11, fontWeight:600, color:"var(--ink-3)", marginBottom:6}}>Income Classification</div>
              <div style={{display:"flex", flexDirection:"column", gap:6}}>
                {interpretation.income_classifications.map((ic, i) => (
                  <div key={i} style={{background:"var(--surface-1)", borderRadius:5, padding:"8px 12px", fontSize:12}}>
                    <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:3}}>
                      <span style={{fontWeight:600, color:"var(--ink-1)"}}>{ic.source_description}</span>
                      <span style={{
                        display:"inline-block", padding:"1px 7px", borderRadius:8, fontSize:10, fontWeight:600,
                        background: ic.tax_regime === "exempt" ? "var(--forest)" : ic.tax_regime === "final" ? "var(--amber)" : "var(--ink-3)",
                        color:"#fff",
                      }}>{ic.tax_regime}</span>
                    </div>
                    <div style={{color:"var(--ink-3)", fontFamily:"var(--mono)", fontSize:10}}>{ic.applicable_section} · {ic.applicable_schedule}</div>
                    <div style={{color:"var(--ink-3)", marginTop:3}}>{ic.reasoning}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Deductions */}
          {interpretation.deductions && interpretation.deductions.length > 0 && (
            <div style={{marginBottom:14}}>
              <div style={{fontSize:11, fontWeight:600, color:"var(--ink-3)", marginBottom:6}}>Deductions</div>
              <div style={{display:"flex", flexDirection:"column", gap:4}}>
                {interpretation.deductions.map((d, i) => (
                  <div key={i} style={{display:"flex", gap:8, fontSize:12, alignItems:"flex-start", padding:"6px 10px", background:"var(--surface-1)", borderRadius:4}}>
                    <span style={{color: d.allowed ? "var(--forest)" : "var(--rose)", fontWeight:700, flexShrink:0}}>
                      {d.allowed ? "✓" : "✗"}
                    </span>
                    <div>
                      <span style={{fontWeight:600}}>{d.type}</span>
                      <span style={{color:"var(--ink-3)"}}> — PKR {(d.claimed_amount||0).toLocaleString()}</span>
                      {d.cap_rule && <div style={{color:"var(--amber)", fontSize:11, marginTop:2}}>{d.cap_rule}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Withholding treatment */}
          {interpretation.withholding && interpretation.withholding.length > 0 && (
            <div style={{marginBottom:14}}>
              <div style={{fontSize:11, fontWeight:600, color:"var(--ink-3)", marginBottom:6}}>Withholding Treatment</div>
              <div style={{display:"flex", flexDirection:"column", gap:4}}>
                {interpretation.withholding.map((wh, i) => (
                  <div key={i} style={{display:"flex", justifyContent:"space-between", fontSize:12, padding:"6px 10px", background:"var(--surface-1)", borderRadius:4}}>
                    <span>{wh.source} <span style={{color:"var(--ink-4)", fontFamily:"var(--mono)", fontSize:10}}>(s.{wh.section})</span></span>
                    <span style={{
                      padding:"1px 7px", borderRadius:8, fontSize:10, fontWeight:600,
                      background: wh.regime === "final" ? "var(--amber)" : "var(--ink-3)",
                      color:"#fff",
                    }}>{wh.regime}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reasoning */}
          {interpretation.overall_reasoning && (
            <blockquote style={{margin:"0 0 10px 0", padding:"8px 12px", borderLeft:"3px solid var(--amber)", background:"var(--surface-1)", fontSize:12, color:"var(--ink-2)", fontStyle:"italic"}}>
              {interpretation.overall_reasoning}
            </blockquote>
          )}

          {/* Caveats */}
          {interpretation.caveats && interpretation.caveats.length > 0 && (
            <div style={{background:"#fffbea", border:"1px solid var(--amber)", borderRadius:5, padding:"8px 12px", fontSize:12}}>
              <div style={{fontWeight:600, color:"var(--amber)", marginBottom:4}}>Caveats & Assumptions</div>
              <ul style={{margin:0, paddingLeft:16, color:"var(--ink-2)"}}>
                {interpretation.caveats.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {interpretation && interpretation.status === "failed" && (
        <div className="out-section">
          <div style={{fontSize:12, color:"var(--rose)", fontStyle:"italic"}}>
            Tax rule interpretation failed — extraction and retrieval results are still available above.
          </div>
          {interpretation.error_message && (
            <div style={{fontFamily:"var(--mono)", fontSize:10, marginTop:6, padding:"6px 10px", background:"var(--surface-1)", borderRadius:4, color:"var(--rose)", whiteSpace:"pre-wrap", wordBreak:"break-all"}}>
              {interpretation.error_message}
            </div>
          )}
        </div>
      )}

      {/* ── Calculation trace ─────────────────────────────── */}
      {canvas.calculation && canvas.calculation.status === "complete" && (() => {
        const calc = canvas.calculation;
        const netColor = calc.is_refund ? "var(--forest)" : "var(--rose)";
        const fmt = (n) => `Rs. ${Number(n).toLocaleString("en-PK", {maximumFractionDigits:0})}`;
        return (
          <div className="out-section out-section-5">
            <div className="section-label"><span className="num">05</span> Tax calculation</div>

            {/* Summary box */}
            <div style={{background:"var(--surface-1)", border:"2px solid var(--line-light)", borderRadius:7, padding:"14px 16px", marginBottom:12}}>
              <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:"6px 20px", fontSize:12, marginBottom:10}}>
                <div style={{display:"flex", justifyContent:"space-between"}}>
                  <span style={{color:"var(--ink-3)"}}>Gross income</span>
                  <span style={{fontFamily:"var(--mono)"}}>{fmt(calc.total_gross_income)}</span>
                </div>
                <div style={{display:"flex", justifyContent:"space-between"}}>
                  <span style={{color:"var(--ink-3)"}}>Taxable income</span>
                  <span style={{fontFamily:"var(--mono)"}}>{fmt(calc.taxable_income_after_deductions)}</span>
                </div>
                <div style={{display:"flex", justifyContent:"space-between"}}>
                  <span style={{color:"var(--ink-3)"}}>Gross liability</span>
                  <span style={{fontFamily:"var(--mono)"}}>{fmt(calc.gross_tax_liability)}</span>
                </div>
                <div style={{display:"flex", justifyContent:"space-between"}}>
                  <span style={{color:"var(--ink-3)"}}>Withholding adjusted</span>
                  <span style={{fontFamily:"var(--mono)"}}>{fmt(calc.total_adjustable_withholding)}</span>
                </div>
              </div>
              <div style={{borderTop:"1px solid var(--line-light)", paddingTop:10, display:"flex", justifyContent:"space-between", alignItems:"center"}}>
                <span style={{fontWeight:700, fontSize:13, color:netColor}}>
                  {calc.is_refund ? "REFUND DUE" : "NET TAX PAYABLE"}
                </span>
                <span style={{fontWeight:700, fontSize:16, fontFamily:"var(--mono)", color:netColor}}>
                  {fmt(calc.is_refund ? calc.refund_due : calc.net_tax_payable)}
                </span>
              </div>
              <div style={{fontSize:11, color:"var(--ink-4)", marginTop:6, fontFamily:"var(--mono)"}}>
                Effective rate: {calc.effective_tax_rate}%
                {calc.minimum_tax_applicable && calc.minimum_tax_amount && (
                  <span style={{marginLeft:12}}>Min tax (s.113): {fmt(calc.minimum_tax_amount)}</span>
                )}
                {calc.super_tax_applicable && calc.super_tax_amount && (
                  <span style={{marginLeft:12}}>Super tax: {fmt(calc.super_tax_amount)}</span>
                )}
              </div>
            </div>

            {/* Income breakdown table */}
            {calc.income_breakdowns && calc.income_breakdowns.length > 0 && (
              <div style={{marginBottom:10}}>
                <div style={{fontSize:11, fontWeight:600, color:"var(--ink-3)", marginBottom:5}}>Income Breakdown</div>
                <div style={{overflowX:"auto"}}>
                  <table style={{width:"100%", borderCollapse:"collapse", fontSize:11}}>
                    <thead>
                      <tr style={{background:"var(--surface-1)"}}>
                        {["Source","Head","Amount","Schedule","Regime","Tax"].map(h => (
                          <th key={h} style={{padding:"5px 8px", textAlign:"left", color:"var(--ink-3)", fontWeight:600, borderBottom:"1px solid var(--line-light)"}}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {calc.income_breakdowns.map((row, i) => (
                        <tr key={i} style={{borderBottom:"1px solid var(--line-light)"}}>
                          <td style={{padding:"5px 8px", color:"var(--ink-1)"}}>{row.source_description}</td>
                          <td style={{padding:"5px 8px", color:"var(--ink-2)", textTransform:"capitalize"}}>{row.head.replace(/_/g," ")}</td>
                          <td style={{padding:"5px 8px", fontFamily:"var(--mono)", textAlign:"right"}}>{fmt(row.gross_income)}</td>
                          <td style={{padding:"5px 8px", color:"var(--ink-3)", fontSize:10}}>{row.applicable_schedule}</td>
                          <td style={{padding:"5px 8px"}}>
                            <span style={{
                              display:"inline-block", padding:"1px 6px", borderRadius:8, fontSize:10, fontWeight:600,
                              background: row.tax_regime === "exempt" ? "var(--forest)" : row.tax_regime === "final" ? "var(--amber)" : row.tax_regime === "separate" ? "#7c6af7" : "var(--ink-3)",
                              color:"#fff",
                            }}>{row.tax_regime}</span>
                          </td>
                          <td style={{padding:"5px 8px", fontFamily:"var(--mono)", textAlign:"right", fontWeight:600}}>
                            {row.withholding_is_final ? <span style={{color:"var(--amber)"}}>final WH</span> : fmt(row.computed_tax)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Deductions & credits */}
            {(calc.deductions_applied.length > 0 || calc.tax_credits_applied.length > 0) && (
              <Collapsible label={`Deductions & Credits (${calc.deductions_applied.length + calc.tax_credits_applied.length})`} defaultOpen={true}>
                {calc.deductions_applied.map((d, i) => (
                  <div key={i} style={{display:"flex", justifyContent:"space-between", fontSize:12, padding:"4px 0", borderBottom:"1px solid var(--line-light)"}}>
                    <div>
                      <span style={{fontWeight:600}}>u/s {d.section} — {d.type}</span>
                      {d.cap_rule && <div style={{fontSize:10, color:"var(--amber)"}}>{d.cap_rule}</div>}
                    </div>
                    <div style={{textAlign:"right", fontFamily:"var(--mono)"}}>
                      <div>Claimed: {fmt(d.claimed_amount)}</div>
                      <div style={{fontWeight:600, color:"var(--forest)"}}>Allowed: {fmt(d.allowed_amount)}</div>
                    </div>
                  </div>
                ))}
                {calc.tax_credits_applied.map((c, i) => (
                  <div key={i} style={{display:"flex", justifyContent:"space-between", fontSize:12, padding:"4px 0"}}>
                    <span style={{fontWeight:600}}>Credit u/s {c.section} — {c.type}</span>
                    <span style={{fontFamily:"var(--mono)", color:"var(--forest)"}}>−{fmt(c.credit_amount)}</span>
                  </div>
                ))}
              </Collapsible>
            )}

            {/* Withholding adjustments */}
            {calc.withholding_adjustments.length > 0 && (
              <Collapsible label={`Withholding Adjustments (${calc.withholding_adjustments.length})`} defaultOpen={true}>
                {calc.withholding_adjustments.map((w, i) => (
                  <div key={i} style={{display:"flex", justifyContent:"space-between", fontSize:12, padding:"4px 0", borderBottom:"1px solid var(--line-light)"}}>
                    <div>
                      <span>{w.source}</span>
                      <span style={{color:"var(--ink-4)", fontFamily:"var(--mono)", fontSize:10, marginLeft:6}}>s.{w.section}</span>
                    </div>
                    <div style={{display:"flex", alignItems:"center", gap:8}}>
                      <span style={{fontFamily:"var(--mono)"}}>{fmt(w.amount)}</span>
                      <span style={{
                        padding:"1px 6px", borderRadius:8, fontSize:10, fontWeight:600,
                        background: w.treatment === "final" ? "var(--amber)" : "var(--forest)",
                        color:"#fff",
                      }}>{w.treatment}</span>
                    </div>
                  </div>
                ))}
                <div style={{fontSize:11, color:"var(--ink-3)", marginTop:8, display:"flex", justifyContent:"space-between"}}>
                  <span>Total adjustable:</span>
                  <span style={{fontFamily:"var(--mono)", fontWeight:600}}>{fmt(calc.total_adjustable_withholding)}</span>
                </div>
              </Collapsible>
            )}

            {/* Computation notes */}
            {calc.computation_notes.length > 0 && (
              <Collapsible label="Computation notes (step-by-step math)" defaultOpen={false}>
                <ol style={{margin:0, paddingLeft:18, fontSize:11, color:"var(--ink-2)", lineHeight:1.8, fontFamily:"var(--mono)"}}>
                  {calc.computation_notes.map((n, i) => <li key={i}>{n}</li>)}
                </ol>
              </Collapsible>
            )}

            {/* Caveats */}
            {calc.caveats && calc.caveats.length > 0 && (
              <div style={{background:"#fffbea", border:"1px solid var(--amber)", borderRadius:5, padding:"8px 12px", fontSize:12, marginTop:8}}>
                <div style={{fontWeight:600, color:"var(--amber)", marginBottom:4}}>Caveats</div>
                <ul style={{margin:0, paddingLeft:16, color:"var(--ink-2)"}}>
                  {calc.caveats.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            )}
          </div>
        );
      })()}

      {canvas.calculation && canvas.calculation.status === "failed" && (
        <div className="out-section">
          <div style={{fontSize:12, color:"var(--rose)", fontStyle:"italic"}}>
            Tax calculation failed — interpretation results are still available above.
            {canvas.calculation.error_message && (
              <div style={{fontFamily:"var(--mono)", fontSize:10, marginTop:4, color:"var(--rose)"}}>
                {canvas.calculation.error_message}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="notice" style={{marginTop:"auto"}}>
        <span className="ico"><Icon name="info" size={16}/></span>
        <div>
          <strong>Not tax advice.</strong> Estimates are based on FBR TY 2025-26 data. Always verify with a licensed tax practitioner before filing.
        </div>
      </div>
    </div>
  );
};

window.CanvasView = CanvasView;
window.OutputView = CanvasView; // backward-compat alias
