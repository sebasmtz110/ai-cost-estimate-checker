"""Streamlit web app for the Cost Estimate Checker. Run: streamlit run app.py"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from checker import analyze, summary, REQUIRED, OPTIONAL, MIN_PEERS
from pdf_parser import parse_pdf
from reviewer import reviewer_summary, _get

st.set_page_config(page_title="AI Construction Cost Estimate Checker", page_icon="🏗️", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)


@st.cache_data
def load_reference():
    return pd.read_csv("data/reference_unit_costs.csv")


def read_upload(up) -> pd.DataFrame:
    """Read an uploaded CSV or PDF; raises ValueError with a friendly message on failure."""
    data = up.getvalue()
    if not data:
        raise ValueError("The uploaded file is empty.")
    if up.name.lower().endswith(".pdf"):
        return parse_pdf(up)
    try:
        return pd.read_csv(up, encoding_errors="replace")
    except pd.errors.EmptyDataError:
        raise ValueError("The CSV has no rows or columns.")
    except pd.errors.ParserError as e:
        raise ValueError(f"The CSV could not be parsed: {e}")


def reviewer_note(df, estimate_id):
    """AI notes are cached per session; template fallbacks are not, so a busy AI gets retried later."""
    cache = st.session_state.setdefault("notes", {})
    key = (estimate_id, pd.util.hash_pandas_object(df[["estimate_id", "item", "qty", "unit_cost"]]).sum())
    if key in cache:
        return cache[key]
    with st.spinner("Writing reviewer note..."):
        note, source = reviewer_summary(df, estimate_id)
    if source != "Template":
        cache[key] = (note, source)
    return note, source


ref = load_reference()
provider = ("Gemini" if (_get("GEMINI_API_KEY") or _get("GOOGLE_API_KEY"))
            else "OpenAI" if _get("OPENAI_API_KEY") else None)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### 📂 Estimate data")
    up = st.file_uploader("Upload estimate (CSV or PDF)", type=["csv", "pdf"])
    st.caption(f"Required columns: **{', '.join(REQUIRED)}** · optional: {', '.join(OPTIONAL)}. "
               "Common headers like *Description*, *UOM*, *Quantity*, *Unit Price* are recognised.")
    with open("data/sample_estimates.csv", "rb") as fh:
        st.download_button("⬇ Sample CSV (synthetic)", fh, "sample_estimates.csv", width="stretch")
    with open("data/sample_estimate.pdf", "rb") as fh:
        st.download_button("⬇ Sample PDF (synthetic)", fh, "sample_estimate.pdf", width="stretch")
    st.markdown("### 🤖 AI reviewer")
    st.caption(f"AI reviewer: {provider} enabled" if provider
               else "AI reviewer: template mode. Set GEMINI_API_KEY for a free AI-written note.")

# ---------------- Data ----------------
if up is not None:
    try:
        est = read_upload(up)
        df = analyze(est, ref)
    except ValueError as e:
        st.markdown(ui.hero(f"Upload: {up.name}", "—"), unsafe_allow_html=True)
        st.error(f"Could not analyze **{up.name}**: {e}")
        st.stop()
    source_label = f"Using uploaded file: {up.name}"
else:
    df = analyze(pd.read_csv("data/sample_estimates.csv"), ref)
    source_label = "Using SYNTHETIC sample data · 8 fictional estimates"

st.markdown(ui.hero(source_label, f"AI reviewer: {provider or 'Template'}"), unsafe_allow_html=True)
issues = pd.DataFrame(df.attrs.get("data_issues", []))
if df.empty:
    st.error("No valid line items to analyze. Every row was missing an item, or had a missing, "
             "non-numeric, zero or negative quantity / unit cost.")
    if len(issues):
        st.dataframe(issues, width="stretch", hide_index=True)
    st.stop()

s = summary(df)
st.markdown(ui.kpi_cards([
    ("Line items", f"{s['line_items']:,}", f"{s['estimates']} estimate(s)", ui.BLUE),
    ("Flagged", f"{s['flagged']}", f"{s['high_severity']} high severity", ui.RED),
    ("High / Low", f"{s['flagged_high']} / {s['flagged_low']}", "over- vs under-priced", ui.ORANGE),
    ("Estimate total", f"${s['estimate_total_$']:,.0f}", "valid line items", ui.GREEN),
    ("Net variance (flagged)", ui.money(s["net_variance_flagged_$"], signed=True),
     f"over {ui.money(s['overpricing_$'], True)} · under {ui.money(s['underpricing_$'], True)}", ui.ACCENT),
]), unsafe_allow_html=True)

notes = []
if not s["peer_check_available"]:
    notes.append(f"Peer comparison needs more than {MIN_PEERS} estimates; this file has {s['estimates']}. "
                 "Flags here are based on the reference price table only.")
if s["unmatched_items"]:
    notes.append(f"{s['unmatched_items']} line item(s) had no usable reference price (unknown item or "
                 "different unit) and were compared to peers only.")
if s["data_issues"]:
    notes.append(f"{s['data_issues']} row(s) were skipped because of missing or invalid values. See the Data tab.")
for n in notes:
    st.markdown(f'<div class="callout warn">{ui.e(n)}</div>', unsafe_allow_html=True)

tab_review, tab_flags, tab_charts, tab_data = st.tabs(
    ["🤖  AI reviewer", "🚩  Flagged items", "📈  Analytics", "🗂️  Data"])

# ---------------- AI reviewer ----------------
with tab_review:
    ids = sorted(df.estimate_id.unique())
    impact = df[df.flagged].assign(a=lambda d: d["potential_variance_$"].abs()).groupby("estimate_id").a.sum()
    default = ids.index(impact.idxmax()) if len(impact) else 0
    c1, c2 = st.columns([1, 2.4])
    sel = c1.selectbox("Estimate", ids, index=default)
    e_df = df[df.estimate_id == sel]
    c2.markdown(ui.kpi_cards([
        ("Estimate total", f"${e_df.line_total.sum():,.0f}", f"{len(e_df)} line items", ui.GREEN),
        ("Flagged", f"{int(e_df.flagged.sum())}", f"{int((e_df.severity == 'High').sum())} high severity", ui.RED),
        ("$ impact", ui.money(e_df.loc[e_df.flagged, 'potential_variance_$'].fillna(0).sum(), True),
         "flagged lines, net", ui.ACCENT)], cols=3), unsafe_allow_html=True)
    note, src = reviewer_note(df, sel)
    with st.container(key="reviewer_card"):
        cls = "src tpl" if src == "Template" else "src"
        st.markdown(f'<span class="{cls}">Generated by: {ui.e(src)}</span>', unsafe_allow_html=True)
        st.markdown(f"#### Reviewer note · {sel}")
        st.markdown(note.replace("$", "\\$"))  # escape $ so Streamlit doesn't treat it as math
    st.caption("AI notes are written only from the checker's computed facts. Always confirm before acting.")

# ---------------- Flagged items ----------------
with tab_flags:
    f = df[df.flagged]
    if f.empty:
        st.success("No line items were flagged.")
    else:
        sev = st.segmented_control("Severity", ["High", "Medium", "Low"], selection_mode="multi",
                                   default=["High", "Medium", "Low"])
        f = f[f.severity.isin(sev or [])]
        st.markdown(ui.flagged_table(f), unsafe_allow_html=True)
        st.caption("Baseline = reference unit cost (or the median of other estimates when the item isn't in "
                   "the reference table). $ impact = (unit cost − baseline) × qty.")

# ---------------- Analytics ----------------
LAYOUT = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
              font=dict(color=ui.TEXT, family="Inter, sans-serif"), margin=dict(l=10, r=10, t=50, b=10),
              legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)"))
with tab_charts:
    c1, c2 = st.columns([3, 2])
    plot = df.dropna(subset=["baseline_unit_cost"]).copy()
    if plot.empty:
        c1.info("No line items have a baseline to chart.")
    else:
        plot["status"] = plot.severity.replace("", "OK").map(lambda v: v if v == "OK" else f"{v} severity")
        colors = {"OK": "#475569", "High severity": ui.RED, "Medium severity": ui.ORANGE, "Low severity": ui.BLUE}
        fig = px.scatter(plot, x="baseline_unit_cost", y="unit_cost", color="status", log_x=True, log_y=True,
                         color_discrete_map=colors, custom_data=["estimate_id", "item", "pct_vs_baseline"],
                         category_orders={"status": ["High severity", "Medium severity", "Low severity", "OK"]})
        fig.update_traces(marker=dict(size=10, line=dict(width=1, color=ui.NAVY), opacity=.9),
                          hovertemplate="<b>%{customdata[1]}</b><br>%{customdata[0]}<br>Unit cost $%{y:,.2f}"
                                        "<br>Baseline $%{x:,.2f}<br>Δ %{customdata[2]:+.0%}<extra></extra>")
        lo, hi = plot.baseline_unit_cost.min() * 0.7, plot.baseline_unit_cost.max() * 1.4
        for k, name in ((1.25, "±25% band"), (0.75, None)):
            fig.add_trace(go.Scatter(x=[lo, hi], y=[lo * k, hi * k], mode="lines", name=name, showlegend=bool(name),
                                     line=dict(color="rgba(245,165,36,.35)", dash="dot", width=1), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="= baseline",
                                 line=dict(color=ui.ACCENT, width=1.5), hoverinfo="skip"))
        fig.update_layout(title="Unit cost vs baseline (log scale)", xaxis_title="Baseline unit cost ($)",
                          yaxis_title="Estimate unit cost ($)", height=470, legend_title_text="", **LAYOUT)
        fig.update_xaxes(gridcolor="#1E293B"); fig.update_yaxes(gridcolor="#1E293B")
        c1.plotly_chart(fig, width="stretch")

    fl = df[df.flagged].copy()
    if fl.empty:
        c2.info("No flagged items to chart.")
    else:
        cat = (fl.assign(cat=fl.category.replace("", "Uncategorized"))
                 .groupby("cat")["potential_variance_$"].sum().sort_values())
        bar = go.Figure(go.Bar(x=cat.values, y=cat.index, orientation="h",
                               marker_color=[ui.RED if v > 0 else ui.BLUE for v in cat.values],
                               hovertemplate="%{y}: %{x:$,.0f}<extra></extra>",
                               text=[ui.money(v, True) for v in cat.values], textposition="outside",
                               cliponaxis=False, textfont=dict(color=ui.TEXT)))
        bar.update_layout(title="Flagged $ impact by category", height=470, xaxis_title="$ impact (+ over / − under)",
                          **LAYOUT)
        span = max(abs(cat.min()), abs(cat.max()), 1)
        bar.update_xaxes(gridcolor="#1E293B", zerolinecolor="#475569",
                         range=[min(cat.min(), 0) - span * 0.35, max(cat.max(), 0) + span * 0.3])
        bar.update_yaxes(ticksuffix="  ")
        c2.plotly_chart(bar, width="stretch")

# ---------------- Data ----------------
with tab_data:
    st.markdown("##### All analyzed line items")
    cols = ["estimate_id", "category", "item", "unit", "qty", "unit_cost", "baseline_unit_cost", "baseline_source",
            "pct_vs_baseline", "potential_variance_$", "severity", "checks_triggered", "anomaly_score", "note"]
    st.dataframe(df[cols], width="stretch", hide_index=True, column_config={
        "unit_cost": st.column_config.NumberColumn("unit cost", format="dollar"),
        "baseline_unit_cost": st.column_config.NumberColumn("baseline", format="dollar"),
        "pct_vs_baseline": st.column_config.NumberColumn("Δ vs base", format="percent"),
        "potential_variance_$": st.column_config.NumberColumn("$ impact", format="dollar"),
        "anomaly_score": st.column_config.ProgressColumn("anomaly", min_value=0.0, max_value=1.0, format="%.2f"),
    })
    if len(issues):
        st.markdown("##### Skipped rows (data issues)")
        st.dataframe(issues, width="stretch", hide_index=True)
    st.download_button("⬇ Download full results CSV", df.to_csv(index=False), "flagged_report.csv")

st.markdown('<div class="foot">All sample data is synthetic and created for demonstration only; it is not from any '
            'real company, project, or pricing database. Built with Python · pandas · scikit-learn · Streamlit · '
            'Plotly · pdfplumber · Gemini.</div>', unsafe_allow_html=True)
