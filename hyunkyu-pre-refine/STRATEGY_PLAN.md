# C1 Terminal Strategy Plan

## Design Philosophy

**Funnel + Shielded Rush.** Build a wall-based funnel that forces enemy mobile units through
a long zig-zag kill corridor lined with upgraded turrets, then launch shielded scout rushes
down the least-defended path when MP accumulates.

Key principles from the ruleset:
- Walls cost 2 SP / 50 HP -- use as funnel structure, not meat shields
- Upgraded turrets: 20 damage, 3.5 range -- the primary kill mechanism
- Upgraded supports: range 12, shield 4 + 0.3*Y -- place deep (low Y) for massive shields
- Scouts: 1 MP, fast -- our main scoring unit, stack them for overwhelming numbers
- Interceptors: 3 MP, 60 HP -- escort scouts or defend early game
- SP-from-damage feedback: if enemy scores, they snowball. Never leak early.
- Zig-zag pathing preference: exploit to maximize time in kill zones

---

## Architecture: Three-Phase Game Plan

### Phase 1: Early Defense (Turns 0-4)
**Goal:** Survive without leaking. Spend all SP on defense; stall with interceptors.

**Build order (Turn 0, 40 SP budget):**

Priority 1 - Corner turrets (6 SP):
  [0, 13], [27, 13] -- Protect the two corners where enemy units cross into our half

Priority 2 - Core turrets along the funnel (9 SP):
  [4, 12], [13, 11], [14, 11], [23, 12] -- Central coverage

Priority 3 - Funnel walls (remaining SP, ~2 SP each):
  Front wall line at y=13 with strategic gaps:
    [1, 13], [2, 13], [3, 13], [4, 13], [5, 13], [6, 13], [7, 13]  -- left wall
    [20, 13], [21, 13], [22, 13], [23, 13], [24, 13], [25, 13], [26, 13] -- right wall
  Leave gap around x=8-19 initially (close progressively)

  Protective walls in front of mid turrets:
    [4, 12] gets wall at [5, 13] (already in wall line)
    [23, 12] gets wall at [22, 13] (already in wall line)

**Mobile units (5 MP):**
  Deploy 1-2 interceptors at random edge locations to intercept early scouts.

**Turns 1-4:**
  - Fill remaining wall gaps at y=13
  - Add walls at [8, 12] and [19, 12] to tighten funnel
  - Begin upgrading corner turrets ([0, 13], [27, 13]) -- 8 SP each
  - Continue interceptor stalling

### Phase 2: Fortification + Support Setup (Turns 5-9)
**Goal:** Complete the kill corridor. Add upgraded supports for offense prep.

**Defense completion:**
  - Upgrade turrets at [13, 11] and [14, 11] -- these are the core killers
  - Add second-row walls at y=12 to create serpentine:
    [9, 12], [10, 12], [11, 12], [12, 12]  -- left inner wall
    [15, 12], [16, 12], [17, 12], [18, 12] -- right inner wall
  - This forces a zig-zag through the center past upgraded turrets

**Support placement (deep backfield for Y-bonus):**
  [13, 2], [14, 2] -- shield = 4 + 0.3*2 = 4.6 each
  Upgrade when affordable (4 SP each) -- range jumps to 12, covers our entire attack path

**Offensive scouting:**
  - Use `find_path_to_edge` to simulate attack paths from [13, 0] and [14, 0]
  - Use `get_attackers` along paths to estimate damage
  - Track enemy structure placement to identify weak side

### Phase 3: Shielded Scout Rush (Turns 10+)
**Goal:** Score damage with massive scout stacks shielded by upgraded supports.

**Attack timing:**
  - MP grows: 6/turn at 10-19, 7/turn at 20-29, etc.
  - Attack on even turns when MP has accumulated (save across 2 turns)
  - Minimum attack threshold: 10+ scouts (10 MP)

**Attack execution:**
  1. Simulate paths from both sides using `find_path_to_edge`
  2. Calculate damage along each path using `get_attackers`
  3. Deploy all scouts from the least-damaged side
  4. If supports are upgraded and in range, scouts get +4.6 shield each

**Alternative: Demolisher line (conditional)**
  - If enemy has >10 structures near their front (y=14-15):
    Build cheapest unit line at y=11 to prevent demolishers from advancing
    Spawn demolishers at [24, 10] to snipe enemy front-line structures
  - This softens defenses for a follow-up scout rush

---

## Adaptive Behaviors

### Breach Tracking
Track all locations where enemy scores via `on_action_frame` breach events.
Build reactive turrets at [breach_x, breach_y + 1] to plug gaps.

### Enemy MP Prediction
Use `project_future_MP(turns, player_index=1)` to predict enemy attack timing.
When enemy MP is high (>15), preemptively deploy interceptors at vulnerable edges.

### Attack Side Selection
Each turn, evaluate both spawn sides:
- `scout_spawn_options = [[13, 0], [14, 0]]` (plus adjacent edge tiles)
- For each option, simulate path and sum turret damage along path
- Choose the side that takes the least damage

### Dynamic Wall Repair
After enemy demolisher attacks, check for missing walls and rebuild.
Wall locations are tracked in a priority list -- highest priority rebuilt first.

---

## Key API Usage

| Method | Purpose |
|--------|---------|
| `game_state.attempt_spawn(UNIT, locations)` | Place structures or mobile units |
| `game_state.attempt_upgrade(locations)` | Upgrade structures in place |
| `game_state.attempt_remove(locations)` | Remove own structure for SP refund |
| `game_state.find_path_to_edge(loc)` | Simulate unit pathing |
| `game_state.get_attackers(loc, player)` | Get turrets threatening a location |
| `game_state.get_resource(MP/SP)` | Check current resources |
| `game_state.project_future_MP(turns)` | Predict future MP |
| `game_state.number_affordable(unit)` | Check how many units we can buy |
| `game_state.contains_stationary_unit(loc)` | Check if location is blocked |

---

## Resource Budget Model

| Turn | SP Income | Cumulative SP | MP Income | Notes |
|------|-----------|---------------|-----------|-------|
| 0    | 40 (start)| 40            | 5         | Build core defense |
| 1    | 5         | ~45           | 5         | Fill walls |
| 2    | 5         | ~50           | 5         | Start upgrading |
| 5    | 5         | ~65           | 5         | Supports online |
| 10   | 5+bonus   | ~90+          | 6         | Rush-ready |
| 20   | 5+bonus   | varies        | 7         | Full economy |

---

## Win Condition

Group stage: beat median opponents by not leaking (strong defense) and scoring
opportunistically with shielded scout rushes. Don't need to be flashy -- just consistent.

Finals: if we can identify opponent patterns, adapt attack timing and side selection.
The adaptive behaviors above handle this automatically.
