"""
Core analysis: flag estimate line items whose unit cost looks unusual.

Three independent checks, then combined:
  1. vs REFERENCE  - % difference from the reference unit cost
  2. vs PEERS      - z-score and IQR fences against the same item on other estimates
  3. ML anomaly    - IsolationForest on (cost ratio, peer z-score, log qty)
"""
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# --- Settings you can tune -------------------------------------------------
REF_PCT_THRESHOLD = 0.25   # flag if >25% above/below reference
Z_THRESHOLD = 2.0          # flag if peer z-score beyond +/-2
IQR_K = 1.5                # standard IQR fence multiplier
ML_CONTAMINATION = 0.06    # share of rows the model treats as anomalies
# ---------------------------------------------------------------------------

REQUIRED = ["item", "category", "unit", "qty", "unit_cost"]


def load(estimate_csv, reference_csv):
    est = pd.read_csv(estimate_csv)
    ref = pd.read_csv(reference_csv)
    missing = [c for c in REQUIRED if c not in est.columns]
    if missing:
        raise ValueError(f"Estimate file is missing columns: {missing}")
    if "estimate_id" not in est.columns:
        est["estimate_id"] = "EST-UPLOAD"
    return est, ref


def analyze(est: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    df = est.copy()
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
    df["unit_cost"] = pd.to_numeric(df["unit_cost"], errors="coerce")
    df = df.dropna(subset=["qty", "unit_cost"])
    df["line_total"] = (df.qty * df.unit_cost).round(2)

    # 1) Reference comparison
    df = df.merge(ref[["item", "reference_unit_cost"]], on="item", how="left")
    df["pct_vs_reference"] = df.unit_cost / df.reference_unit_cost - 1
    df["flag_reference"] = df.pct_vs_reference.abs() > REF_PCT_THRESHOLD

    # 2) Peer comparison (same item across estimates)
    g = df.groupby("item")["unit_cost"]
    df["peer_median"] = g.transform("median")
    df["peer_count"] = g.transform("count")
    mean, std = g.transform("mean"), g.transform("std").replace(0, np.nan)
    df["peer_z"] = ((df.unit_cost - mean) / std).fillna(0)
    q1, q3 = g.transform(lambda s: s.quantile(0.25)), g.transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    df["flag_iqr"] = (df.peer_count >= 4) & ((df.unit_cost < q1 - IQR_K * iqr) | (df.unit_cost > q3 + IQR_K * iqr))
    df["flag_zscore"] = (df.peer_count >= 4) & (df.peer_z.abs() > Z_THRESHOLD)

    # 3) IsolationForest anomaly model
    ratio = (df.unit_cost / df.reference_unit_cost.fillna(df.peer_median)).fillna(1.0)
    X = np.column_stack([np.log(ratio.clip(lower=1e-6)), df.peer_z, np.log1p(df.qty)])
    if len(df) >= 10:
        model = IsolationForest(contamination=ML_CONTAMINATION, random_state=0).fit(X)
        df["anomaly_score"] = -model.score_samples(X)  # higher = more unusual
        df["flag_ml"] = model.predict(X) == -1
    else:
        df["anomaly_score"], df["flag_ml"] = 0.0, False

    checks = ["flag_reference", "flag_zscore", "flag_iqr", "flag_ml"]
    df["checks_triggered"] = df[checks].sum(axis=1)
    df["flagged"] = df.flag_reference | ((df.checks_triggered >= 2))
    df["direction"] = np.where(df.unit_cost >= df.reference_unit_cost.fillna(df.peer_median), "HIGH", "LOW")
    ref_cost = df.reference_unit_cost.fillna(df.peer_median)
    df["potential_variance_$"] = ((df.unit_cost - ref_cost) * df.qty).round(2)
    df["reason"] = df.apply(_reason, axis=1)
    return df.sort_values(["flagged", "anomaly_score"], ascending=False).reset_index(drop=True)


def _reason(r) -> str:
    if not r.flagged:
        return ""
    parts = []
    if pd.notna(r.reference_unit_cost):
        parts.append(f"Unit cost ${r.unit_cost:,.2f}/{r.unit} is {abs(r.pct_vs_reference):.0%} "
                     f"{'above' if r.pct_vs_reference > 0 else 'below'} the reference ${r.reference_unit_cost:,.2f}")
    else:
        parts.append("Item not in reference table")
    if r.flag_zscore or r.flag_iqr:
        parts.append(f"outlier vs {int(r.peer_count)} peer estimates (median ${r.peer_median:,.2f}, z={r.peer_z:+.1f})")
    if r.flag_ml:
        parts.append("anomaly model also marked it unusual")
    msg = "; ".join(parts) + "."
    tip = " Verify scope/quantity or request backup pricing." if r.direction == "HIGH" else \
          " Check for missing scope or a pricing error."
    return msg + tip


def summary(df: pd.DataFrame) -> dict:
    f = df[df.flagged]
    return {
        "line_items": len(df),
        "flagged": len(f),
        "flagged_high": int((f.direction == "HIGH").sum()),
        "flagged_low": int((f.direction == "LOW").sum()),
        "estimate_total_$": round(float(df.line_total.sum()), 2),
        "net_variance_flagged_$": round(float(f["potential_variance_$"].sum()), 2),
    }


if __name__ == "__main__":
    est_path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_estimates.csv"
    est, ref = load(est_path, "data/reference_unit_costs.csv")
    out = analyze(est, ref)
    print(summary(out))
    cols = ["estimate_id", "item", "unit_cost", "reference_unit_cost", "direction", "reason"]
    pd.set_option("display.width", 250, "display.max_colwidth", 140)
    print(out[out.flagged][cols].to_string(index=False))
    out.to_csv("flagged_report.csv", index=False)
    print("\nFull results written to flagged_report.csv")
