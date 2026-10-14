"""
Generate SYNTHETIC example data for the Cost Estimate Checker.

IMPORTANT: Every number here is made up for demonstration only.
It is NOT from any real company, project, client, or pricing database.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

# Synthetic "typical" unit costs (example values, not real pricing)
REFERENCE = [
    # item, category, unit, typical_unit_cost
    ("Remove & replace drywall 1/2in", "Drywall", "SF", 3.50),
    ("Tape, mud & texture drywall", "Drywall", "SF", 1.75),
    ("Interior paint - 2 coats", "Painting", "SF", 1.40),
    ("Exterior paint - 2 coats", "Painting", "SF", 2.10),
    ("Laminate flooring install", "Flooring", "SF", 4.25),
    ("Carpet & pad install", "Flooring", "SF", 3.60),
    ("Ceramic tile flooring", "Flooring", "SF", 9.50),
    ("Baseboard trim replace", "Finish Carpentry", "LF", 3.20),
    ("Interior door - prehung", "Finish Carpentry", "EA", 285.00),
    ("Asphalt shingle roofing", "Roofing", "SQ", 425.00),
    ("Roof felt underlayment", "Roofing", "SQ", 38.00),
    ("Drip edge", "Roofing", "LF", 2.80),
    ("Batt insulation R-13", "Insulation", "SF", 1.30),
    ("Base cabinets", "Cabinets", "LF", 210.00),
    ("Laminate countertop", "Cabinets", "LF", 48.00),
    ("Water heater 40 gal", "Plumbing", "EA", 1350.00),
    ("Toilet - remove & reset", "Plumbing", "EA", 260.00),
    ("Electrical outlet replace", "Electrical", "EA", 95.00),
    ("Light fixture replace", "Electrical", "EA", 165.00),
    ("Debris haul-off", "General Conditions", "LD", 375.00),
    ("Water extraction & drying", "Mitigation", "SF", 2.40),
    ("Vinyl window replace", "Windows & Doors", "EA", 620.00),
]

QTY_RANGE = {"SF": (80, 1600), "LF": (10, 220), "EA": (1, 12),
             "SQ": (10, 35), "LD": (1, 5)}


def build():
    ref = pd.DataFrame(REFERENCE, columns=["item", "category", "unit", "reference_unit_cost"])
    rows = []
    for p in range(1, 9):  # 8 fictional properties
        est_id = f"EST-{1000 + p}"
        for item, cat, unit, cost in REFERENCE:
            if RNG.random() < 0.15:  # not every job has every item
                continue
            lo, hi = QTY_RANGE[unit]
            qty = int(RNG.integers(lo, hi))
            unit_cost = round(cost * RNG.normal(1.0, 0.08), 2)  # normal spread
            rows.append([est_id, item, cat, unit, qty, unit_cost])
    est = pd.DataFrame(rows, columns=["estimate_id", "item", "category", "unit", "qty", "unit_cost"])

    # Inject a few deliberate problems so the checker has something to find
    def bump(est_id, item, factor):
        m = (est.estimate_id == est_id) & (est.item == item)
        if not m.any():  # make sure the row exists
            r = ref[ref.item == item].iloc[0]
            est.loc[len(est)] = [est_id, item, r.category, r.unit, 10, r.reference_unit_cost]
            m = (est.estimate_id == est_id) & (est.item == item)
        est.loc[m, "unit_cost"] = round(float(ref[ref.item == item].reference_unit_cost.iloc[0]) * factor, 2)

    bump("EST-1002", "Asphalt shingle roofing", 1.85)   # overpriced
    bump("EST-1003", "Interior paint - 2 coats", 0.40)  # suspiciously cheap
    bump("EST-1005", "Water heater 40 gal", 2.10)       # overpriced
    bump("EST-1006", "Laminate flooring install", 1.60)
    bump("EST-1007", "Debris haul-off", 0.35)
    bump("EST-1008", "Base cabinets", 1.70)

    est["line_total"] = (est.qty * est.unit_cost).round(2)
    return ref, est.sort_values(["estimate_id", "category", "item"]).reset_index(drop=True)


if __name__ == "__main__":
    ref, est = build()
    ref.to_csv("data/reference_unit_costs.csv", index=False)
    est.to_csv("data/sample_estimates.csv", index=False)
    print(f"Wrote {len(ref)} reference items and {len(est)} SYNTHETIC estimate lines to data/")
