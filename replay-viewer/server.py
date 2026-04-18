#!/usr/bin/env python3
"""Local replay viewer server. Usage: python3 server.py [port]"""

import http.server
import json
import os
import sys
import urllib.parse

REPLAY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'replays')
PORT = 3000


class ReplayHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        root = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=root, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # Stub endpoints so the frontend doesn't break
        if parsed.path == '/api/algos':
            self.send_json([])
            return

        if parsed.path == '/api/matches':
            # Build match list from local replay files
            matches = []
            if os.path.isdir(REPLAY_DIR):
                for f in sorted(os.listdir(REPLAY_DIR), reverse=True):
                    if not f.endswith('.replay'):
                        continue
                    match_id = f.replace('.replay', '')
                    filepath = os.path.join(REPLAY_DIR, f)
                    # Default names
                    algo1_name, algo2_name = 'P1', 'P2'
                    # Look for sidecar metadata with algo names
                    meta_path = os.path.join(REPLAY_DIR, match_id + '.meta.json')
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path) as mf:
                                meta = json.load(mf)
                                algo1_name = meta.get('algo1', 'P1')
                                algo2_name = meta.get('algo2', 'P2')
                        except Exception:
                            pass
                    # Parse replay for winner info
                    p1_hp, p2_hp, winner = 0, 0, 0
                    try:
                        with open(filepath) as rf:
                            lines = [l.strip() for l in rf if l.strip()]
                            for line in reversed(lines):
                                try:
                                    data = json.loads(line)
                                    if 'p1Stats' in data:
                                        p1_hp = data['p1Stats'][0]
                                        p2_hp = data['p2Stats'][0]
                                        winner = 1 if p1_hp > p2_hp else 2 if p2_hp > p1_hp else 0
                                        break
                                except json.JSONDecodeError:
                                    continue
                    except Exception:
                        pass
                    matches.append({
                        'match_id': match_id,
                        'algo1_id': algo1_name,
                        'algo2_id': algo2_name,
                        'winner': winner,
                        'p1_hp': p1_hp,
                        'p2_hp': p2_hp,
                        'created': '',
                        'replay_key': f,
                    })
            self.send_json(matches)
            return

        if parsed.path.startswith('/api/replay/'):
            # /api/replay/{match_id} — load from local replays dir
            match_id = parsed.path.split('/api/replay/')[-1]
            # Try exact match first, then with .replay extension
            filepath = None
            for candidate in [
                os.path.join(REPLAY_DIR, match_id),
                os.path.join(REPLAY_DIR, match_id + '.replay'),
            ]:
                if os.path.exists(candidate):
                    filepath = candidate
                    break
            if not filepath:
                self.send_json({'error': 'Replay not found'}, 404)
                return
            frames, config = [], None
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if 'turnInfo' not in data:
                            config = data
                        else:
                            frames.append(data)
                    except json.JSONDecodeError:
                        continue
            self.send_json({'config': config, 'frames': frames, 'match_id': match_id})
            return

        # Legacy endpoint (old frontend compat)
        if parsed.path == '/api/replay':
            params = urllib.parse.parse_qs(parsed.query)
            filename = params.get('file', [None])[0]
            if not filename:
                files = sorted(os.listdir(REPLAY_DIR), reverse=True)
                filename = next((f for f in files if f.endswith('.replay')), None)
            if not filename:
                self.send_json({'error': 'No replay files found'}, 404)
                return
            filepath = os.path.join(REPLAY_DIR, os.path.basename(filename))
            if not os.path.exists(filepath):
                self.send_json({'error': 'File not found'}, 404)
                return
            frames, config = [], None
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if 'turnInfo' not in data:
                            config = data
                        else:
                            frames.append(data)
                    except json.JSONDecodeError:
                        continue
            self.send_json({'config': config, 'frames': frames, 'filename': filename})
            return

        super().do_GET()

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # quiet


if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            PORT = int(sys.argv[1])
        except ValueError:
            pass
    print(f'Replay viewer: http://localhost:{PORT}')
    server = http.server.HTTPServer(('', PORT), ReplayHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
