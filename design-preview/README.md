# Setline — Design Preview (Prototype Only)

Isolated high-fidelity UI prototype for a **proposed** premium fitness redesign.  
**This folder does not modify the production application.**

> **Repo note:** The existing project in this repository is the *AI Construction Cost Estimate Checker* (Streamlit). There is no gym app to redesign in production files. This prototype explores the fitness product UI described in the brief so it can be evaluated before any integration decision.

## How to preview

From the repository root:

```bash
cd design-preview
python3 -m http.server 8765
```

Open: [http://localhost:8765](http://localhost:8765)

Or open `design-preview/index.html` directly in a browser.

Use the phone frame on desktop, or resize the window. Bottom tabs switch screens. On **Home**, tap **Start session**. On **Workout**, tap set checkmarks to log sets and trigger the rest timer. On **Library**, search/filter and open an exercise. On **Progress**, review sample history/charts.

## What’s included

| Screen | Purpose |
|--------|---------|
| Home | Next session CTA, consistency strip, recent sessions, volume snapshot |
| Workout | Active set logging, rest timer, exercise progression |
| Library | Search, muscle/equipment filters, exercise detail |
| Progress | History list, volume trend, strength sparkline (sample data) |

## Placeholders

- Exercise figures are **simple SVG silhouettes** (consistent style demo), not a finished animation library.
- All training numbers are **synthetic sample data** for layout only.
- Brand name **Setline** is a prototype label only.

## Design tokens

See `styles.css` (`:root` variables) and `DESIGN.md`.

## Do not integrate

Do not copy these files into the Streamlit app unless explicitly approved after review.
