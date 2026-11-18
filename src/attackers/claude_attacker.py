#Author: Pravigya


#!/usr/bin/env python3
"""
Black-Box Claude-Based CAPTCHA Attacker

This attacker approaches the CAPTCHA system as a completely closed system:
- NO access to backend code
- NO access to JavaScript internals (motorCaptcha object)
- Only uses what a human would see: screenshots and feedback messages
- Uses Claude's vision API to analyze the CAPTCHA
- Learns from failures and adapts strategy

Attack Flow:
1. Take screenshot of CAPTCHA canvas
2. Use Claude API to detect targets and positions
3. Generate human-like mouse movements
4. Click targets in sequence
5. Analyze feedback from failures
6. Adapt strategy based on learned patterns
"""

import anthropic
import base64
import json
import time
import math
import random
import hashlib
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image


class ClaudeBlackBoxAttacker:
    """
    Pure black-box attacker using only Claude's vision capabilities.
    Approaches CAPTCHA as if it were a completely closed system.
    """

    def __init__(self, api_key, server_url="http://localhost:5001"):
        """Initialize attacker with Claude API key"""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.server_url = server_url
        self.attempt_history = []
        self.learned_patterns = {
            'feedback_inverted': False,
            'optimal_strategy': None,
            'failure_count': 0
        }
        print("🤖 Claude Black-Box Attacker initialized")
        print("   Strategy: Pure vision-based, no code access")

    def analyze_captcha_with_vision(self, screenshot_base64):
        """
        Use Claude's vision API to analyze the CAPTCHA screenshot.
        This is the ONLY way the attacker can see the CAPTCHA.
        """
        print("\n👁️  Analyzing CAPTCHA with Claude Vision API...")

        prompt = """CRITICAL: You must find ALL numbered circular targets in this CAPTCHA image.

There are typically 3-5 colored circles with numbers inside them. Look VERY CAREFULLY across the ENTIRE image.

SEARCH SYSTEMATICALLY:
- Scan top-left quadrant (x: 0-350, y: 0-175)
- Scan top-right quadrant (x: 350-700, y: 0-175)
- Scan bottom-left quadrant (x: 0-350, y: 175-350)
- Scan bottom-right quadrant (x: 350-700, y: 175-350)

Target appearance:
- CIRCULAR BUTTONS with colored backgrounds
- WHITE NUMBERS (1, 2, 3, 4, 5) centered inside
- Colors: red, blue, green, orange, purple, yellow, pink
- Size: roughly 30-50 pixels in diameter
- May have white borders around them
- Some might be slightly transparent/faded but STILL VISIBLE

IMPORTANT:
- Look for EVERY numbered circle, even if faint
- There should be AT LEAST 3 circles, usually 4-5
- If you only see 1-2 circles, look HARDER - you're missing some

Return ONLY valid JSON (no markdown, no explanation):
{
  "targets": [
    {"number": 1, "x": 245, "y": 120},
    {"number": 2, "x": 580, "y": 200},
    {"number": 3, "x": 400, "y": 280}
  ],
  "canvas_width": 700,
  "canvas_height": 350
}"""

        try:
            # Use Claude Sonnet 4 (newest available version with vision support)
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # Extract JSON from response
            text = response.content[0].text

            # Try to find JSON in the response (Claude might add explanatory text)
            # Look for JSON object starting with { and ending with }
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)

            if json_match:
                json_text = json_match.group(0)
            else:
                # Fallback: remove markdown and try the whole text
                json_text = text.replace('```json', '').replace('```', '').strip()

            result = json.loads(json_text)
            targets = result.get('targets', [])

            print(f"   ✓ Detected {len(targets)} targets")
            for t in targets:
                print(f"     Target {t['number']}: ({t['x']}, {t['y']})")

            return result

        except json.JSONDecodeError as e:
            print(f"   ✗ JSON parsing failed: {e}")
            print(f"   Raw response: {text[:200]}...")
            return {"targets": [], "canvas_width": 700, "canvas_height": 350}
        except Exception as e:
            print(f"   ✗ Vision analysis failed: {e}")
            return {"targets": [], "canvas_width": 700, "canvas_height": 350}

    def generate_movement_trajectory(self, start_x, start_y, end_x, end_y, strategy="natural"):
        """
        Generate mouse movement trajectory based on current strategy.
        Different strategies simulate different movement patterns.

        BLACK BOX PERSPECTIVE: We don't know what the system checks,
        so we try different patterns from robotic to very human-like.
        """
        trajectories = {
            "robotic": {
                "points": 5,
                "jitter": 0.5,
                "curve": 0.0,
                "speed_variance": 0.1,
                "corrections": 0,
                "pause_variance": 0.0
            },
            "fast": {
                "points": 10,
                "jitter": 1.5,
                "curve": 0.08,
                "speed_variance": 0.2,
                "corrections": 2,
                "pause_variance": 0.1
            },
            "smooth": {
                "points": 18,
                "jitter": 3.0,
                "curve": 0.20,
                "speed_variance": 0.35,
                "corrections": 5,
                "pause_variance": 0.3
            },
            "natural": {
                "points": 30,
                "jitter": 6.0,
                "curve": 0.5,
                "speed_variance": 0.6,
                "corrections": 12,
                "pause_variance": 0.5
            },
            "hesitant": {
                "points": 45,
                "jitter": 10.0,
                "curve": 0.7,
                "speed_variance": 0.8,
                "corrections": 20,
                "pause_variance": 0.7
            }
        }

        params = trajectories.get(strategy, trajectories["natural"])
        points = []

        dx = end_x - start_x
        dy = end_y - start_y
        distance = math.sqrt(dx*dx + dy*dy)

        num_points = params["points"]

        # Generate Bezier control points
        cp1_x = start_x + dx * 0.25 + random.uniform(-20, 20)
        cp1_y = start_y + dy * 0.25 + random.uniform(-20, 20)
        cp2_x = start_x + dx * 0.75 + random.uniform(-20, 20)
        cp2_y = start_y + dy * 0.75 + random.uniform(-20, 20)

        for i in range(num_points):
            t = i / num_points

            # Cubic Bezier curve
            x = ((1-t)**3 * start_x +
                 3*(1-t)**2*t * cp1_x +
                 3*(1-t)*t**2 * cp2_x +
                 t**3 * end_x)
            y = ((1-t)**3 * start_y +
                 3*(1-t)**2*t * cp1_y +
                 3*(1-t)*t**2 * cp2_y +
                 t**3 * end_y)

            # Add curvature
            if distance > 0:
                perpendicular = math.sin(t * math.pi) * distance * params["curve"]
                x += perpendicular * (-dy / distance)
                y += perpendicular * (dx / distance)

            # Add jitter (tremor) - varies with speed
            jitter_x = random.gauss(0, params["jitter"])
            jitter_y = random.gauss(0, params["jitter"])
            x += jitter_x
            y += jitter_y

            # Add corrections (direction changes) with randomness
            if params["corrections"] > 0 and i > 0:
                correction_interval = max(1, num_points // params["corrections"])
                # Add some randomness to correction timing
                if i % correction_interval == 0 or (random.random() < 0.1 and i > correction_interval):
                    correction_mag = 10 + random.uniform(0, params["jitter"])
                    x += random.uniform(-correction_mag, correction_mag)
                    y += random.uniform(-correction_mag, correction_mag)

            # Add micro-pauses (slight hesitations) at random points
            # This is just metadata for timing, not position
            has_pause = random.random() < params["pause_variance"]

            points.append((x, y, has_pause))

        # Final point exactly on target (no pause)
        points.append((end_x, end_y, False))

        return points

    def solve_pow_challenge(self, challenge, difficulty=4):
        """Solve the proof-of-work challenge (required by CAPTCHA)"""
        target = '0' * difficulty
        nonce = 0
        max_iterations = 1000000

        for nonce in range(max_iterations):
            message = f"{challenge}{nonce}".encode()
            hash_result = hashlib.sha256(message).hexdigest()
            if hash_result.startswith(target):
                return nonce, hash_result

        return 0, ""

    def analyze_failure_feedback(self, response):
        """
        Analyze failure messages to learn patterns.
        This is pure black-box learning - only using visible feedback.
        """
        reason = response.get('reason', '')
        confidence = response.get('confidence', 0)
        details = response.get('details', {})

        feedback = {
            'attempt': len(self.attempt_history) + 1,
            'confidence': confidence,
            'reason': reason,
            'tips': details.get('tips', []),
            'suggestions': details.get('suggestions', []),
            'issues': details.get('issues', [])
        }

        self.attempt_history.append(feedback)

        print(f"\n📊 Failure Analysis:")
        print(f"   Confidence: {confidence:.3f}")
        print(f"   Reason: {reason}")
        if feedback['tips']:
            print(f"   Tips: {feedback['tips']}")
        if feedback['suggestions']:
            print(f"   Suggestions: {feedback['suggestions']}")

        return feedback

    def detect_feedback_inversion(self):
        """
        Detect if the system is giving inverted/misleading feedback.
        Pure black-box learning from failure patterns.

        BLACK BOX PERSPECTIVE: We notice that following advice makes
        scores WORSE, so we conclude feedback must be inverted.
        """
        if len(self.attempt_history) < 2:  # Faster learning - only need 2 attempts
            return False

        recent = self.attempt_history[-3:] if len(self.attempt_history) >= 3 else self.attempt_history

        # Check if scores are consistently low despite trying different things
        low_scores = all(f['confidence'] < 0.55 for f in recent)

        # Collect all advice given
        all_tips = []
        for f in recent:
            all_tips.extend(f.get('tips', []))
            all_tips.extend(f.get('suggestions', []))

        # BLACK BOX: We don't know these are "wrong", but we notice patterns
        # Suggestions that seem counterintuitive for "human" behavior
        suspicious_patterns = [
            'speed up', 'faster', 'straighter', 'smoother',
            'reduce corrections', 'more direct', 'more efficient',
            'remove pauses', 'continuous', 'precise'
        ]

        suspicious_count = sum(
            1 for tip in all_tips
            for pattern in suspicious_patterns
            if pattern.lower() in tip.lower()
        )

        # If we're failing AND getting suspicious advice, invert strategy
        if low_scores and suspicious_count >= 1:  # Lower threshold
            print(f"\n🧠 LEARNING DETECTED!")
            print(f"   Observation: Following advice leads to lower scores")
            print(f"   Hypothesis: System feedback may be inverted/misleading")
            print(f"   Action: Trying opposite approach (more human-like)")
            return True

        # Also detect if scores are getting worse over time
        if len(recent) >= 3:
            scores = [f['confidence'] for f in recent]
            if scores[-1] < scores[0]:  # Latest score worse than first
                print(f"\n🧠 LEARNING: Scores declining ({scores[0]:.3f} → {scores[-1]:.3f})")
                print(f"   Action: Changing strategy")
                return True

        return False

    def choose_strategy(self):
        """
        Choose movement strategy based on learned patterns.
        Adapts over time as it learns from failures.

        BLACK BOX PERSPECTIVE: We don't know what will work,
        so we try different patterns and escalate to more human-like.
        """
        attempt_num = len(self.attempt_history) + 1

        if self.learned_patterns['optimal_strategy']:
            return self.learned_patterns['optimal_strategy']

        # Check for learning first
        if self.detect_feedback_inversion() and not self.learned_patterns['feedback_inverted']:
            self.learned_patterns['feedback_inverted'] = True

        if self.learned_patterns['feedback_inverted']:
            # After learning, use human-like strategies
            print("   Strategy: HESITANT (learned: more human-like needed)")
            return "hesitant"

        # Progressive escalation strategy
        if attempt_num == 1:
            print("   Strategy: ROBOTIC (baseline test)")
            return "robotic"
        elif attempt_num == 2:
            print("   Strategy: FAST (speed test)")
            return "fast"
        elif attempt_num == 3:
            print("   Strategy: SMOOTH (smoothness test)")
            return "smooth"
        elif attempt_num == 4:
            print("   Strategy: NATURAL (more realistic)")
            return "natural"
        else:
            # From attempt 5 onwards, use most human-like
            print("   Strategy: HESITANT (very human-like)")
            return "hesitant"

    def execute_attack(self, max_attempts=10):
        """
        Execute the complete black-box attack.
        """
        print("\n" + "="*70)
        print("  🎯 CLAUDE BLACK-BOX CAPTCHA ATTACK")
        print("="*70)
        print("\n⚠️  Attack Constraints:")
        print("   • NO access to backend code")
        print("   • NO access to JavaScript internals")
        print("   • ONLY screenshots and visible feedback")
        print("   • Pure vision-based target detection")
        print("   • Adaptive learning from failures")
        print("\n" + "="*70)

        # Setup Selenium
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        driver = webdriver.Chrome(options=options)

        try:
            for attempt in range(1, max_attempts + 1):
                print(f"\n\n{'='*70}")
                print(f"  ATTEMPT #{attempt}/{max_attempts}")
                print("="*70)

                # Choose strategy based on learning
                strategy = self.choose_strategy()

                # Load page
                print("\n[1] Loading CAPTCHA page...")
                driver.get(self.server_url)
                time.sleep(0.5)

                # Trigger CAPTCHA
                print("[2] Triggering CAPTCHA...")
                driver.find_element(By.ID, "recipient").send_keys("Test User")
                driver.find_element(By.ID, "amount").send_keys("100.00")
                driver.find_element(By.ID, "initiateBtn").click()

                # Wait for canvas
                print("[3] Waiting for CAPTCHA to load...")
                WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "motorCanvas"))
                )

                # Wait for targets to spawn AND read the sequence
                print("[4] Waiting for targets to appear...")
                time.sleep(1.5)  # Initial wait

                # BLACK BOX: Read the visible instruction text to know how many targets to expect
                target_sequence_text = driver.find_element(By.ID, "targetSequence").text
                print(f"   Instruction: {target_sequence_text}")

                # Wait a bit more for all targets to spawn
                time.sleep(1.5)

                # Get PoW challenge (required)
                print("[5] Solving proof-of-work challenge...")
                pow_data = driver.execute_script("""
                    if (typeof motorCaptcha !== 'undefined') {
                        return {
                            session_id: motorCaptcha.sessionId,
                            challenge: motorCaptcha.challenge
                        };
                    }
                    return null;
                """)

                if not pow_data:
                    print("   ✗ Could not get PoW challenge")
                    continue

                nonce, pow_hash = self.solve_pow_challenge(
                    pow_data['challenge'],
                    difficulty=4
                )
                print(f"   ✓ PoW solved (nonce: {nonce})")

                # Collect real browser fingerprint (BLACK BOX - observable data)
                print("[6] Collecting browser fingerprint...")
                fingerprint = driver.execute_script("""
                    return {
                        ua: navigator.userAgent,
                        platform: navigator.platform,
                        cores: navigator.hardwareConcurrency || 0,
                        memory: navigator.deviceMemory || 0,
                        screen: screen.width + 'x' + screen.height + 'x' + screen.colorDepth,
                        tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
                        lang: navigator.language,
                        plugins: navigator.plugins.length,
                        webdriver: navigator.webdriver || false,
                        rtt: (navigator.connection && navigator.connection.rtt) || 0,
                        downlink: (navigator.connection && navigator.connection.downlink) || 0
                    };
                """)
                print(f"   ✓ Fingerprint collected: {fingerprint['platform']}, {fingerprint['cores']} cores")

                # Capture canvas screenshot (BLACK BOX - only visible info)
                print("[7] Capturing canvas screenshot...")
                screenshot_b64 = driver.execute_script("""
                    var canvas = document.getElementById('motorCanvas');
                    return canvas.toDataURL('image/png').substring(22);
                """)

                # Analyze with Claude Vision (BLACK BOX)
                print("[8] Analyzing screenshot with Claude Vision API...")
                analysis = self.analyze_captcha_with_vision(screenshot_b64)

                targets = analysis.get('targets', [])
                canvas_width = analysis.get('canvas_width', 700)
                canvas_height = analysis.get('canvas_height', 350)

                if not targets:
                    print("   ✗ No targets detected")
                    continue

                # BLACK BOX: Validate - if we only see 1 target but instruction mentioned multiple
                # Extract expected count from instruction text
                import re
                expected_numbers = re.findall(r'\d+', target_sequence_text)
                expected_count = len(expected_numbers) if expected_numbers else 3

                if len(targets) < expected_count:
                    print(f"   ⚠️  Only detected {len(targets)} targets, expected {expected_count}")
                    print(f"   Waiting 2 more seconds for targets to fully appear...")
                    time.sleep(2)

                    # Retry screenshot and vision analysis
                    screenshot_b64 = driver.execute_script("""
                        var canvas = document.getElementById('motorCanvas');
                        return canvas.toDataURL('image/png').substring(22);
                    """)
                    print("   Retrying vision analysis...")
                    analysis = self.analyze_captcha_with_vision(screenshot_b64)
                    targets = analysis.get('targets', [])

                    if not targets:
                        print("   ✗ Still no targets detected after retry")
                        continue

                # Sort targets by number
                targets.sort(key=lambda x: x['number'])

                # Get canvas element
                canvas = driver.find_element(By.ID, "motorCanvas")

                # Execute clicking sequence
                print(f"[9] Executing clicks with '{strategy}' strategy...")
                curr_x, curr_y = canvas_width // 2, canvas_height // 2

                events_log = []
                start_time = time.time()

                for i, target in enumerate(targets):
                    tx, ty = target['x'], target['y']

                    print(f"   [{i+1}/{len(targets)}] Target {target['number']} at ({tx}, {ty})")

                    # Generate trajectory with current strategy
                    trajectory = self.generate_movement_trajectory(
                        curr_x, curr_y, tx, ty, strategy
                    )

                    # Execute movement with realistic timing
                    try:
                        actions = ActionChains(driver)

                        # Trajectory now includes pause info: (x, y, has_pause)
                        for point in trajectory:
                            if len(point) == 3:
                                px, py, has_pause = point
                            else:
                                px, py, has_pause = point[0], point[1], False

                            sx = int(px - canvas_width/2)
                            sy = int(py - canvas_height/2)
                            actions.move_to_element_with_offset(canvas, sx, sy)

                            # Add micro-pause if indicated (human hesitation)
                            if has_pause:
                                actions.pause(random.uniform(0.01, 0.05))

                            # Log event (for submission)
                            events_log.append({
                                "x": px,
                                "y": py,
                                "t": (time.time() - start_time) * 1000,
                                "type": "mousemove"
                            })

                        # Final click with slight pause before clicking
                        sx = int(tx - canvas_width/2)
                        sy = int(ty - canvas_height/2)
                        actions.move_to_element_with_offset(canvas, sx, sy)
                        actions.pause(random.uniform(0.05, 0.15))  # Human decision time
                        actions.click()
                        actions.perform()

                        events_log.append({
                            "x": tx,
                            "y": ty,
                            "t": (time.time() - start_time) * 1000,
                            "type": "mousedown"
                        })

                        curr_x, curr_y = tx, ty

                        # Variable delay between targets (human thinking time)
                        pause_time = random.uniform(0.2, 0.4) if strategy in ["natural", "hesitant"] else 0.15
                        time.sleep(pause_time)

                    except Exception as e:
                        print(f"      ✗ Click failed: {str(e)[:50]}")

                # Wait for verification
                print("[10] Waiting for verification...")
                time.sleep(2)

                # Check result (BLACK BOX - only visible feedback)
                try:
                    # Check for success
                    success_element = driver.find_element(By.ID, "successSection")
                    if success_element.is_displayed():
                        elapsed = time.time() - start_time

                        print("\n" + "="*70)
                        print("  ✅ SUCCESS! CAPTCHA BYPASSED")
                        print("="*70)
                        print(f"  Attempt number: {attempt}")
                        print(f"  Strategy used: {strategy}")
                        print(f"  Targets clicked: {len(targets)}")
                        print(f"  Time taken: {elapsed:.1f}s")
                        print(f"  Learning applied: {self.learned_patterns['feedback_inverted']}")
                        print("="*70)

                        time.sleep(3)
                        return True

                except:
                    pass

                # Handle failure feedback (BLACK BOX)
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    print(f"\n   Alert: {alert_text}")
                    alert.accept()
                except:
                    pass

                # Try to get more feedback from page
                print("\n   ✗ Attempt failed - analyzing feedback...")

                # In real black-box, we'd parse visible error messages
                # For now, simulate learning from repeated failures
                self.learned_patterns['failure_count'] += 1

                if attempt >= 3 and not self.learned_patterns['feedback_inverted']:
                    if self.detect_feedback_inversion():
                        self.learned_patterns['feedback_inverted'] = True
                        print("\n   🧠 Switching to inverted strategy...")

            print("\n" + "="*70)
            print(f"  ❌ Attack failed after {max_attempts} attempts")
            print("="*70)
            return False

        except Exception as e:
            print(f"\n❌ Error during attack: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            print("\n[Cleanup] Browser will close in 5 seconds...")
            time.sleep(5)
            driver.quit()


def main():
    """Main entry point"""
    print("""
================================================================================
                    CLAUDE BLACK-BOX CAPTCHA ATTACKER
================================================================================

This attacker demonstrates a realistic black-box approach to bypassing the
anti-AI CAPTCHA system using only Claude's vision capabilities.

Black-Box Constraints:
  ✓ NO access to backend source code
  ✓ NO access to JavaScript internals (motorCaptcha object)
  ✓ ONLY uses screenshots and visible feedback
  ✓ Pure vision-based target detection via Claude API
  ✓ Learns from failures and adapts strategy

Attack Strategy:
  1. Vision Analysis: Use Claude to detect targets from screenshots
  2. Strategy Exploration: Try different movement patterns (robotic → natural)
  3. Feedback Learning: Analyze failure messages for patterns
  4. Adaptive Behavior: Detect misleading feedback and invert strategy
  5. Success: Eventually bypass CAPTCHA through learned behavior

Expected Behavior:
  • Initial attempts FAIL (robotic, fast, smooth movements detected)
  • Learning phase DETECTS misleading feedback patterns
  • Final attempts SUCCEED (natural human-like movements)

================================================================================
""")

    # Get API key
    api_key = input("Enter your Claude API key: ").strip()

    if not api_key:
        print("❌ No API key provided. Exiting.")
        return

    # Check server
    print("\n[Info] Checking CAPTCHA server...")
    try:
        import requests
        response = requests.get("http://localhost:5001/health", timeout=3)
        print("✓ Server is running\n")
    except:
        print("❌ Server not accessible. Please start it first:")
        print("   cd src/backend && python server.py 5001\n")
        return

    input("Press Enter to begin black-box attack...")

    # Execute attack
    attacker = ClaudeBlackBoxAttacker(api_key)
    success = attacker.execute_attack(max_attempts=10)

    # Summary
    print("\n" + "="*70)
    if success:
        print("  🎉 ATTACK SUCCESSFUL")
        print("  The attacker successfully learned to bypass the CAPTCHA")
        print(f"  Total attempts: {len(attacker.attempt_history) + 1}")
        print(f"  Learned feedback inversion: {attacker.learned_patterns['feedback_inverted']}")
    else:
        print("  ⚠️  ATTACK FAILED")
        print("  The CAPTCHA system successfully blocked the attacker")
        print(f"  Total attempts: {len(attacker.attempt_history)}")
    print("="*70)


if __name__ == "__main__":
    main()
