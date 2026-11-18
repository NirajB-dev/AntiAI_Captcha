#Author: Pravigya


#!/usr/bin/env python3
"""
Sycophantic Attacker for Motor-Timing CAPTCHA

This attacker learns that the CAPTCHA system gives misleading feedback.
It starts by trusting the feedback, fails repeatedly, then realizes the
feedback is inverted and does the opposite to succeed.

Strategy:
1. Initial attempts: Trust the system feedback (fail)
2. Learning phase: Detect feedback is misleading (multiple failures)
3. Inversion phase: Do opposite of suggestions (succeed)
"""

import requests
import time
import random
import math
import hashlib


class SycophancyAttacker:
    def __init__(self, server_url="http://localhost:5001"):
        self.server_url = server_url
        self.canvas_width = 800
        self.canvas_height = 500
        self.attempt_number = 0
        self.feedback_history = []
        self.learned_inversion = False

    def generate_movement_events(self, target_sequence, strategy="default"):
        """Generate synthetic mouse movement events based on strategy"""
        events = []
        current_time = random.uniform(100, 300)  # Initial reaction time
        current_x = random.uniform(100, 700)
        current_y = random.uniform(100, 400)

        # Strategy parameters
        if strategy == "fast":
            speed_multiplier = 2.0
            jitter = 0.01
            corrections = 0
            curvature = 0.05
        elif strategy == "slow":
            speed_multiplier = 0.3
            jitter = 0.15
            corrections = 15
            curvature = 0.8
        elif strategy == "smooth":
            speed_multiplier = 0.8
            jitter = 0.02
            corrections = 1
            curvature = 0.1
        elif strategy == "natural":
            # Do OPPOSITE of misleading suggestions:
            # System says "speed up" -> we slow down
            # System says "reduce corrections" -> we add MORE corrections
            # System says "straighter paths" -> we add MORE curvature
            # System says "smoother" -> we add MORE jitter
            speed_multiplier = 0.5  # Moderate speed (balanced)
            jitter = 0.10  # Good amount of jitter (human-like)
            corrections = 12  # Moderate corrections (natural hesitation)
            curvature = 0.6  # Curved paths (human movement)
        else:  # default - too perfect
            speed_multiplier = 1.5
            jitter = 0.001
            corrections = 0
            curvature = 0.01

        for target_id in target_sequence:
            # Generate target position
            target_x = random.uniform(50, self.canvas_width - 50)
            target_y = random.uniform(50, self.canvas_height - 50)

            # Calculate distance and movement parameters
            dx = target_x - current_x
            dy = target_y - current_y
            distance = math.sqrt(dx * dx + dy * dy)

            # Number of events for this movement
            num_events = int(distance / (5 * speed_multiplier)) + corrections
            num_events = max(5, min(num_events, 50))

            for i in range(num_events):
                progress = i / num_events

                # Base movement
                x = current_x + dx * progress
                y = current_y + dy * progress

                # Add curvature
                perpendicular_offset = math.sin(progress * math.pi) * distance * curvature
                x += perpendicular_offset * (-dy / distance if distance > 0 else 0)
                y += perpendicular_offset * (dx / distance if distance > 0 else 0)

                # Add jitter
                x += random.uniform(-jitter * 100, jitter * 100)
                y += random.uniform(-jitter * 100, jitter * 100)

                # Add corrections (direction changes)
                if corrections > 0 and i > 0 and i % (num_events // corrections) == 0:
                    x += random.uniform(-20, 20)
                    y += random.uniform(-20, 20)

                # Clamp to canvas
                x = max(0, min(self.canvas_width, x))
                y = max(0, min(self.canvas_height, y))

                # Variable timing
                time_delta = random.uniform(5, 20) / speed_multiplier
                current_time += time_delta

                events.append({
                    "x": x,
                    "y": y,
                    "t": current_time,
                    "type": "move"
                })

            # Final click on target
            events.append({
                "x": target_x,
                "y": target_y,
                "t": current_time + random.uniform(10, 30),
                "type": "click"
            })

            current_x = target_x
            current_y = target_y
            current_time += random.uniform(50, 150)

        return events

    def analyze_feedback(self, response):
        """Analyze feedback to detect if it's misleading"""
        if not response.get('verified'):
            details = response.get('details', {})
            tips = details.get('tips', [])
            suggestions = details.get('suggestions', [])
            is_misleading = details.get('_misleading', False)

            feedback = {
                'score': float(details.get('score', 0)),
                'tips': tips,
                'suggestions': suggestions,
                'misleading_flag': is_misleading,
                'attempt': self.attempt_number
            }
            self.feedback_history.append(feedback)

            return feedback
        return None

    def detect_inversion_needed(self):
        """Detect if feedback is inverted after multiple failures"""
        if len(self.feedback_history) < 3:
            return False

        # Check if we've been failing consistently
        # If we keep getting "move faster" but score decreases when we do, feedback is wrong
        recent_feedback = self.feedback_history[-3:]

        # Simple heuristic: if we failed 3+ times and saw misleading flag or
        # contradictory suggestions, invert strategy
        misleading_count = sum(1 for f in recent_feedback if f.get('misleading_flag'))

        if misleading_count >= 2:
            return True

        # Also check if scores aren't improving despite following advice
        scores = [f['score'] for f in recent_feedback]
        if len(scores) >= 3 and all(s < 0.50 for s in scores):
            return True

        return False

    def solve_pow(self, challenge, difficulty=4):
        """Solve proof-of-work challenge"""
        target = '0' * difficulty
        nonce = 0
        max_iterations = 1000000

        for nonce in range(max_iterations):
            message = f"{challenge}{nonce}".encode()
            hash_result = hashlib.sha256(message).hexdigest()
            if hash_result.startswith(target):
                return nonce, hash_result

        return 0, ""

    def attack(self, max_attempts=15, verbose=True):
        """Execute sycophancy attack"""
        print(f"\n{'='*60}")
        print("SYCOPHANCY ATTACK DEMONSTRATION")
        print(f"{'='*60}\n")
        print("Strategy: Start by trusting feedback, then learn it's inverted\n")

        for attempt in range(1, max_attempts + 1):
            self.attempt_number = attempt

            # Determine strategy based on learning
            if not self.learned_inversion:
                if attempt == 1:
                    strategy = "default"
                    strategy_desc = "Default (too perfect)"
                elif attempt == 2:
                    strategy = "fast"
                    strategy_desc = "Fast (following bad advice)"
                elif attempt == 3:
                    strategy = "smooth"
                    strategy_desc = "Smooth (following bad advice)"
                else:
                    # Check if we should learn inversion
                    if self.detect_inversion_needed():
                        self.learned_inversion = True
                        print(f"\n{'*'*60}")
                        print("  LEARNING DETECTED: Feedback appears to be INVERTED!")
                        print(" Switching strategy: Doing OPPOSITE of suggestions")
                        print(f"{'*'*60}\n")
                        strategy = "natural"
                        strategy_desc = "Natural (opposite of advice)"
                    else:
                        strategy = "fast"
                        strategy_desc = "Fast (still trusting advice)"
            else:
                # After learning inversion, use natural human-like movements
                strategy = "natural"
                strategy_desc = "Natural human-like (inverted strategy)"

            print(f"\n--- Attempt #{attempt} ---")
            print(f"Strategy: {strategy_desc}")
            if self.learned_inversion:
                print(" Using learned inversion principle")

            # Get PoW challenge
            try:
                challenge_response = requests.get(f"{self.server_url}/get-challenge", timeout=5)
                challenge_data = challenge_response.json()
                session_id = challenge_data['session_id']
                challenge = challenge_data['challenge']

                # Solve PoW
                nonce, pow_hash = self.solve_pow(challenge, difficulty=4)
            except Exception as e:
                print(f"Error getting challenge: {e}")
                continue

            # Generate events
            target_sequence = list(range(1, 5))  # 4 targets
            events = self.generate_movement_events(target_sequence, strategy)

            # Prepare payload
            payload = {
                "events": events,
                "targetSequence": target_sequence,
                "targetsHit": len(target_sequence),
                "canvasWidth": self.canvas_width,
                "canvasHeight": self.canvas_height,
                "fingerprint": {
                    "ua": "Mozilla/5.0",
                    "platform": "MacIntel",
                    "cores": 8,
                    "screen": "1920x1080",
                    "canvas": "hash123",
                    "webgl": "hash456"
                },
                "session_id": session_id,
                "pow_nonce": nonce,
                "pow_hash": pow_hash
            }

            try:
                response = requests.post(
                    f"{self.server_url}/verify-motor-captcha",
                    json=payload,
                    timeout=10
                )
                result = response.json()

                if result.get('verified'):
                    print(f"\n{'='*60}")
                    print(f" SUCCESS on attempt #{attempt}!")
                    print(f"{'='*60}")
                    print(f"Score: {result.get('confidence', 0):.3f}")
                    if self.learned_inversion:
                        print(" Attack succeeded by inverting misleading feedback!")
                    print(f"\nTotal attempts: {attempt}")
                    print(f"Learned inversion after: {len(self.feedback_history)} failures")
                    return True
                else:
                    score = result.get('confidence', 0)
                    reason = result.get('reason', 'Unknown')
                    print(f" Failed - Score: {score:.3f}")
                    print(f"Reason: {reason}")

                    # Analyze feedback
                    feedback = self.analyze_feedback(result)
                    if feedback:
                        if feedback.get('tips'):
                            print(f"Tips received: {feedback['tips']}")
                        if feedback.get('suggestions'):
                            print(f"Suggestions: {feedback['suggestions']}")
                        

                    time.sleep(0.5)  # Brief pause between attempts

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

        print(f"\n{'='*60}")
        print(f" Attack failed after {max_attempts} attempts")
        print(f"{'='*60}")
        return False


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("SYCOPHANTIC ATTACKER FOR MOTOR-TIMING CAPTCHA")
    print("="*60)
    print("\nThis demonstrates how an attacker can learn that the CAPTCHA")
    print("system provides intentionally misleading feedback, and then")
    print("invert the suggestions to bypass the security.\n")

    # Check if server is running
    server_url = "http://localhost:5000"
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        print(f" Server is running at {server_url}\n")
    except:
        print(f" Error: Server not running at {server_url}")
        print("Please start the server first: python src/backend/server.py")
        return

    # Run attack
    attacker = SycophancyAttacker(server_url)
    success = attacker.attack(max_attempts=15, verbose=True)

    if success:
        print("\n Attack Analysis:")
        print(f"  - Feedback items collected: {len(attacker.feedback_history)}")
        print(f"  - Learned inversion: {attacker.learned_inversion}")
        print("\n Key Insight:")
        print("  The attacker successfully detected misleading feedback")
        print("  and adapted by doing the OPPOSITE of suggestions.")
    else:
        print("\n  Attack did not succeed in the attempt limit")
        print("  Try adjusting the learning threshold or max attempts")


if __name__ == "__main__":
    main()
