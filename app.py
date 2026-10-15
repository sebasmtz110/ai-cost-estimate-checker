"""Streamlit web app for the Cost Estimate Checker. Run: streamlit run app.py"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from checker import analyze, summary, REQUIRED, OPTIONAL, MIN_PEERS, REF_PCT_THRESHOLD
from pdf_parser import parse_pdf
from reviewer import reviewer_summary, _get

st.set_page_config(page_title="AI Construction Cost Estimate Checker", page_icon="🏗️", layout="centered")
st.markdown(ui.CSS, unsafe_allow_html=True)


@st.cache_data
def load_reference():
    return pd.read_csv("data/reference_unit_costs.csv")


def read_upload(up) -> pd.DataFrame:
    """Read an uploaded CSV or PDF; raises ValueError with a friendly message on failure."""
    if not up.getvalue():
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
    key = (estimate_id, int(pd.util.hash_pandas_object(df[["estimate_id", "item", "qty", "unit_cost"]]).sum()))
    if key in cache:
        return cache[key]
    with st.spinner("Writing reviewer note..."):
        note, source = reviewer_summary(df, estimate_id)
    if source != "Template":
        cache[key] = (note, source)
    return note, source


def esc(text: str) -> str:
    """Escape $ so Streamlit markdown doesn't render dollar amounts as math."""
    return str(text).replace("$", "\\$")


def set_view(k):
    st.session_state.view = k
    st.session_state.pop("picked", None)


def show_all():
    set_view("all")
    st.session_state.f_trade, st.session_state.f_est = [], []


def pick(rid):
    st.session_state.picked = rid


def close_detail():
    st.session_state.pop("picked", None)


def line_detail(r):
    """Full breakdown of one line item."""
    with st.container(border=True, key="line_detail"):
        st.markdown(f"#### {r['item']}")
        st.caption(f"{r.estimate_id} · {r.category or 'No trade'} · {r.qty:,.0f} {r.unit}"
                   + (f" · {ui.SEVERITY_ICON[r.severity]} severity · {ui.SIGNAL[r.direction]}" if r.severity
                      else " · not flagged"))
        c = st.columns(4)
        c[0].metric("Unit cost", ui.money(r.unit_cost), help="Price per unit on this estimate")
        c[1].metric("Reference", ui.money(r.baseline_unit_cost),
                    help=f"Source: {r.baseline_source}. Reference price table, or the median of other estimates.")
        c[2].metric("% off", ui.pct(r.pct_vs_baseline), help="(unit cost ÷ reference) − 1")
        c[3].metric("$ impact", ui.money(r["potential_variance_$"], True), help="(unit cost − reference) × qty")
        z = "—" if pd.isna(r.peer_z) else f"z = {r.peer_z:+.1f}"
        checks = [("Reference price", r.flag_reference, f"beyond ±{REF_PCT_THRESHOLD:.0%}"),
                  ("Peer z-score", r.flag_zscore, f"{int(r.peer_count)} other estimates, {z}"),
                  ("Peer IQR fence", r.flag_iqr, "outside the typical range of other estimates"),
                  ("Anomaly model", r.flag_ml, f"IsolationForest score {r.anomaly_score:.2f}")]
        st.markdown("  \n".join(f"{'🚩' if hit else '✅'} **{n}**: {'flagged' if hit else 'ok'} ({d})"
                                for n, hit, d in checks))
        if r.reason:
            st.info(esc(r.reason))
        elif r.note:
            st.caption(r.note)


ref = load_reference()
provider = ("Gemini" if (_get("GEMINI_API_KEY") or _get("GOOGLE_API_KEY"))
            else "OpenAI" if _get("OPENAI_API_KEY") else None)

# ---------------- Header ----------------
header_slot = st.empty()  # navy header bar; filled once we know the data source
header_slot.markdown(ui.header("Loading…"), unsafe_allow_html=True)
with st.expander("💡 How it works (60-second version)"):
    st.markdown(
        "1. **Load** an estimate (CSV or PDF), or use the synthetic sample of 8 fictional repair estimates.\n"
        "2. **Check** every line three ways: against a **reference price table** (same item & unit), against the "
        "**same item on other estimates** (leave-one-out z-score + IQR), and with an **IsolationForest** "
        "anomaly model.\n"
        "3. **Flag** a line if it's more than 25% off the reference, or if two checks agree. Severity: "
        "🔴 High = ≥50% off or ≥$5,000, 🟠 Medium = ≥25%, 🔵 Low = the rest.\n"
        "4. **Review**: an AI (Google Gemini) turns the computed facts into a reviewer memo. Without an API key a "
        "template writes it.\n\n"
        "*$ impact = (unit cost − reference) × qty. Built in Python with pandas, scikit-learn, Streamlit, Plotly, "
        "pdfplumber.*")

# ---------------- Step 1: data ----------------
st.markdown(ui.step(1, "Choose your estimate"), unsafe_allow_html=True)
mode = st.segmented_control("Data source", ["Use sample data", "Upload my file"], default="Use sample data",
                            key="mode", label_visibility="collapsed") or "Use sample data"
up = None
if mode == "Upload my file":
    up = st.file_uploader("Upload a CSV or PDF estimate", type=["csv", "pdf"])
    st.caption(f"CSV needs **{', '.join(REQUIRED)}** (optional {', '.join(OPTIONAL)}). Headers like "
               "*Description, UOM, Quantity, Unit Price* also work. Need a file to try?")
    c1, c2 = st.columns(2)
    with open("data/sample_estimates.csv", "rb") as fh:
        c1.download_button("⬇ Sample CSV", fh, "sample_estimates.csv", width="stretch", key="dl_csv")
    with open("data/sample_estimate.pdf", "rb") as fh:
        c2.download_button("⬇ Sample PDF", fh, "sample_estimate.pdf", width="stretch", key="dl_pdf")
    if up is None:
        header_slot.markdown(ui.header("Waiting for your file"), unsafe_allow_html=True)
        st.info("👆 Upload a file to analyze it, or switch back to **Use sample data**.")
        st.stop()

if up is not None:
    try:
        df = analyze(read_upload(up), ref)
    except ValueError as e:
        st.error(f"Could not analyze **{up.name}**: {e}")
        st.stop()
    st.success(f"Using uploaded file: {up.name}")
    header_slot.markdown(ui.header(f"Reviewing your file: {up.name}"), unsafe_allow_html=True)
else:
    df = analyze(pd.read_csv("data/sample_estimates.csv"), ref)
    st.caption("Using SYNTHETIC sample data: 8 fictional residential repair estimates (not real projects or prices).")
    header_slot.markdown(ui.header("Reviewing sample data · 8 fictional estimates (synthetic)"), unsafe_allow_html=True)

issues = pd.DataFrame(df.attrs.get("data_issues", []))
if df.empty:
    st.error("No valid line items to analyze. Every row was missing an item, or had a missing, "
             "non-numeric, zero or negative quantity / unit cost.")
    if len(issues):
        st.dataframe(issues, width="stretch", hide_index=True)
    st.stop()
df["category"] = df.category.replace("", "Uncategorized")

# Reset the drill-down when the data changes
sig = (up.name if up else "sample", len(df))
if st.session_state.get("data_sig") != sig:
    st.session_state.data_sig, st.session_state.view = sig, "flagged"
    st.session_state.pop("picked", None)

# ---------------- Step 2: results ----------------
st.markdown(ui.step(2, "See what needs a closer look"), unsafe_allow_html=True)
s = summary(df)
for msg in ([f"Peer comparison needs more than {MIN_PEERS} estimates; this file has {s['estimates']}, so flags "
             "use the reference price table only."] if not s["peer_check_available"] else []) + \
           ([f"{s['unmatched_items']} line item(s) had no usable reference price and were compared to peers only."]
            if s["unmatched_items"] else []) + \
           ([f"{s['data_issues']} row(s) were skipped because of missing or invalid values (see Details)."]
            if s["data_issues"] else []):
    st.warning(msg)

with st.container(key="searchbar"):
    f1, f2 = st.columns(2)
    trades = f1.multiselect("🔍 Filter by trade", sorted(df.category.unique()), placeholder="All trades", key="f_trade")
    ests = f2.multiselect("🔍 Filter by estimate", sorted(df.estimate_id.unique()), placeholder="All estimates",
                          key="f_est")
scope = df[(df.category.isin(trades) if trades else pd.Series(True, index=df.index))
          & (df.estimate_id.isin(ests) if ests else pd.Series(True, index=df.index))]

VIEWS = {  # key: (label, row mask, tooltip)
    "all": ("Line items", pd.Series(True, index=scope.index), "Every analyzed line in the current filter."),
    "flagged": ("Flagged", scope.flagged, "Lines more than 25% off reference, or where 2+ checks agree."),
    "over": ("Over-priced", scope.flagged & (scope.direction == "HIGH"),
             "Flagged lines priced above reference (possible overpricing)."),
    "under": ("Under-priced", scope.flagged & (scope.direction == "LOW"),
              "Flagged lines priced below reference (possible missing scope)."),
    "severe": ("High severity", scope.flagged & (scope.severity == "High"),
               "Flagged lines ≥50% off reference or with ≥$5,000 impact."),
}
st.caption("👇 Tap a tile to see exactly the items it counts. Tap **See details** on any item for the full breakdown.")
cols = st.columns(len(VIEWS))
for col, (k, (label, mask, hlp)) in zip(cols, VIEWS.items()):
    with col.container(key=f"kpi_{k}"):
        st.button(f"**{int(mask.sum()):,}**\n\n{label}", key=f"btn_{k}", help=hlp, width="stretch",
                  type="primary" if st.session_state.view == k else "secondary", on_click=set_view, args=(k,))

view = st.session_state.view
label, mask, hlp = VIEWS[view]
rows = scope[mask].sort_values("potential_variance_$", key=lambda v: v.abs(), ascending=False)
impact = rows["potential_variance_$"].fillna(0)
h1, h2 = st.columns([4, 1], vertical_alignment="center")
h1.markdown(esc(f"**{len(rows):,} {label.lower()}** · net $ impact **{ui.money(impact.sum(), True)}** "
                f"(over {ui.money(impact[impact > 0].sum(), True)} · under {ui.money(impact[impact < 0].sum(), True)})"),
            help="$ impact = (unit cost − reference) × qty, summed over the rows shown.")
if view != "all" or trades or ests:
    h2.button("↺ Show all", key="show_all", width="stretch", on_click=show_all)

table = rows.assign(sev=rows.severity.map(ui.SEVERITY_ICON).fillna("—"), pct_vs_baseline=rows.pct_vs_baseline * 100,
                    sig=rows.direction.map(ui.SIGNAL).where(rows.flagged, "—"))[
    ["sev", "sig", "estimate_id", "item", "category", "qty", "unit", "unit_cost", "baseline_unit_cost", "pct_vs_baseline",
     "potential_variance_$", "reason"]]
def _color(col):
    return [f"color: {ui.OVER}" if str(v).startswith("▲") or (isinstance(v, (int, float)) and v > 0)
            else f"color: {ui.UNDER}" if str(v).startswith("▼") or (isinstance(v, (int, float)) and v < 0)
            else "" for v in col]


MAX_CARDS = 12
if view != "all" and len(rows):
    shown_rows = rows.head(MAX_CARDS)
    for start in range(0, len(shown_rows), 3):
        for col, (rid, r) in zip(st.columns(3), list(shown_rows.iloc[start:start + 3].iterrows())):
            with col.container(key=f"card_{rid}"):
                st.markdown(ui.product_card(r), unsafe_allow_html=True)
                st.button("See details", key=f"see_{rid}", width="stretch", on_click=pick, args=(int(rid),))
    if len(rows) > MAX_CARDS:
        st.caption(f"Showing the {MAX_CARDS} biggest by $ impact. See the table below for all {len(rows)}.")

styled = table.style.apply(_color, subset=["sig", "potential_variance_$"])
table_box = st.container() if view == "all" else st.expander(f"📋 See these {len(rows)} items as a table")
event = table_box.dataframe(
    styled, width="stretch", hide_index=True, height=min(400, 38 + 35 * max(len(table), 1)),
    key="drill_table", on_select="rerun", selection_mode="single-row", column_config={
        "sev": st.column_config.TextColumn("Severity", width="small"),
        "sig": st.column_config.TextColumn("Price vs reference", width="small",
                                           help="▲ Over reference (red) · ▼ Under (green)"),
        "estimate_id": st.column_config.TextColumn("Estimate", width="small"),
        "item": st.column_config.TextColumn("Line item", width="medium"),
        "category": st.column_config.TextColumn("Trade", width="small"),
        "qty": st.column_config.NumberColumn("Qty", format="%,.0f", width="small"),
        "unit": st.column_config.TextColumn("Unit", width="small"),
        "unit_cost": st.column_config.NumberColumn("Unit cost", format="dollar"),
        "baseline_unit_cost": st.column_config.NumberColumn("Reference", format="dollar",
                                                            help="Reference price, or peer median if not in table"),
        "pct_vs_baseline": st.column_config.NumberColumn("% off", format="%+.0f%%", help="vs reference"),
        "potential_variance_$": st.column_config.NumberColumn("$ impact", format="dollar",
                                                              help="(unit cost − reference) × qty"),
        "reason": st.column_config.TextColumn("Why it was flagged", width="large")})
if event.selection.rows:
    st.session_state.picked = int(rows.index[event.selection.rows[0]])
if rows.empty:
    st.success(f"Good news: no {label.lower()} items match this filter. 🎉 Try another tile, or tap **Show all**.")

with st.expander("📈 Chart: unit cost vs reference · tap a point for details", expanded=False):
    plot = scope.dropna(subset=["baseline_unit_cost"]).copy()
    if plot.empty:
        st.info("No line items have a reference to chart.")
    else:
        plot["status"] = (plot.direction.map({"HIGH": "Over (flagged)", "LOW": "Under (flagged)"})
                          .where(plot.flagged, "OK").fillna("OK"))
        plot["rid"] = plot.index
        fig = px.scatter(plot, x="baseline_unit_cost", y="unit_cost", color="status", log_x=True, log_y=True,
                         color_discrete_map={"OK": "#C7CCCC", "Over (flagged)": ui.OVER, "Under (flagged)": ui.UNDER},
                         category_orders={"status": ["Over (flagged)", "Under (flagged)", "OK"]},
                         custom_data=["rid", "estimate_id", "item", "pct_vs_baseline"])
        fig.update_traces(marker=dict(size=10, line=dict(width=0)),
                          hovertemplate="<b>%{customdata[2]}</b> · %{customdata[1]}<br>$%{y:,.2f} vs $%{x:,.2f}"
                                        " (%{customdata[3]:+.0%})<extra></extra>")
        lo, hi = plot.baseline_unit_cost.min() * 0.7, plot.baseline_unit_cost.max() * 1.4
        fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="= reference",
                                 line=dict(color=ui.ORANGE, dash="dot", width=1.5), hoverinfo="skip"))
        fig.update_layout(template="plotly_white", paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                          font=dict(family="Inter, -apple-system, Segoe UI, Roboto, Arial, sans-serif", size=12,
                                    color="#0F1111"),
                          height=400, margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(orientation="h", y=1.1, title_text=""), clickmode="event+select",
                          xaxis_title="Reference unit cost ($)", yaxis_title="Estimate unit cost ($)")
        fig.update_xaxes(gridcolor="#EAEDED", zeroline=False)
        fig.update_yaxes(gridcolor="#EAEDED", zeroline=False)
        ch = st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="chart",
                             on_select="rerun", selection_mode="points")
        pts = [p for p in (ch.selection.points if ch else []) if p.get("customdata")]
        if pts:
            st.session_state.picked = int(pts[0]["customdata"][0])

picked = st.session_state.get("picked")
if picked is not None and picked in df.index:
    line_detail(df.loc[picked])
    st.button("✕ Close details", key="close_detail", on_click=close_detail)

# ---------------- Step 3: AI review ----------------
st.markdown(ui.step(3, "Read the AI reviewer note"), unsafe_allow_html=True)
ids = sorted(df.estimate_id.unique())
fl = df[df.flagged]
imp = fl.assign(a=fl["potential_variance_$"].abs()).groupby("estimate_id").a.sum()
default = ids.index(ests[0]) if len(ests) == 1 else (ids.index(imp.idxmax()) if len(imp) else 0)
sel = st.selectbox("Estimate", ids, index=default, key="estimate",
                   help="Defaults to the estimate with the largest flagged $ impact.")
e_df = df[df.estimate_id == sel]
e_imp = e_df.loc[e_df.flagged, "potential_variance_$"].fillna(0).sum()
st.caption(esc(f"{sel}: {len(e_df)} lines · total ${e_df.line_total.sum():,.0f} · "
               f"{int(e_df.flagged.sum())} flagged · net impact {ui.money(e_imp, True)}"))
note, src = reviewer_note(df, sel)
with st.container(border=True, key="reviewer_card"):
    st.caption(f"Generated by: {src}" + ("" if provider else " · set GEMINI_API_KEY for an AI-written note"))
    st.markdown(esc(note))
st.caption("AI notes are written only from the checker's computed facts. Always confirm before acting.")

# ---------------- Details ----------------
with st.expander("🗂️ All data, skipped rows & download"):
    st.dataframe(df, width="stretch", hide_index=True)
    if len(issues):
        st.markdown("**Skipped rows**")
        st.dataframe(issues, width="stretch", hide_index=True)
    st.download_button("⬇ Download full results CSV", df.to_csv(index=False), "flagged_report.csv", key="dl_results")

st.caption("All sample data is synthetic and for demonstration only. Built with Python · pandas · scikit-learn · "
           "Streamlit · Plotly · pdfplumber · Gemini.")
