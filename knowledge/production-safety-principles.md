# Public production safety principles

This file contains generic release-safe production rules. It is not a runtime
memory, creator profile, incident log, analytics ledger, or record of human
review outcomes. Each installation learns its own preferences under `data/`
and `knowledge/runtime/state.json` after installation.

## Evidence integrity

- Do not invent metrics, product names, locations, quotes, or achievements.
- A number shown on screen must come from an authorized source capture or be
  clearly labelled as an estimate.
- Do not reconstruct another person's dashboard or results as if it were
  direct evidence.

## Privacy

- Treat notifications, private messages, unrelated tabs, account identifiers,
  local paths, and background windows as sensitive.
- Crop or re-record unsafe screen footage before editing; do not rely on a
  last-minute blur as the only control.
- A guest's material requires an explicit on-screen allowlist and review.

## Readability and media QA

- Derive captions from visible or audible evidence and keep persistent labels
  separate from the sentence-caption lane.
- Use licensed fonts with verified glyph coverage; render emoji as licensed
  image assets when the subtitle renderer lacks glyphs.
- Select music from an energetic usable section, then control dynamics and
  loudness without masking speech.
- Preserve one readable focal hierarchy and verify the delivered render on a
  phone-sized preview.

## Runtime boundary

These principles guide public defaults only. Project incidents, creator taste,
review quotes, timestamps, outcome values, and contradiction evidence remain
local and must never be copied into a public release.
