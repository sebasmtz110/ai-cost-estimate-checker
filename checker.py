"""
Core analysis: flag estimate line items whose unit cost looks unusual.

Checks per line item:
  1. vs REFERENCE  - % difference from the reference unit cost (same item AND same unit)
  2. vs PEERS      - z-score and IQR fences against the same item/unit on OTHER estimates
                     (leave-one-out: a line is never compared against itself)
  3. ML anomaly    - IsolationForest on (cost ratio, peer z-score, log qty)
A line is flagged if it is beyond the reference threshold, or if at least two checks agree.
Rows with missing, non-numeric, zero or negative qty/unit cost are set aside as data issues.
"""
import re
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# --- Settings you can tune -------------------------------------------------
REF_PCT_THRESHOLD = 0.25   # flag if >25% above/below reference
Z_THRESHOLD = 3.0          # peer z-score beyond +/-3 (leave-one-out)
IQR_K = 1.5                # standard IQR fence multiplier
MIN_PEERS = 4              # need at least this many other estimates for peer checks
MIN_PEER_DEV = 0.15        # ignore peer outliers that are <15% from the peer median
ML_CONTAMINATION = 0.06    # share of rows the model treats as anomalies
ML_MIN_ROWS = 20           # too few rows -> skip the ML model
HIGH_SEVERITY_PCT = 0.50   # >=50% off baseline ...
HIGH_SEVERITY_USD = 5000   # ... or >= $5,000 impact -> High severity
# ---------------------------------------------------------------------------

REQUIRED = ["item", "qty", "unit_cost"]
OPTIONAL = ["estimate_id", "category", "unit"]
COLUMN_ALIASES = {
    "item": ["item", "description", "line item", "line_item", "task", "scope"],
    "category": ["category", "trade", "division", "section"],
    "unit": ["unit", "uom", "units", "u/m"],
    "qty": ["qty", "quantity", "qnty"],
    "unit_cost": ["unit_cost", "unit cost", "unit price", "unit_price", "rate", "price/unit"],
    "estimate_id": ["estimate_id", "estimate id", "est id", "est_id", "estimate #", "estimate no"],
}


def match_column(name) -> str | None:
    """Map a header like 'Unit Price' or ' QTY ' to a standard column name (exact alias match only)."""
    h = re.sub(r"\s+", " ", str(name or "")).strip().lower()
    for target, names in COLUMN_ALIASES.items():
        if h in names:
            return target
    return None


def standardize_columns(est: pd.DataFrame) -> pd.DataFrame:
    """Rename recognised headers, add missing optional columns, and check required ones."""
    rename, used = {}, set()
    for c in est.columns:
        t = match_column(c)
        if t and t not in used:
            rename[c], used = t, used | {t}
    est = est.rename(columns=rename)
    missing = [c for c in REQUIRED if c not in est.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}. "
                         f"Required: {', '.join(REQUIRED)}; optional: {', '.join(OPTIONAL)}.")
    for c, default in (("estimate_id", "EST-UPLOAD"), ("category", ""), ("unit", "")):
        if c not in est.columns:
            est[c] = default
    est["estimate_id"] = est["estimate_id"].fillna("EST-UPLOAD").astype(str).str.strip()
    for c in ("item", "category", "unit"):
        est[c] = est[c].fillna("").astype(str).str.strip()
    return est


def to_number(s: pd.Series) -> pd.Series:
    """'$1,200.50' -> 1200.5, '(300)' -> -300, 'abc' -> NaN."""
    t = s.astype(str).str.strip()
    neg = t.str.match(r"^\(.*\)$")
    t = t.str.replace(r"[\$,\s()]", "", regex=True)
    out = pd.to_numeric(t, errors="coerce")
    return out.where(~neg, -out)


def load(estimate_csv, reference_csv):
    return standardize_columns(pd.read_csv(estimate_csv)), pd.read_csv(reference_csv)


def _peer_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Leave-one-out stats vs the same item+unit on OTHER estimates."""
    out = pd.DataFrame(index=df.index, columns=["peer_count", "peer_median", "peer_z", "flag_zscore", "flag_iqr"])
    out[["flag_zscore", "flag_iqr"]] = False
    for _, g in df.groupby(["item_key", "unit_key"]):
        for i, row in g.iterrows():
            others = g.loc[g.estimate_id != row.estimate_id, "unit_cost"]
            n = len(others)
            out.at[i, "peer_count"] = n
            if n == 0:
                continue
            med = others.median()
            out.at[i, "peer_median"] = med
            if n < MIN_PEERS:
                continue
            mean, std = others.mean(), others.std(ddof=1)
            z = (row.unit_cost - mean) / std if std > 0 else (0.0 if row.unit_cost == mean else np.sign(row.unit_cost - mean) * 99)
            out.at[i, "peer_z"] = z
            meaningful = abs(row.unit_cost / med - 1) >= MIN_PEER_DEV
            q1, q3 = others.quantile(0.25), others.quantile(0.75)
            out.at[i, "flag_zscore"] = bool(abs(z) > Z_THRESHOLD and meaningful)
            out.at[i, "flag_iqr"] = bool(meaningful and (row.unit_cost < q1 - IQR_K * (q3 - q1)
                                                         or row.unit_cost > q3 + IQR_K * (q3 - q1)))
    out["peer_count"] = out.peer_count.fillna(0).astype(int)
    out["peer_median"] = pd.to_numeric(out.peer_median)
    out["peer_z"] = pd.to_numeric(out.peer_z)
    return out.astype({"flag_zscore": bool, "flag_iqr": bool})


def analyze(est: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """Returns one row per valid line item. df.attrs holds 'data_issues' (list of skipped rows) and 'n_estimates'."""
    df = standardize_columns(est.copy())
    df["qty"], df["unit_cost"] = to_number(df["qty"]), to_number(df["unit_cost"])
    bad = df.qty.isna() | df.unit_cost.isna() | (df.qty <= 0) | (df.unit_cost <= 0) | (df["item"] == "")
    issues = df[bad].copy()
    issues["issue"] = np.select(
        [issues["item"] == "", issues.qty.isna() | issues.unit_cost.isna()],
        ["Missing item description", "Missing or non-numeric qty / unit cost"],
        "Zero or negative qty / unit cost")
    df = df[~bad].reset_index(drop=True)
    df["line_total"] = (df.qty * df.unit_cost).round(2)
    df["item_key"] = df["item"].str.lower().str.replace(r"\s+", " ", regex=True)
    df["unit_key"] = df["unit"].str.upper()

    # 1) Reference comparison (item must match, and unit too when both are given)
    r = ref.copy()
    r["item_key"] = r["item"].astype(str).str.strip().str.lower().str.replace(r"\s+", " ", regex=True)
    r = r.drop_duplicates("item_key").rename(columns={"unit": "reference_unit"})
    df = df.merge(r[["item_key", "reference_unit", "reference_unit_cost"]], on="item_key", how="left")
    df["unit_mismatch"] = (df.reference_unit.notna() & (df.unit_key != "")
                           & (df.unit_key != df.reference_unit.astype(str).str.upper()))
    df.loc[df.unit_mismatch | ~(df.reference_unit_cost > 0), "reference_unit_cost"] = np.nan
    df["pct_vs_reference"] = df.unit_cost / df.reference_unit_cost - 1
    df["flag_reference"] = df.pct_vs_reference.abs() > REF_PCT_THRESHOLD

    # 2) Peer comparison
    if len(df):
        df = df.join(_peer_stats(df))
    else:
        df = df.assign(peer_count=0, peer_median=np.nan, peer_z=np.nan, flag_zscore=False, flag_iqr=False)

    # Baseline = reference price if we have one, otherwise the peer median
    df["baseline_unit_cost"] = df.reference_unit_cost.fillna(df.peer_median)
    df["baseline_source"] = np.where(df.reference_unit_cost.notna(), "Reference",
                                     np.where(df.peer_median.notna(), "Peer median", "None"))
    df["pct_vs_baseline"] = df.unit_cost / df.baseline_unit_cost - 1

    # 3) IsolationForest anomaly model (only rows with a baseline)
    df["anomaly_score"], df["flag_ml"] = 0.0, False
    has_base = df.baseline_unit_cost.notna()
    if has_base.sum() >= ML_MIN_ROWS:
        sub = df[has_base]
        X = np.column_stack([np.log(sub.unit_cost / sub.baseline_unit_cost),
                             sub.peer_z.fillna(0).clip(-10, 10), np.log1p(sub.qty)])
        model = IsolationForest(contamination=ML_CONTAMINATION, random_state=0).fit(X)
        df.loc[has_base, "anomaly_score"] = -model.score_samples(X)
        df.loc[has_base, "flag_ml"] = model.predict(X) == -1

    checks = ["flag_reference", "flag_zscore", "flag_iqr", "flag_ml"]
    df["checks_triggered"] = df[checks].sum(axis=1).astype(int)
    df["flagged"] = df.flag_reference | (df.checks_triggered >= 2)
    df["direction"] = np.select([df.pct_vs_baseline > 0, df.pct_vs_baseline < 0], ["HIGH", "LOW"], "N/A")
    df["potential_variance_$"] = ((df.unit_cost - df.baseline_unit_cost) * df.qty).round(2)
    absv = df["potential_variance_$"].abs()
    sev = np.select([(df.pct_vs_baseline.abs() >= HIGH_SEVERITY_PCT) | (absv >= HIGH_SEVERITY_USD),
                     df.pct_vs_baseline.abs() >= REF_PCT_THRESHOLD], ["High", "Medium"], "Low")
    df["severity"] = np.where(df.flagged, sev, "")
    df["note"] = np.select([df.unit_mismatch, df.baseline_source == "None"],
                           ["Unit differs from reference table; reference check skipped",
                            "Not in reference table and no peers; not checked"], "")
    df["reason"] = [_reason(r) for _, r in df.iterrows()] if len(df) else pd.Series(dtype=str)
    df = df.sort_values(["flagged", "anomaly_score"], ascending=False).reset_index(drop=True)
    df = df.drop(columns=["item_key", "unit_key"])
    df.attrs["data_issues"] = issues.astype(object).where(issues.notna(), None).to_dict("records")  # JSON-safe
    df.attrs["n_estimates"] = int(df.estimate_id.nunique())
    return df


def _reason(r) -> str:
    if not r.flagged:
        return ""
    parts = []
    if pd.notna(r.reference_unit_cost):
        parts.append(f"Unit cost ${r.unit_cost:,.2f}/{r.unit or 'unit'} is {abs(r.pct_vs_reference):.0%} "
                     f"{'above' if r.pct_vs_reference > 0 else 'below'} the reference ${r.reference_unit_cost:,.2f}")
    else:
        parts.append(f"Not in reference table; compared to peer median ${r.peer_median:,.2f} "
                     f"({r.pct_vs_baseline:+.0%})")
    if r.flag_zscore or r.flag_iqr:
        parts.append(f"outlier vs {int(r.peer_count)} other estimates (median ${r.peer_median:,.2f}, z={r.peer_z:+.1f})")
    if r.flag_ml:
        parts.append("anomaly model also marked it unusual")
    tip = (" Verify scope/quantity or request backup pricing." if r.direction == "HIGH"
           else " Check for missing scope or a pricing error.")
    return "; ".join(parts) + "." + tip


def summary(df: pd.DataFrame) -> dict:
    f = df[df.flagged]
    var = f["potential_variance_$"].fillna(0)
    issues = df.attrs.get("data_issues")
    return {
        "estimates": int(df.estimate_id.nunique()),
        "line_items": len(df),
        "flagged": len(f),
        "flagged_high": int((f.direction == "HIGH").sum()),
        "flagged_low": int((f.direction == "LOW").sum()),
        "high_severity": int((f.severity == "High").sum()),
        "estimate_total_$": round(float(df.line_total.sum()), 2),
        "overpricing_$": round(float(var[var > 0].sum()), 2),
        "underpricing_$": round(float(var[var < 0].sum()), 2),
        "net_variance_flagged_$": round(float(var.sum()), 2),
        "unmatched_items": int((df.reference_unit_cost.isna()).sum()),
        "data_issues": len(issues or []),
        "peer_check_available": bool(df.estimate_id.nunique() > MIN_PEERS),
    }


if __name__ == "__main__":
    est_path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_estimates.csv"
    est, ref = load(est_path, "data/reference_unit_costs.csv")
    out = analyze(est, ref)
    print(summary(out))
    cols = ["estimate_id", "item", "unit_cost", "reference_unit_cost", "severity", "direction", "reason"]
    pd.set_option("display.width", 250, "display.max_colwidth", 140)
    print(out[out.flagged][cols].to_string(index=False))
    out.to_csv("flagged_report.csv", index=False)
    print("\nFull results written to flagged_report.csv")
