"""Terminal-style look. CSS only restyles real Streamlit widgets; the only custom HTML (ticker strip and
section labels) is decorative and has pointer-events:none, so nothing can block clicks/taps."""
import html
import pandas as pd

ACCENT, OVER, UNDER, MUTED, GRID = "#FF9F1C", "#FF4D4F", "#2ECC71", "#7D8590", "#1E252E"
SEVERITY_ICON = {"High": "■ HIGH", "Medium": "■ MED", "Low": "■ LOW"}
SIGNAL = {"HIGH": "▲ OVER", "LOW": "▼ UNDER", "N/A": "—"}

CSS = f"""
<style>
  .block-container {{padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px;}}
  h1 {{font-size: 1.55rem !important; letter-spacing: .02em; text-transform: uppercase;}}
  h3 {{font-size: 1.05rem !important; text-transform: uppercase; letter-spacing: .06em;}}
  h4 {{font-size: 1rem !important;}}
  * {{font-variant-numeric: tabular-nums;}}
  /* thin-bordered panels */
  [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] details {{border-radius: 4px !important; border-color: {GRID} !important;}}
  /* KPI counters = real st.buttons, styled like terminal quote cells */
  [class*="st-key-kpi_"] button {{min-height: 84px; border-radius: 3px; border: 1px solid {GRID}; background: #0D1117;}}
  [class*="st-key-kpi_"] button:hover {{border-color: {ACCENT};}}
  [class*="st-key-kpi_"] button p {{font-size: .7rem; letter-spacing: .12em; text-transform: uppercase; margin: 0; line-height: 1.4;}}
  [class*="st-key-kpi_"] button p strong {{font-size: 1.75rem; font-weight: 700; display: block; letter-spacing: 0;}}
  .st-key-kpi_over button p strong {{color: {OVER};}}
  .st-key-kpi_under button p strong {{color: {UNDER};}}
  /* active counter: solid amber cell with dark text */
  [class*="st-key-kpi_"] button[data-testid="stBaseButton-primary"] {{background: {ACCENT}; border-color: {ACCENT};}}
  [class*="st-key-kpi_"] button[data-testid="stBaseButton-primary"] p,
  [class*="st-key-kpi_"] button[data-testid="stBaseButton-primary"] p strong {{color: #07090C !important;}}
  [data-testid="stMetricValue"] {{font-size: 1.45rem;}}
  [data-testid="stMetricLabel"] p {{text-transform: uppercase; letter-spacing: .1em; font-size: .68rem; color: {MUTED};}}
  /* decorative-only elements: never capture pointer events */
  .ticker, .ticker *, .lbl, .lbl * {{pointer-events: none; user-select: none;}}
  .ticker {{overflow: hidden; white-space: nowrap; border-top: 1px solid {GRID}; border-bottom: 1px solid {GRID};
            background: #0B0E13; font-size: .74rem; padding: 6px 0; margin: 4px 0 14px;}}
  .ticker .track {{display: inline-block; animation: tick 45s linear infinite;}}
  .ticker span {{margin-right: 28px; color: {MUTED};}}
  .ticker b {{color: #E6E6E6; font-weight: 600;}} .ticker .up {{color: {OVER};}} .ticker .dn {{color: {UNDER};}}
  .ticker .acc {{color: {ACCENT}; font-weight: 700;}}
  @keyframes tick {{from {{transform: translateX(0);}} to {{transform: translateX(-50%);}}}}
  @media (prefers-reduced-motion: reduce) {{.ticker .track {{animation: none; white-space: normal;}}}}
  .lbl {{color: {ACCENT}; font-size: .7rem; letter-spacing: .16em; text-transform: uppercase; font-weight: 700;
         border-bottom: 1px solid {GRID}; padding-bottom: 4px; margin: 1.3rem 0 .4rem;}}
  .lbl i {{color: {MUTED}; font-style: normal; font-weight: 400;}}
  @media (max-width: 640px) {{
    [class*="st-key-kpi_"] button {{min-height: 58px;}}
    [class*="st-key-kpi_"] button p strong {{font-size: 1.35rem;}}
    .ticker .track {{animation-duration: 28s;}}
  }}
</style>
"""


def step(n: int, title: str) -> str:
    return f'<div class="lbl">{n:02d} <i>//</i> {html.escape(title)}</div>'


def ticker(items) -> str:
    """items: list of (label, value, css class or ''). Decorative; content is duplicated for a seamless loop."""
    cells = "".join(f'<span>{html.escape(l)} <b class="{c}">{html.escape(v)}</b></span>' for l, v, c in items)
    half = f'<span class="acc">COSTCHK ▸</span>{cells}'
    return f'<div class="ticker" aria-hidden="true"><div class="track">{half}{half}</div></div>'


def money(v, signed=False) -> str:
    if pd.isna(v):
        return "—"
    if signed:
        return "$0" if round(v) == 0 else f"{'+' if v > 0 else '-'}${abs(v):,.0f}"
    return f"${v:,.2f}"


def pct(v) -> str:
    return "—" if pd.isna(v) else f"{v:+.0%}"
