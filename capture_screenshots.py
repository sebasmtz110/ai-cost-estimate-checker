"""Capture README screenshots. Start the app first: streamlit run app.py --server.port 8599 --server.headless true
Then: python capture_screenshots.py  (needs: playwright install chromium)"""
from playwright.sync_api import sync_playwright
D="docs/screenshots/"
def wait(p):
    p.wait_for_selector("text=AI reviewer summary", timeout=60000); p.wait_for_timeout(3500)
with sync_playwright() as pw:
    b=pw.chromium.launch(); p=b.new_page(viewport={"width":1440,"height":1000})
    p.goto("http://localhost:8599"); wait(p)
    p.screenshot(path=D+"01_dashboard.png")
    p.get_by_text("Reviewer note").first.scroll_into_view_if_needed(); p.wait_for_timeout(800)
    p.screenshot(path=D+"02_ai_reviewer_summary.png")
    p.locator(".js-plotly-plot").first.scroll_into_view_if_needed(); p.wait_for_timeout(1500)
    p.screenshot(path=D+"03_chart.png")
    for f,name in [("data/sample_estimates.csv","04_csv_upload.png"),("data/sample_estimate.pdf","05_pdf_upload.png")]:
        p.locator("input[type=file]").set_input_files(f)
        p.wait_for_selector(f"text=Using uploaded file: {f.split('/')[-1]}", timeout=60000); wait(p)
        assert p.locator("[data-testid=stException]").count()==0, f
        p.evaluate("window.scrollTo(0,0)"); p.wait_for_timeout(500)
        p.screenshot(path=D+name)
        print(name, "ok; flagged metric:", p.locator("[data-testid=stMetricValue]").nth(1).inner_text())
    print("exceptions on page:", p.locator("[data-testid=stException]").count())
    b.close()
