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
        gamelib.debug_write('Configuring custom algo strategy...')
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

        self.scored_on_locations = []

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
        self.build_defense(game_state)
        self.build_upgrades(game_state)
        self.build_reactive_defense(game_state)

        # if game_state.turn_number < 5:
        #     self.stall_with_interceptors(game_state)
        # else:
        self.execute_attack(game_state)

    # ------------------------------------------------------------------ #
    #  DEFENSE: Two-phase V-shape
    #
    #  Turn 0 (map 1): Dense center defense
    #    y13: ..TT.........TT.........TT..
    #    y12:  ..........TTssTT..........
    #
    #  Turn ~10 (map 2): Full V-arms with turret barriers
    #    y13: wwTT.........TT.........TTww
    #    y12:  ....T......TssT......T....
    #    y11:   ....T..............T....
    #    y10:    ....T............T....
    #    y08:      ....T........T....
    #    y06:        ....T....T....
    #    y05:         ....T..T....
    #
    #  Transition: Remove [11,12],[16,12] once V-arms at y=11
    #  provide coverage. Rebuild as [5,12],[22,12] for width.
    # ------------------------------------------------------------------ #

    def build_defense(self, game_state):
        # === URGENT CORNER WALLS (if enemy scored through corners) ===
        left_breached = any(loc[0] <= 2 for loc in self.scored_on_locations)
        right_breached = any(loc[0] >= 25 for loc in self.scored_on_locations)
        left_blocked = game_state.contains_stationary_unit([0, 14])
        right_blocked = game_state.contains_stationary_unit([27, 14])

        if left_breached and not left_blocked:
            game_state.attempt_spawn(WALL, [[0, 13], [1, 13]])
        if right_breached and not right_blocked:
            game_state.attempt_spawn(WALL, [[26, 13], [27, 13]])

        # === CORE: y=13 turret pairs (always, placed turn 0) ===
        game_state.attempt_spawn(TURRET, [
            [2, 13], [3, 13], [13, 13], [14, 13], [24, 13], [25, 13]
        ])

        # === CORE: y=12 center turrets + supports (placed turn 0) ===
        game_state.attempt_spawn(TURRET, [[12, 12], [15, 12]])
        game_state.attempt_spawn(SUPPORT, [[13, 12], [14, 12]])
        # Upgrade supports ASAP -- shields are critical for scout attacks
        game_state.attempt_upgrade([[13, 12], [14, 12]])

        # === TEMPORARY: Dense center turrets (turn 0-4 only) ===
        # These hold the center before V-arms are built, then get
        # removed to open scout pathing through x=11 and x=16
        if game_state.turn_number < 5:
            game_state.attempt_spawn(TURRET, [[11, 12], [16, 12]])
        else:
            game_state.attempt_remove([[11, 12], [16, 12]])

        # === V-ARM TURRETS (progressive, breach-priority order) ===
        # Breach data shows scouts exploit y=7-9 flanks first,
        # so mid-V positions are built before top extensions
        v_arm_turrets = [
            [9, 8], [18, 8],        # mid V — covers breach zone y=7-9
            [6, 11], [21, 11],      # upper V arms
            [5, 12], [22, 12],      # widen y=12 flanks
            [7, 10], [20, 10],      # fill gap between y=12 and y=8
            [11, 6], [16, 6],       # deep V
            [12, 5], [15, 5],       # V tip
        ]
        game_state.attempt_spawn(TURRET, v_arm_turrets)

        # === CORNER WALLS (skip if enemy blocks edge, remove for refund) ===
        left_blocked = game_state.contains_stationary_unit([0, 14])
        right_blocked = game_state.contains_stationary_unit([27, 14])

        if left_blocked:
            game_state.attempt_remove([[0, 13], [1, 13]])
        else:
            game_state.attempt_spawn(WALL, [[0, 13], [1, 13]])

        if right_blocked:
            game_state.attempt_remove([[26, 13], [27, 13]])
        else:
            game_state.attempt_spawn(WALL, [[26, 13], [27, 13]])

    # ------------------------------------------------------------------ #
    #  UPGRADES (lowest SP priority -- uses leftovers)
    # ------------------------------------------------------------------ #

    def build_upgrades(self, game_state):
        # Corner walls (cheap, 1 SP each) -- only if they exist
        left_blocked = game_state.contains_stationary_unit([0, 14])
        right_blocked = game_state.contains_stationary_unit([27, 14])
        if not left_blocked:
            game_state.attempt_upgrade([[0, 13], [1, 13]])
        if not right_blocked:
            game_state.attempt_upgrade([[26, 13], [27, 13]])

    # ------------------------------------------------------------------ #
    #  REACTIVE DEFENSE
    # ------------------------------------------------------------------ #

    def build_reactive_defense(self, game_state):
        # Protect the center scout corridor from reactive turrets
        protected = {(13, 13), (14, 13), (13, 12), (14, 12),
                     (13, 11), (14, 11), (11, 12), (16, 12)}
        for location in self.scored_on_locations:
            build_location = [location[0], location[1] + 1]
            if (game_state.game_map.in_arena_bounds(build_location)
                    and build_location[1] < 14
                    and tuple(build_location) not in protected):
                game_state.attempt_spawn(TURRET, build_location)

    # ------------------------------------------------------------------ #
    #  OFFENSE
    # ------------------------------------------------------------------ #

    def execute_attack(self, game_state):
        best_location = self.best_spawn_location(game_state)
        game_state.attempt_spawn(SCOUT, best_location, 5)

    # def demolisher_line_strategy(self, game_state):
    #     # Wall line on right side, avoid center corridor
    #     for x in range(27, 16, -1):
    #         game_state.attempt_spawn(WALL, [x, 11])
    #     game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)

    # ------------------------------------------------------------------ #
    #  INTERCEPTORS (disabled)
    # ------------------------------------------------------------------ #

    # def stall_with_interceptors(self, game_state):
    #     # 1 interceptor per turn to conserve MP
    #     friendly_edges = (
    #         game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
    #         + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT))
    #     deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
    #
    #     if (game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP]
    #             and len(deploy_locations) > 0):
    #         deploy_index = random.randint(0, len(deploy_locations) - 1)
    #         game_state.attempt_spawn(INTERCEPTOR, deploy_locations[deploy_index])

    # def deploy_defensive_interceptor(self, game_state):
    #     # Deploy 1 interceptor when saving MP
    #     spots = [[6, 7], [21, 7]]
    #     for spot in spots:
    #         if game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP]:
    #             if not game_state.contains_stationary_unit(spot):
    #                 game_state.attempt_spawn(INTERCEPTOR, spot)
    #                 return

    # ------------------------------------------------------------------ #
    #  UTILITY
    # ------------------------------------------------------------------ #

    def best_spawn_location(self, game_state):
        # Evaluate all bottom-edge spawn points
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
            # Skip paths that self-destruct (don't reach enemy edge)
            if path[-1] not in enemy_edges:
                continue

            # Sum turret damage along the FULL path (both halves)
            damage = 0
            for path_location in path:
                for attacker in game_state.get_attackers(path_location, 0):
                    damage += attacker.damage_i

            # Count enemy structures near the path in their half (y >= 14)
            # to penalize routes through heavily fortified areas
            enemy_density = 0
            for path_location in path:
                if path_location[1] >= 14:
                    for nearby in game_state.game_map.get_locations_in_range(path_location, 3.5):
                        if game_state.contains_stationary_unit(nearby):
                            for unit in game_state.game_map[nearby]:
                                if unit.player_index == 1:
                                    enemy_density += 1

            # Lower is better: turret damage + path length penalty + enemy density
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
    #  ACTION FRAME: Track breaches
    # ------------------------------------------------------------------ #

    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
