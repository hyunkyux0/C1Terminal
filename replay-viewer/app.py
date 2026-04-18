#!/usr/bin/env python3
"""C1 Terminal Match Runner — FastAPI backend."""

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import boto3
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# ── Config ────────────────────────────────────────────────────
S3_BUCKET = os.environ.get("S3_BUCKET", "")
ENGINE_JAR = os.environ.get("ENGINE_JAR", "/opt/c1terminal/engine.jar")
GAME_CONFIGS = os.environ.get("GAME_CONFIGS", "/opt/c1terminal/game-configs.json")
WORK_DIR = "/tmp/c1matches"

s3 = boto3.client("s3")
os.makedirs(WORK_DIR, exist_ok=True)


# ── Serve frontend ───────────────────────────────────────────
@app.get("/")
async def serve_index():
    return FileResponse(Path(__file__).parent / "index.html")


# ── Algo management ──────────────────────────────────────────
@app.get("/api/algos")
async def list_algos():
    try:
        resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="algos/")
        algos = []
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".zip"):
                name = key.split("/")[-1].replace(".zip", "")
                algos.append({
                    "id": name,
                    "name": name,
                    "size": obj["Size"],
                    "uploaded": obj["LastModified"].isoformat(),
                })
        return algos
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/algos")
async def upload_algo(file: UploadFile = File(...), name: str = Form("")):
    algo_name = name or file.filename.replace(".zip", "").replace(" ", "-")
    algo_name = "".join(c for c in algo_name if c.isalnum() or c in "-_").lower()
    if not algo_name:
        algo_name = f"algo-{uuid.uuid4().hex[:8]}"

    content = await file.read()
    s3_key = f"algos/{algo_name}.zip"

    try:
        s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=content)
    except Exception as e:
        raise HTTPException(500, f"S3 upload failed: {e}")

    return {"id": algo_name, "name": algo_name, "key": s3_key}


@app.delete("/api/algos/{algo_id}")
async def delete_algo(algo_id: str):
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=f"algos/{algo_id}.zip")
        return {"deleted": algo_id}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Match execution ──────────────────────────────────────────
@app.get("/api/matches")
async def list_matches():
    try:
        resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="replays/")
        matches = []
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json"):
                meta = s3.get_object(Bucket=S3_BUCKET, Key=key)
                data = json.loads(meta["Body"].read())
                matches.append(data)
        matches.sort(key=lambda m: m.get("created", ""), reverse=True)
        return matches
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/matches")
async def run_match(body: dict):
    algo1_id = body.get("algo1_id")
    algo2_id = body.get("algo2_id")
    if not algo1_id or not algo2_id:
        raise HTTPException(400, "algo1_id and algo2_id required")

    match_id = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    match_dir = os.path.join(WORK_DIR, match_id)
    os.makedirs(match_dir, exist_ok=True)

    try:
        # Download and unzip both algos
        for algo_id, dirname in [(algo1_id, "algo1"), (algo2_id, "algo2")]:
            zip_path = os.path.join(match_dir, f"{dirname}.zip")
            algo_dir = os.path.join(match_dir, dirname)
            s3.download_file(S3_BUCKET, f"algos/{algo_id}.zip", zip_path)
            shutil.unpack_archive(zip_path, algo_dir)
            # Handle nested directory: if unzip created a single subfolder, use that
            contents = os.listdir(algo_dir)
            if len(contents) == 1 and os.path.isdir(os.path.join(algo_dir, contents[0])):
                nested = os.path.join(algo_dir, contents[0])
                for item in os.listdir(nested):
                    shutil.move(os.path.join(nested, item), algo_dir)
                os.rmdir(nested)
            # Make run.sh executable
            run_sh = os.path.join(algo_dir, "run.sh")
            if os.path.exists(run_sh):
                os.chmod(run_sh, 0o755)

        # Copy engine + config to match dir
        shutil.copy2(ENGINE_JAR, os.path.join(match_dir, "engine.jar"))
        shutil.copy2(GAME_CONFIGS, os.path.join(match_dir, "game-configs.json"))

        # Run match
        result = subprocess.run(
            ["java", "-jar", "engine.jar", "work", "algo1/run.sh", "algo2/run.sh"],
            cwd=match_dir,
            capture_output=True, text=True, timeout=120,
        )

        # Find replay file
        replay_file = None
        replays_dir = os.path.join(match_dir, "replays")
        if os.path.isdir(replays_dir):
            for f in os.listdir(replays_dir):
                if f.endswith(".replay"):
                    replay_file = os.path.join(replays_dir, f)
                    break

        if not replay_file:
            # Check match_dir root too
            for f in os.listdir(match_dir):
                if f.endswith(".replay"):
                    replay_file = os.path.join(match_dir, f)
                    break

        if not replay_file:
            raise HTTPException(500, f"No replay file generated. stderr: {result.stderr[-500:]}")

        # Parse replay for winner
        winner = None
        p1_hp = 0
        p2_hp = 0
        with open(replay_file) as rf:
            lines = [l.strip() for l in rf if l.strip()]
            for line in reversed(lines):
                try:
                    data = json.loads(line)
                    if "p1Stats" in data:
                        p1_hp = data["p1Stats"][0]
                        p2_hp = data["p2Stats"][0]
                        winner = 1 if p1_hp > p2_hp else 2 if p2_hp > p1_hp else 0
                        break
                except json.JSONDecodeError:
                    continue

        # Upload replay to S3
        replay_s3_key = f"replays/{match_id}.replay"
        s3.upload_file(replay_file, S3_BUCKET, replay_s3_key)

        # Save match metadata
        match_meta = {
            "match_id": match_id,
            "algo1_id": algo1_id,
            "algo2_id": algo2_id,
            "winner": winner,
            "p1_hp": p1_hp,
            "p2_hp": p2_hp,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "replay_key": replay_s3_key,
        }
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"replays/{match_id}.json",
            Body=json.dumps(match_meta),
            ContentType="application/json",
        )

        return match_meta

    except subprocess.TimeoutExpired:
        raise HTTPException(500, "Match timed out (120s)")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        shutil.rmtree(match_dir, ignore_errors=True)


@app.get("/api/replay/{match_id}")
async def get_replay(match_id: str):
    try:
        replay_key = f"replays/{match_id}.replay"
        resp = s3.get_object(Bucket=S3_BUCKET, Key=replay_key)
        content = resp["Body"].read().decode()

        frames = []
        config = None
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if "turnInfo" not in data:
                    config = data
                else:
                    frames.append(data)
            except json.JSONDecodeError:
                continue

        return {"config": config, "frames": frames, "match_id": match_id}
    except s3.exceptions.NoSuchKey:
        raise HTTPException(404, "Replay not found")
    except Exception as e:
        raise HTTPException(500, str(e))
