import json
import os
import subprocess
import sys
import time

# Runs a single game
def run_single_game(process_command):
    print("Start run a match")
    p = subprocess.Popen(
        process_command,
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr
        )
    # daemon necessary so game shuts down if this script is shut down by user
    p.daemon = 1
    p.wait()
    print("Finished running match")

# Get location of this run file
file_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.join(file_dir, os.pardir)
parent_dir = os.path.abspath(parent_dir)

# Get if running in windows OS
is_windows = sys.platform.startswith('win')
print("Is windows: {}".format(is_windows))

# Set default path for algos if script is run with no params
default_algo = parent_dir + "\\python-algo\\run.ps1" if is_windows else parent_dir + "/python-algo/run.sh"
algo1 = default_algo
algo2 = default_algo

# If script run with params, use those algo locations when running the game
if len(sys.argv) > 1:
    algo1 = sys.argv[1]
if len(sys.argv) > 2:
    algo2 = sys.argv[2]

# Display names (derived from algo paths, before appending run.sh)
def pretty_name(path):
    p = path.rstrip("/\\")
    for trail in ("run.sh", "run.ps1"):
        if p.endswith(trail):
            p = p[: -len(trail)].rstrip("/\\")
    return os.path.basename(p) or p

algo1_name = pretty_name(algo1)
algo2_name = pretty_name(algo2)

# If folder path is given instead of run file path, add the run file to the path based on OS
# trailing_char deals with if there is a trailing \ or / or not after the directory name
if is_windows:
    if "run.ps1" not in algo1:
        trailing_char = "" if algo1.endswith("\\") else "\\"
        algo1 = algo1 + trailing_char + "run.ps1"
    if "run.ps1" not in algo2:
        trailing_char = "" if algo2.endswith("\\") else "\\"
        algo2 = algo2 + trailing_char + "run.ps1"
else:
    if "run.sh" not in algo1:
        trailing_char = "" if algo1.endswith('/') else "/"
        algo1 = algo1 + trailing_char + "run.sh"
    if "run.sh" not in algo2:
        trailing_char = "" if algo2.endswith('/') else "/"
        algo2 = algo2 + trailing_char + "run.sh"

print("Algo 1: ", algo1)
print("Algo 2:", algo2)

# Snapshot replays before the match so we can detect the new one
replays_dir = os.path.join(parent_dir, "replays")
existing_replays = set()
if os.path.isdir(replays_dir):
    existing_replays = {f for f in os.listdir(replays_dir) if f.endswith(".replay")}
start_time = time.time()

run_single_game("cd {} && java -jar engine.jar work {} {}".format(parent_dir, algo1, algo2))

# Find the new replay file and write a .meta.json sidecar with algo names
try:
    if os.path.isdir(replays_dir):
        new_replays = [
            f for f in os.listdir(replays_dir)
            if f.endswith(".replay")
            and f not in existing_replays
            and os.path.getmtime(os.path.join(replays_dir, f)) >= start_time - 1
        ]
        if new_replays:
            newest = max(new_replays, key=lambda f: os.path.getmtime(os.path.join(replays_dir, f)))
            meta_path = os.path.join(replays_dir, newest.replace(".replay", ".meta.json"))
            with open(meta_path, "w") as f:
                json.dump({"algo1": algo1_name, "algo2": algo2_name}, f)
            print("Replay metadata: {} vs {}".format(algo1_name, algo2_name))
except Exception as e:
    print("Warning: failed to write replay metadata:", e)
