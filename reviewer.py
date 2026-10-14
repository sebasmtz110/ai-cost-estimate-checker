"""
AI reviewer summary: writes a reviewer-style note for one estimate.

Provider order:
  1. Google Gemini (free tier) if GEMINI_API_KEY or GOOGLE_API_KEY is set
  2. OpenAI (optional) if OPENAI_API_KEY is set
  3. Deterministic template (always works, no key needed)
Keys are read from environment variables or Streamlit secrets (.streamlit/secrets.toml
or the Streamlit Cloud "Secrets" box). Never put a key in this file.
"""
import os
import time
import pandas as pd


def _get(name, default=None):
    """Read a setting from the environment first, then Streamlit secrets."""
    if os.getenv(name):
        return os.getenv(name)
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:  # no secrets file / not running in Streamlit
        return default


GEMINI_DEFAULT_MODEL = "gemini-3.8-flash"
GEMINI_BACKUP_MODEL = "gemini-3.5-flash-lite"  # used if the main model is busy (free tier 503s)
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


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


def _prompt(df, estimate_id) -> str:
    x = _facts(df, estimate_id)
    issues = x["top"][["item", "unit", "unit_cost", "reference_unit_cost", "pct_vs_reference",
                       "potential_variance_$", "direction", "reason"]].to_dict("records")
    return ("You are a construction cost reviewer. Write a concise reviewer note in Markdown with sections "
            "'Overall assessment', 'Top issues', 'Dollar impact', 'Recommended follow-ups'. Use only these "
            f"facts; do not invent numbers.\nEstimate: {estimate_id}\nLine items: {x['lines']}\n"
            f"Flagged: {x['flagged']}\nEstimate total: ${x['total']:,.2f}\n"
            f"Overpricing variance: ${x['high_var']:,.2f}\nUnderpricing variance: ${x['low_var']:,.2f}\n"
            f"Top flagged items: {issues}")


def gemini_summary(prompt: str) -> str | None:
    key = _get("GEMINI_API_KEY") or _get("GOOGLE_API_KEY")
    if not key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=key, http_options={"timeout": 30000})
    except Exception:
        return None
    models = [_get("GEMINI_MODEL", GEMINI_DEFAULT_MODEL), GEMINI_BACKUP_MODEL]
    for model in dict.fromkeys(models):      # main model first, then backup
        for attempt in range(2):            # one quick retry for "busy" errors
            try:
                resp = client.models.generate_content(model=model, contents=prompt,
                                                      config={"temperature": 0.2})
                if resp.text:
                    return resp.text
            except Exception as e:
                if "API key" in str(e) or "PERMISSION" in str(e):
                    return None             # bad key: no point retrying
                time.sleep(1.5 * (attempt + 1))
    return None


def openai_summary(prompt: str) -> str | None:
    key = _get("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        resp = OpenAI(api_key=key, timeout=30).chat.completions.create(
            model=_get("OPENAI_MODEL", OPENAI_DEFAULT_MODEL),
            messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return resp.choices[0].message.content or None
    except Exception:
        return None


def llm_summary(df: pd.DataFrame, estimate_id: str) -> tuple[str, str] | None:
    prompt = _prompt(df, estimate_id)
    for fn, label in ((gemini_summary, "AI (Gemini)"), (openai_summary, "AI (OpenAI)")):
        note = fn(prompt)
        if note:
            return note, label
    return None


def reviewer_summary(df: pd.DataFrame, estimate_id: str) -> tuple[str, str]:
    """Returns (note, source): source is 'AI (Gemini)', 'AI (OpenAI)' or 'Template'."""
    return llm_summary(df, estimate_id) or (template_summary(df, estimate_id), "Template")
