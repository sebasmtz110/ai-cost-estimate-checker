# Walkthrough (plain English)

## The big picture
You give the app a construction repair estimate (a spreadsheet-style CSV or a PDF). For every line it asks: *"Is this price normal?"* Lines that look too expensive or too cheap get a flag, a severity (High / Medium / Low), a sentence explaining why, and a dollar impact. Then an AI writes a short reviewer memo for each estimate.

## The files
**`generate_sample_data.py`**: makes the fake practice data. It has a list of 22 repair items (drywall, roofing, water heater…) with a made-up "typical" price for each. It creates 8 fictional estimates, wiggles each price a little (about ±8%) so they look realistic, and plants 6 deliberate pricing problems (like a roof priced 85% too high) so we can prove the tool catches them.

**`data/reference_unit_costs.csv`**: the "price book", i.e. what each item should roughly cost per unit (SF = square foot, LF = linear foot, EA = each, SQ = roofing square, LD = load).

**`data/sample_estimates.csv`**: the estimates to review, one row per line item.

**`checker.py`**: the brain. First it **cleans the data**: it recognises different column names ("Description" means item), turns text like `$1,200.00` into numbers, and sets aside bad rows (blank item, letters instead of numbers, zero or negative prices) so they don't break anything. Then for every line it:
1. Compares the price to the price book, but only if the **unit** matches too (a price per square yard can't be compared to a price per square foot).
2. Compares it to the same item on the **other** estimates. A *z-score* says how many "standard deviations" it is from the others' average; *IQR* is a similar test using the middle 50% of prices. The line is left out of its own comparison, otherwise a real outlier would hide itself by pulling the average toward it. This needs at least 4 other estimates.
3. Runs an *IsolationForest*, a machine-learning model that finds rows that are easy to "isolate" from the rest, i.e. the weird ones.
4. Flags the line if it's more than 25% off the price book, or if two checks agree. It then gives a severity: **High** = 50%+ off or $5,000+ at stake, **Medium** = 25%+, **Low** = the rest.

The settings at the top (`REF_PCT_THRESHOLD`, `Z_THRESHOLD`, etc.) control how strict it is.

**`reviewer.py`**: writes the "reviewer note" for one estimate, like a short memo a cost reviewer would send: overall verdict, biggest problems, dollars at stake, next steps. It tries **Google Gemini** (free) first, then **OpenAI** (only if you have that key), then a fill-in-the-blanks **template**. The AI gets only the checker's numbers and is told not to make anything up. It's also told how strong the wording should be, so one flagged line doesn't get called a disaster. If only one estimate is loaded, the note says peer comparison wasn't possible. If no key is set, or a key is wrong, it quietly uses the template, so the app never breaks.

**`pdf_parser.py`**: lets you upload a PDF estimate. It uses `pdfplumber` to find the table, works out which column is which ("UOM" = unit, "Unit Price" = unit cost), handles tables that continue onto the next page, and skips "Total" rows. Scanned PDFs (pictures of paper) don't contain text, so they can't be read.

**`make_sample_pdf.py`**: makes `data/sample_estimate.pdf`, a fake estimate PDF (stamped as synthetic) for testing the upload.

**`app.py`**: the website. Streamlit turns Python into a web page. It's laid out as 3 steps:
1. **Choose your estimate**: sample data or upload a CSV/PDF.
2. **Explore the results**: 5 clickable **counters**. Each is a real button: tap one and the table shows exactly the rows it counts, and the button turns orange so you know which is active. "Show all" resets it. Trade and Estimate filters narrow everything. Tap a row (or a chart point) to open a **detail card** that shows the four checks with 🚩 or ✅.
3. **Get the AI reviewer note** for the estimate you pick.

The buttons use Streamlit's `on_click` callbacks: a small function runs *before* the page redraws and records which counter you picked in `st.session_state` (the app's memory between clicks).

**`ui.py`**: a few lines of CSS that make the counter buttons big, plus helpers that format money and percentages. The CSS deliberately has no overlays or floating layers, so nothing can block clicks on a phone.

**`.streamlit/config.toml`**: Streamlit's theme settings: a light background and one orange accent color.

**`tests_smoke.py`, `tests_edge_cases.py`, `tests_llm_fallback.py`**: automatic checks. Run each with `python <file>`. Each should end with `... PASSED`. The edge-case tests throw bad data at the checker (missing columns, letters in number columns, zero prices, unknown items, a broken PDF) and make sure it handles them politely.

**`capture_screenshots.py`**: opens the app in an invisible browser, once as a desktop and once as a phone, and clicks every counter, filter, row, dropdown, download and upload (including a bad file). It also saves the README pictures. Point it at the live site with `APP_URL=... python capture_screenshots.py --no-shots`.

**`requirements.txt` / `requirements-dev.txt`**: the Python libraries to install. The dev file adds the screenshot tool.

## Using a free AI key (optional)
1. Go to **https://aistudio.google.com/app/apikey**, sign in with a Google account, and click **Create API key**. Copy it. (The free tier costs nothing. Google may use free-tier requests to improve its products, which is fine here because the data is synthetic.)
2. Tell your computer about it (only for the current terminal window):
   - Mac/Linux: `export GEMINI_API_KEY=your_key`
   - Windows: `set GEMINI_API_KEY=your_key`
3. Run `streamlit run app.py`. The sidebar says "Gemini enabled" and the note card shows "Generated by: AI (Gemini)".

**Alternative:** create a file `.streamlit/secrets.toml` containing `GEMINI_API_KEY = "your_key"`. This file is in `.gitignore`, so it never goes to GitHub. (The other file in that folder, `config.toml`, is just the theme and *is* committed.) When you deploy on Streamlit Community Cloud, paste the same line into the app's **Secrets** settings.

**Never** paste the key into a `.py` file or commit it. If one leaks, delete it in AI Studio and make a new one.

If the card says "Generated by: Template" even though your key is set, Google's free model was probably busy. It already retried. Change the estimate dropdown or refresh to try again.

To try a different model, set `GEMINI_MODEL` (for example `gemini-3.5-flash-lite`).

## Try these edits yourself
1. **Make it stricter.** In `checker.py`, change `REF_PCT_THRESHOLD = 0.25` to `0.15`. Run `python checker.py` again: more items get flagged. Be ready to talk about this trade-off in interviews (catching more vs. false alarms).
2. **Add an item to the price book.** In `generate_sample_data.py`, add a line to `REFERENCE`, e.g. `("Gutter replace", "Exteriors", "LF", 9.00),`, then run `python generate_sample_data.py` and `python make_sample_pdf.py`, and refresh the app. (The random prices will shift a little, so the exact flag counts may change.)
3. **Change the accent color.** In `.streamlit/config.toml` change `primaryColor = "#EA580C"` (orange) to e.g. `"#2563EB"` (blue), and change `ACCENT` in `ui.py` to match. Restart the app.
4. **Add a follow-up recommendation.** In `reviewer.py`, find `"- Verify quantities against field measurements and the scope of work before approval."` and add a line below it, e.g. `lines.append("- Compare against the original scope of loss.")`. You'll see it in template notes (run the app without a key).

After each edit, run the tests, then commit: `git add . && git commit -m "Describe your change"`.
