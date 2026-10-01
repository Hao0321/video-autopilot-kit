# Visual-quality audit (provisional)

Read for user-facing visual/UI/material/art work. Audit remains read-only;
implementation and polish are owned by R&D's
[visual workflow](../../../run-benchmark-driven-rd/references/topics/visual-quality.md).

- `cleanup.visual.contract`: find the project's art direction, refinement default,
  viewing scales and resource budget. Respect explicit rough/debug/minimal work;
  do not demand decorative detail for a backend-only change.
- `cleanup.visual.evidence`: distinguish diagnostic geometry, generated concepts,
  actual renderer output, internal review and human approval. Check source/build/
  settings identity and before/after images. Functional PASS or increased pixels,
  bloom or shader counts cannot replace aesthetic review. Missing native/art
  evidence is NOT_CHECKED; visible defects or subjective approval need REVIEW.
- `cleanup.visual.scope`: inspect relevant contour/alpha, hierarchy, material,
  lighting, scale/readability and motion evidence. Keep GPU cost independent from
  appearance and list unresolved issues. Never repaint, approve, publish or enable
  expensive services from an audit. Reciprocally reference the workflow's local
  record visual-polish-default-20260908; do not copy private artifacts into skills.
