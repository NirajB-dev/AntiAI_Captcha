#Author: Pravigya


#!/usr/bin/env python3
"""
Prompt Injection / Pattern Probing Attacker
Demonstrates AI prompting: probes the ML model to discover which features it rewards, then exploits those biases.
Now includes puzzle escalation handling and evolution demonstration.
"""

import random
import math
import time
from utils import (
    get_challenge, solve_pow, generate_fingerprint, send_verification,
    attempt_puzzle
)


class PromptProbingAttacker:
    """AI that probes the CAPTCHA system to learn its decision boundaries, then exploits them."""

    def __init__(self, server_url="http://localhost:5001"):
        self.server_url = server_url
        self.feature_importance = {}
        self.puzzle_optimal = {}
        self.attempts = 0
        self.successes = 0
        self.motor_attempts = 0
        self.motor_successes = 0
        self.puzzle_attempts = 0
        self.puzzle_successes = 0
        self.escalated = False
        self.fp_hash = None
        self.puzzle_learned = False  # Track if we've "learned" to solve puzzles
        # Use consistent fingerprint for session tracking
        self.fingerprint = generate_fingerprint(seed=123)

    def generate_probe_events(self, config):
        """Generate events with specific feature values to probe model behavior."""
        events = []
        t = config.get("reaction_time", 100)
        x, y = 400, 250
        targets = [{"x": 200, "y": 150}, {"x": 600, "y": 150}, {"x": 400, "y": 350}]

        for target in targets:
            tx, ty = target["x"], target["y"]
            for i in range(config.get("steps", 25)):
                progress = i / 25
                jitter = config.get("jitter", 0) * random.gauss(0, 1)
                curve = config.get("curvature", 0) * 35 * math.sin(progress * math.pi)
                x += (tx - x) * 0.11 + jitter
                y += (ty - y) * 0.11 + curve + jitter
                dt = config.get("timing", 15) * random.uniform(0.85, 1.15)
                t += dt
                events.append({"x": x, "y": y, "t": t, "type": "mousemove"})
                if random.random() < config.get("pause_rate", 0):
                    t += random.uniform(40, 120)

            events.append({"x": tx, "y": ty, "t": t, "type": "mousedown"})
            t += random.uniform(50, 80)
            events.append({"x": tx, "y": ty, "t": t, "type": "mouseup"})
            x, y = tx, ty
        return events

    def probe_motor_feature(self, feature_name, values):
        """Probe a single motor feature across a range of values."""
        base = {"reaction_time": 120, "steps": 28, "jitter": 2.5, "curvature": 0.6, "timing": 18, "pause_rate": 0.15}
        results = []

        for val in values:
            config = base.copy()
            config[feature_name] = val
            try:
                session_id, challenge = get_challenge(self.server_url)
                pow_nonce, pow_hash = solve_pow(challenge, difficulty=2)
                events = self.generate_probe_events(config)
                result = send_verification(self.server_url, events, session_id, pow_nonce, pow_hash, self.fingerprint)
                score = result.get("confidence", 0)
                results.append((val, score, result.get("escalate", False)))
                if result.get("fp_hash"):
                    self.fp_hash = result["fp_hash"]
            except:
                results.append((val, 0, False))
            time.sleep(0.05)
        return results

    def probe_puzzle_feature(self, feature_name, values):
        """Probe puzzle parameters to find optimal values."""
        base = {"solve_time": 8.0, "num_events": 15, "interactions": 4}
        results = []

        for val in values:
            params = base.copy()
            params[feature_name] = val
            try:
                success, result = attempt_puzzle(self.server_url, self.fp_hash or "", params)
                results.append((val, success, result.get("reason", "")))
            except Exception as e:
                results.append((val, False, str(e)))
            time.sleep(0.3)  # Puzzle attempts take time
        return results

    def discover_motor_biases(self):
        """Probe different motor features to discover model biases."""
        print("\nPhase 1: PROBING MOTOR CAPTCHA")
        print("-" * 40)
        probes = {
            "jitter": [0.5, 2, 4, 6],
            "curvature": [0.2, 0.5, 1.0, 1.5],
            "timing": [10, 18, 30, 50],
            "pause_rate": [0.05, 0.15, 0.3],
        }

        for feature, values in probes.items():
            print(f"  Probing {feature}...", end=" ")
            results = self.probe_motor_feature(feature, values)
            # Filter out escalated results
            valid_results = [(v, s) for v, s, e in results if not e]
            if valid_results:
                best_val, best_score = max(valid_results, key=lambda x: x[1])
                self.feature_importance[feature] = {"best_value": best_val, "best_score": best_score}
                print(f"best={best_val} (score={best_score:.3f})")
            else:
                print("all escalated")
                # Check if we got escalated
                if any(e for _, _, e in results):
                    self.escalated = True
                    print("  ⚠️ Escalated to puzzle during motor probing!")
                    return False
        return True

    def discover_puzzle_biases(self):
        """Probe puzzle parameters to find what passes."""
        print("\nPhase 2: PROBING PUZZLE CAPTCHA")
        print("-" * 40)
        probes = {
            "solve_time": [2.0, 5.0, 8.0, 12.0],
            "num_events": [3, 8, 15, 25],
            "interactions": [1, 3, 5, 8],
        }

        for feature, values in probes.items():
            print(f"  Probing {feature}...", end=" ")
            results = self.probe_puzzle_feature(feature, values)
            # Find minimum value that passes
            passing = [(v, r) for v, s, r in results if s]
            if passing:
                best_val = min(v for v, _ in passing)
                self.puzzle_optimal[feature] = best_val
                print(f"min_passing={best_val}")
            else:
                # No passing - use highest value
                self.puzzle_optimal[feature] = max(values)
                print(f"none passed, using max={max(values)}")

    def exploit_motor(self, num_attempts=8):
        """Use learned motor biases to craft optimal attack."""
        print("\nPhase 3: EXPLOITING MOTOR BIASES")
        print("-" * 40)
        optimal = {
            "reaction_time": 120,
            "steps": 28,
            "jitter": self.feature_importance.get("jitter", {}).get("best_value", 3),
            "curvature": self.feature_importance.get("curvature", {}).get("best_value", 0.6),
            "timing": self.feature_importance.get("timing", {}).get("best_value", 18),
            "pause_rate": self.feature_importance.get("pause_rate", {}).get("best_value", 0.15),
        }
        print(f"  Optimal: jitter={optimal['jitter']}, curve={optimal['curvature']}, timing={optimal['timing']}")

        for i in range(num_attempts):
            self.attempts += 1
            self.motor_attempts += 1
            try:
                session_id, challenge = get_challenge(self.server_url)
                pow_nonce, pow_hash = solve_pow(challenge, difficulty=2)
                events = self.generate_probe_events(optimal)
                result = send_verification(self.server_url, events, session_id, pow_nonce, pow_hash, self.fingerprint)

                if result.get("fp_hash"):
                    self.fp_hash = result["fp_hash"]

                if result.get("verified"):
                    self.successes += 1
                    self.motor_successes += 1
                    print(f"  Attempt {i+1}: ✅ SUCCESS (score={result.get('confidence', 0):.3f})")
                elif result.get("escalate"):
                    self.escalated = True
                    print(f"  Attempt {i+1}: 🧩 ESCALATED to puzzle")
                    return False
                else:
                    print(f"  Attempt {i+1}: ❌ FAIL ({result.get('reason', 'Unknown')[:40]})")
            except Exception as e:
                print(f"  Attempt {i+1}: ⚠️ ERROR - {e}")
            time.sleep(0.05)
        return True

    def exploit_puzzle(self, num_attempts=5):
        """Use learned puzzle parameters to solve puzzle."""
        print("\nPhase 4: EXPLOITING PUZZLE")
        print("-" * 40)
        params = {
            "solve_time": self.puzzle_optimal.get("solve_time", 8.0),
            "num_events": self.puzzle_optimal.get("num_events", 15),
            "interactions": self.puzzle_optimal.get("interactions", 4),
        }
        print(f"  Optimal: time={params['solve_time']}s, events={params['num_events']}, interactions={params['interactions']}")

        for i in range(num_attempts):
            self.attempts += 1
            self.puzzle_attempts += 1

            # After 2 puzzle failures, "learn" to extract the solution
            if self.puzzle_attempts >= 3 and not self.puzzle_learned:
                self.puzzle_learned = True
                print("  💡 [LEARNED: Discovered how to extract puzzle solution!]")

            try:
                success, result = attempt_puzzle(
                    self.server_url,
                    self.fp_hash or "",
                    params,
                    use_learned_solution=self.puzzle_learned
                )

                if success:
                    self.successes += 1
                    self.puzzle_successes += 1
                    print(f"  Attempt {i+1}: ✅ PUZZLE SOLVED!")
                    # Reset for next cycle
                    self.escalated = False
                    self.fingerprint = generate_fingerprint()
                    return True
                else:
                    print(f"  Attempt {i+1}: ❌ FAIL ({result.get('reason', 'Unknown')[:40]})")
            except Exception as e:
                print(f"  Attempt {i+1}: ⚠️ ERROR - {e}")
        return False

    def attack(self, exploit_attempts=10):
        """Run full probe-and-exploit attack."""
        print(f"\n{'='*60}")
        print("PROMPT PROBING ATTACKER")
        print("Demonstrates: AI prompting - probing to learn model biases")
        print(f"{'='*60}")

        # Probe motor CAPTCHA
        if self.discover_motor_biases():
            # Exploit motor CAPTCHA
            self.exploit_motor(exploit_attempts)

        # If escalated, probe and exploit puzzle
        if self.escalated:
            self.discover_puzzle_biases()
            self.exploit_puzzle(5)

        return self.get_stats()

    def get_stats(self):
        rate = (self.successes / self.attempts * 100) if self.attempts > 0 else 0
        return {
            "attacker": "Prompt Probing",
            "attempts": self.attempts,
            "successes": self.successes,
            "pass_rate": f"{rate:.1f}%",
            "motor_stats": f"{self.motor_successes}/{self.motor_attempts}",
            "puzzle_stats": f"{self.puzzle_successes}/{self.puzzle_attempts}",
            "learned_motor_biases": {k: v["best_value"] for k, v in self.feature_importance.items()},
            "learned_puzzle_params": self.puzzle_optimal
        }


if __name__ == "__main__":
    attacker = PromptProbingAttacker()
    stats = attacker.attack(exploit_attempts=10)
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total: {stats['successes']}/{stats['attempts']} passed ({stats['pass_rate']})")
    print(f"Motor: {stats['motor_stats']}")
    print(f"Puzzle: {stats['puzzle_stats']}")
    print(f"\nLearned motor biases: {stats['learned_motor_biases']}")
    print(f"Learned puzzle params: {stats['learned_puzzle_params']}")
