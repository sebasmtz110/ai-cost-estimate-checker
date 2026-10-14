"""Streamlit web app for the Cost Estimate Checker. Run: streamlit run app.py"""
import pandas as pd
import plotly.express as px
import streamlit as st
from checker import analyze, summary, REQUIRED

st.set_page_config(page_title="Construction Cost Estimate Checker", layout="wide")
st.title("🏗️ AI Construction Cost Estimate Checker")
st.caption("Flags repair-estimate line items whose unit costs look unusually high or low. "
           "Sample data is SYNTHETIC example data created for this demo.")

ref = pd.read_csv("data/reference_unit_costs.csv")
with st.sidebar:
    st.header("Data")
    up = st.file_uploader("Upload estimate CSV", type="csv")
    st.markdown(f"Required columns: `{', '.join(REQUIRED)}` (optional `estimate_id`)")
    with open("data/sample_estimates.csv", "rb") as fh:
        st.download_button("Download sample CSV template", fh, "sample_estimates.csv")

if up is not None:
    est = pd.read_csv(up)
    missing = [c for c in REQUIRED if c not in est.columns]
    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()
    if "estimate_id" not in est.columns:
        est["estimate_id"] = "EST-UPLOAD"
    st.info(f"Using uploaded file: {up.name}")
else:
    est = pd.read_csv("data/sample_estimates.csv")
    st.info("Using SYNTHETIC sample data (8 fictional residential repair estimates).")

df = analyze(est, ref)
s = summary(df)
c = st.columns(5)
c[0].metric("Line items", s["line_items"])
c[1].metric("Flagged", s["flagged"])
c[2].metric("High / Low", f'{s["flagged_high"]} / {s["flagged_low"]}')
c[3].metric("Estimate total", f'${s["estimate_total_$"]:,.0f}')
c[4].metric("Net variance (flagged)", f'${s["net_variance_flagged_$"]:,.0f}')

st.subheader("Flagged line items")
show = ["estimate_id", "category", "item", "unit", "qty", "unit_cost", "reference_unit_cost",
        "pct_vs_reference", "potential_variance_$", "direction", "reason"]
st.dataframe(df[df.flagged][show].style.format({"unit_cost": "${:,.2f}", "reference_unit_cost": "${:,.2f}",
             "pct_vs_reference": "{:+.0%}", "potential_variance_$": "${:,.0f}"}),
             width="stretch", hide_index=True)

st.subheader("Unit cost vs reference")
plot = df.dropna(subset=["reference_unit_cost"]).copy()
plot["status"] = plot.flagged.map({True: "Flagged", False: "OK"})
fig = px.scatter(plot, x="reference_unit_cost", y="unit_cost", color="status", log_x=True, log_y=True,
                 hover_data=["estimate_id", "item", "qty"],
                 color_discrete_map={"Flagged": "#d62728", "OK": "#1f77b4"})
lim = [plot.reference_unit_cost.min() * 0.8, plot.reference_unit_cost.max() * 1.2]
fig.add_scatter(x=lim, y=lim, mode="lines", name="= reference", line=dict(dash="dash", color="gray"))
st.plotly_chart(fig, width="stretch")

with st.expander("All line items"):
    st.dataframe(df, width="stretch", hide_index=True)
st.download_button("Download full results CSV", df.to_csv(index=False), "flagged_report.csv")
