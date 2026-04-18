"""Diagnostic algo: does nothing, just logs MP/SP to isolate resource formula."""
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
        mp_before = game_state.get_resource(MP, 0)
        sp_before = game_state.get_resource(SP, 0)
        # Just place 2 upgraded supports, nothing else
        if game_state.turn_number == 0:
            game_state.attempt_spawn(SUPPORT, [[13, 12], [14, 12]])
            # NO upgrade
        mp_after = game_state.get_resource(MP, 0)
        gamelib.debug_write(f"DIAG TURN {game_state.turn_number}: MP_before={mp_before} MP_after={mp_after} SP_before={sp_before}")
        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        pass


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
