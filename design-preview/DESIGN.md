# Setline v2 — Design Direction

## Draft 1 weaknesses (addressed)

1. **Generic AI dashboard composition** — hero card → three meta stats → identical history rows → KPI strip. No editorial hierarchy.
2. **Thin brand identity** — white canvas + red CTA + stick-figure SVGs read as template, not product.
3. **Fake device chrome** — simulated 9:41 bar and phone bezel fought the real iPhone browser (safe areas, tab overlap).

## Research → principles

| Reference | Principle carried forward |
|-----------|---------------------------|
| Nike Training Club | Full-bleed session storytelling; black/white foundation; bold condensed type; content over chrome |
| Nike Run Club | Glanceable live metrics; one decisive primary action; calm surfaces |
| Strava | Data as narrative; single accent for “earned” signals; hairline structure; feed with varied density |
| Strong / Hevy | Set table as the product; huge tap targets; rest after log |

## Identity: Setline v2

- **Canvas:** cool light stone `#F2F3F5` (not pure white sheet)
- **Ink:** near-black `#0B0B0C`
- **Primary action:** solid black (Nike clarity) — not a rainbow of colored buttons
- **Signal accent:** volt `#B6F400` for live/complete/streak only
- **Type:** *Oswald* (display) + *IBM Plex Sans* (UI, tabular nums)
- **Imagery:** photographic training hero + clearly badged **TEMP MEDIA** exercise stills (Unsplash, demo only)
- **Layout:** edge-to-edge session stage; rhythm track; one featured last session; compact metrics — not card stacks
- **Mobile:** no fake status bar; `env(safe-area-inset-*)`; tab bar clears content

Prototype-only. Sample data labeled throughout.
