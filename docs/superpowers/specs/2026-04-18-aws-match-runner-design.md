# AWS C1 Terminal Match Runner

## Overview
Deploy the replay viewer + match runner as a web app on AWS. Small team, no auth, intended for ~1 day of use.

## Architecture
Single EC2 t3.medium instance running a FastAPI app. S3 bucket for persistent storage.

## AWS Resources
| Resource | Config |
|----------|--------|
| EC2 instance | t3.medium, Amazon Linux 2023, public IP |
| Security group | Inbound: 22 (SSH), 80 (HTTP) |
| S3 bucket | `c1terminal-{account_id}` |
| Key pair | `c1terminal-key` → saved locally |

## S3 Layout
```
algos/{algo_id}.zip          # uploaded algorithm archives
replays/{match_id}.replay    # match replay files
```

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve frontend |
| GET | `/api/algos` | List uploaded algorithms |
| POST | `/api/algos` | Upload algorithm zip |
| DELETE | `/api/algos/{id}` | Delete algorithm |
| POST | `/api/matches` | Run match (body: `{algo1_id, algo2_id}`) |
| GET | `/api/matches` | List completed matches |
| GET | `/api/replay/{match_id}` | Get parsed replay data |

## Match Execution Flow
1. Receive POST with two algo IDs
2. Download both zips from S3 to `/tmp/matches/{match_id}/`
3. Unzip both into `algo1/` and `algo2/`
4. Run: `java -jar engine.jar work algo1/run.sh algo2/run.sh`
5. Parse replay file from output
6. Upload replay to S3
7. Clean up temp directory
8. Return match result + replay data

## Frontend Pages (single HTML, tab-based)
- **Match Runner**: algo dropdowns for P1/P2, "Run Match" button, status indicator
- **Algo Manager**: upload form, list with delete buttons
- **Replay Viewer**: existing viewer (loads from match selection or match list)

## EC2 Setup (user-data script)
- Install: Python 3, pip, Java 17 (for engine.jar), unzip
- Copy: engine.jar, game-configs.json, app files
- Run: FastAPI on port 80 via uvicorn

## Deployment Script (`deploy.sh`)
Creates all AWS resources, uploads app files via SCP, starts the server. Outputs the public URL.

## Teardown Script (`teardown.sh`)
Terminates EC2 instance, deletes security group, deletes key pair, empties and deletes S3 bucket. Includes instructions and confirmation prompt.

## Files to Create
```
replay-viewer/
  app.py              # FastAPI backend
  index.html           # Updated frontend (match runner + viewer)
  requirements.txt     # Python dependencies
  deploy.sh           # AWS provisioning + deployment
  teardown.sh         # AWS cleanup
  TEARDOWN.md         # Human-readable shutdown instructions
```
