#Author: Pravigya


#!/usr/bin/env python3
"""
Shared utilities for AI attackers.
Handles PoW solving, fingerprint generation, and puzzle solving.
"""

import hashlib
import requests
import random
import base64
import time
from io import BytesIO

# Try to import PIL for image similarity (optional)
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not available, puzzle solving will use brute force")


def get_challenge(server_url):
    """Get PoW challenge from server."""
    resp = requests.get(f"{server_url}/get-challenge", timeout=5)
    data = resp.json()
    return data["session_id"], data["challenge"]


def solve_pow(challenge, difficulty=2):
    """Solve proof-of-work challenge."""
    target = "0" * difficulty
    nonce = 0
    while True:
        message = f"{challenge}{nonce}".encode()
        hash_result = hashlib.sha256(message).hexdigest()
        if hash_result.startswith(target):
            return nonce, hash_result
        nonce += 1
        if nonce > 10_000_000:  # Safety limit
            return 0, ""


def generate_fingerprint(consistent=True, seed=None):
    """Generate realistic browser fingerprint.

    Args:
        consistent: If True, generates same fingerprint for same seed
        seed: Optional seed for consistent fingerprints
    """
    if seed is not None:
        random.seed(seed)

    platforms = ["MacIntel", "Win32", "Linux x86_64"]
    browsers = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    ]

    idx = random.randint(0, 2)
    fp = {
        "ua": browsers[idx],
        "platform": platforms[idx],
        "cores": random.choice([4, 8, 12, 16]),
        "memory": random.choice([8, 16, 32]),
        "screen": f"{random.choice([1920, 2560, 1440])}x{random.choice([1080, 1440, 900])}x24",
        "colorDepth": 24,
        "timezone": random.choice([-8, -5, 0, 1, 5]),
        "language": "en-US",
        "plugins": random.randint(3, 8),
        "canvas": "canvas_hash_" + str(random.randint(1000, 9999)),
        "webgl": "ANGLE (Intel, Mesa Intel Graphics)",
        "webdriver": False,
        "phantom": False,
        "selenium": False,
        "headless": False,
    }

    if seed is not None:
        random.seed()  # Reset random state

    return fp


def send_verification(server_url, events, session_id, pow_nonce, pow_hash, fingerprint):
    """Send verification request to server."""
    payload = {
        "events": events,
        "targetSequence": [1, 2, 3],
        "targetsHit": 3,
        "canvasWidth": 800,
        "canvasHeight": 500,
        "session_id": session_id,
        "pow_nonce": pow_nonce,
        "pow_hash": pow_hash,
        "fingerprint": fingerprint,
    }
    resp = requests.post(f"{server_url}/verify-motor-captcha", json=payload, timeout=10)
    return resp.json()


# =============================================================================
# PUZZLE SOLVING UTILITIES
# =============================================================================

def get_puzzle(server_url, use_debug=False):
    """Get a new puzzle from server.

    Args:
        server_url: Server URL
        use_debug: If True, get debug info with solution (simulates learned attack)
    """
    url = f"{server_url}/api/puzzle"
    if use_debug:
        url += "?debug=1"
    resp = requests.get(url, timeout=5)
    return resp.json()


def decode_tile_image(data_url):
    """Decode base64 data URL to PIL Image."""
    if not HAS_PIL:
        return None
    # Remove data:image/png;base64, prefix
    if "base64," in data_url:
        data_url = data_url.split("base64,")[1]
    img_data = base64.b64decode(data_url)
    return Image.open(BytesIO(img_data))


def get_tile_signature(img):
    """Get a simple signature for tile comparison (average color of regions)."""
    if img is None:
        return None
    # Resize to small size and get average colors of quadrants
    small = img.resize((8, 8))
    pixels = list(small.getdata())
    return tuple(sum(p[i] for p in pixels) // len(pixels) for i in range(3))


def solve_puzzle_by_similarity(puzzle):
    """Solve puzzle using image similarity (compare tile edges).

    Returns the correct order based on analyzing tile content.
    """
    if not HAS_PIL:
        # Fallback: return shuffled order (will fail but shows attempt)
        return puzzle.get("order", list(range(9)))

    tiles = puzzle.get("tiles", [])
    grid = puzzle.get("grid", 3)
    n_tiles = grid * grid

    if len(tiles) != n_tiles:
        return list(range(n_tiles))

    # Decode all tiles
    tile_images = [decode_tile_image(t) for t in tiles]

    # Get signatures for each tile
    signatures = []
    for img in tile_images:
        if img:
            # Get edge signatures (top, bottom, left, right averages)
            w, h = img.size
            top = img.crop((0, 0, w, h//4))
            bottom = img.crop((0, 3*h//4, w, h))
            left = img.crop((0, 0, w//4, h))
            right = img.crop((3*w//4, 0, w, h))
            sig = {
                'top': get_tile_signature(top),
                'bottom': get_tile_signature(bottom),
                'left': get_tile_signature(left),
                'right': get_tile_signature(right),
                'full': get_tile_signature(img)
            }
            signatures.append(sig)
        else:
            signatures.append(None)

    # Simple heuristic: tiles in top row have brighter tops (sky)
    # tiles in bottom row have darker/greener bottoms (ground)
    # This is specific to the abstract landscape images generated

    scored_tiles = []
    for i, sig in enumerate(signatures):
        if sig is None:
            scored_tiles.append((i, 0, 0))
            continue
        # Sky brightness (higher = more sky = top row)
        top_brightness = sum(sig['top']) if sig['top'] else 0
        # Green-ness of bottom (for ground detection)
        bottom_green = sig['bottom'][1] if sig['bottom'] else 0
        scored_tiles.append((i, top_brightness, bottom_green))

    # Sort by top brightness (brightest = top-left corner typically)
    scored_tiles.sort(key=lambda x: (-x[1], x[2]))

    # Return indices in sorted order
    return [t[0] for t in scored_tiles]


def generate_puzzle_events(num_events=15, duration_ms=8000):
    """Generate realistic mouse events for puzzle solving."""
    events = []
    start_time = 0

    for i in range(num_events):
        # Spread events over duration
        t = start_time + (i / num_events) * duration_ms + random.uniform(0, 200)
        x = random.randint(50, 400)
        y = random.randint(50, 400)
        event_type = random.choice(["move", "move", "move", "down"])
        events.append({"x": x, "y": y, "t": t, "type": event_type})

    return events


def submit_puzzle_solution(server_url, puzzle_id, order, events, solve_time, interactions, fp_hash=""):
    """Submit puzzle solution with behavioral data."""
    payload = {
        "id": puzzle_id,
        "order": order,
        "events": events,
        "solve_time": solve_time,
        "interactions": interactions,
        "fp_hash": fp_hash
    }
    resp = requests.post(f"{server_url}/api/check", json=payload, timeout=5)
    return resp.json()


def attempt_puzzle(server_url, fp_hash="", params=None, use_learned_solution=False):
    """Full puzzle solving attempt with configurable parameters.

    Args:
        server_url: Server URL
        fp_hash: Fingerprint hash for session tracking
        params: Dict with 'solve_time', 'num_events', 'interactions'
        use_learned_solution: If True, use debug endpoint to get correct solution
                              (simulates attacker having "learned" the pattern)

    Returns:
        (success, result_dict)
    """
    if params is None:
        params = {"solve_time": 8.0, "num_events": 15, "interactions": 4}

    # Get puzzle (with debug info if we've "learned")
    puzzle = get_puzzle(server_url, use_debug=use_learned_solution)
    puzzle_id = puzzle.get("id")

    # Get solution - either from debug or via image analysis
    if use_learned_solution and puzzle.get("debug"):
        # Attacker has learned to extract the solution
        solution = puzzle["debug"]["solution"]
    else:
        # Try to solve using image similarity (usually fails)
        solution = solve_puzzle_by_similarity(puzzle)

    # Generate behavioral data
    events = generate_puzzle_events(
        num_events=params.get("num_events", 15),
        duration_ms=params.get("solve_time", 8.0) * 1000
    )

    # Add delay to simulate solving time
    actual_solve_time = params.get("solve_time", 8.0)
    time.sleep(max(0.5, actual_solve_time - 0.5))  # Simulate most of solve time

    # Submit
    result = submit_puzzle_solution(
        server_url,
        puzzle_id,
        solution,
        events,
        actual_solve_time,
        params.get("interactions", 4),
        fp_hash
    )

    return result.get("ok", False), result
