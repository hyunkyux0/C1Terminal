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
        gamelib.debug_write('Configuring v1 strategy: adaptive supports + demolisher mode...')
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

        # === Tracking state ===
        self.scored_on_locations = []
        # Damage we dealt per turn (count of successful breaches)
        self.damage_dealt = []
        # Damage we took per turn (count of enemy breaches)
        self.damage_taken = []
        # Enemy mobile-unit spawns per turn (detect MP saving)
        self.enemy_spawns = []
        # Running counters populated by on_action_frame, committed in strategy()
        self._cur_dmg_dealt = 0
        self._cur_dmg_taken = 0
        self._cur_enemy_spawns = 0
        self._last_committed_turn = -1

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Turn {}'.format(game_state.turn_number))
        game_state.suppress_warnings(True)

        self.strategy(game_state)

        game_state.submit_turn()

    # ------------------------------------------------------------------ #
    #  MAIN STRATEGY
    # ------------------------------------------------------------------ #

    def strategy(self, game_state):
        # Commit previous turn's damage tallies before using them for decisions
        self._commit_turn_damage(game_state.turn_number)

        self.build_defense(game_state)
        self.build_upgrades(game_state)
        self.build_reactive_defense(game_state)
        self.execute_attack(game_state)

    def _commit_turn_damage(self, current_turn):
        """Commit counters from previous turn's action frames into history."""
        if current_turn <= 0:
            return
        if self._last_committed_turn == current_turn - 1:
            return
        self.damage_dealt.append(self._cur_dmg_dealt)
        self.damage_taken.append(self._cur_dmg_taken)
        self.enemy_spawns.append(self._cur_enemy_spawns)
        self._cur_dmg_dealt = 0
        self._cur_dmg_taken = 0
        self._cur_enemy_spawns = 0
        self._last_committed_turn = current_turn - 1

    # ------------------------------------------------------------------ #
    #  DEFENSE: Two-phase V-shape with adaptive supports
    #
    #  Turn 0: Dense center defense + 2 baseline supports (upgraded)
    #  Turn 5+: Temp center turrets removed, V-arms build out
    #
    #  v1 additions:
    #    - Support target (2/3/4) adapts to enemy defense + our attack success
    #    - Front-line turret upgrades [13,13][14,13] prioritized to counter
    #      heavily-shielded enemy scouts
    #    - Corner wall emergency rebuild when enemy scores through corners
    # ------------------------------------------------------------------ #

    CORE_SUPPORTS = [[13, 12], [14, 12]]      # supports 1-2 (baseline, placed turn 0)
    EXTRA_SUPPORTS = [[13, 11], [14, 11]]     # supports 3-4 (added on signal)
    FRONT_TURRETS = [[13, 13], [14, 13]]      # upgraded early vs shielded scouts

    # Support area reinforcement — surrounds the 2x2 support cluster
    # y=12: .TT...........TT...........TT.   (existing core at 12,15 + front)
    # y=11: ..........T.W.ss.W.T..........   (T-W-ss-W-T pattern)
    # y=10: ............T..T.............   (rear turrets protect backlane supports)
    SUPPORT_GUARD_TURRETS = [[11, 11], [16, 11]]  # flanks the support cluster
    SUPPORT_GUARD_WALLS = [[12, 11], [15, 11]]    # walls directly adjacent to supports
    SUPPORT_REAR_TURRETS = [[12, 10], [15, 10]]   # protect backlane supports from y<11 scouts
    SUPPORT_AREA_TURRET_UPGRADES = [[12, 12], [15, 12]]  # existing y=12 turrets

    # V-arm positions in TOP-DOWN order — scouts enter near midline first,
    # so upper-V catches them earlier than deeper positions.
    V_ARM_POSITIONS = [
        [6, 11], [21, 11],      # first V extension (closest to midline)
        [7, 10], [20, 10],      # second row down
        [5, 12], [22, 12],      # widen y=12 flanks
        [9, 8], [18, 8],        # mid V
        [11, 6], [16, 6],       # deep V
        [12, 5], [15, 5],       # V tip
    ]
    # Gate: support escalation requires at least this many V-arm turrets
    # already built. Prevents SP diversion before defense is stable.
    V_ARM_GATE_FOR_SUPPORTS = 6

    # Per-wall "blocked" mapping — each wall at y=13 is made useless by the
    # enemy structure at the y=14 position directly above it.
    CORNER_WALL_BLOCKERS = {
        (0, 13): [0, 14],
        (1, 13): [1, 14],
        (26, 13): [26, 14],
        (27, 13): [27, 14],
    }
    LEFT_CORNER_WALLS = [[0, 13], [1, 13]]
    RIGHT_CORNER_WALLS = [[26, 13], [27, 13]]

    def build_defense(self, game_state):
        # === URGENT CORNER WALLS (if enemy scored through corners) ===
        # Rebuild each individual wall only if (a) enemy has breached that side
        # AND (b) the enemy hasn't blocked the tile directly above that wall.
        left_breached = any(loc[0] <= 2 for loc in self.scored_on_locations)
        right_breached = any(loc[0] >= 25 for loc in self.scored_on_locations)
        for wall in self.LEFT_CORNER_WALLS if left_breached else []:
            if not self._wall_blocked(game_state, wall):
                game_state.attempt_spawn(WALL, [wall])
        for wall in self.RIGHT_CORNER_WALLS if right_breached else []:
            if not self._wall_blocked(game_state, wall):
                game_state.attempt_spawn(WALL, [wall])

        # === CORE: y=13 turret pairs ===
        game_state.attempt_spawn(TURRET, [
            [2, 13], [3, 13], [13, 13], [14, 13], [24, 13], [25, 13]
        ])

        # === CORE: y=12 center turrets + 2 baseline supports ===
        game_state.attempt_spawn(TURRET, [[12, 12], [15, 12]])
        game_state.attempt_spawn(SUPPORT, self.CORE_SUPPORTS)
        game_state.attempt_upgrade(self.CORE_SUPPORTS)

        # === TEMPORARY: Dense center turrets (turn 0-4 only) ===
        if game_state.turn_number < 5:
            game_state.attempt_spawn(TURRET, [[11, 12], [16, 12]])
        else:
            game_state.attempt_remove([[11, 12], [16, 12]])

        # === V-ARM TURRETS (top-down — catch scouts near midline first) ===
        game_state.attempt_spawn(TURRET, self.V_ARM_POSITIONS)

        # === ADAPTIVE: 3rd / 4th supports (gated on V-arm count) ===
        v_arms_built = sum(
            1 for pos in self.V_ARM_POSITIONS
            if game_state.contains_stationary_unit(pos)
        )
        if v_arms_built >= self.V_ARM_GATE_FOR_SUPPORTS:
            target = self.determine_support_target(game_state)
            if target >= 3:
                game_state.attempt_spawn(SUPPORT, [self.EXTRA_SUPPORTS[0]])
                game_state.attempt_upgrade([self.EXTRA_SUPPORTS[0]])
            if target >= 4:
                game_state.attempt_spawn(SUPPORT, [self.EXTRA_SUPPORTS[1]])
                game_state.attempt_upgrade([self.EXTRA_SUPPORTS[1]])

            # === SUPPORT AREA REINFORCEMENT (turrets around supports) ===
            # Permanent turret flanks at [11,11],[16,11] kill scouts approaching
            # from the front. Rear turrets at [12,10],[15,10] kill scouts that
            # pass through y<11 and could attack backlane supports from range 3.5.
            # Upgrade y=12 turrets too.
            game_state.attempt_spawn(TURRET, self.SUPPORT_GUARD_TURRETS)
            game_state.attempt_upgrade(self.SUPPORT_GUARD_TURRETS)
            game_state.attempt_spawn(TURRET, self.SUPPORT_REAR_TURRETS)
            game_state.attempt_upgrade(self.SUPPORT_REAR_TURRETS)
            game_state.attempt_upgrade(self.SUPPORT_AREA_TURRET_UPGRADES)

            # Front-line turret upgrades
            game_state.attempt_upgrade(self.FRONT_TURRETS)

            # === SUPPORT GUARD WALLS (only when enemy pressing with supports) ===
            # Walls at [12,11],[15,11] tighten the defense ring. Enabled when
            # enemy has 3+ supports (they're pushing shielded scouts).
            enemy_supports = self.count_enemy_structures(game_state, SUPPORT)
            if enemy_supports >= 3:
                game_state.attempt_spawn(WALL, self.SUPPORT_GUARD_WALLS)
                game_state.attempt_upgrade(self.SUPPORT_GUARD_WALLS)

        # === CORNER WALLS (per-wall: remove if that specific wall is blocked,
        # else build). The wall at [x,13] is blocked iff enemy has a structure
        # at [x,14] directly above it. ===
        for wall in self.LEFT_CORNER_WALLS + self.RIGHT_CORNER_WALLS:
            if self._wall_blocked(game_state, wall):
                game_state.attempt_remove([wall])
            else:
                game_state.attempt_spawn(WALL, [wall])

    def _wall_blocked(self, game_state, wall):
        """A corner wall is blocked iff the enemy has a structure at the tile
        directly above it (same x, y+1)."""
        blocker = self.CORNER_WALL_BLOCKERS.get(tuple(wall))
        if not blocker:
            return False
        return game_state.contains_stationary_unit(blocker)

    # ------------------------------------------------------------------ #
    #  SIGNAL-BASED SUPPORT ESCALATION
    # ------------------------------------------------------------------ #

    def determine_support_target(self, game_state):
        """Signal-driven support count (2/3/4). Turn is floor-only accelerator."""
        turn = game_state.turn_number
        enemy_turrets = self.count_enemy_structures(game_state, TURRET)

        last2 = self.damage_dealt[-2:] if len(self.damage_dealt) >= 2 else []
        last3 = self.damage_dealt[-3:] if len(self.damage_dealt) >= 3 else []
        avg2 = sum(last2) / len(last2) if last2 else None
        avg3 = sum(last3) / len(last3) if last3 else None

        # Damage-dealt threshold: if our scouts are scoring ≤ 2.5 breaches/turn
        # on average, our offense is being neutralized → add supports for shield
        target = 2
        if enemy_turrets >= 8 or (avg2 is not None and avg2 <= 2.5):
            target = 3
        if enemy_turrets >= 12 or (avg3 is not None and avg3 <= 2.5):
            target = 4

        # Turn floor (accelerator only, never downgrades)
        if turn >= 20 and target < 3:
            target = 3
        if turn >= 40 and target < 4:
            target = 4

        return target

    def count_enemy_structures(self, game_state, unit_type=None):
        total = 0
        for location in game_state.game_map:
            if not game_state.contains_stationary_unit(location):
                continue
            for unit in game_state.game_map[location]:
                if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type):
                    total += 1
        return total

    # ------------------------------------------------------------------ #
    #  UPGRADES (lowest SP priority — leftover budget)
    # ------------------------------------------------------------------ #

    def build_upgrades(self, game_state):
        # Corner walls upgrade only if (a) enemy breached that side AND
        # (b) that specific wall isn't blocked from above.
        left_breached = any(loc[0] <= 2 for loc in self.scored_on_locations)
        right_breached = any(loc[0] >= 25 for loc in self.scored_on_locations)
        for wall in self.LEFT_CORNER_WALLS if left_breached else []:
            if not self._wall_blocked(game_state, wall):
                game_state.attempt_upgrade([wall])
        for wall in self.RIGHT_CORNER_WALLS if right_breached else []:
            if not self._wall_blocked(game_state, wall):
                game_state.attempt_upgrade([wall])

    # ------------------------------------------------------------------ #
    #  REACTIVE DEFENSE
    # ------------------------------------------------------------------ #

    def build_reactive_defense(self, game_state):
        protected = {(13, 13), (14, 13), (13, 12), (14, 12),
                     (13, 11), (14, 11), (11, 12), (16, 12)}
        for location in self.scored_on_locations:
            build_location = [location[0], location[1] + 1]
            if (game_state.game_map.in_arena_bounds(build_location)
                    and build_location[1] < 14
                    and tuple(build_location) not in protected):
                game_state.attempt_spawn(TURRET, build_location)

    # ------------------------------------------------------------------ #
    #  OFFENSE: adaptive mode selection
    #
    #  Modes (checked in order):
    #    DEMOLISHER  — enemy 3+ supports, scouts failing, defense holding
    #                  Launches 4 demolishers + zig-zag walls, or saves MP
    #    DEFENSIVE   — enemy MP saved for big push (>=10): interceptor + reduced scouts
    #    SCOUT       — default 5-scout attack
    # ------------------------------------------------------------------ #

    ZIGZAG_WALLS = [[11, 11], [16, 11]]   # tighten funnel during demolisher push
    DEMOLISHER_COUNT = 4
    DEMOLISHER_MP_THRESHOLD = 12
    ENEMY_MP_SAVE_SIGNAL = 15             # MP alone isn't enough — combined w/ spawn signal
    MAX_SCOUT_STACK = 1000                # attempt_spawn clamps to MP, so this
                                          # effectively means "all available MP"

    def execute_attack(self, game_state):
        # === Demolisher scenario check ===
        if self._is_demolisher_scenario(game_state):
            mp = game_state.get_resource(MP)
            if mp >= self.DEMOLISHER_MP_THRESHOLD:
                self.launch_demolishers(game_state)
            # else: save MP silently (no spawn)
            return

        # === Defensive response: enemy saving MP for big push ===
        # Trigger requires TWO signals: high MP AND no spawns last turn
        if self._is_enemy_saving(game_state):
            self.deploy_defensive_interceptor(game_state)
            # Interceptor costs 3 MP; dump remaining MP into scouts
            best_location = self.best_spawn_location(game_state)
            game_state.attempt_spawn(SCOUT, best_location, self.MAX_SCOUT_STACK)
            return

        # === Default: spawn max scouts at best location ===
        # MP decays 25%/turn, so holding MP is a loss unless we're saving for
        # demolishers (handled above). Dump all MP into scouts every turn.
        best_location = self.best_spawn_location(game_state)
        game_state.attempt_spawn(SCOUT, best_location, self.MAX_SCOUT_STACK)

    def _is_enemy_saving(self, game_state):
        """Enemy is saving MP iff high MP AND didn't spawn mobile units last turn."""
        enemy_mp = game_state.get_resource(MP, 1)
        if enemy_mp < self.ENEMY_MP_SAVE_SIGNAL:
            return False
        # Need at least 1 turn of history
        if not self.enemy_spawns:
            return False
        # Enemy saving if they spawned 0 mobile units last turn
        return self.enemy_spawns[-1] == 0

    # ------------------------------------------------------------------ #
    #  DEMOLISHER MODE
    # ------------------------------------------------------------------ #

    def _is_demolisher_scenario(self, game_state):
        """All conditions true → consider demolisher mode (save or launch)."""
        enemy_supports = self.count_enemy_structures(game_state, SUPPORT)
        if enemy_supports < 3:
            return False

        if len(self.damage_dealt) < 2:
            return False
        if sum(self.damage_dealt[-2:]) / 2 >= 4:
            return False

        if game_state.my_health < 15:
            return False

        if self.damage_taken and self.damage_taken[-1] > 0:
            return False

        return True

    def launch_demolishers(self, game_state):
        """Spawn demolishers with zig-zag walls to keep them in firing zone longer."""
        game_state.attempt_spawn(WALL, self.ZIGZAG_WALLS)
        game_state.attempt_remove(self.ZIGZAG_WALLS)

        best_location = self.best_spawn_location(game_state, unit_type=DEMOLISHER)
        game_state.attempt_spawn(DEMOLISHER, best_location, self.DEMOLISHER_COUNT)

    # ------------------------------------------------------------------ #
    #  DEFENSIVE INTERCEPTOR (enemy MP saving detected)
    # ------------------------------------------------------------------ #

    def deploy_defensive_interceptor(self, game_state):
        """Deploy 1 interceptor to meet incoming enemy scouts."""
        mp = game_state.get_resource(MP)
        if mp < game_state.type_cost(INTERCEPTOR)[MP]:
            return False
        for spot in ([13, 0], [14, 0]):
            if not game_state.contains_stationary_unit(spot):
                game_state.attempt_spawn(INTERCEPTOR, spot)
                return True
        return False

    # ------------------------------------------------------------------ #
    #  UTILITY
    # ------------------------------------------------------------------ #

    def best_spawn_location(self, game_state, unit_type=None):
        candidates = (
            game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
            + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT))
        candidates = self.filter_blocked_locations(candidates, game_state)

        enemy_edges = (
            game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT)
            + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT))

        best_location = [13, 0]
        best_score = float('inf')

        for location in candidates:
            path = game_state.find_path_to_edge(location)
            if not path:
                continue
            if path[-1] not in enemy_edges:
                continue

            damage = 0
            for path_location in path:
                for attacker in game_state.get_attackers(path_location, 0):
                    damage += attacker.damage_i

            enemy_density = 0
            for path_location in path:
                if path_location[1] >= 14:
                    for nearby in game_state.game_map.get_locations_in_range(path_location, 3.5):
                        if game_state.contains_stationary_unit(nearby):
                            for unit in game_state.game_map[nearby]:
                                if unit.player_index == 1:
                                    enemy_density += 1

            score = damage + len(path) * 0.5 + enemy_density * 2
            if score < best_score:
                best_score = score
                best_location = location

        return best_location

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x=None, valid_y=None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if (unit.player_index == 1
                            and (unit_type is None or unit.unit_type == unit_type)
                            and (valid_x is None or location[0] in valid_x)
                            and (valid_y is None or location[1] in valid_y)):
                        total_units += 1
        return total_units

    def filter_blocked_locations(self, locations, game_state):
        return [loc for loc in locations if not game_state.contains_stationary_unit(loc)]

    # ------------------------------------------------------------------ #
    #  ACTION FRAME: Track breaches (both directions)
    # ------------------------------------------------------------------ #

    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        events = state["events"]
        # Track breaches (both directions)
        for breach in events.get("breach", []):
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            if unit_owner_self:
                self._cur_dmg_dealt += 1
            else:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                self._cur_dmg_taken += 1
        # Track enemy mobile spawns (categories 3=scout,4=demo,5=interc; player==2 is enemy)
        for spawn in events.get("spawn", []):
            unit_cat = spawn[1]
            player = spawn[3]
            if player == 2 and unit_cat in (3, 4, 5):
                self._cur_enemy_spawns += 1


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
