"""Smoke tests: run with `python tests_smoke.py`. Checks sample, CSV upload and PDF upload paths."""
from streamlit.testing.v1 import AppTest
import pandas as pd
from checker import analyze
from pdf_parser import parse_pdf
from reviewer import reviewer_summary

ref = pd.read_csv("data/reference_unit_costs.csv")
# 1. App with sample data
at = AppTest.from_file("app.py", default_timeout=60).run()
assert not at.exception, at.exception
assert any("Reviewer note" in m.value for m in at.markdown)
print("app (sample data): OK,", [(m.label, m.value) for m in at.metric])
# 2. CSV path (same code the app runs after upload)
csv = pd.read_csv("data/sample_estimates.csv")
out = analyze(csv[csv.estimate_id == "EST-1005"], ref)
assert out.flagged.any(); print("csv path: OK, flagged", int(out.flagged.sum()))
# 3. PDF path
pdf = parse_pdf("data/sample_estimate.pdf")
out = analyze(pdf, ref)
assert len(pdf) == 18 and out.flagged.any()
note, src = reviewer_summary(out, "EST-1002")
print(f"pdf path: OK, {len(pdf)} lines, flagged {int(out.flagged.sum())}, reviewer={src}")
print("ALL SMOKE TESTS PASSED")
