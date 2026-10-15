"""Small visual helpers. CSS is minimal and only restyles real Streamlit widgets
(no overlays, no fixed/absolute elements), so everything stays clickable on desktop and mobile."""
import pandas as pd

ACCENT = "#EA580C"
SEVERITY_ICON = {"High": "🔴 High", "Medium": "🟠 Medium", "Low": "🔵 Low"}

CSS = """
<style>
  .block-container {padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1100px;}
  /* KPI counters are real st.buttons inside keyed containers; this only makes them bigger */
  [class*="st-key-kpi_"] button {min-height: 88px; border-radius: 14px;}
  [class*="st-key-kpi_"] button p {font-size: .82rem; line-height: 1.3; margin: 0;}
  [class*="st-key-kpi_"] button p strong {font-size: 1.65rem; font-weight: 700; display: block;}
  @media (max-width: 640px) {[class*="st-key-kpi_"] button {min-height: 62px;}}
  .step {color: #EA580C; font-weight: 700; font-size: .75rem; letter-spacing: .12em;
         text-transform: uppercase; margin-top: 1.4rem;}
</style>
"""


def step(n: int, title: str) -> str:
    return f'<div class="step">Step {n}</div>\n\n### {title}'


def money(v, signed=False) -> str:
    if pd.isna(v):
        return "—"
    if signed:
        return "$0" if round(v) == 0 else f"{'+' if v > 0 else '-'}${abs(v):,.0f}"
    return f"${v:,.2f}"


def pct(v) -> str:
    return "—" if pd.isna(v) else f"{v:+.0%}"
