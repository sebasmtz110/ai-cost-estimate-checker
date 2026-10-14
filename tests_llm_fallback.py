"""Checks the reviewer falls back to the template with no key or an invalid key."""
import os, pandas as pd
from checker import analyze
import reviewer
df = analyze(pd.read_csv("data/sample_estimates.csv"), pd.read_csv("data/reference_unit_costs.csv"))
for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(k, None)
assert reviewer.reviewer_summary(df, "EST-1005")[1] == "Template"; print("no key -> Template")
for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"):
    os.environ[k] = "invalid-test-key"
    assert reviewer.reviewer_summary(df, "EST-1005")[1] == "Template"; print(f"invalid {k} -> Template")
    os.environ.pop(k)
print("FALLBACK TESTS PASSED")
