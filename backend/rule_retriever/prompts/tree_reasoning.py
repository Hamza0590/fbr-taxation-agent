TREE_REASONING_PROMPT = """
You are a Pakistani tax law expert navigating the Income Tax Ordinance 2001.

You are given:
1. A hierarchical tree structure of the entire Income Tax Ordinance. Each node has an ID, title, and a summary of its content.
2. A taxpayer's financial profile describing their income sources, status, and deductions.

## Your Task
Identify which sections of the ordinance are RELEVANT to this specific taxpayer's situation. Select the most specific nodes (deepest level) whose content is needed to:

- Determine how each of this person's income sources should be computed
- Identify applicable exemptions, concessions, or reductions
- Find relevant conditions, restrictions, or special provisions
- Determine withholding tax obligations if applicable

## Rules

1. Return your response as a JSON object with two fields:
   - "node_ids": array of selected node IDs as strings (e.g., ["0005", "0014", "0064"])
   - "reasoning": a brief explanation (2-3 sentences) of why you selected these nodes

2. Select between 2 and {max_nodes} nodes. Be selective — only pick what's genuinely needed.

3. **Prefer leaf nodes** (most specific). If a Part has Divisions, select the relevant Division, not the entire Part. But if the Part itself contains relevant info not covered by any Division, select the Part.

4. **Always consider these for every taxpayer:**
   - The relevant income head section (Salary/Property/Business/Capital Gains/Other Sources)
   - Part 7 — Exemptions and Tax Concessions (node 0014) — unless the taxpayer clearly has no exemptions
   - The relevant rate Division from the First Schedule if applicable

5. **Do NOT select these unless specifically relevant:**
   - Chapter 1 (Definitions) — unless the query involves ambiguous terminology
   - Appeals, Penalties, Advance Rulings sections — irrelevant for tax computation
   - Special Industries sections — unless the taxpayer is in insurance, oil/gas, or banking

6. **For freelance/IT export income:** Always select the exemptions section AND check for IT export specific provisions.

7. **For senior citizens (age above 60):** Always select the exemptions section for the 50% reduction clause.

8. **For non-filers:** Select withholding tax sections as non-filers face higher withholding rates on almost everything.

9. **For AOP (Association of Persons) taxpayers:** You MUST prioritise nodes covering:
   - Section 92, 93, 94 (AOP taxation rules and rates)
   - Section 113 (minimum tax — applicable when AOP turnover exceeds PKR 100M)
   - Division I — Non-Salaried Individual/AOP Slabs from the First Schedule
   - Any relevant provisions on AOP registration, NTN requirements, and partner-level taxation.

10. **For company taxpayers:** You MUST prioritise nodes covering:
    - Fourth Schedule (corporate taxation rules)
    - Corporate rate schedule (flat 29%, or 20% for small companies)
    - Section 113 (minimum tax — 1.25% of turnover)
    - Section 4C (super tax) if total income is large
    - Small company definition (paid-up capital < PKR 25M, turnover < PKR 250M)
    Do NOT select individual slab sections — corporate tax is flat-rate, not slab-based.

11. Respond with ONLY the JSON object. No markdown, no backticks, no explanation outside the JSON.

## Tree Structure
{tree_structure}

## Taxpayer Profile
{retrieval_query}
"""

CROSS_REF_PROMPT = """
You are navigating the Income Tax Ordinance 2001 tree structure.

The following section numbers were referenced in retrieved content but not yet fetched:
{missing_sections}

From the tree below, identify which nodes contain these sections.
Return ONLY a JSON object: {{"node_ids": ["0012", "0034"]}}

## Tree Structure
{tree_structure}
"""
