"""Mock opponent replicating the 4-support layout from the earlier screenshot.

Layout (player side, y<=13):
  y=13: ..TT.........TT.........TT..          (front-line turrets)
  y=12: ..........TTssssTT.........           (2 turrets + 4 supports + 2 turrets)
  y=11: .........T.ssss.T.........            (narrower ring)

Scout rush every turn from the least-damage edge.
"""
import gamelib
import random
import math
from sys import maxsize
import json


class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)

    def on_game_start(self, config):
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

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)
        self.build_defense(game_state)
        self.attack(game_state)
        game_state.submit_turn()

    # ------------------------------------------------------------------ #
    #  DEFENSE: 4-support tight cluster layout
    # ------------------------------------------------------------------ #

    def build_defense(self, game_state):
        # Priority 1: Front-line y=13 turrets (6 turrets, 18 SP)
        game_state.attempt_spawn(TURRET, [
            [2, 13], [3, 13], [13, 13], [14, 13], [24, 13], [25, 13]
        ])

        # Priority 2: y=12 turret flanks (6 SP)
        game_state.attempt_spawn(TURRET, [[11, 12], [16, 12]])

        # Priority 3: 4 center supports, all upgraded (32 SP)
        supports = [[12, 12], [13, 12], [14, 12], [15, 12]]
        game_state.attempt_spawn(SUPPORT, supports)
        game_state.attempt_upgrade(supports)

        # Priority 4: Outer y=12 extensions
        game_state.attempt_spawn(TURRET, [[10, 12], [17, 12]])

        # Priority 5: y=11 protection ring
        game_state.attempt_spawn(TURRET, [[10, 11], [17, 11]])

        # Priority 6: y=14 push barrier (NOT applicable — that's enemy half)
        # Add upgrades to front turrets over time
        game_state.attempt_upgrade([[13, 13], [14, 13]])

        # Priority 7: Corner walls
        game_state.attempt_spawn(WALL, [[0, 13], [1, 13], [26, 13], [27, 13]])

        # Priority 8: More turret coverage (top priority once core built)
        game_state.attempt_spawn(TURRET, [
            [6, 11], [21, 11], [7, 10], [20, 10],
            [9, 8], [18, 8], [5, 12], [22, 12],
        ])
        game_state.attempt_upgrade([[2, 13], [3, 13], [24, 13], [25, 13]])

    # ------------------------------------------------------------------ #
    #  ATTACK: 5-scout rush every turn at best spawn location
    # ------------------------------------------------------------------ #

    def attack(self, game_state):
        candidates = (
            game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
            + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT))
        candidates = [c for c in candidates if not game_state.contains_stationary_unit(c)]
        enemy_edges = (
            game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT)
            + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT))

        best, best_score = [13, 0], float('inf')
        for loc in candidates:
            path = game_state.find_path_to_edge(loc)
            if not path or path[-1] not in enemy_edges:
                continue
            damage = sum(
                a.damage_i
                for p in path
                for a in game_state.get_attackers(p, 0)
            )
            if damage < best_score:
                best_score = damage
                best = loc
        game_state.attempt_spawn(SCOUT, best, 5)

    def on_action_frame(self, turn_string):
        pass


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
