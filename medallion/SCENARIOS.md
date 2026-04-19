# Shielded Scout-Rush Scenarios

Every turn, dump all MP as scouts on the trajectory that best combines:
1. **Shield gain** — path passes through our upgraded-support auras (range 12)
2. **Enemy support damage** — path tiles where an enemy support is the closest
   enemy structure in scout attack range (3.5)
3. **Survivability** — minimize cumulative enemy turret damage along path

## Score formula

    score = (path tiles where enemy support is closest target within 3.5) × 8
          - (sum of enemy turret damage taken along path)

Pick the bottom-edge tile with max score that reaches an enemy edge.

Shielding is dropped from the score — upgraded supports have range 12, which
covers basically every trajectory through our half, so shielding is effectively
a constant and doesn't help discriminate between spawns.

## Why supports at y=10/y=11

Upgraded support shield range = 12 (euclidean). With back supports at y=10,
shields reach up to ~y=22 — well past midline. Scouts keep a shield buffer
through the enemy's turret zone, reaching enemy supports at y=14-16.

With 4 upgraded supports, a scout passing through all 4 auras absorbs up to
16 shield (4 × 4), bringing effective HP to 31 (vs base 15).

## Trajectory selection (FRONT vs FLANK)

The algo doesn't hardcode FRONT vs FLANK — the score naturally biases:

- **Enemy front-center fortified, weak flanks** → flank path wins (more
  distance near enemy supports with less turret damage taken)
- **Enemy flanks fortified, weak center** → direct center path wins
- **No enemy supports yet** → enemy-support term = 0, scoring degrades to
  "shield aura pass + safe path", still useful as a scout rush

## Implementation

- `_best_shielded_scout_spawn(game_state)` in `algo_strategy.py`
- Called every turn when MP ≥ 1
- Returns `[x, y]` bottom-edge spawn tile

## Tuning knobs

| Constant | Default | Meaning |
|----------|---------|---------|
| `WEIGHT_ENEMY_SUPPORT_TILE` | 8 | Scout-damage value per frame against a support target |

## Notes

- Scouts fire at CLOSEST enemy structure in range. If a wall or turret is
  closer than a support, damage goes there instead — scoring reflects this
  via the "closest is support" per-tile check.
- Scouts die quickly (15 HP base, 31 with 4 shields). Scoring assumes scouts
  survive full trajectory — real outcome lower but relative ranking stays valid.
- Paths that self-destruct (don't reach enemy edge) are skipped.
