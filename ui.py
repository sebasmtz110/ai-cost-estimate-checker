"""Visual building blocks for the app: colors, CSS, KPI cards, badges and the flagged-items table."""
import html
import pandas as pd

NAVY, PANEL, BORDER = "#0B1220", "#131C2E", "#22304A"
TEXT, MUTED, ACCENT = "#E2E8F0", "#94A3B8", "#F5A524"
RED, ORANGE, GREEN, BLUE = "#F87171", "#FB923C", "#34D399", "#60A5FA"
SEVERITY_COLORS = {"High": RED, "Medium": ORANGE, "Low": BLUE}

CSS = f"""
<style>
  .block-container {{padding-top: 2.2rem; max-width: 1320px;}}
  header[data-testid="stHeader"] {{background: transparent;}}
  h1, h2, h3 {{letter-spacing: -0.01em;}}
  .hero {{background: radial-gradient(1200px 300px at 0% 0%, rgba(245,165,36,.18), transparent 60%),
          linear-gradient(135deg, #111A2E 0%, #0B1220 100%);
          border: 1px solid {BORDER}; border-radius: 18px; padding: 26px 30px; margin-bottom: 18px;}}
  .hero .eyebrow {{color: {ACCENT}; font-size: .78rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;}}
  .hero h1 {{font-size: 2.05rem; margin: 6px 0 6px 0; padding: 0; color: {TEXT};}}
  .hero p {{color: {MUTED}; margin: 0; font-size: .98rem; max-width: 860px;}}
  .chip {{display: inline-block; margin: 12px 8px 0 0; padding: 4px 10px; border-radius: 999px; font-size: .76rem;
          color: {TEXT}; background: rgba(148,163,184,.10); border: 1px solid {BORDER};}}
  .chip.accent {{color: {NAVY}; background: {ACCENT}; border-color: {ACCENT}; font-weight: 700;}}
  .kpis {{display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 14px; margin: 4px 0 18px 0;}}
  .kpi {{background: {PANEL}; border: 1px solid {BORDER}; border-radius: 14px; padding: 16px 18px; position: relative; overflow: hidden;}}
  .kpi:before {{content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--c);}}
  .kpi .label {{color: {MUTED}; font-size: .74rem; text-transform: uppercase; letter-spacing: .08em; font-weight: 600;}}
  .kpi .value {{color: {TEXT}; font-size: 1.65rem; font-weight: 700; margin-top: 4px; font-variant-numeric: tabular-nums;}}
  .kpi .sub {{color: {MUTED}; font-size: .78rem; margin-top: 2px;}}
  .tbl {{width: 100%; border-collapse: separate; border-spacing: 0; font-size: .86rem;}}
  .tbl-wrap {{border: 1px solid {BORDER}; border-radius: 14px; overflow: auto; max-height: 560px; background: {PANEL};}}
  .tbl th {{position: sticky; top: 0; background: #0F1728; color: {MUTED}; text-align: left; font-weight: 600;
            font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; padding: 11px 12px; border-bottom: 1px solid {BORDER};}}
  .tbl td {{padding: 11px 12px; border-bottom: 1px solid rgba(34,48,74,.6); color: {TEXT}; vertical-align: top;}}
  .tbl tr:hover td {{background: rgba(245,165,36,.04);}}
  .tbl td.num {{text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap;}}
  .tbl td.reason {{color: {MUTED}; max-width: 420px; font-size: .8rem;}}
  .badge {{display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: .72rem; font-weight: 700;
           border: 1px solid var(--c); color: var(--c); background: color-mix(in srgb, var(--c) 14%, transparent);}}
  .dir-up {{color: {RED}; font-weight: 700;}} .dir-down {{color: {BLUE}; font-weight: 700;}}
  .st-key-reviewer_card {{background: linear-gradient(180deg, #131C2E, #0F1728); border: 1px solid {BORDER};
           border-left: 4px solid {ACCENT}; border-radius: 16px; padding: 22px 26px;}}
  .src {{display: inline-block; font-size: .74rem; padding: 3px 10px; border-radius: 999px; color: {NAVY};
         background: {ACCENT}; font-weight: 700; margin-bottom: 4px;}}
  .src.tpl {{background: rgba(148,163,184,.2); color: {TEXT};}}
  .callout {{background: rgba(96,165,250,.08); border: 1px solid rgba(96,165,250,.35); color: {TEXT};
             border-radius: 12px; padding: 10px 14px; font-size: .86rem; margin-bottom: 12px;}}
  .callout.warn {{background: rgba(245,165,36,.08); border-color: rgba(245,165,36,.4);}}
  .foot {{color: {MUTED}; font-size: .78rem; margin-top: 26px; border-top: 1px solid {BORDER}; padding-top: 12px;}}
  [data-testid="stSidebar"] {{border-right: 1px solid {BORDER};}}
  .stTabs [data-baseweb="tab-list"] {{gap: 6px;}}
  .stTabs [data-baseweb="tab"] {{background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px 10px 0 0; padding: 8px 16px;}}
  @media (max-width: 1000px) {{ .kpis {{grid-template-columns: repeat(2, minmax(0,1fr));}} }}
</style>
"""

e = html.escape


def hero(source_label: str, ai_label: str) -> str:
    return f"""<div class="hero"><div class="eyebrow">Project Controls · Cost Review</div>
<h1>AI Construction Cost Estimate Checker</h1>
<p>Reviews residential repair estimates line by line, flags unit costs that are unusually high or low against
reference pricing and peer estimates, and drafts a reviewer note with dollar impact and follow-ups.</p>
<span class="chip accent">{e(source_label)}</span><span class="chip">{e(ai_label)}</span>
<span class="chip">Reference · Peer z-score / IQR · IsolationForest</span></div>"""


def kpi_cards(items, cols: int = 5) -> str:
    cards = "".join(f'<div class="kpi" style="--c:{c}"><div class="label">{e(l)}</div>'
                    f'<div class="value">{e(v)}</div><div class="sub">{e(s)}</div></div>' for l, v, s, c in items)
    return f'<div class="kpis" style="grid-template-columns: repeat({cols}, minmax(0,1fr))">{cards}</div>'


def badge(text, color) -> str:
    return f'<span class="badge" style="--c:{color}">{e(text)}</span>'


def money(v, signed=False) -> str:
    if pd.isna(v):
        return "—"
    if signed and round(v) == 0:
        return "$0"
    return (f"{'+' if v >= 0 else '-'}${abs(v):,.0f}" if signed else f"${v:,.2f}")


def flagged_table(f: pd.DataFrame) -> str:
    rows = []
    for _, r in f.iterrows():
        d = ('<span class="dir-up">▲ HIGH</span>' if r.direction == "HIGH"
             else '<span class="dir-down">▼ LOW</span>' if r.direction == "LOW" else "—")
        pct = "—" if pd.isna(r.pct_vs_baseline) else f"{r.pct_vs_baseline:+.0%}"
        rows.append(
            f"<tr><td>{badge(r.severity, SEVERITY_COLORS.get(r.severity, MUTED))}</td><td>{e(r.estimate_id)}</td>"
            f"<td><b>{e(r['item'])}</b><br><span style='color:{MUTED};font-size:.76rem'>{e(r.category)}</span></td>"
            f"<td class='num'>{r.qty:,.0f} {e(r.unit)}</td><td class='num'>{money(r.unit_cost)}</td>"
            f"<td class='num'>{money(r.baseline_unit_cost)}</td><td class='num'>{pct}</td><td>{d}</td>"
            f"<td class='num'>{money(r['potential_variance_$'], signed=True)}</td>"
            f"<td class='reason'>{e(r.reason)}</td></tr>")
    head = "".join(f"<th>{h}</th>" for h in ["Severity", "Estimate", "Line item", "Qty", "Unit cost",
                                             "Baseline", "Δ vs base", "Direction", "$ impact", "Why it was flagged"])
    return f'<div class="tbl-wrap"><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
