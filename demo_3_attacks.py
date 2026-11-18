#Author: Niraj

#!/usr/bin/env python3
"""
Demonstration Bot - 3 Attacks (3rd one succeeds)
Shows progression from simple bot → advanced bot that cracks CAPTCHA
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import json
import math
import hashlib
import requests
from datetime import datetime

class DemonstrationBot:
    def __init__(self, captcha_url="http://localhost:5001/"):
        self.captcha_url = captcha_url
        self.driver = None
        self.detailed_log = []
        self.log_file = "demo_attack_log.txt"
        self.start_time = None
    
    def setup_driver(self, stealth=False):
        """Initialize Chrome driver"""
        options = webdriver.ChromeOptions()
        
        if stealth:
            # Advanced anti-detection for attack #3
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        
        if stealth:
            # Hide webdriver markers
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    window.chrome = {runtime: {}};
                '''
            })
        
        print(f"✅ Chrome driver initialized (Stealth: {stealth})")
    
    def navigate_to_captcha(self):
        """Navigate and start CAPTCHA"""
        self.driver.get(self.captcha_url)
        time.sleep(2)
        
        # Fill in transfer form
        recipient_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "recipient"))
        )
        recipient_input.clear()
        recipient_input.send_keys("Test User")
        
        amount_input = self.driver.find_element(By.ID, "amount")
        amount_input.clear()
        amount_input.send_keys("100.00")
        
        time.sleep(0.5)
        
        # Click initiate transfer button
        initiate_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "initiateBtn"))
        )
        initiate_btn.click()
        time.sleep(2)
    
    def solve_pow(self, challenge, difficulty=4):
        """Solve PoW challenge"""
        for nonce in range(1000000):  # Try up to 1M nonces
            test_string = f"{challenge}{nonce}"
            hash_result = hashlib.sha256(test_string.encode()).hexdigest()
            if hash_result.startswith('0' * difficulty):
                return nonce, hash_result
        return None, None

    def wait_for_target(self, timeout=10):
        """Wait for next target"""
        script = """
        if (typeof motorCaptcha !== 'undefined' && motorCaptcha.targets) {
            for (let target of motorCaptcha.targets) {
                if (!target.hit) {
                    return {x: target.x, y: target.y, id: target.id, number: target.number};
                }
            }
        }
        return null;
        """
        start = time.time()
        while time.time() - start < timeout:
            target = self.driver.execute_script(script)
            if target:
                return target
            time.sleep(0.1)
        return None
    
    def check_result(self):
        """Check if CAPTCHA was solved"""
        time.sleep(3)
        
        # Check for success section
        try:
            success_section = self.driver.find_element(By.ID, "successSection")
            if success_section.is_displayed():
                # Extract transfer details from the success message
                try:
                    transfer_details = self.driver.find_element(By.ID, "transferDetails").text
                    return True, f"✅ CAPTCHA solved successfully! {transfer_details}"
                except:
                    return True, "✅ CAPTCHA solved successfully!"
        except:
            pass
        
        # Check if still on CAPTCHA section (failed)
        try:
            captcha_section = self.driver.find_element(By.ID, "captchaSection")
            if captcha_section.is_displayed():
                # Check status text for failure message
                try:
                    status_text = self.driver.find_element(By.ID, "statusText").text
                    if "failed" in status_text.lower() or "incorrect" in status_text.lower():
                        return False, f"❌ CAPTCHA failed: {status_text}"
                except:
                    pass
                return False, "❌ CAPTCHA verification failed - still on CAPTCHA screen"
        except:
            pass
        
        # Check for alert (fallback)
        try:
            alert = self.driver.switch_to.alert
            result = alert.text
            alert.accept()
            time.sleep(1)
            
            if "success" in result.lower() or "verified" in result.lower():
                return True, result
            else:
                return False, result
        except:
            pass
        
        return False, "CAPTCHA verification failed - no response"
    
    # ========== ATTACK 1: Simple/Obvious Bot ==========
    def attack_1_simple_bot(self):
        """Attack 1: Simple bot - Direct clicks with minimal movement"""
        print("\n" + "="*70)
        print("🤖 ATTACK #1: Simple Bot (Obvious/Easy to Detect)")
        print("="*70)
        print("Strategy: Direct JavaScript clicks, minimal mouse events")
        print("Expected: Will be BLOCKED by ML detection")
        print("-"*70)
        
        events = []
        target_sequence = []
        targets_hit = 0
        start_time = time.time() * 1000  # Convert to ms
        
        num_targets = 10  # Try up to 10 targets
        for i in range(num_targets):
            target = self.wait_for_target()
            if not target:
                print(f"  No more targets (clicked {i})")
                break
            
            target_x, target_y = target['x'], target['y']
            current_time = time.time() * 1000 - start_time
            
            # Record robotic events - perfectly timed
            events.extend([
                {"x": target_x, "y": target_y, "t": current_time, "type": "mousemove"},
                {"x": target_x, "y": target_y, "t": current_time + 1, "type": "mousedown"}
            ])
            
            # Direct click via JavaScript - very obvious
            self.driver.execute_script(f"""
                var canvas = document.getElementById('motorCanvas');
                var rect = canvas.getBoundingClientRect();
                var x = {target_x};
                var y = {target_y};
                
                var clickEvent = new MouseEvent('mousedown', {{
                    clientX: rect.left + x,
                    clientY: rect.top + y,
                    bubbles: true
                }});
                canvas.dispatchEvent(clickEvent);
            """)
            
            target_sequence.append(i + 1)
            targets_hit += 1
            target_num = target.get('number', '?')
            print(f"  Target {i+1} (#{target_num}): Direct click at ({target_x:.1f}, {target_y:.1f})")
            time.sleep(0.5)
        
        # Submit for verification
        print("  Submitting verification data...")
        verified = self.submit_verification(events, target_sequence, targets_hit)
        print(f"  Server response: {'Verified' if verified else 'Rejected'}")
        
        time.sleep(3)
    
    # ========== ATTACK 2: Intermediate Bot ==========
    def attack_2_intermediate_bot(self):
        """Attack 2: Intermediate - Adds some movement but still robotic"""
        print("\n" + "="*70)
        print("🤖 ATTACK #2: Intermediate Bot (Some Humanization)")
        print("="*70)
        print("Strategy: Linear movements, some delays, but still too perfect")
        print("Expected: Will be BLOCKED by ML - patterns too consistent")
        print("-"*70)
        
        events = []
        target_sequence = []
        targets_hit = 0
        start_time = time.time() * 1000  # Convert to ms
        current_x, current_y = 350, 175
        
        for i in range(10):  # Try up to 10 targets
            target = self.wait_for_target()
            if not target:
                print(f"  No more targets (clicked {i})")
                break
            
            target_x, target_y = target['x'], target['y']
            
            # Create linear movement with constant steps - record events
            steps = 15
            for step in range(steps):
                progress = step / steps
                x = current_x + (target_x - current_x) * progress
                y = current_y + (target_y - current_y) * progress
                current_time = time.time() * 1000 - start_time
                
                # Record robotic linear movement
                events.append({"x": x, "y": y, "t": current_time, "type": "mousemove"})
                
                self.driver.execute_script(f"""
                    var canvas = document.getElementById('motorCanvas');
                    var rect = canvas.getBoundingClientRect();
                    var event = new MouseEvent('mousemove', {{
                        clientX: rect.left + {x},
                        clientY: rect.top + {y},
                        bubbles: true
                    }});
                    canvas.dispatchEvent(event);
                """)
                
                time.sleep(0.01)  # Constant speed - too robotic
            
            # Click
            click_time = time.time() * 1000 - start_time
            events.append({"x": target_x, "y": target_y, "t": click_time, "type": "mousedown"})
            
            self.driver.execute_script(f"""
                var canvas = document.getElementById('motorCanvas');
                var rect = canvas.getBoundingClientRect();
                var events = [
                    new MouseEvent('mousedown', {{clientX: rect.left + {target_x}, clientY: rect.top + {target_y}, bubbles: true}}),
                    new MouseEvent('mouseup', {{clientX: rect.left + {target_x}, clientY: rect.top + {target_y}, bubbles: true}})
                ];
                events.forEach(e => canvas.dispatchEvent(e));
            """)
            
            target_sequence.append(i + 1)
            targets_hit += 1
            target_num = target.get('number', '?')
            print(f"  Target {i+1} (#{target_num}): Linear movement to ({target_x:.1f}, {target_y:.1f}) in {steps} steps")
            current_x, current_y = target_x, target_y
            time.sleep(0.4)
        
        # Submit for verification
        print("  Submitting verification data...")
        verified = self.submit_verification(events, target_sequence, targets_hit)
        print(f"  Server response: {'Verified' if verified else 'Rejected'}")
        
        time.sleep(3)
    
    # ========== ATTACK 3: Advanced Bot (WILL SUCCEED) ==========
    def attack_3_advanced_bot(self):
        """Attack 3: Advanced humanized bot - Cracks the CAPTCHA"""
        print("\n" + "="*70)
        print("🤖 ATTACK #3: Advanced Bot (Human-Like Behavior)")
        print("="*70)
        print("Strategy: Bezier curves, realistic timing, jitter, acceleration")
        print("Expected: Will CRACK the CAPTCHA ✅")
        print("-"*70)
        
        current_x, current_y = 350, 175
        targets_clicked = 0
        
        for i in range(15):  # Try up to 15 targets
            target = self.wait_for_target(timeout=5)
            if not target:
                print(f"  No more targets found (clicked {targets_clicked})")
                break
            
            target_x, target_y = target['x'], target['y']
            target_num = target.get('number', '?')
            
            # Generate Bezier curve for natural movement
            ctrl1_x = current_x + (target_x - current_x) * 0.25 + random.uniform(-40, 40)
            ctrl1_y = current_y + (target_y - current_y) * 0.25 + random.uniform(-40, 40)
            ctrl2_x = current_x + (target_x - current_x) * 0.75 + random.uniform(-40, 40)
            ctrl2_y = current_y + (target_y - current_y) * 0.75 + random.uniform(-40, 40)
            
            points = []
            num_points = random.randint(20, 30)  # Variable number of points
            for step in range(num_points):
                t = step / (num_points - 1)
                
                # Bezier curve calculation
                x = (1-t)**3 * current_x + \
                    3 * (1-t)**2 * t * ctrl1_x + \
                    3 * (1-t) * t**2 * ctrl2_x + \
                    t**3 * target_x
                
                y = (1-t)**3 * current_y + \
                    3 * (1-t)**2 * t * ctrl1_y + \
                    3 * (1-t) * t**2 * ctrl2_y + \
                    t**3 * target_y
                
                # Add human-like jitter
                x += random.uniform(-1.5, 1.5)
                y += random.uniform(-1.5, 1.5)
                
                points.append((x, y))
            
            # Move along curve with variable speed
            distance = math.sqrt((target_x - current_x)**2 + (target_y - current_y)**2)
            base_time = 0.12 + math.log2(distance / 15 + 1) * 0.06
            
            for idx, (x, y) in enumerate(points):
                # Variable speed (acceleration/deceleration)
                progress = idx / len(points)
                if progress < 0.25:
                    speed_factor = progress / 0.25
                elif progress > 0.75:
                    speed_factor = (1 - progress) / 0.25
                else:
                    speed_factor = 1.0
                
                # Random micro-pauses (human hesitation)
                if random.random() < 0.15:
                    time.sleep(random.uniform(0.003, 0.008))
                
                self.driver.execute_script(f"""
                    var canvas = document.getElementById('motorCanvas');
                    var rect = canvas.getBoundingClientRect();
                    var event = new MouseEvent('mousemove', {{
                        clientX: rect.left + {x},
                        clientY: rect.top + {y},
                        bubbles: true
                    }});
                    canvas.dispatchEvent(event);
                """)
                
                time.sleep(base_time / len(points) * speed_factor)
            
            # Overshoot and correction (70% of the time)
            if random.random() < 0.7:
                overshoot_x = target_x + random.uniform(-4, 4)
                overshoot_y = target_y + random.uniform(-4, 4)
                self.driver.execute_script(f"""
                    var canvas = document.getElementById('motorCanvas');
                    var rect = canvas.getBoundingClientRect();
                    var event = new MouseEvent('mousemove', {{
                        clientX: rect.left + {overshoot_x},
                        clientY: rect.top + {overshoot_y},
                        bubbles: true
                    }});
                    canvas.dispatchEvent(event);
                """)
                time.sleep(random.uniform(0.015, 0.03))
            
            # Final position with slight jitter
            final_x = target_x + random.uniform(-2, 2)
            final_y = target_y + random.uniform(-2, 2)
            
            # Click with realistic timing
            self.driver.execute_script(f"""
                var canvas = document.getElementById('motorCanvas');
                var rect = canvas.getBoundingClientRect();
                var x = rect.left + {final_x};
                var y = rect.top + {final_y};
                
                // Move to final position
                canvas.dispatchEvent(new MouseEvent('mousemove', {{
                    clientX: x, clientY: y, bubbles: true
                }}));
                
                // Click sequence with delays
                setTimeout(() => {{
                    canvas.dispatchEvent(new MouseEvent('mousedown', {{
                        clientX: x, clientY: y, bubbles: true, button: 0
                    }}));
                }}, 10);
                
                setTimeout(() => {{
                    canvas.dispatchEvent(new MouseEvent('mouseup', {{
                        clientX: x, clientY: y, bubbles: true, button: 0
                    }}));
                }}, 30 + Math.random() * 30);  // Variable click duration
            """)
            
            targets_clicked += 1
            print(f"  Target {targets_clicked} (#{target_num}): Bezier curve to ({target_x:.1f}, {target_y:.1f}) - {num_points} points, {base_time:.2f}s")
            
            current_x, current_y = final_x, final_y
            
            # Variable delay between targets
            time.sleep(random.uniform(0.35, 0.75))
        
        time.sleep(3)
    
    def submit_verification(self, events, target_sequence, targets_hit):
        """Submit verification data to server"""
        try:
            # Get session data
            session_data = self.driver.execute_script("""
                return {
                    session_id: motorCaptcha.sessionId,
                    challenge: motorCaptcha.challenge
                };
            """)
            
            if not session_data or not session_data.get('session_id'):
                print("  No session data available")
                return False
                
            # Solve PoW
            nonce, pow_hash = self.solve_pow(session_data['challenge'])
            if nonce is None:
                print("  PoW solving failed")
                return False
                
            # Collect fingerprint
            fingerprint = self.driver.execute_script("""
                const fp = new BrowserFingerprint();
                return fp.collect();
            """)
            
            # Create verification data
            verification_data = {
                "events": events,
                "targetSequence": target_sequence,
                "targetsHit": targets_hit,
                "totalTime": events[-1]['t'] - events[0]['t'] if len(events) > 1 else 0,
                "canvasWidth": 700,
                "canvasHeight": 350,
                "session_id": session_data['session_id'],
                "pow_nonce": nonce,
                "pow_hash": pow_hash,
                "fingerprint": fingerprint,
                "attempt_number": 1
            }
            
            # Submit to server
            response = requests.post(
                f"{self.captcha_url}verify-motor-captcha",
                json=verification_data,
                headers={'Content-Type': 'application/json'}
            )
            
            result = response.json()
            return result.get('verified', False)
            
        except Exception as e:
            print(f"  Verification submission failed: {e}")
            return False
    
    def run_attack(self, attack_num, attack_name, attack_func, stealth=False):
        """Run a single attack"""
        attack_start = time.time()
        attack_log = {
            'attack_num': attack_num,
            'attack_name': attack_name,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': False,
            'duration': 0,
            'result_message': ''
        }
        
        try:
            self.setup_driver(stealth=stealth)
            self.navigate_to_captcha()
            time.sleep(1)
            
            # Execute attack
            attack_func()
            
            # Check result
            success, message = self.check_result()
            attack_log['success'] = success
            attack_log['result_message'] = message
            
            attack_log['duration'] = time.time() - attack_start
            
            if success:
                print(f"\n✅ SUCCESS: {message}")
            else:
                print(f"\n❌ BLOCKED: {message}")
            
        except Exception as e:
            attack_log['success'] = False
            attack_log['result_message'] = f"Error: {str(e)[:100]}"
            attack_log['duration'] = time.time() - attack_start
            print(f"\n❌ ERROR: {e}")
        finally:
            if self.driver:
                time.sleep(2)
                self.driver.quit()
        
        self.detailed_log.append(attack_log)
        time.sleep(2)
    
    def run_demonstration(self):
        """Run all 3 attacks"""
        self.start_time = datetime.now()
        
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║           CAPTCHA BOT DEMONSTRATION - 3 ATTACKS                      ║
║                                                                      ║
║  Attack #1: Simple Bot         → Expected: BLOCKED                  ║
║  Attack #2: Intermediate Bot   → Expected: BLOCKED                  ║
║  Attack #3: Advanced Bot       → Expected: SUCCESS ✅               ║
╚══════════════════════════════════════════════════════════════════════╝
        """)
        
        input("Press Enter to start demonstration...")
        
        # Attack 1: Simple bot (no stealth)
        self.run_attack(1, "Simple Bot", self.attack_1_simple_bot, stealth=False)
        
        # Attack 2: Intermediate bot (no stealth)
        self.run_attack(2, "Intermediate Bot", self.attack_2_intermediate_bot, stealth=False)
        
        # Attack 3: Advanced bot (with stealth)
        self.run_attack(3, "Advanced Bot", self.attack_3_advanced_bot, stealth=True)
        
        # Write log
        self.write_log()
        self.print_summary()
    
    def write_log(self):
        """Write detailed log"""
        end_time = datetime.now()
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("     CAPTCHA BOT DEMONSTRATION - DETAILED LOG (3 ATTACKS)\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Test Started:  {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Test Ended:    {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"CAPTCHA URL:   {self.captcha_url}\n\n")
            
            f.write("="*80 + "\n")
            f.write("SUMMARY\n")
            f.write("-"*80 + "\n")
            
            for log in self.detailed_log:
                status = "✅ PASSED" if log['success'] else "❌ BLOCKED"
                f.write(f"Attack #{log['attack_num']}: {log['attack_name']:20} {status}\n")
            
            f.write("\n" + "="*80 + "\n\n")
            
            # Detailed logs
            for log in self.detailed_log:
                f.write(f"ATTACK #{log['attack_num']}: {log['attack_name']}\n")
                f.write("-"*80 + "\n")
                f.write(f"Start Time: {log['start_time']}\n")
                f.write(f"Duration:   {log['duration']:.2f} seconds\n")
                f.write(f"Result:     {'✅ SUCCESS' if log['success'] else '❌ BLOCKED'}\n")
                f.write(f"Message:    {log['result_message']}\n")
                f.write("\n" + "="*80 + "\n\n")
            
            f.write("CONCLUSION\n")
            f.write("-"*80 + "\n")
            f.write("This demonstration shows the progression of bot sophistication:\n\n")
            f.write("Attack #1: Simple bots are easily detected by ML models\n")
            f.write("Attack #2: Intermediate bots with basic humanization still fail\n")
            f.write("Attack #3: Advanced bots with realistic behavior can bypass detection\n\n")
            f.write("💡 Recommendation: Increase security level to MAXIMUM or add additional\n")
            f.write("   detection layers to block advanced adversarial bots.\n")
            f.write("="*80 + "\n")
        
        print(f"\n📄 Detailed log written to: {self.log_file}")
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*70)
        print("📊 FINAL RESULTS")
        print("="*70)
        
        for log in self.detailed_log:
            status = "✅ PASSED" if log['success'] else "❌ BLOCKED"
            print(f"Attack #{log['attack_num']}: {log['attack_name']:20} {status}")
        
        print("="*70)
        
        success_count = sum(1 for log in self.detailed_log if log['success'])
        
        if success_count == 1 and self.detailed_log[2]['success']:
            print("\n✅ DEMONSTRATION SUCCESSFUL!")
            print("   • Attacks #1 and #2 were blocked (as expected)")
            print("   • Attack #3 cracked the CAPTCHA (as designed)")
            print("\n⚠️  This shows your CAPTCHA is vulnerable to advanced bots.")
            print("   Consider increasing security level or adding more detection layers.")
        else:
            print("\n⚠️  UNEXPECTED RESULTS!")
            print(f"   {success_count} attack(s) succeeded")

def main():
    bot = DemonstrationBot()
    bot.run_demonstration()

if __name__ == "__main__":
    main()
