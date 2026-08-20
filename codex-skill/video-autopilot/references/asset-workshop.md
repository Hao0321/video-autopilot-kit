# Asset Workshop

## 導航 / Navigation

- Purpose／reality hierarchy／production loop
- Icon boundary／mobile delivery／Hao taste override
- VFX plate routing／asset classes／hard gates／expansion targets

## Purpose

Turn one-off generation into a governed production system. Maintain separate reality, photoreal-assist and graphic layers; generate reusable atoms before full-frame cards, register only verified assets, and keep generation cost, token use, licensing and visual fatigue visible.

## Reality hierarchy

1. Real project footage, recorded production sound and verified screenshots/documents.
2. Licensed real stock or deliberately captured generic B-roll with known provenance.
3. Synthetic photoreal cutouts/plates and pre-rendered 3D for illustration, scale or transition setup; label `illustrative_not_evidence`.
4. Graphic atoms, HUD, typography, particles and textures as overlays. Non-real editorial illustration is limited to travel, food and cafe.
5. Clean hold when none of the above is semantically honest.

High-information challenge editing is not a cartoon style. Real subjects and environments carry the promise; graphics clarify value, location, state, comparison and progress. Never let a sprite atlas become the main footage language.

## Production loop

1. Run `python asset_workshop.py plan` and read only `assets/workshop/production_plan.json`.
2. Query `asset_registry.py` first. Create a job only when the semantic role or domain has insufficient approved variety.
3. Create one 4-8 frame taste board first. Bulk generation is blocked until Hao approves the style family.
4. Define one batch as a single asset family: photoreal object, VFX plate, pre-rendered 3D element, Japanese-lifestyle travel/food illustration, background or texture.
5. Use the built-in Imagegen path. Ask for isolated subjects, stable cell order, no text/logos and transparency. Only an approved style may expand to a 4x4 atlas.
6. Ingest the atlas with `asset_workshop.py ingest-atlas`; do not hand-copy files or invent metadata later.
7. Run `asset_workshop.py audit`, inspect `catalog-preview.webp`, then review the batch with `review-asset-batch`. Pending and `needs_edit` assets stay out of automatic selection; rejection removes the atlas, split atoms and manifest rows together.
8. Register approved atoms through the virtual registry. Record real usage only after the asset appears in an exported cut.
9. Derive animation from approved atoms: pop/settle, tracked pin, parallax, orbit, masked sheen, scan sweep, particle burst or reveal. A generated still is not automatically a transition.
10. Review performance and fatigue every 20 published videos. Delete rejected batches, orphan derivatives and exact duplicates; quality has priority over library size.

## Icon boundary

- An icon is a UI annotation, not footage, B-roll, a narrative subject or a missing-shot substitute. Exclude icons from narrative asset coverage and library-size claims.
- Use one solid colour, a flat fill, a minimal silhouette and a clear outline at small sizes. Block gradients, realistic shading, faux 3D, multi-colour stickers, decorative clutter and mixed visual languages.
- Keep icons in the `minimal_monochrome_icon` role with `coverage_credit=ui_annotation_only`. Human approval is still required.
- A taste board calibrates style only. Never split it into many icon-like cells and call the resulting count a production asset library.
- Hao rejected the 2026-08-13 32-item icon-like batch at score 0. Do not regenerate that implementation or use it as a positive example.

## Mobile delivery completion gate

- Treat every created or revised visual asset as unfinished until Hao can open the authoritative media from a phone outside the local filesystem.
- Run `python scripts/hao_autopilot.py review deliver "<asset-or-folder>" --content-id "<id>" --bundle-dir "<work-dir>/_review"`. This single transaction creates the review bundle, starts the detached secret HTTPS tunnel and verifies the public review page plus byte-range media route.
- Put the verified HTTPS review URL first in the handoff. A Windows path, local HTML file, catalog preview or contact sheet is supporting information only and never satisfies delivery.
- Keep the computer and tunnel online while Hao reviews. The page records per-asset approve/redo decisions and comments in `review.json`; pending assets remain ineligible for automatic selection.
- Review decisions and issue comments must autosync to `review.json` when Hao taps them; the final submit button is only an explicit completion marker, never the sole persistence path. This prevents valid phone annotations from remaining trapped in browser local storage.
- If tunnel startup or public verification fails, stop the partial session and report the visual task as not yet delivered. Do not claim completion.
- After Hao says the review is finished, run `review remote-stop`. Runtime session/log files remain inside `_review`; authoritative assets and review decisions are preserved.

## Hao taste override: calm Japanese lifestyle

- Non-real editorial art is allowed only for travel, food and cafe.
- Direction: Japanese lifestyle magazine / restrained Muji-like calm, warm off-white paper, natural wood and linen, low-saturation earth colours, daylight, generous negative space, small hand-drawn local marks and relaxed pacing.
- Use real destination and food photography as the hero. Illustration may frame a route, ingredient, diary note or breathing beat; it cannot replace proof.
- Avoid neon HUD, glossy game UI, generic 3D badges, hard cyber gradients, dense sticker walls, fake cultural symbols and loud motion without a story beat.
- AI, technology, toy, automotive and business routes default to real footage, licensed stock, honest screencast, photoreal composite or clean hold.

## Black/white VFX plate routing

- Black-background light, fire, sparks, smoke and energy: retain the original master and default to `Screen` or `Add`. Convert to alpha only for occlusion, tracking or multi-layer composites.
- White-background ink, speed lines and dark line art: default to `Multiply`. Convert to alpha for coloured subjects or transparent delivery.
- `vfx_keyer.py` creates straight-alpha PNG or ProRes 4444 derivatives with a soft luma/colour matte. Never overwrite the source plate.
- Inspect the matte at 100% for black/white fringe, clipped smoke, colour spill and premultiplication halos before registration.

## Functional benchmark translation

- High-information challenge editing: rapidly readable value, state, location, comparison, progress, reveal and payoff.
- Cinematic craft: material consistency, subject integration, motivated light, sound-design cue, shot-match and contrast rests.
- Do not copy creator logos, exact typography, branded UI, layouts, characters or proprietary footage. Learn the function and rebuild an original Hao visual language.

## Asset classes

| Class | Use | Required metadata |
|---|---|---|
| `vfx_overlay` | sheen, scan, shockwave, dust, sparks | blend/matte intent, energy, alpha |
| `prerendered_3d` | glass cards, podiums, HUD objects | capability label, view limit, alpha |
| `photoreal_cutout` | realistic generic objects and hands | synthetic disclosure, evidence ban, alpha |
| `japanese_lifestyle_illustration` | calm travel/food diary support | travel/food/cafe only, style approval, alpha |
| `background` | breathing/title field | aspect, safe areas, loop/hold rules |
| `texture` | paper, halftone, grain, scan | blend mode, scale, fatigue family |
| `minimal_monochrome_icon` | UI label, location, state or category cue | one solid colour, flat silhouette, UI-only coverage |

## Hard gates

- Numeric claims, locations, product specs, results and proof must come from verified project sources. Workshop assets may frame proof, never impersonate it.
- Synthetic photoreal assets must carry `truth_label=illustrative_not_evidence`; do not name a generated location, product model, price or experiment result as real.
- `prerendered_3d` means a raster element with a fixed camera; it is not a mesh, camera solve or true 3D scene.
- Subject sheen requires a real subject matte and track. The generated light plate alone cannot authorize the effect.
- No pending human-review asset may be selected automatically; no rejected batch may remain in the working library.
- Bulk generation before taste-board approval is blocked.
- Exact duplicates, missing provenance, unusable alpha, unsafe crop, unreadable silhouette and private/unlicensed material block registration.
- Backgrounds cannot be inserted just to hide missing footage. Use clean hold when no semantically correct asset exists.
- Icons cannot satisfy a footage, subject, proof, B-roll or narrative-coverage gap.

## Expansion targets

There is no minimum asset quota. Maintain enough approved variety for actual recurrent gaps, then stop. Expand only a proven lowest-coverage family; delete rejected and fatigued families. Produce landscape and portrait compositions from components rather than duplicating every atom by aspect.

## Hao motion-review calibration — 2026-08-13

- Contact sheets are internal QA evidence, not a default phone-review deliverable. Use them for frame coverage, privacy, tracking drift and matte edge inspection. Deliver the playable motion asset first; include a contact sheet only when cross-frame comparison is the actual review question, and explain its purpose in plain language.
- The USD note particle preview was explicitly approved by Hao. Keep it as a standalone value/prize overlay with known context; approval does not authorize inserting money into unrelated toy footage.
- The first gold-coin motion batch was rejected because oversized particles blocked the frame. Gold coins are supporting punctuation: cap the pre-rotation coin width at 7.8% of the short edge, total frame alpha coverage at 12% and centre-safe-area coverage at 10%. Use more small depth layers instead of a few giant foreground coins; any violation is ineligible for automatic selection.
- The paired portrait/landscape gold-coin horizontal sweeps were rejected as physically strange. Rigid coins must not enter from both sides and cross the subject-safe centre like a wipe. Use edge-safe lower-corner tosses with gravity, bounded inward velocity and natural fade instead; movement semantics are reviewed independently from particle size.
