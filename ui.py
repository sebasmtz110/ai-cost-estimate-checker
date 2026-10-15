"""Friendly storefront-style look. CSS only restyles real Streamlit widgets. The custom HTML (header bar and card
text) is display-only and has pointer-events:none, so it can never block a click or tap."""
import html
import pandas as pd

NAVY, NAVY2, ORANGE, YELLOW = "#131921", "#232F3E", "#FF9900", "#FFD814"
OVER, UNDER, MUTED, LINE = "#CC0C39", "#067D62", "#565959", "#D5D9D9"
ACCENT = ORANGE
STARS = {"High": "★★★", "Medium": "★★☆", "Low": "★☆☆"}
SEVERITY_ICON = {k: f"{v} {k}" for k, v in STARS.items()}
SIGNAL = {"HIGH": "▲ Over", "LOW": "▼ Under", "N/A": "—"}
e = html.escape

CSS = f"""
<style>
  html, body, [class*="css"], .stApp {{font-family: Inter, "Amazon Ember", -apple-system, "Segoe UI", Roboto, Arial, sans-serif;}}
  * {{font-variant-numeric: tabular-nums;}}
  .block-container {{padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1180px;}}
  header[data-testid="stHeader"] {{background: transparent;}}
  /* display-only HTML: never capture clicks */
  .hdr, .hdr *, .pcard, .pcard *, .steplbl, .steplbl * {{pointer-events: none;}}
  .hdr {{background: {NAVY}; color: #fff; border-radius: 12px 12px 0 0; padding: 14px 22px; display: flex;
         align-items: center; gap: 14px; flex-wrap: wrap;}}
  .hdr .logo {{font-size: 1.35rem; font-weight: 800; letter-spacing: -.01em;}}
  .hdr .logo b {{color: {ORANGE};}}
  .hdr .tag {{color: #CCCCCC; font-size: .86rem;}}
  .subhdr {{background: {NAVY2}; color: #fff; border-radius: 0 0 12px 12px; padding: 7px 22px; font-size: .82rem; margin-bottom: 14px;}}
  /* white rounded cards with soft shadow */
  [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{background: #fff;}}
  div[class*="st-key-panel_"], div[class*="st-key-card_"], .st-key-line_detail, .st-key-reviewer_card {{
     background: #fff; border-radius: 12px !important; border: 1px solid {LINE} !important;
     box-shadow: 0 2px 6px rgba(15,17,17,.08); padding: 14px 16px;}}
  /* search-like filter bar */
  .st-key-searchbar {{background: {NAVY2}; border-radius: 12px; padding: 10px 14px 4px;}}
  .st-key-searchbar label p {{color: #fff !important; font-weight: 600;}}
  .st-key-searchbar [data-baseweb="select"] > div {{border-radius: 999px; border: 2px solid {ORANGE};}}
  .steplbl {{font-size: 1.2rem; font-weight: 700; margin: 1.2rem 0 .2rem; color: #0F1111;}}
  .steplbl span {{background: {ORANGE}; color: #fff; border-radius: 999px; padding: 1px 10px; margin-right: 8px; font-size: .9rem;}}
  /* pill buttons */
  .stButton button, .stDownloadButton button {{border-radius: 999px;}}
  [class*="st-key-see_"] button, .stDownloadButton button {{background: {YELLOW}; border: 1px solid #FCD200; color: #0F1111;}}
  [class*="st-key-see_"] button:hover, .stDownloadButton button:hover {{background: #F7CA00; border-color: #F2C200; color: #0F1111;}}
  /* counter tiles = real st.buttons */
  [class*="st-key-kpi_"] button {{min-height: 92px; border-radius: 14px; background: #fff; border: 1px solid {LINE};
                                  box-shadow: 0 2px 6px rgba(15,17,17,.08);}}
  [class*="st-key-kpi_"] button:hover {{border-color: {ORANGE};}}
  [class*="st-key-kpi_"] button p {{font-size: .85rem; margin: 0; line-height: 1.35; color: {MUTED};}}
  [class*="st-key-kpi_"] button p strong {{font-size: 1.8rem; font-weight: 800; display: block; color: #0F1111;}}
  .st-key-kpi_over button p strong {{color: {OVER};}}
  .st-key-kpi_under button p strong {{color: {UNDER};}}
  [class*="st-key-kpi_"] button[data-testid="stBaseButton-primary"] {{background: #FFF8E6; border: 2px solid {ORANGE};
                                  box-shadow: 0 0 0 3px rgba(255,153,0,.25);}}
  [class*="st-key-kpi_"] button[data-testid="stBaseButton-primary"] p {{color: #0F1111 !important;}}
  /* product cards */
  .pcard .t {{font-weight: 700; font-size: 1rem; color: #0F1111; line-height: 1.3; min-height: 2.6em;}}
  .pcard .m {{color: {MUTED}; font-size: .8rem; margin: 2px 0 8px;}}
  .pcard .p {{font-size: 1.45rem; font-weight: 700; color: #0F1111;}}
  .pcard .p small {{font-size: .8rem; color: {MUTED}; font-weight: 400;}}
  .pcard .r {{color: {MUTED}; font-size: .85rem;}} .pcard .r s {{color: {MUTED};}}
  .pcard .badge {{display: inline-block; color: #fff; font-weight: 700; font-size: .78rem; padding: 3px 9px;
                  border-radius: 4px; margin: 8px 6px 4px 0;}}
  .pcard .over {{background: {OVER};}} .pcard .under {{background: {UNDER};}}
  .pcard .stars {{color: #FFA41C; font-size: 1rem; letter-spacing: 1px;}} .pcard .stars em {{color: {MUTED}; font-size: .78rem; font-style: normal; margin-left: 4px;}}
  .pcard .imp {{font-size: .85rem; margin-top: 2px;}} .pcard .imp b.o {{color: {OVER};}} .pcard .imp b.u {{color: {UNDER};}}
  [data-testid="stMetricValue"] {{font-weight: 700;}}
  @media (max-width: 640px) {{
    [class*="st-key-kpi_"] button {{min-height: 64px;}}
    [class*="st-key-kpi_"] button p strong {{font-size: 1.45rem;}}
    .hdr .tag {{display: none;}}
  }}
</style>
"""


def header(source: str) -> str:
    return (f'<div class="hdr"><div class="logo">🏗️ Cost Estimate <b>Checker</b></div>'
            f'<div class="tag">Find over- and under-priced line items in repair estimates, with an AI reviewer note.</div></div>'
            f'<div class="subhdr">📍 {e(source)}</div>')


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


def product_card(r) -> str:
    over = r.direction == "HIGH"
    badge = (f'<span class="badge {"over" if over else "under"}">{"▲" if over else "▼"} '
             f'{abs(r.pct_vs_baseline):.0%} {"over" if over else "under"}</span>') if pd.notna(r.pct_vs_baseline) else ""
    stars = f'<span class="stars">{STARS.get(r.severity, "")}<em>{e(r.severity)} severity</em></span>' if r.severity else ""
    imp = r["potential_variance_$"]
    return (f'<div class="pcard"><div class="t">{e(r["item"])}</div>'
            f'<div class="m">{e(r.estimate_id)} · {e(r.category)} · {r.qty:,.0f} {e(r.unit)}</div>'
            f'<div class="p">{money(r.unit_cost)} <small>/ {e(r.unit or "unit")}</small></div>'
            f'<div class="r">Reference: <s>{money(r.baseline_unit_cost)}</s></div>{badge}{stars}'
            f'<div class="imp">Impact: <b class="{"o" if over else "u"}">{money(imp, True)}</b></div></div>')
