"""
AI reviewer summary: writes a reviewer-style note for one estimate.

If the OPENAI_API_KEY environment variable is set (and the `openai` package is
installed), an LLM writes the note from the checker's findings. Otherwise -- or
if the API call fails -- a deterministic template writes it, so the app always works.
Keys are only ever read from the environment; never put a key in this file.
"""
import os
import pandas as pd

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _facts(df: pd.DataFrame, estimate_id: str) -> dict:
    e = df[df.estimate_id == estimate_id]
    f = e[e.flagged].copy()
    f["abs_var"] = f["potential_variance_$"].abs()
    f = f.sort_values("abs_var", ascending=False)
    total = float(e.line_total.sum())
    high = float(f.loc[f.direction == "HIGH", "potential_variance_$"].sum())
    low = float(f.loc[f.direction == "LOW", "potential_variance_$"].sum())
    return {"estimate_id": estimate_id, "lines": len(e), "flagged": len(f), "total": total,
            "high_var": high, "low_var": low, "top": f.head(3)}


def template_summary(df: pd.DataFrame, estimate_id: str) -> str:
    x = _facts(df, estimate_id)
    if x["flagged"] == 0:
        return (f"**Estimate {estimate_id} — Reviewer note**\n\n"
                f"**Overall assessment:** All {x['lines']} line items (total ${x['total']:,.0f}) are within "
                "expected ranges versus reference pricing and peer estimates. No pricing exceptions noted.\n\n"
                "**Recommended follow-ups:** Confirm quantities against the scope of work and site photos.")
    share = abs(x["high_var"]) / x["total"] if x["total"] else 0
    level = ("Significant pricing concerns" if share > 0.05 or x["flagged"] >= 3
             else "Minor pricing exceptions")
    lines = [f"**Estimate {estimate_id} — Reviewer note**", "",
             f"**Overall assessment:** {level}. {x['flagged']} of {x['lines']} line items {'was' if x['flagged'] == 1 else 'were'} flagged "
             f"on an estimate total of ${x['total']:,.0f}.", "", "**Top issues:**"]
    for _, r in x["top"].iterrows():
        lines.append(f"- {r['item']} ({r['direction']}): ${r.unit_cost:,.2f}/{r.unit} vs reference "
                     f"${r.reference_unit_cost:,.2f} ({r.pct_vs_reference:+.0%}), "
                     f"impact ${r['potential_variance_$']:+,.0f}.")
    lines += ["", f"**Dollar impact:** Potential overpricing ${x['high_var']:,.0f}; "
              f"underpricing ${abs(x['low_var']):,.0f} (may indicate missing scope).", "",
              "**Recommended follow-ups:**"]
    if x["high_var"] > 0:
        lines.append("- Request supporting invoices or vendor quotes for high-priced items.")
    if x["low_var"] < 0:
        lines.append("- Confirm low-priced items include full scope (materials, labor, disposal).")
    lines.append("- Verify quantities against field measurements before approval.")
    return "\n".join(lines)


def llm_summary(df: pd.DataFrame, estimate_id: str) -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        x = _facts(df, estimate_id)
        issues = x["top"][["item", "unit", "unit_cost", "reference_unit_cost", "pct_vs_reference",
                           "potential_variance_$", "direction", "reason"]].to_dict("records")
        prompt = (
            "You are a construction cost reviewer. Write a concise reviewer note in Markdown with sections "
            "'Overall assessment', 'Top issues', 'Dollar impact', 'Recommended follow-ups'. Use only these "
            f"facts; do not invent numbers.\nEstimate: {estimate_id}\nLine items: {x['lines']}\n"
            f"Flagged: {x['flagged']}\nEstimate total: ${x['total']:,.2f}\n"
            f"Overpricing variance: ${x['high_var']:,.2f}\nUnderpricing variance: ${x['low_var']:,.2f}\n"
            f"Top flagged items: {issues}")
        resp = OpenAI(api_key=key).chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.2, timeout=30)
        return resp.choices[0].message.content
    except Exception:
        return None  # fall back to the template


def reviewer_summary(df: pd.DataFrame, estimate_id: str) -> tuple[str, str]:
    """Returns (note, source) where source is 'AI (LLM)' or 'Template'."""
    note = llm_summary(df, estimate_id)
    return (note, "AI (LLM)") if note else (template_summary(df, estimate_id), "Template")
