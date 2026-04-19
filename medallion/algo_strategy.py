import gamelib
import random
import math
import warnings
from sys import maxsize
import json


class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        gamelib.debug_write('Configuring medallion strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0

        # Track breaches against us (for reactive defense + dynamic priority)
        self.scored_on_locations = []

        # Track enemy mobile-unit spawn x-positions across turns. Used to
        # identify which side the enemy attacks from and reinforce that
        # flank before they breach.
        self.enemy_spawn_xs = []

        # Unit type ids for mobile units (scout=3, demolisher=4, interceptor=5)
        # read lazily from config in on_turn so they're available early.
        self._mobile_type_ids = None

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Turn {}'.format(game_state.turn_number))
        game_state.suppress_warnings(True)
        self.strategy(game_state)
        game_state.submit_turn()

    # ==================================================================== #
    #  LAYOUT CONSTANTS (match LAYOUT.md)
    # ==================================================================== #

    # Outer corner walls are "active" — block-checked (removed if enemy
    # structure blocks the tile above, refunded 75% SP). Inner walls at
    # [1,13][26,13] are "passive" — placed once and kept, no block-check.
    CORNER_WALL_BLOCKERS = {
        (0, 13): [0, 14],
        (27, 13): [27, 14],
    }

    # Starting structures (turn 0, 39 SP / 40 budget). 1 spare for turn 1.
    # No walls at start — shields + SD turrets are the priority; walls go in
    # via progressive once the aura is fully up.
    #   5 turrets                           15 SP
    #   4 supports                          16 SP
    #   2 support upgrades (back y=10)       8 SP
    #   = 39 SP
    START_WALLS = []
    START_TURRETS = [
        [7, 13],                 # y=13 left-flank pressure (asymmetric, per layout)
        [12, 12], [15, 12],      # y=12 support-defense (front of supports)
        [12, 9], [15, 9],        # rear guards (behind back supports)
    ]
    START_SUPPORTS = [[13, 11], [14, 11], [13, 10], [14, 10]]
    # Only the back (y=10) supports upgraded at turn 0 — their shield range
    # 12 already reaches to y=22 (deep into enemy). Front (y=11) supports
    # upgrade in progressive.
    START_SUPPORT_UPGRADES = [[13, 10], [14, 10]]

    # Progressive build (starting → final). Complete the 2x2 support block
    # first (goal: 4 upgraded supports by ~turn 3-4), then front pressure
    # and outer reinforcement.
    PROGRESSIVE_BUILDS = [
        # PHASE 1 — Front line (y=13 and y=12). Build both sides fully
        # before touching y=11 or y=10 turrets.
        # y=13 mirror + outer + corner-adjacent turrets
        ('T', [20, 13]),                        # mirror [7,13]
        ('T', [6, 13]), ('T', [21, 13]),
        ('T', [3, 13]), ('T', [24, 13]),
        ('T', [2, 13]), ('T', [25, 13]),
        ('T', [1, 13]), ('T', [26, 13]),

        # y=12 inner, outer, outer-edge
        ('T', [9, 12]), ('T', [18, 12]),
        ('T', [5, 12]), ('T', [22, 12]),
        ('T', [4, 12]), ('T', [23, 12]),

        # Support upgrades (y=11 supports; y=10 already upgraded at start)
        ('SU', [13, 11]), ('SU', [14, 11]),

        # Outer corner walls — front-line complete
        ('W', [0, 13]), ('W', [27, 13]),

        # PHASE 2 — y=11 and y=10 turrets (deferred until front line done)
        ('T', [11, 11]), ('T', [16, 11]),       # y=11 SD
        ('T', [7, 11]), ('T', [20, 11]),        # y=11 outer
        ('T', [10, 10]), ('T', [17, 10]),       # y=10 inner forward
        ('T', [7, 10]), ('T', [20, 10]),        # y=10 outer forward

        # PHASE 3 — late SD upgrades
        ('TU', [12, 12]), ('TU', [15, 12]),
        ('TU', [11, 11]), ('TU', [16, 11]),
    ]

    # ==================================================================== #
    #  MAIN STRATEGY
    # ==================================================================== #

    def strategy(self, game_state):
        self._build_starting(game_state)
        self._build_reactive(game_state)
        self._build_progressive(game_state)
        self._execute_offense(game_state)

    # ==================================================================== #
    #  DEFENSE BUILD
    # ==================================================================== #

    def _build_starting(self, game_state):
        """Place turn-0 starting layout. attempt_spawn is idempotent."""
        for wall in self.START_WALLS:
            if self._wall_blocked(game_state, wall):
                game_state.attempt_remove([wall])
            else:
                game_state.attempt_spawn(WALL, [wall])
        game_state.attempt_spawn(TURRET, self.START_TURRETS)
        game_state.attempt_spawn(SUPPORT, self.START_SUPPORTS)
        game_state.attempt_upgrade(self.START_SUPPORT_UPGRADES)

    def _build_progressive(self, game_state):
        """Build toward final structure, breach-priority reordered."""
        ordered = self._reorder_by_breach_priority(list(self.PROGRESSIVE_BUILDS))
        for action, loc in ordered:
            self._attempt_build(game_state, action, loc)

    def _attempt_build(self, game_state, action, loc):
        if action == 'T':
            game_state.attempt_spawn(TURRET, [loc])
        elif action == 'S':
            game_state.attempt_spawn(SUPPORT, [loc])
        elif action == 'W':
            if tuple(loc) in self.CORNER_WALL_BLOCKERS:
                if self._wall_blocked(game_state, loc):
                    game_state.attempt_remove([loc])
                    return
            game_state.attempt_spawn(WALL, [loc])
        elif action in ('TU', 'SU', 'WU'):
            game_state.attempt_upgrade([loc])

    def _wall_blocked(self, game_state, wall):
        blocker = self.CORNER_WALL_BLOCKERS.get(tuple(wall))
        if not blocker:
            return False
        return game_state.contains_stationary_unit(blocker)

    # ==================================================================== #
    #  REACTIVE / DYNAMIC PRIORITY
    # ==================================================================== #

    def _build_reactive(self, game_state):
        """Reactive defense hook. Wall upgrades are NOT performed here —
        the user has explicitly opted out of upgrading edge walls. Left
        as a stub in case other reactive actions are wired in later.
        """
        return

    # Flank reinforcement on breach/spawn — build EDGE turrets first
    # (most-corner y=13 / y=12 positions), then progressively inward along
    # the front line. y=11 and y=10 turrets are deferred until the front
    # line (y=12 & y=13) is complete. Corner wall is the very last item.
    LEFT_FLANK_REINFORCE = [
        # --- Edge y=13 / y=12 front line, corner-first ---
        (1, 13),            # most-corner y=13 turret
        (2, 13),
        (3, 13),
        (4, 12),            # most-corner y=12
        (5, 12),
        (6, 13),
        (9, 12),            # inner-flank y=12
        # --- y=11 and y=10 (deferred) ---
        (7, 11),
        (11, 11),
        (7, 10),
        (10, 10),
        # --- Corner wall LAST ---
        (0, 13),
    ]
    RIGHT_FLANK_REINFORCE = [
        (26, 13),
        (25, 13),
        (24, 13),
        (23, 12),
        (22, 12),
        (21, 13),
        (18, 12),
        (20, 11),
        (16, 11),
        (20, 10),
        (17, 10),
        (27, 13),
    ]
    CENTER_REINFORCE = [(9, 12), (18, 12)]
    REAR_REINFORCE = [(12, 9), (15, 9)]
    ENEMY_SPAWN_SIDE_THRESHOLD = 2
    ENEMY_SPAWN_WINDOW = 5        # short window — react to RECENT attacks only
    RECENT_BREACH_WINDOW = 5      # only last N breaches count for priority

    def _reorder_by_breach_priority(self, build_list):
        """Bias next-turn builds based on MOST RECENT attack signals:
          1. Enemy scout spawn side in last ENEMY_SPAWN_WINDOW events
          2. Our last RECENT_BREACH_WINDOW breaches

        Old breaches/spawns are intentionally ignored — if right side gets
        breached after left, we switch focus to right for the next round
        rather than continuing to reinforce left.
        """
        left_hot = False
        right_hot = False
        center_hot = False
        rear_hot = False

        recent_spawns = self.enemy_spawn_xs[-self.ENEMY_SPAWN_WINDOW:]
        if sum(1 for x in recent_spawns if x <= 3) >= self.ENEMY_SPAWN_SIDE_THRESHOLD:
            left_hot = True
        if sum(1 for x in recent_spawns if x >= 24) >= self.ENEMY_SPAWN_SIDE_THRESHOLD:
            right_hot = True

        recent_breaches = self.scored_on_locations[-self.RECENT_BREACH_WINDOW:]
        for loc in recent_breaches:
            x, y = loc[0], loc[1]
            if y >= 11 and x <= 3:
                left_hot = True
            elif y >= 11 and x >= 24:
                right_hot = True
            elif y >= 11 and 8 <= x <= 19:
                center_hot = True
            elif y < 10:
                rear_hot = True

        if not (left_hot or right_hot or center_hot or rear_hot):
            return build_list

        # Build the ordered priority tuple list
        ordered_priority = []
        if left_hot:
            ordered_priority.extend(self.LEFT_FLANK_REINFORCE)
        if right_hot:
            ordered_priority.extend(self.RIGHT_FLANK_REINFORCE)
        if center_hot:
            ordered_priority.extend(self.CENTER_REINFORCE)
        if rear_hot:
            ordered_priority.extend(self.REAR_REINFORCE)

        # Extract matching items from build_list in priority order
        high = []
        consumed = set()
        for target in ordered_priority:
            for idx, b in enumerate(build_list):
                if idx in consumed:
                    continue
                if tuple(b[1]) == target:
                    high.append(b)
                    consumed.add(idx)
                    break

        low = [b for idx, b in enumerate(build_list) if idx not in consumed]
        return high + low

    # ==================================================================== #
    #  OFFENSE — shielded scout rush toward enemy supports
    # ==================================================================== #

    SCOUT_DMG_PER_FRAME = 2       # scout damage per frame
    SCOUT_COUNT_ESTIMATE = 5      # assumed scouts alive per frame (tuning)
    SUPPORT_DMG_WEIGHT = 3.0      # multiplier on damage-to-supports vs damage-taken
    # Expected damage to support at a given tile = SCOUT_DMG_PER_FRAME *
    # SCOUT_COUNT_ESTIMATE * SUPPORT_DMG_WEIGHT = 30 per tile where a support
    # is the closest enemy target within scout range (3.5). Weighted higher
    # than turret_dmg (1 per HP) so the picker accepts real damage to reach
    # supports.

    # Default aim point when no enemy supports are visible (turn 0 etc.)
    DEFAULT_ENEMY_CENTER = (13.5, 15.0)
    # Weight on shortest-distance-to-nearest-support. Penalizes paths that
    # stay far from enemy supports even if they technically deliver damage.
    DIST_WEIGHT = 2.0

    def _execute_offense(self, game_state):
        """Every turn: dump all MP as scouts on best-scoring trajectory."""
        if game_state.get_resource(MP) < 1:
            return
        enemy_supports = self._find_enemy_supports(game_state)
        best_loc = self._best_scout_spawn(game_state, enemy_supports)
        game_state.attempt_spawn(SCOUT, best_loc, 1000)

    def _best_scout_spawn(self, game_state, enemy_supports):
        """Unified scoring — single pass over candidate spawns.

            score = support_dmg                  (damage dealt to supports)
                  - turret_dmg                   (damage taken from turrets)
                  - DIST_WEIGHT * min_dist       (shortest distance from path
                                                  to nearest enemy support)

        When no enemy supports exist, min_dist is measured to the default
        enemy-center point (aims turn-0 scouts at likely support area).
        """
        candidates = (
            game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
            + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT))
        candidates = [c for c in candidates if not game_state.contains_stationary_unit(c)]
        enemy_edges = (
            game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT)
            + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT))

        targets = enemy_supports if enemy_supports else [self.DEFAULT_ENEMY_CENTER]

        best_loc = [13, 0]
        best_score = float('-inf')
        for loc in candidates:
            path = game_state.find_path_to_edge(loc)
            if not path or path[-1] not in enemy_edges:
                continue
            score = self._score_path(path, targets, game_state)
            if score > best_score:
                best_score = score
                best_loc = loc
        return best_loc

    def _score_path(self, path, targets, game_state):
        """Compute unified score for a path. See _best_scout_spawn."""
        support_dmg = 0
        turret_dmg = 0
        min_dist = float('inf')
        dmg_per_tile = (self.SCOUT_DMG_PER_FRAME
                        * self.SCOUT_COUNT_ESTIMATE
                        * self.SUPPORT_DMG_WEIGHT)
        for p in path:
            for atk in game_state.get_attackers(p, 0):
                turret_dmg += atk.damage_i
            if self._enemy_support_is_closest(p, game_state):
                support_dmg += dmg_per_tile
            for t in targets:
                dx, dy = p[0] - t[0], p[1] - t[1]
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < min_dist:
                    min_dist = dist
        return support_dmg - turret_dmg - self.DIST_WEIGHT * min_dist

    def _enemy_support_is_closest(self, p, game_state):
        """True iff an enemy support is the closest enemy structure within
        scout attack range (3.5) of tile p."""
        nearest_dist_sq = float('inf')
        nearest_is_support = False
        for nearby in game_state.game_map.get_locations_in_range(p, 3.5):
            if not game_state.contains_stationary_unit(nearby):
                continue
            for unit in game_state.game_map[nearby]:
                if unit.player_index != 1:
                    continue
                dx, dy = p[0] - nearby[0], p[1] - nearby[1]
                dist_sq = dx * dx + dy * dy
                if dist_sq < nearest_dist_sq:
                    nearest_dist_sq = dist_sq
                    nearest_is_support = (unit.unit_type == SUPPORT)
        return nearest_is_support

    def _find_enemy_supports(self, game_state):
        found = []
        for loc in game_state.game_map:
            if not game_state.contains_stationary_unit(loc):
                continue
            for u in game_state.game_map[loc]:
                if u.player_index == 1 and u.unit_type == SUPPORT:
                    found.append(loc)
        return found

    # ==================================================================== #
    #  EVENT TRACKING
    # ==================================================================== #

    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        events = state["events"]
        for breach in events.get("breach", []):
            location = breach[0]
            unit_owner_self = breach[4] == 1
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
        # Track enemy mobile-unit spawns (mobile types 3/4/5, player_index 2).
        # Spawn event format: [location, unit_type_id, unit_id, player_index]
        for sp in events.get("spawn", []):
            if len(sp) < 4:
                continue
            loc, type_id, _uid, player = sp[0], sp[1], sp[2], sp[3]
            if player != 2:
                continue
            if type_id in (3, 4, 5):
                self.enemy_spawn_xs.append(loc[0])


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
