# Shop, projectile rendering and DNS acceptance — 2026-09-07

## Scope and results

- Reused the existing Sites project and public custom URL `https://game.jkesbyebye.com`.
- Bluehost cleanup: backed up 12 original editable records, restored the missing required `game` CNAME, removed 10 unrelated records. The final editable table has one CNAME and two game verification TXT records. NS/SOA infrastructure remains intact. Root Google TXT deletion received explicit additional user authorization after automatic approval review requested it.
- `dns-before-20260907.json` contains the original records and SRV port/priority/weight. `dns-after-20260907.json` records successful authoritative DNS verification of the three retained records and absence of all removed host/type pairs.

## Implementation

- All 20 weapon cards have distinct geometry and palette, explanations, category, targeting/fire mode, effective damage, fire rate/interval, range, reload/ammunition or lock/projectile statistics.
- Shop and held weapon use the same model factory, colors, source pattern textures and equipped attachment geometry. Armor previews cover all six armor models; all three turret models also match their battlefield factory.
- Upgrade and attachment previews are resolved by the Python gameplay rules. Player upgrades explain base health and regeneration allowance; each weapon upgrade names its owning weapon. Success notices require an actual `applied` transaction result.
- Color/pattern preview supports combinations and restoration without spending coins. One shared preview renderer produces image snapshots and keeps at most 64 cached previews; it is disposed on leaving the shop.
- Missile/rocket snapshots expose their actual forward vector. Nose direction is aligned with the reflected world velocity. Trails store only actual world positions, are bounded to 24 samples/0.18 seconds, freeze with simulation time and are disposed with the projectile.
- Instant traces are restricted to hitscan attacks, including every shotgun pellet. Homing missiles and rockets no longer draw contradictory instantaneous lines to their destinations.
- Turret heads aim at the actual target center. If a first shot kills and removes a target, the shot event endpoint preserves that frame's aim.

## Validation

- `pnpm test`: 8 control tests, original Pyodide integration scenario, 7 existing adapter tests and 7 new armory/projectile tests all passed.
- New tests exercise all weapon metadata/models, 48 upgrade transactions, attachment installation/replacement/removal, rejected purchases, player/armor health changes, actual homing simulation frame displacement versus rendered nose direction, tracer classification, snapshot fields, and a T02 first-shot kill against a side target.
- TypeScript check and production build passed. Existing bundler notices for the Three.js chunk size and route classification remain informational.
- Independent small-AI code review PASS: 20 models, 48 upgrades, 76 attachment installs, 76 removals, 16 same-slot replacements, bounded trail lifecycle and the turret instant-kill edge case.
- Independent Chrome UI review PASS: 20/20 distinct loaded weapon previews; W01/W03/W17 workshop explanations, prices and deltas; combined cosmetic preview/reset; six armor and three turret previews; player upgrade; desktop and 390×844 narrow layout. Fixed header occlusion was rechecked after making the menu header opaque.
- Root IAB check confirmed all 20 previews loaded, no horizontal overflow and the shared W01 model displayed in a normal battle. An attempted manual AA play session ended in an ordinary defeat; no claim is made that its missile flight was visually observed.

## Limits

Browser tests used local zero-coin profiles and normal UI only. Purchases, upgrades and detailed flight/collision consistency were tested offline through the real Pyodide adapter/rules, without changing browser save data or adding test cheats. This is scoped AI acceptance, not a claim that every campaign, device or long-duration performance condition was tested.

## Publication

- Source: `635d5d2e8ca02904033ceebc0397ce562eb3db69`, pushed to the existing Sites source repository.
- Saved version: 4 (`appgprj_6a9eafb956ac8191b8edb17687af6668~appgver_30feb8ef7de4819191ae557c25650cf7`).
- Deployment: `appgdep_6a9ecfedd4a08191929d3a095b88a698`, succeeded at 2026-09-07 14:53:48 UTC, existing public audience retained.
- Post-publication verification: custom homepage and `bridge.py` returned HTTPS 200; live bridge includes the new shop details, explicit transaction result and turret endpoint fix.
- The existing in-app Site tab was navigated to `https://game.jkesbyebye.com/`. The Codex panel handoff was queued because the calling task was not the focused task.
