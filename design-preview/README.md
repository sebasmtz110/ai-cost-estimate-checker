# Setline — Design Preview (Draft 2)

Isolated high-fidelity UI prototype. **Does not modify the production application.**

## Phone preview

If a tunnel is running in the agent environment, use the HTTPS link shared in chat.

Locally:

```bash
cd design-preview
python3 -m http.server 8765
```

Open `http://localhost:8765` (full-bleed on phone browsers; desktop shows a device frame).

## Draft 2 changes

- Stronger identity: cool light canvas, black primary actions, volt signal accent, Oswald + IBM Plex Sans
- Home rebuilt as full-bleed next-session stage + rhythm track + editorial last session (not KPI card stacks)
- Exercise media: photographic temps with **Temp media** badges (not stick figures)
- Workout: sticky session header, larger inputs, volt complete states, rest dock
- Progress: compact charts, sample labels, tighter hierarchy
- Mobile: removed fake 9:41 bar; safe-area padding; tab bar clearance

## Restrictions

Prototype-only under `design-preview/`. Wait for explicit approval before any production integration.
