"""
Read line-item tables out of a PDF estimate and map them to the checker's columns.
Uses pdfplumber to find tables; headers are matched by exact alias (e.g. "Description" -> item,
"Unit Price" -> unit_cost). Tables that continue onto the next page without a header row
reuse the previous header. Scanned (image-only) PDFs have no text and are not supported.
"""
import re
import pandas as pd
import pdfplumber
from checker import match_column


def _map_header(header):
    mapping = {}
    for i, h in enumerate(header):
        t = match_column(h)
        if t and t not in mapping.values():
            mapping[i] = t
    return mapping


def _num(s):
    """'$1,234.50' -> 1234.5; '(300)' -> -300; anything unparseable -> None."""
    t = str(s or "").strip()
    neg = t.startswith("(") and t.endswith(")")
    t = re.sub(r"[^0-9.\-]", "", t)
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def parse_pdf(file) -> pd.DataFrame:
    """file: path or file-like object. Returns estimate_id, item, category, unit, qty, unit_cost."""
    rows, est_id, mapping, ncols = [], None, None, None
    try:
        pdf = pdfplumber.open(file)
    except Exception as e:
        raise ValueError(f"Could not open the PDF ({type(e).__name__}). Is it a valid, unencrypted PDF?")
    with pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            m = re.search(r"Estimate\s*(?:ID|#|No\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]*)", text, re.I)
            if m and not est_id:
                est_id = m.group(1)
            for table in page.extract_tables():
                if not table:
                    continue
                head = _map_header(table[0])
                if {"item", "qty", "unit_cost"} <= set(head.values()):
                    mapping, ncols, body = head, len(table[0]), table[1:]
                elif mapping and len(table[0]) == ncols:
                    body = table          # continuation table without a header row
                else:
                    continue
                for r in body:
                    rec = {t: (r[i] if i < len(r) else None) for i, t in mapping.items()}
                    item = re.sub(r"\s+", " ", str(rec.get("item") or "")).strip()
                    qty, cost = _num(rec.get("qty")), _num(rec.get("unit_cost"))
                    if not item or qty is None or cost is None or item.lower().startswith(("total", "subtotal")):
                        continue
                    rec.update(item=item, qty=qty, unit_cost=cost)
                    rows.append(rec)
    if not rows:
        raise ValueError("No line-item table with item / quantity / unit cost columns was found in the PDF "
                         "(scanned image PDFs are not supported).")
    df = pd.DataFrame(rows)
    for c in ("category", "unit"):
        df[c] = df[c].fillna("").astype(str).str.strip() if c in df else ""
    if "estimate_id" not in df:
        df["estimate_id"] = est_id or "EST-PDF"
    return df[["estimate_id", "item", "category", "unit", "qty", "unit_cost"]]
