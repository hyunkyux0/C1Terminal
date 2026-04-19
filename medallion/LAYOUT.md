# Medallion Structure Layout

Diamond arena. Our half: y=0 (bottom, 2 cells) → y=13 (top/midline, 28 cells).

Valid x range per y:

| y  | valid x | cells |
|----|---------|-------|
| 13 | 0..27   | 28 |
| 12 | 1..26   | 26 |
| 11 | 2..25   | 24 |
| 10 | 3..24   | 22 |
| 9  | 4..23   | 20 |
| 8  | 5..22   | 18 |
| 7  | 6..21   | 16 |
| 6  | 7..20   | 14 |
| 5  | 8..19   | 12 |
| 4  | 9..18   | 10 |
| 3  | 10..17  | 8  |
| 2  | 11..16  | 6  |
| 1  | 12..15  | 4  |
| 0  | 13..14  | 2  |

---

## Design Instructions

Shielded scout-rush strategy. Every turn, dump all available MP as scouts on the
trajectory that (a) passes through the most of our upgraded-support shield auras,
and (b) routes close to enemy supports (scout attack range 3.5). This is the
"best of both worlds": the scouts score HP while chipping at enemy supports.
Defense is a dense 2×2 upgraded-support core pushed back to y=10/y=11 so the
shield aura (range 12) reaches deep into enemy territory, plus support-defense
turrets flanking the core.

### Goals
- 2×2 upgraded-support core at `[13,10][14,10][13,11][14,11]` — shield aura
  reaches y=22+ (enemy half) so scouts stay shielded past midline
- Support-defense turrets hugging the core: `[12,12][15,12]` in front,
  `[11,11][16,11]` on the flanks
- Walls at corners with block-check (carried from v1)
- Turrets preferred over walls everywhere else
- Symmetric across x=13.5

### Constraints
- Turn 0 budget: 40 SP
- Income: +5 SP/turn (plus breach bonuses)
- 4 upgraded supports reached by ~turn 3-4

### Trade-offs / rationale
- Walls only at corners (cheap blockers, don't need attack value at edges)
- Turrets everywhere else since turrets both block AND damage
- Supports pushed back to y=10/y=11 so shield range 12 covers deep into enemy
  half — scouts keep shields through the enemy's defense zone
- 2×2 block at center forces enemy scouts to flank; our SD turrets cover the flanks
- Center column is support-blocked; exit trajectories naturally flank

### Attack trajectory choice
Every turn, pick bottom-edge spawn maximizing:

    score = (path tiles where enemy support is closest target within 3.5) × 8
          - (sum of enemy turret damage taken along path)

Shielding isn't in the score — upgraded support range 12 from y=10/y=11 covers
nearly every trajectory through our half, so shielding is effectively constant
across spawn choices. Scouts pass through the aura either way; the picker's job
is purely trajectory-vs-damage-vs-enemy-supports.

---

## Starting Structure (Turn 0, 40 SP budget)

```
         x= 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27
 y=13:      . . . . . . . T . .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
 y=12:        . . . . . . . . .  .  T  .  .  T  .  .  .  .  .  .  .  .  .  .  .
 y=11:          . . . . . . . .  .  .  s  s  .  .  .  .  .  .  .  .  .  .  .
 y=10:            . . . . . . .  .  .  S  S  .  .  .  .  .  .  .  .  .  .
 y=9:               . . . . . .  .  T  .  .  T  .  .  .  .  .  .  .  .  
```

Structures:

| Row | Walls | Turrets | Supports |
|-----|-------|---------|----------|
| y=13 | — | `[7,13]` | — |
| y=12 | — | `[12,12]` `[15,12]` (SD — front of supports) | — |
| y=11 | — | — | `[13,11]` `[14,11]` (base) |
| y=10 | — | — | `[13,10]` `[14,10]` (upgraded) |
| y=9  | — | `[12,9]` `[15,9]` (rear guards) | — |

**SP breakdown:**
- 5 turrets × 3 = 15 SP (2 SD at y=12 + `[7,13]` + 2 rear guards at y=9)
- 4 supports × 4 = 16 SP
- 2 support upgrades (back y=10) × 4 = 8 SP
- **Total: 39 SP** (1 SP carried to turn 1)

No walls at turn 0 — shield aura + SD turrets take priority. Corner walls go
in via progressive once the aura is fully established. y=11 SD `[11,11]
[16,11]` are added early in progressive, not at start.

The 2×2 support block is already complete at turn 0. Back row (y=10) is
upgraded first — range 12 reaches y=22 (deep in enemy half). Front row (y=11)
upgrades happen early in progressive.

Symmetry: SD T 12↔15 (y=12); rear guards 12↔15 (y=9); supports 13↔14.
`[7,13]` is intentionally asymmetric (left-flank pressure).

---

## Final Structure (late game)

Support system shifted one y-row down from the prior design — back supports now
at y=10, front supports at y=11, SD turrets at y=11/y=12, rear guards at y=9.
This maximizes shield-aura reach into enemy territory.

```
         x= 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27
 y=13:      W T T T . . T T . . .  .  .  .  .  .  .  .  .  .  T  T  .  .  T  T  T  W
 y=12:        . . . T T . . . T .  .  T  .  .  T  .  .  T  .  .  .  T  T  .  .  .
 y=11:          . . . . . T . . .  T  .  s  s  .  T  .  .  .  T  .  .  .  .  .  
 y=10:            . . . . T . . T  .  .  s  s  .  .  T  .  .  T  .  .  .  .
 y= 9:              . . . . . . .  .  T  .  .  T  .  .  .  .  .  .  .  .
```

Structures:

| Row | Walls | Turrets | Supports |
|-----|-------|---------|----------|
| y=13 | `[0,13]` `[27,13]` (active, block-check) | `[1,13]` `[2,13]` `[3,13]` `[6,13]` `[7,13]` `[20,13]` `[21,13]` `[24,13]` `[25,13]` `[26,13]` | — |
| y=12 | — | `[4,12]` `[5,12]` `[9,12]` `[12,12]` `[15,12]` `[18,12]` `[22,12]` `[23,12]` | — |
| y=11 | — | `[7,11]` `[11,11]` `[16,11]` `[20,11]` | `[13,11]` `[14,11]` (upgraded) |
| y=10 | — | `[7,10]` `[10,10]` `[17,10]` `[20,10]` | `[13,10]` `[14,10]` (upgraded) |
| y=9  | — | `[12,9]` `[15,9]` (rear guards) | — |

Center y=13 `[8..19, 13]` is deliberately empty — opens the midline for our
scouts to exit through, while flank pairs `[6,13][7,13]` and `[20,13][21,13]`
punish enemy scouts that drift away from center.

### Counts & SP

| Item | Count | SP |
|------|-------|----|
| Walls (outer corners only) | 2 | 2 × 2 = 4 |
| Turrets | 28 | 28 × 3 = 84 |
| Supports | 4 | 4 × 4 = 16 |
| **Structures base** | | **104** |
| Support upgrades | 4 | 4 × 4 = 16 |
| SD turret upgrades (`[12,12][15,12][11,11][16,11]`) | 4 | 4 × 8 = 32 |
| **With core upgrades** | | **152** |

Reached around turn ~24-28 (5 SP/turn + breach bonuses).

### Symmetry check ✓
- y=13: W 0↔27; T 1↔26, 2↔25, 3↔24, 6↔21, 7↔20
- y=12: T 4↔23, 5↔22, 9↔18, 12↔15
- y=11: T 7↔20, 11↔16; S 13↔14
- y=10: T 7↔20, 10↔17; S 13↔14
- y=9 : T 12↔15

### Evolution (starting → final)

Starting has the 2×2 support block (`[13,10][14,10]` upgraded, `[13,11][14,11]`
base), y=12 SD turrets, `[7,13]` front-flank pressure, and y=9 rear guards.
Progressive adds (in order):

| Position | Action |
|----------|--------|
| `[11,11][16,11]` | y=11 SD turrets (core flank defense) |
| `[13,11][14,11]` | Upgrade front supports (SU) |
| `[20,13]` | Mirror of `[7,13]` — front-flank pressure |
| `[6,13][21,13]` | Front-flank secondary pair |
| `[3,13][24,13]` | Outer y=13 |
| `[2,13][25,13]` | Corner-adjacent y=13 pair |
| `[9,12][18,12]` | y=12 inner-flank |
| `[5,12][22,12]` | y=12 outer pair |
| `[4,12][23,12]` | y=12 outer edge |
| `[7,11][20,11]` | Outer y=11 flanks |
| `[10,10][17,10]` | y=10 inner forward turrets |
| `[7,10][20,10]` | y=10 outer forward turrets |
| `[1,13][26,13]` | Corner-adjacent turrets |
| `[0,13][27,13]` | Outer corner walls (active, block-check) |
| `[12,12][15,12][11,11][16,11]` | SD turret upgrades (late) |

### Dynamic priority (breach-reactive)

While building, bias toward side-specific reinforcement driven by BOTH:
- **Enemy mobile-unit spawn positions** (tracked via `on_action_frame`
  spawn events) — if enemy spawns ≥ N scouts on a flank over the last
  window of events, rush that side's defense pre-breach.
- **Our breach locations** (tracked via breach events).

| Trigger | Priority boost |
|---------|----------------|
| Enemy spawns ≥ 2 at x ≤ 3 (last 10 events) | Rush `[1,13][11,11][7,11][4,12][5,12][9,12][3,13][6,13][2,13][7,10][10,10][0,13]` |
| Enemy spawns ≥ 2 at x ≥ 24 | Mirror right-flank list |
| Breach near left edge (x≤3, y≥11) | Same left-flank rush |
| Breach near right edge (x≥24, y≥11) | Same right-flank rush |
| Mid-flank breach (x=4..7 or 20..23, y=11-12) | `[4,12][5,12][7,11][9,12]` / mirror |
| Center breach (x=8..19, y≥11) | `[9,12][18,12]` |
| Rear breach (y<10) | `[12,9][15,9]` |

Walls are never upgraded. Outer corners `[0,13] [27,13]` are **active** —
block-checked: if the enemy has a structure at `[0,14]` or `[27,14]` the
wall is useless and we remove for 75% SP refund. `[1,13] [26,13]` are
turrets, not walls.

---

## Notes

- **Legend:** `T` = turret, `W` = wall, `w` = upgraded wall, `s` = support, `S` = upgraded support, `.` = empty
- **Costs:** Wall 2 SP (+1 upgrade, 50→120 HP), Turret 3 SP (+8 upgrade, 6→20 dmg, 2.5→3.5 range), Support 4 SP (+4 upgrade, 3→4 shield/unit, 6→12 range)
- **Turn 0 budget:** 40 SP | **Income:** +5 SP/turn
- **Shield reach:** upgraded support at y=10 covers up to y=22 (deep into enemy half)
