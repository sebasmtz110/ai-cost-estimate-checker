"""Edge-case tests: run with `python tests_edge_cases.py`."""
import io
import numpy as np
import pandas as pd
from checker import analyze, summary, standardize_columns, to_number
from pdf_parser import parse_pdf, _num, _map_header
from reviewer import template_summary

ref = pd.read_csv("data/reference_unit_costs.csv")


def check(name, cond):
    assert cond, name
    print("ok -", name)


# Column handling
try:
    standardize_columns(pd.DataFrame({"item": ["x"], "qty": [1]}))
    raise AssertionError("missing column not caught")
except ValueError as e:
    check("missing unit_cost column -> clear error", "unit_cost" in str(e))
d = standardize_columns(pd.DataFrame({" Description ": ["a"], "QTY": [1], "Unit Price": [2]}))
check("header aliases + optional columns added", {"item", "qty", "unit_cost", "unit", "category", "estimate_id"} <= set(d.columns))
check("'Unit Price' is not mistaken for 'unit'", _map_header(["UOM", "Unit Price", "Estimate Total"]) == {0: "unit", 1: "unit_cost"})

# Number parsing
check("currency strings parse", to_number(pd.Series(["$1,200.50", "(300)", "abc", ""])).tolist()[:2] == [1200.5, -300.0])
check("pdf _num never crashes", _num("1.2.3") is None and _num("$1,234.00") == 1234.0 and _num("(5)") == -5)

# Bad rows are set aside, not crashing
bad = pd.DataFrame({"item": ["Drywall", "Zero", "Neg", "", "Asphalt shingle roofing"],
                    "qty": ["abc", 2, -1, 1, 10], "unit_cost": [3, 0, 10, 10, 425], "unit": ["SF", "EA", "EA", "EA", "SQ"]})
out = analyze(bad, ref)
check("invalid rows skipped and reported", len(out) == 1 and summary(out)["data_issues"] == 4)

# Everything invalid -> empty result, no crash
empty = analyze(pd.DataFrame({"item": ["x"], "qty": [0], "unit_cost": [0]}), ref)
check("all-invalid input -> empty frame + summary works", empty.empty and summary(empty)["line_items"] == 0)

# Unknown item / unit mismatch / case-insensitive matching
mix = pd.DataFrame({"item": ["Mystery widget", "Interior paint - 2 coats", "  ASPHALT shingle roofing "],
                    "unit": ["EA", "SY", "sq"], "qty": [1, 100, 10], "unit_cost": [50, 9, 425]})
o = analyze(mix, ref).set_index("item")
check("unknown item not checked, not flagged", not o.loc["Mystery widget", "flagged"] and o.loc["Mystery widget", "direction"] == "N/A")
check("unit mismatch skips reference", np.isnan(o.loc["Interior paint - 2 coats", "reference_unit_cost"]))
check("item/unit match is case/space-insensitive", o.loc["ASPHALT shingle roofing", "reference_unit_cost"] == 425)

# Reference price of 0 never divides by zero
r0 = ref.copy(); r0.loc[r0.item == "Drip edge", "reference_unit_cost"] = 0
z = analyze(pd.DataFrame({"item": ["Drip edge"], "unit": ["LF"], "qty": [10], "unit_cost": [3]}), r0)
check("zero reference cost -> no inf", not np.isinf(z.pct_vs_reference.fillna(0)).any())

# Peer z-score can actually fire with a small peer group (leave-one-out)
peers = pd.DataFrame({"estimate_id": [f"E{i}" for i in range(6)], "item": ["Mystery widget"] * 6, "unit": ["EA"] * 6,
                      "qty": [1] * 6, "unit_cost": [100, 102, 98, 101, 99, 160]})
p = analyze(peers, ref)
row = p[p.unit_cost == 160].iloc[0]
check("peer outlier detected with 5 peers", bool(row.flag_zscore) and bool(row.flag_iqr) and row.flagged)
check("in-line items not flagged", p[p.unit_cost != 160].flagged.sum() == 0)

# Variance math
r = analyze(pd.DataFrame({"item": ["Water heater 40 gal"], "unit": ["EA"], "qty": [2], "unit_cost": [2700]}), ref).iloc[0]
check("variance = (unit cost - reference) x qty", r["potential_variance_$"] == (2700 - 1350) * 2)
check("severity High at +100%", r.severity == "High")

# Single-estimate wording is proportionate and caveated
pdf = analyze(parse_pdf("data/sample_estimate.pdf"), ref)
note = template_summary(pdf, "EST-1002")
check("single-PDF note caveats missing peer comparison", "Peer comparison was not available" in note)
check("single-PDF note not overstated", "Significant" not in note)
clean = analyze(pd.DataFrame({"item": ["Drip edge"], "unit": ["LF"], "qty": [10], "unit_cost": [2.8]}), ref)
check("no-flag note says no exceptions", "No pricing exceptions" in template_summary(clean, "EST-UPLOAD"))

# Corrupt PDF -> friendly error
try:
    parse_pdf(io.BytesIO(b"not a pdf"))
    raise AssertionError("corrupt pdf not caught")
except ValueError as e:
    check("corrupt PDF -> ValueError", "PDF" in str(e))
print("ALL EDGE-CASE TESTS PASSED")
