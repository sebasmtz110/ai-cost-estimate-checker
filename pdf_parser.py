"""
Read line-item tables out of a PDF estimate and map them to the checker's columns.
Uses pdfplumber to find tables; header names are matched flexibly (e.g. "Description" -> item).
"""
import re
import pandas as pd
import pdfplumber

ALIASES = {
    "item": ["item", "description", "line item", "task", "scope"],
    "category": ["category", "trade", "division", "section"],
    "unit": ["unit", "uom", "units", "u/m"],
    "qty": ["qty", "quantity", "qnty", "amount qty"],
    "unit_cost": ["unit cost", "unit price", "rate", "price/unit", "unit $"],
    "estimate_id": ["estimate id", "estimate", "est id", "claim"],
}


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _map_header(header):
    mapping = {}
    for i, h in enumerate(map(_norm, header)):
        for target, names in ALIASES.items():
            if target not in mapping.values() and any(h == n or h.startswith(n) for n in names):
                mapping[i] = target
                break
    return mapping


def _num(s):
    s = re.sub(r"[^0-9.\-]", "", str(s or ""))
    return float(s) if s not in ("", "-", ".") else None


def parse_pdf(file) -> pd.DataFrame:
    """file: path or file-like object. Returns DataFrame with item, category, unit, qty, unit_cost[, estimate_id]."""
    rows, est_id = [], None
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            m = re.search(r"Estimate\s*(?:ID|#|No\.?)\s*[:\-]?\s*([A-Z0-9\-]+)", page.extract_text() or "", re.I)
            if m and not est_id:
                est_id = m.group(1)
            for table in page.extract_tables():
                if not table:
                    continue
                mapping = _map_header(table[0])
                if not {"item", "qty", "unit_cost"} <= set(mapping.values()):
                    continue
                for r in table[1:]:
                    rec = {t: r[i] for i, t in mapping.items() if i < len(r)}
                    rec["qty"], rec["unit_cost"] = _num(rec.get("qty")), _num(rec.get("unit_cost"))
                    if rec.get("item") and rec["qty"] is not None and rec["unit_cost"] is not None:
                        rec["item"] = re.sub(r"\s+", " ", rec["item"]).strip()
                        rows.append(rec)
    if not rows:
        raise ValueError("No line-item table with item / qty / unit cost columns found in the PDF.")
    df = pd.DataFrame(rows)
    for c in ("category", "unit"):
        if c not in df:
            df[c] = ""
    if "estimate_id" not in df:
        df["estimate_id"] = est_id or "EST-PDF"
    return df[["estimate_id", "item", "category", "unit", "qty", "unit_cost"]]
