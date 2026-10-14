"""Capture README screenshots and run browser checks (sample, CSV, PDF, bad uploads).
Start the app first:  streamlit run app.py --server.port 8599
Then run:             python capture_screenshots.py   (needs: pip install -r requirements-dev.txt
                                                        and: playwright install chromium)"""
import os
import tempfile
from playwright.sync_api import sync_playwright

D = "docs/screenshots/"
URL = os.getenv("APP_URL", "http://localhost:8599")


def settle(p):
    """Wait until Streamlit finished running (no Stop button, no spinner)."""
    p.wait_for_timeout(1500)
    p.wait_for_function("""() => !document.body.innerText.includes('Writing reviewer note')
        && ![...document.querySelectorAll('button')].some(b => b.innerText.trim() === 'Stop')""", timeout=180000)
    p.wait_for_timeout(1800)


def no_errors(p, where):
    n = p.locator("[data-testid=stException]").count()
    assert n == 0, f"{n} exception(s) on page: {where}"


def tab(p, name):
    p.get_by_role("tab", name=name).click(); p.wait_for_timeout(1500)


def top(p):
    p.locator(".hero").first.evaluate("e => e.scrollIntoView({block: 'start'})"); p.wait_for_timeout(600)


def upload(p, path, expect):
    p.locator("input[type=file]").set_input_files(path)
    p.wait_for_selector(f"text={expect}", timeout=60000); settle(p)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={"width": 1500, "height": 1050}, device_scale_factor=1)
    p.goto(URL); p.wait_for_selector(".hero", timeout=60000); settle(p); no_errors(p, "sample")
    src = p.locator(".src").first.inner_text(); print("sample reviewer:", src)
    p.screenshot(path=D + "01_overview.png")
    p.locator(".st-key-reviewer_card").evaluate("e => e.scrollIntoView({block: 'start'})"); p.wait_for_timeout(600)
    p.locator(".st-key-reviewer_card").screenshot(path=D + "02_ai_reviewer_card.png")
    top(p); tab(p, "🚩  Flagged items"); no_errors(p, "flagged"); p.screenshot(path=D + "03_flagged_items.png")
    tab(p, "📈  Analytics"); p.wait_for_selector(".js-plotly-plot", timeout=30000); p.wait_for_timeout(1500)
    no_errors(p, "analytics"); p.screenshot(path=D + "04_analytics.png")
    tab(p, "🗂️  Data"); no_errors(p, "data")

    upload(p, "data/sample_estimates.csv", "Using uploaded file: sample_estimates.csv"); no_errors(p, "csv")
    tab(p, "🚩  Flagged items"); top(p); p.screenshot(path=D + "05_csv_upload.png")
    print("csv reviewer:", p.locator(".src").first.inner_text())

    upload(p, "data/sample_estimate.pdf", "Using uploaded file: sample_estimate.pdf"); no_errors(p, "pdf")
    tab(p, "🤖  AI reviewer"); top(p); p.screenshot(path=D + "06_pdf_upload.png")
    print("pdf reviewer:", p.locator(".src").first.inner_text())

    tmp = tempfile.mkdtemp()
    for name, content, expect in [("empty.csv", "", "The uploaded file is empty"),
                                  ("wrong_cols.csv", "a,b\n1,2\n", "Missing required column"),
                                  ("all_bad.csv", "item,qty,unit_cost\nx,abc,0\n", "No valid line items"),
                                  ("fake.pdf", "not a pdf", "Could not open the PDF")]:
        path = os.path.join(tmp, name)
        with open(path, "w") as fh:
            fh.write(content)
        p.locator("input[type=file]").set_input_files(path)
        p.wait_for_selector(f"text={expect}", timeout=60000); settle(p); no_errors(p, name)
        print(f"bad upload {name}: friendly error shown, 0 exceptions")
    print("ALL BROWSER CHECKS PASSED")
    b.close()
