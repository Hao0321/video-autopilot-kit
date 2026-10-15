# 3D character audit (provisional)

Read the [full rules](character-3d-audit-detail.md) first; evidence and limits stay there.

- `cleanup.character.evidence`: Hashes; native parity.
- `cleanup.character.texture`: UV coverage, views, rights.
- `cleanup.character.uv-storage`: Reloaded float32 UV collapse.
- `cleanup.character.uv-fragmentation`: Charts vs geometry; chart image.
- `cleanup.character.hair-uv-pilot`: Reject cap/strand degeneracy.
- `cleanup.character.hair-orientability`: Fan-free is not orientable.
- `cleanup.character.component-hybrid-uv`: Cold atlas; paintability.
- `cleanup.character.triangle-chart-hair`: Triangle IDs; quad splits.
- `cleanup.character.hair-orientation-cut`: Orientable is not wound.
- `cleanup.character.hair-two-sided`: One-sided culling; scalp.
- `cleanup.character.render-uv`: Source/bake/render UV channels.
- `cleanup.character.ai-atlas`: Exact size; pixel registration.
- `cleanup.character.ai-detail-layer`: Cloth/skin masks; tiling.
- `cleanup.character.part-registration`: Registered part bounds.
- `cleanup.character.ornament-visibility`: Motif contours, not grain.
- `cleanup.character.scope-override`: Latest user density.
- `cleanup.character.registered-current`: Builds trace to CURRENT pin.
- `cleanup.character.head-uv-standard`: Face, back, two ear charts.
- `cleanup.character.uv-transfer-sharpness`: Close-up A/B after rebake.
- `cleanup.character.closure`: Rights/privacy/runtime gaps open.
- `cleanup.character.npr`: Native normals, outline, light, motion.
- `cleanup.character.material-persist`: Cold UE material readback.
- `cleanup.character.repair`: Boundaries, corners, native seams.
- `cleanup.character.rig-guide`: Real rig/weights; native physics.
