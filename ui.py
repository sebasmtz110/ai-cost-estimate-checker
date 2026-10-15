"""Friendly storefront-style look. CSS only restyles real Streamlit widgets. The custom HTML (header bar and card
text) is display-only and has pointer-events:none, so it can never block a click or tap."""
import html
import pandas as pd

ACCENT, ACCENT_SOFT = "#4F46E5", "#EEF2FF"
OVER, UNDER, MUTED, LINE, INK = "#5B21B6", "#0F766E", "#64748B", "#E2E8F0", "#1E293B"  # over = deep purple, under = teal
SEV_STYLE = {"High": (ACCENT, "#FFFFFF", ACCENT), "Medium": ("#C7D2FE", "#3730A3", "#C7D2FE"),
             "Low": ("#FFFFFF", ACCENT, ACCENT)}  # (background, text, border): solid / lighter / outline
SEVERITY_ICON = {"High": "● High", "Medium": "● Medium", "Low": "● Low"}
SIGNAL = {"HIGH": "▲ Over", "LOW": "▼ Under", "N/A": "—"}
e = html.escape

CSS = f"""
<style>
  html, body, .stApp {{font-family: Inter, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;}}
  * {{font-variant-numeric: tabular-nums;}}
  .block-container {{padding-top: 2.4rem; padding-bottom: 3.5rem; max-width: 1120px;}}
  /* display-only HTML: never capture clicks */
  .hdr, .hdr *, .pcard, .pcard *, .steplbl, .steplbl * {{pointer-events: none;}}
  .hdr {{padding: 4px 2px 10px;}}
  .hdr .logo {{font-size: 1.7rem; font-weight: 750; letter-spacing: -.02em; color: {INK};}}
  .hdr .tag {{color: {MUTED}; font-size: .95rem; margin-top: 2px;}}
  .hdr .src {{display: inline-block; margin-top: 10px; font-size: .8rem; color: {ACCENT}; background: {ACCENT_SOFT};
              border-radius: 999px; padding: 3px 12px;}}
  /* white cards with subtle borders and gentle shadows */
  div[class*="st-key-card_"], .st-key-line_detail, .st-key-reviewer_card, .st-key-searchbar {{
     background: #fff; border-radius: 14px !important; border: 1px solid {LINE} !important;
     box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 4px 14px rgba(15,23,42,.05); padding: 16px 18px;}}
  .st-key-searchbar {{padding: 12px 16px 6px;}}
  .steplbl {{font-size: 1.15rem; font-weight: 700; margin: 1.8rem 0 .3rem; color: {INK};}}
  .steplbl span {{display: inline-block; width: 26px; height: 26px; line-height: 26px; text-align: center;
                  background: {ACCENT}; color: #fff; border-radius: 50%; margin-right: 10px; font-size: .85rem;}}
  .stButton button, .stDownloadButton button {{border-radius: 10px;}}
  [class*="st-key-see_"] button {{border: 1px solid {ACCENT}; color: {ACCENT}; background: #fff;}}
  [class*="st-key-see_"] button:hover {{background: {ACCENT_SOFT}; color: {ACCENT}; border-color: {ACCENT};}}
  /* counter tiles = real st.buttons */
  [class*="st-key-kpi_"] button {{min-height: 92px; border-radius: 14px; background: #fff; border: 1px solid {LINE};
                                  box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 4px 14px rgba(15,23,42,.05);}}
  [class*="st-key-kpi_"] button:hover {{border-color: {ACCENT};}}
  [class*="st-key-kpi_"] button p {{font-size: .85rem; margin: 0; line-height: 1.35; color: {MUTED};}}
  [class*="st-key-kpi_"] button p strong {{font-size: 1.75rem; font-weight: 750; display: block; color: {INK};}}
  .st-key-kpi_over button p strong {{color: {OVER};}}
  .st-key-kpi_under button p strong {{color: {UNDER};}}
  [class*="st-key-kpi_"] button[data-testid="stBaseButton-primary"] {{background: {ACCENT}; border-color: {ACCENT};}}
  [class*="st-key-kpi_"] button[data-testid="stBaseButton-primary"] p,
  [class*="st-key-kpi_"] button[data-testid="stBaseButton-primary"] p strong {{color: #fff !important;}}
  /* flagged item cards */
  .pcard .t {{font-weight: 650; font-size: 1rem; color: {INK}; line-height: 1.3; min-height: 2.6em;}}
  .pcard .m {{color: {MUTED}; font-size: .8rem; margin: 2px 0 10px;}}
  .pcard .p {{font-size: 1.4rem; font-weight: 700; color: {INK};}}
  .pcard .p small {{font-size: .8rem; color: {MUTED}; font-weight: 400;}}
  .pcard .r {{color: {MUTED}; font-size: .85rem;}}
  .pcard .pill {{display: inline-block; font-weight: 600; font-size: .75rem; padding: 2px 10px; border-radius: 999px; margin: 10px 6px 4px 0;}}
  .pcard .imp {{font-size: .85rem; margin-top: 4px; color: {MUTED};}} .pcard .imp b.o {{color: {OVER};}} .pcard .imp b.u {{color: {UNDER};}}
  [data-testid="stMetricValue"] {{font-weight: 700;}}
  @media (max-width: 640px) {{
    [class*="st-key-kpi_"] button {{min-height: 64px;}}
    [class*="st-key-kpi_"] button p strong {{font-size: 1.4rem;}}
  }}
</style>
"""


def header(source: str) -> str:
    return (f'<div class="hdr"><div class="logo">Cost Estimate Checker</div>'
            f'<div class="tag">Find over- and under-priced line items in repair estimates, with an AI reviewer note.</div>'
            f'<div class="src">{e(source)}</div></div>')


def step(n: int, title: str) -> str:
    return f'<div class="steplbl"><span>{n}</span>{e(title)}</div>'


def money(v, signed=False) -> str:
    if pd.isna(v):
        return "—"
    if signed:
        return "$0" if round(v) == 0 else f"{'+' if v > 0 else '-'}${abs(v):,.0f}"
    return f"${v:,.2f}"


def pct(v) -> str:
    return "—" if pd.isna(v) else f"{v:+.0%}"


def _pill(text, bg, fg, border=None) -> str:
    return f'<span class="pill" style="background:{bg};color:{fg};border:1px solid {border or bg}">{e(text)}</span>'


def product_card(r) -> str:
    over = r.direction == "HIGH"
    sig = (_pill(f"{'▲' if over else '▼'} {abs(r.pct_vs_baseline):.0%} {'over' if over else 'under'}",
                 "#EDE9FE" if over else "#CCFBF1", OVER if over else UNDER) if pd.notna(r.pct_vs_baseline) else "")
    sev = _pill(f"{r.severity} severity", *SEV_STYLE[r.severity]) if r.severity else ""
    imp = r["potential_variance_$"]
    return (f'<div class="pcard"><div class="t">{e(r["item"])}</div>'
            f'<div class="m">{e(r.estimate_id)} · {e(r.category)} · {r.qty:,.0f} {e(r.unit)}</div>'
            f'<div class="p">{money(r.unit_cost)} <small>/ {e(r.unit or "unit")}</small></div>'
            f'<div class="r">Reference {money(r.baseline_unit_cost)}</div>{sig}{sev}'
            f'<div class="imp">Impact <b class="{"o" if over else "u"}">{money(imp, True)}</b></div></div>')
