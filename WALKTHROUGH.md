# Walkthrough (plain English)

## The files
**`generate_sample_data.py`** – Makes the fake practice data. It has a list of 22 repair items (drywall, roofing, water heater…) with a made-up "typical" price for each. It then creates 8 fictional estimates, wiggling each price a little (±8%) so they look realistic, and plants 6 deliberate pricing problems (like a roof priced 85% too high) so we can check that the tool catches them.

**`data/reference_unit_costs.csv`** – The "price book": what each item should roughly cost per unit (SF = square foot, LF = linear foot, EA = each, SQ = roofing square, LD = load).

**`data/sample_estimates.csv`** – The estimates to review. One row per line item.

**`checker.py`** – The brain. For every line it:
1. Compares the price to the price book (% above/below).
2. Compares it to the same item on the other estimates. A *z-score* says how many "standard deviations" away from average it is; *IQR* is a similar test based on the middle 50% of prices.
3. Runs an *IsolationForest*, a machine learning model that finds rows that are easy to "isolate" from the rest — i.e., weird ones.
4. Flags the line if it's far off the price book or if two checks agree, and writes a sentence explaining why.

The settings at the top (`REF_PCT_THRESHOLD`, etc.) control how strict it is.

**`app.py`** – The website. Streamlit turns Python into a web page: sidebar to upload a file, metric cards across the top, a table of flagged items, and a scatter chart (dots far from the dashed line are priced far from the reference).

**`requirements.txt`** – The list of Python libraries to install.

## Try these edits yourself
1. **Make it stricter.** In `checker.py`, change `REF_PCT_THRESHOLD = 0.25` to `0.15`. Run `python checker.py` again — more items get flagged. Talk about this trade-off in interviews (catching more vs. false alarms).
2. **Add an item to the price book.** In `generate_sample_data.py`, add a line to `REFERENCE`, e.g. `("Gutter replace", "Exteriors", "LF", 9.00),`, then run `python generate_sample_data.py` and refresh the app.
3. **Change the app title.** In `app.py`, edit the `st.title(...)` text (for example add your name), save, and the browser updates.

After each edit, commit it: `git add . && git commit -m "Describe your change"`.
