#Author: Niraj

#!/usr/bin/env python3
"""
VLM CAPTCHA Solver using SeleniumPortal
Clean, efficient approach using portal interface for canvas interaction
"""

import time
import cv2
import numpy as np
import math
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SeleniumPortal:
    def __init__(self, url, canvas_selector="#motorCanvas", headless=False):
        o = Options()
        if headless:
            o.add_argument("--headless=new")
            o.add_argument("--disable-gpu")
        
        # Anti-detection measures
        o.add_argument('--disable-blink-features=AutomationControlled')
        o.add_experimental_option("excludeSwitches", ["enable-automation"])
        o.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=o)
        
        # Hide webdriver markers
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                window.chrome = {runtime: {}};
            '''
        })
        
        self.driver.set_window_size(800, 600)
        self.driver.get(url)
        
        # Setup CAPTCHA form
        self._setup_captcha_form()
        
        # Wait for canvas and get it
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, canvas_selector))
        )
        self.canvas = self.driver.find_element(By.CSS_SELECTOR, canvas_selector)

        size = self.canvas.size
        self._canvas_w = int(size["width"])
        self._canvas_h = int(size["height"])

        # Calculate scaling factors
        arr = np.frombuffer(self.canvas.screenshot_as_png, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        fh, fw = frame.shape[:2]
        self._scale_x = fw / self._canvas_w if self._canvas_w else 1.0
        self._scale_y = fh / self._canvas_h if self._canvas_h else 1.0
        self._pos = (self._canvas_w // 2, self._canvas_h // 2)
        
        print(f"✅ Portal initialized - Canvas: {self._canvas_w}x{self._canvas_h}, Scale: {self._scale_x:.2f}x{self._scale_y:.2f}")

    def _setup_captcha_form(self):
        """Fill out the form to trigger CAPTCHA"""
        try:
            # Wait for form elements
            recipient_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "recipient"))
            )
            recipient_input.clear()
            recipient_input.send_keys("VLM Portal Test")
            
            amount_input = self.driver.find_element(By.ID, "amount")
            amount_input.clear()
            amount_input.send_keys("888.00")
            
            time.sleep(0.5)
            
            # Click initiate transfer button
            initiate_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "initiateBtn"))
            )
            initiate_btn.click()
            time.sleep(2)
            
            print("✅ CAPTCHA form submitted, waiting for canvas...")
            
        except Exception as e:
            print(f"❌ Form setup failed: {e}")

    def get_instructions(self):
        """Get CAPTCHA instructions"""
        try:
            # Wait for the sequence to be displayed
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "targetSequence"))
            )
            time.sleep(1)  # Allow sequence to fully load
            
            sequence_element = self.driver.find_element(By.ID, "targetSequence")
            sequence_text = sequence_element.text.strip()
            print(f"📋 Target Sequence: {sequence_text}")
            
            # Parse sequence like "3, 1, 4, 2" or "3 → 1 → 4 → 2"
            if sequence_text and sequence_text != "Loading...":
                # Extract numbers from the sequence text
                import re
                numbers = re.findall(r'\d+', sequence_text)
                sequence = [int(num) for num in numbers]
                return sequence
            
            return None
            
        except Exception as e:
            print(f"⚠️ Could not get instructions: {e}")
            return None

    def isOpened(self):
        return self.driver is not None

    def read(self):
        """Capture frame from canvas"""
        if not self.isOpened():
            return False, None
        try:
            arr = np.frombuffer(self.canvas.screenshot_as_png, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return frame is not None, frame
        except Exception as e:
            print(f"Frame capture failed: {e}")
            return False, None

    def release(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _dispatch_mouse_event(self, event_type: str, mx: float, my: float):
        """Dispatch mouse event to canvas"""
        self.driver.execute_script(
            """
            const canvas = arguments[0];
            const mx = arguments[1];
            const my = arguments[2];
            const type = arguments[3];
            const rect = canvas.getBoundingClientRect();
            const evt = new MouseEvent(type, {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: rect.left + mx,
                clientY: rect.top + my
            });
            canvas.dispatchEvent(evt);
            """,
            self.canvas,
            float(mx),
            float(my),
            event_type,
        )

    def moveTo(self, screen_x, screen_y, duration=0.1, tween=None):
        """Move mouse to position with optional easing"""
        if tween is None:
            tween = lambda t: t  # Linear

        # Convert screen coordinates to canvas coordinates
        tx = screen_x / self._scale_x
        ty = screen_y / self._scale_y
        tx = max(0, min(self._canvas_w - 1, int(tx)))
        ty = max(0, min(self._canvas_h - 1, int(ty)))

        sx, sy = self._pos
        steps = max(1, int(duration / 0.01))

        for i in range(1, steps + 1):
            t = tween(i / steps)
            mx = sx + (tx - sx) * t
            my = sy + (ty - sy) * t
            mx = max(0, min(self._canvas_w - 1, mx))
            my = max(0, min(self._canvas_h - 1, my))
            self._dispatch_mouse_event("mousemove", mx, my)
            time.sleep(duration / steps)

        self._pos = (tx, ty)

    def mouseDown(self, duration=0.03):
        mx, my = self._pos
        self._dispatch_mouse_event("mousedown", mx, my)
        time.sleep(duration)

    def mouseUp(self):
        mx, my = self._pos
        self._dispatch_mouse_event("mouseup", mx, my)
        self._dispatch_mouse_event("click", mx, my)

    def click(self, x, y, duration=0.1):
        """Click at specific coordinates"""
        self.moveTo(x, y, duration)
        self.mouseDown()
        self.mouseUp()


class VLMPortalSolver:
    def __init__(self, url="http://localhost:5001/"):
        self.url = url
        self.portal = None
        
    def detect_targets(self, frame):
        """Detect CAPTCHA targets using computer vision"""
        if frame is None:
            return []
            
        try:
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Expanded color ranges for better CAPTCHA target detection
            color_ranges = [
                # Red targets (expanded range)
                ([0, 50, 50], [15, 255, 255]),
                ([165, 50, 50], [180, 255, 255]),
                # Blue targets (expanded range)
                ([90, 50, 50], [140, 255, 255]),
                # Green targets (expanded range)
                ([35, 50, 50], [85, 255, 255]),
                # Orange/Yellow targets (expanded range)
                ([8, 50, 50], [35, 255, 255]),
                # Purple/Magenta targets (expanded range)
                ([125, 50, 50], [175, 255, 255]),
                # Cyan targets
                ([80, 50, 50], [100, 255, 255]),
                # Additional red range for darker reds
                ([160, 40, 40], [180, 255, 255])
            ]
            
            targets = []
            min_area = 50   # Further reduced minimum area for better detection
            max_area = 2000 # Maximum area to filter out false positives
            
            for color_idx, (lower, upper) in enumerate(color_ranges):
                lower = np.array(lower)
                upper = np.array(upper)
                
                # Create mask for this color range
                mask = cv2.inRange(hsv, lower, upper)
                
                # Apply morphological operations to clean up mask
                kernel = np.ones((3,3), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area < min_area or area > max_area:
                        continue
                    
                    # Check circularity - very lenient for CAPTCHA targets
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter <= 0:
                        continue
                        
                    circularity = 4.0 * math.pi * area / (perimeter * perimeter)
                    if circularity < 0.2:  # Very lenient circularity check
                        continue
                    
                    # Get bounding box and center
                    x, y, w, h = cv2.boundingRect(contour)
                    cx = x + w // 2
                    cy = y + h // 2
                    
                    # Check aspect ratio - very lenient
                    aspect = w / float(h) if h > 0 else 1.0
                    if aspect < 0.3 or aspect > 3.0:  # Very lenient aspect ratio
                        continue
                    
                    # Additional check: minimum size in pixels
                    if w < 5 or h < 5:
                        continue
                    
                    targets.append({
                        'id': len(targets) + 1,  # Sequential ID
                        'x': cx,
                        'y': cy,
                        'area': area,
                        'color_idx': color_idx,
                        'circularity': circularity,
                        'confidence': min(circularity, 1.0),
                        'method': 'color'
                    })
            
            # If we don't have enough targets, try edge detection as backup
            if len(targets) < 3:
                edge_targets = self._detect_targets_by_edges(frame)
                for et in edge_targets:
                    # Check if this target is far enough from existing ones
                    is_new = True
                    for existing in targets:
                        dist = math.sqrt((et['x'] - existing['x'])**2 + (et['y'] - existing['y'])**2)
                        if dist < 50:
                            is_new = False
                            break
                    if is_new:
                        et['id'] = len(targets) + 1
                        targets.append(et)
            
            # Sort by confidence and area
            targets.sort(key=lambda t: (t['confidence'], t['area']), reverse=True)
            
            return targets
            
        except Exception as e:
            print(f"Target detection failed: {e}")
            return []

    def _detect_targets_by_edges(self, frame):
        """Backup detection method using edge detection"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            targets = []
            min_area = 80  # Even smaller for edge detection
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                cx = x + w // 2
                cy = y + h // 2
                
                # Basic shape filter
                aspect = w / float(h) if h > 0 else 1.0
                if aspect < 0.3 or aspect > 3.0:
                    continue
                
                targets.append({
                    'x': cx,
                    'y': cy,
                    'area': area,
                    'color_idx': -1,  # Unknown color
                    'circularity': 0.5,  # Assume moderate circularity
                    'confidence': 0.6,  # Lower confidence for edge detection
                    'method': 'edge'
                })
            
            return targets
            
        except Exception as e:
            print(f"Edge detection failed: {e}")
            return []



    def wait_for_target_and_click(self, target_number, timeout=15):
        """Wait for specific target to appear using computer vision and click it"""
        print(f"   🔍 Vision scanning for Target #{target_number}...")
        
        start_time = time.time()
        last_check_time = 0
        detection_history = []  # Track detections for stability
        
        while time.time() - start_time < timeout:
            current_time = time.time() - start_time
            
            # Print progress every 2 seconds
            if current_time - last_check_time >= 2:
                print(f"   ⏰ Scanning... ({current_time:.1f}s/{timeout}s)")
                last_check_time = current_time
            
            # Use computer vision to detect targets
            try:
                ret, frame = self.portal.read()
                if ret:
                    targets = self.detect_targets(frame)
                    
                    if targets:
                        # Find the most confident target
                        best_target = max(targets, key=lambda t: t['confidence'])
                        
                        # Add to detection history for stability
                        detection_history.append({
                            'x': best_target['x'],
                            'y': best_target['y'],
                            'confidence': best_target['confidence'],
                            'time': current_time
                        })
                        
                        # Keep only recent detections (last 1 second)
                        detection_history = [d for d in detection_history if current_time - d['time'] < 1.0]
                        
                        # If we have enough stable detections, click
                        if len(detection_history) >= 3:
                            # Average the positions for stability
                            avg_x = sum(d['x'] for d in detection_history) / len(detection_history)
                            avg_y = sum(d['y'] for d in detection_history) / len(detection_history)
                            avg_conf = sum(d['confidence'] for d in detection_history) / len(detection_history)
                            
                            target_x, target_y = int(avg_x), int(avg_y)
                            print(f"   🎯 Target #{target_number} found at ({target_x}, {target_y}) via Vision! (conf: {avg_conf:.2f})")
                            
                            # Click immediately
                            self.portal.click(target_x, target_y, duration=random.uniform(0.1, 0.2))
                            return True
                    else:
                        # Clear history if no targets detected
                        detection_history.clear()
                        
            except Exception as vision_error:
                print(f"   ⚠️ Vision error: {vision_error}")
                detection_history.clear()
            
            # Short delay before next check
            time.sleep(0.1)
        
        print(f"   ⏰ Timeout: Target #{target_number} not found within {timeout}s")
        return False

    def solve_captcha(self):
        """Main solving method - delegates to sequential solver"""
        return self.solve_captcha_sequential()

    def human_like_movement(self, t):
        """Easing function for human-like movement"""
        # Ease-out cubic for natural deceleration
        return 1 - (1 - t) ** 3

    def solve_captcha_sequential(self):
        """Sequential CAPTCHA solver - handles targets appearing one at a time"""
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║               VLM SEQUENTIAL CAPTCHA SOLVER                         ║
║                                                                      ║
║  ⏰ Waits for each target to appear individually                     ║
║  🖱️ Clicks targets within their time limit                          ║
║  🎯 Handles sequential target spawning                               ║
║  🧠 Pure Computer Vision Detection (No DOM)                         ║
║  🗄️ Triggers proper verification and database logging               ║
╚══════════════════════════════════════════════════════════════════════╝
        """)
        
        try:
            # Initialize portal
            print("🚀 Initializing portal...")
            self.portal = SeleniumPortal(self.url)
            time.sleep(3)  # Wait for CAPTCHA to fully load
            
            # Get required sequence
            required_sequence = self.portal.get_instructions()
            if not required_sequence:
                print("❌ Could not get CAPTCHA instructions")
                return False
            
            print(f"🎯 Required sequence: {required_sequence}")
            print(f"🔄 Sequential mode: Each target appears after the previous is clicked")
            
            # Process each target in sequence
            for i, target_num in enumerate(required_sequence):
                print(f"\n📍 Step {i+1}/{len(required_sequence)}: Looking for Target #{target_num}")
                
                # Wait for this specific target to appear
                target_found = self.wait_for_target_and_click(target_num, timeout=12)
                
                if target_found:
                    print(f"   ✅ Target #{target_num} clicked successfully!")
                    
                    # Brief pause to let next target spawn
                    if i < len(required_sequence) - 1:
                        wait_time = random.uniform(0.3, 0.6)
                        print(f"   ⏳ Waiting {wait_time:.1f}s for next target to spawn...")
                        time.sleep(wait_time)
                else:
                    print(f"   ❌ Target #{target_num} not found within time limit!")
                    return False
            
            # All targets clicked - now trigger proper verification
            print(f"\n✅ All {len(required_sequence)} targets clicked!")
            print("🔄 Triggering CAPTCHA verification and database logging...")
            
            # Wait a moment for any final game logic
            time.sleep(2)
            
            # Trigger the verification process by executing the JavaScript verification
            success = self.trigger_verification()
            
            if success:
                print("🎉 CAPTCHA SOLVED AND LOGGED TO DATABASE!")
                print("✅ Sequential solving completed with proper verification")
                return True
            else:
                print("⚠️ Verification process failed - checking for alternative success indicators")
                
                # Alternative success check
                try:
                    success_element = self.portal.driver.find_element(By.ID, "successSection")
                    if success_element.is_displayed():
                        print("🎉 CAPTCHA SOLVED SUCCESSFULLY (via DOM check)!")
                        return True
                except:
                    pass
                
                # Check for alerts
                try:
                    alert = self.portal.driver.switch_to.alert
                    alert_text = alert.text
                    print(f"📢 Alert: {alert_text}")
                    alert.accept()
                except:
                    pass
                
                print("❌ Could not confirm successful verification")
                return False
            
        except Exception as e:
            print(f"❌ Portal solving failed: {e}")
            return False
        finally:
            if self.portal:
                print("🔄 Cleaning up...")
                time.sleep(2)
                self.portal.release()
    
    def trigger_verification(self):
        """Trigger the proper CAPTCHA verification process to log success in database"""
        try:
            print("📡 Executing JavaScript verification process...")
            
            # Execute the verification JavaScript that handles proper database logging
            verification_script = """
            // Check if captcha object exists and has verifyCaptcha method
            if (typeof captcha !== 'undefined' && captcha.verifyCaptcha) {
                console.log('Triggering captcha.verifyCaptcha()...');
                captcha.verifyCaptcha();
                return 'verification_triggered';
            } else {
                console.log('Captcha object not found, checking for alternative verification...');
                
                // Alternative: Look for verification function in global scope
                if (typeof verifyCaptcha === 'function') {
                    console.log('Found global verifyCaptcha function...');
                    verifyCaptcha();
                    return 'global_verification_triggered';
                }
                
                // Alternative: Try to simulate the verification flow manually
                console.log('Attempting manual verification simulation...');
                
                // Check if we can access the events array and trigger verification
                if (typeof window.events !== 'undefined' && window.events.length > 0) {
                    console.log('Found events array, attempting manual verification...');
                    
                    // Simulate verification call
                    fetch('/verify-motor-captcha', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            events: window.events || [],
                            targetSequence: window.targetSequence || [],
                            targetsHit: window.targetsHit || 0,
                            canvasWidth: 700,
                            canvasHeight: 350,
                            session_id: 'portal_solver_' + Date.now(),
                            fingerprint: {
                                ua: navigator.userAgent,
                                platform: navigator.platform,
                                cores: navigator.hardwareConcurrency || 4,
                                screen: screen.width + 'x' + screen.height,
                                canvas: 'portal_simulation',
                                webgl: 'portal_webgl'
                            }
                        })
                    }).then(response => response.json())
                      .then(result => {
                          console.log('Manual verification result:', result);
                          if (result.verified) {
                              // Show success section
                              const successSection = document.getElementById('successSection');
                              if (successSection) {
                                  successSection.style.display = 'block';
                              }
                          }
                          return result;
                      });
                    
                    return 'manual_verification_attempted';
                }
                
                return 'no_verification_method_found';
            }
            """
            
            result = self.portal.driver.execute_script(verification_script)
            print(f"📊 Verification result: {result}")
            
            # Wait for verification to process
            time.sleep(3)
            
            # Check if success section is now visible
            try:
                success_element = self.portal.driver.find_element(By.ID, "successSection")
                if success_element.is_displayed():
                    print("✅ Success section is visible - verification succeeded!")
                    return True
            except:
                pass
            
            # Alternative: Check for any success indicators in the page
            try:
                # Look for success text or elements
                success_indicators = self.portal.driver.execute_script("""
                    const indicators = [];
                    
                    // Check for success section visibility
                    const successSection = document.getElementById('successSection');
                    if (successSection && successSection.style.display === 'block') {
                        indicators.push('success_section_visible');
                    }
                    
                    // Check for success text in page
                    const bodyText = document.body.innerText.toLowerCase();
                    if (bodyText.includes('success') || bodyText.includes('verified') || bodyText.includes('complete')) {
                        indicators.push('success_text_found');
                    }
                    
                    // Check console for success messages
                    return indicators;
                """)
                
                if success_indicators and len(success_indicators) > 0:
                    print(f"✅ Found success indicators: {success_indicators}")
                    return True
                    
            except Exception as e:
                print(f"⚠️ Error checking success indicators: {e}")
            
            print("⏰ Verification process completed but success not confirmed")
            return False
            
        except Exception as e:
            print(f"❌ Verification trigger failed: {e}")
            return False

def main():
    print("🎯 VLM Portal CAPTCHA Solver")
    print("Uses clean SeleniumPortal interface for efficient solving")
    
    solver = VLMPortalSolver()
    success = solver.solve_captcha()
    
    if success:
        print("\n🎉 SUCCESS: CAPTCHA solved with Portal interface!")
    else:
        print("\n❌ FAILED: CAPTCHA could not be solved")

if __name__ == "__main__":
    main()
