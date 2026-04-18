# v1 Features

New behavior added on top of v0 (the `hyunkyu-copy-wall-v0` baseline).

## Overview

v1 adapts to the enemy instead of running a fixed plan. It tracks game events,
scales supports up to 4 based on signals, prioritizes turret upgrades against
shielded scouts, and switches between scout / demolisher / defensive attack modes
depending on context.

## 1. Event Tracking (`on_action_frame`)

Two counters populated each action frame, committed to history at the start of
the next turn:

| Attribute | Meaning |
|-----------|---------|
| `damage_dealt[]` | Breaches WE caused per turn (how many of our scouts scored) |
| `damage_taken[]` | Breaches enemy caused per turn (how many of their units scored) |

These power every adaptive decision below.

## 2. Adaptive Support Count (2 → 3 → 4)

`determine_support_target()` picks how many supports to place based on **signals**,
not a hard turn schedule. Turn number is a FLOOR only — it can push the count up,
never down.

**V-arm gate:** support escalation (3rd/4th) is gated on having at least
`V_ARM_GATE_FOR_SUPPORTS = 6` V-arm turrets already built. This prevents early-game
SP diversion away from V-arms, which hurts defense more than supports help offense.
Front-line turret upgrades share the same gate.

Baseline: **2 supports** at `[13,12]` and `[14,12]` (placed + upgraded turn 0).

**Escalate to 3 when:**
- Enemy has ≥ 8 turrets, OR
- Avg damage dealt in last 2 turns < 5

**Escalate to 4 when:**
- Enemy has ≥ 12 turrets, OR
- Avg damage dealt in last 3 turns < 5

**Turn floors (safety net):**
- Turn ≥ 20 → at least 3 supports
- Turn ≥ 40 → at least 4 supports

Extra supports are placed at `[13,11]` and `[14,11]` (stacked behind the core two).
Each support is upgraded the same turn it's placed.

## 3. Front-Line Turret Upgrades (new priority)

`[13,13]` and `[14,13]` (the center y=13 turrets) are upgraded right after supports.
Rationale: base turrets (6 dmg) can't kill shielded scouts fast enough. Upgraded
turrets (20 dmg, 3.5 range) one-shot most shielded scouts.

Priority order in `build_defense`:

1. Urgent corner walls (if breached)
2. y=13 turret pairs (6 turrets)
3. y=12 center turrets + 2 core supports + upgrades
4. 3rd/4th supports (adaptive) + upgrades
5. **Front-line turret upgrades** [13,13],[14,13]
6. Temp center turrets (turn 0-4 only)
7. V-arm turrets (breach-priority order)
8. Corner walls (if not already built)

## 4. Adaptive Offense Modes (`execute_attack`)

Three modes, checked in order:

### Mode A — DEMOLISHER (enemy has many supports, scouts failing)

Conditions (ALL must be true):
- Enemy supports ≥ 3
- Avg damage dealt in last 2 turns < 4
- Our HP ≥ 15
- No breach against us in the last turn (defense stable)

If conditions met:
- MP ≥ 12: launch 4 demolishers via `launch_demolishers()`
- MP < 12: save MP silently (no spawn this turn)

### Mode B — DEFENSIVE (enemy saving MP for big push)

Trigger: enemy MP ≥ 15 **AND** enemy spawned 0 mobile units last turn.

Both signals are required. MP alone isn't enough — in mid/late game, normal
scout-every-turn enemies can hover around MP 10+ due to MP cap ramping. We need
to confirm the enemy actually skipped attacks (saving for a bigger push).

Action:
- Deploy 1 interceptor at `[13,0]` or `[14,0]` to meet incoming scouts
- Still spawn 5 scouts for counter-pressure

### Mode C — SCOUT (default)

Spawn 5 scouts at `best_spawn_location()` (least damage + shortest path + weakest
flank scoring).

## 5. Demolisher Launch with Zig-Zag Walls

`launch_demolishers()` places temporary walls at `[11,11]` and `[16,11]` to narrow
the center corridor. Walls are marked for removal the same turn so 75% SP is
refunded next turn (net cost ~2 SP).

4 demolishers spawn from the best edge location. Math for expected damage:

| Enemy defense | Survival | Dmg/demolisher | Total (4x) |
|---------------|----------|----------------|------------|
| Upgraded turrets | 2 frames | ~16 | ~64 dmg |
| Base turrets | ~6 frames | ~48 | ~192 dmg |

Zig-zag walls mostly help against base (unupgraded) enemies — forcing lateral
movement keeps demolisher fire concentrated on front structures.

Against upgraded defense, demolishers function as attrition — weaken enemy front
line over multiple pushes rather than destroying it in one go.

## 6. Defensive Interceptor (`deploy_defensive_interceptor`)

Triggered when enemy MP ≥ 10 (they're saving for an attack).

Spawns 1 interceptor at center-bottom to intercept enemy scouts routing through
the center corridor. Cost: 3 MP.

## 7. Corner Walls — Block Detection + Removal

**Block detection regions** (any enemy structure here → corner blocked):
- Left: `[0,14]`, `[1,14]`, `[2,14]`, `[1,15]`
- Right: `[27,14]`, `[26,14]`, `[25,14]`, `[26,15]`

**Behavior:**
- If enemy blocks the corner approach → **remove** our corner walls (75% SP refund)
- If no block AND we were breached at that corner → **urgent rebuild** (priority above V-arms)
- Otherwise → **default low priority** build after V-arms

## File Structure

```
hyunkyu-copy-wall-v1/
├── algo_strategy.py    # Main algo (all v1 logic)
├── V1_FEATURES.md      # This file
├── MY_LAYOUT.md        # Original layout spec (inherited)
├── STRATEGY_PLAN.md    # Original strategy plan (inherited)
├── ROUND_DIAGRAMS.md   # Original round diagrams (inherited)
└── gamelib/            # Game library (inherited)
```

## Tuning Constants

Defined at the top of the `AlgoStrategy` class — tweak these without diving into
method logic:

| Constant | Default | Meaning |
|----------|---------|---------|
| `CORE_SUPPORTS` | `[[13,12],[14,12]]` | Baseline 2 supports |
| `EXTRA_SUPPORTS` | `[[13,11],[14,11]]` | 3rd and 4th support positions |
| `FRONT_TURRETS` | `[[13,13],[14,13]]` | Turrets to upgrade early |
| `ZIGZAG_WALLS` | `[[11,11],[16,11]]` | Temp walls during demolisher push |
| `DEMOLISHER_COUNT` | `4` | Demolishers per launch |
| `DEMOLISHER_MP_THRESHOLD` | `12` | Min MP to launch (saves if below) |
| `ENEMY_MP_SAVE_SIGNAL` | `15` | Enemy MP level considered "saving" (combined w/ spawn check) |

## Resource Mechanics Notes

MP formula (for future projections):
```
MP_next = MP_current × 0.75 + income
  where income = 5 + (turn // 10)
```

SP: flat +5/turn income, +1 per damage dealt via breach (from `coresForPlayerDamage`).

Note: the shipped `game-configs.json` originally had `generatesResource1/2` nonzero on supports (making them generate MP/SP passively). Those fields were zeroed out in our local config so testing matches expected behavior. If you pull a fresh copy of `game-configs.json`, re-apply the zeros or expect different MP math.

## Known Limitations

- **Demolisher can't one-shot 4 supports** if they're protected by upgraded front
  turrets. Expected ~64 dmg per push against upgraded defense; treat as attrition.
- **Damage tracking is breach-count based** — doesn't count hits our units land on
  enemy structures. Good enough as a signal but not a full damage ledger.
- **Support placement at `[13,11]`/`[14,11]`** blocks center y=11. Scouts route
  around via `[11-12,11]` or `[15-16,11]`. Support range (12 upgraded) still
  shields them.

## Migration Notes from v0

| v0 behavior | v1 behavior |
|-------------|-------------|
| Fixed 2 supports, always | 2/3/4 supports based on signals |
| No turret upgrades (except corners) | Front-line upgrades priority |
| Always 5 scouts | Scout / demolisher / interceptor based on scenario |
| Interceptors disabled | Re-enabled for defensive response only |
| Single corner wall policy | Emergency rebuild if breached |
