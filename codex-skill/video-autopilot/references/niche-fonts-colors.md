# Shorts typography and color routing
> **PUBLIC_FIXTURE / privacy boundary:** no private palette verdict, dated feedback,
> local font inventory or maintainer preference; projects supply reviewed tokens.
## Semantic color roles
| Token | Purpose |
|---|---|
| `<TEXT_PRIMARY>` | normal captions with verified contrast |
| `<ACCENT_FACT>` | a price, measurement, place or key fact |
| `<ACCENT_ACTION>` | a single action or state change |
| `<SURFACE>` | restrained support panel when footage contrast varies |
| `<DANGER>` | verified warning or destructive action only |
## Routing and QA
- Start with one text color and one accent; add a role only when it carries distinct information. Test representative bright, dark and textured frames.
- Select fonts by language coverage, license, weight range, renderer support and small-screen legibility; use at most one display and one utility family with deterministic fallbacks.
- Niche is an input to tone, not a fixed palette. Map the brief to qualities such as warm, technical, playful, restrained or documentary, then choose project tokens.
- Verify family resolution, glyph fallback, line breaks, clipping, safe areas, dwell, contrast and color conversion on the final render.
- Record selected font files and tokens in the project receipt for reproducible rerenders.
