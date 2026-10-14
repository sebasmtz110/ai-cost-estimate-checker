"""Create data/sample_estimate.pdf -- a SYNTHETIC example estimate (fictional, for demo only)."""
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

EST_ID = "EST-1002"


def build(path="data/sample_estimate.pdf"):
    est = pd.read_csv("data/sample_estimates.csv")
    e = est[est.estimate_id == EST_ID]
    ss = getSampleStyleSheet()
    data = [["Description", "Trade", "UOM", "Quantity", "Unit Price", "Line Total"]]
    for _, r in e.iterrows():
        data.append([r["item"], r.category, r.unit, f"{r.qty:,}", f"${r.unit_cost:,.2f}", f"${r.line_total:,.2f}"])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                           ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    doc = SimpleDocTemplate(path, pagesize=letter)
    doc.build([Paragraph("Residential Repair Estimate", ss["Title"]),
               Paragraph(f"Estimate ID: {EST_ID}", ss["Normal"]),
               Paragraph("SYNTHETIC EXAMPLE DATA - fictional estimate for demonstration only. "
                         "Not a real property, contractor, or pricing source.", ss["Italic"]),
               Spacer(1, 12), t])
    print(f"Wrote {path} ({len(e)} line items)")


if __name__ == "__main__":
    build()
