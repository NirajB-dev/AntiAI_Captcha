#Author: Niraj

#!/usr/bin/env python3
"""
VLM Live Canvas Tracker
Real-time CAPTCHA canvas tracking using modified Kalman filter system
Captures canvas like a video stream instead of static screenshots
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
import base64
from datetime import datetime

# Computer vision imports with fallback
try:
    import cv2
    import numpy as np
    from PIL import Image
    import io
    import queue
    import threading
    from typing import Tuple, List, Dict, Generator, Optional
    VISION_AVAILABLE = True
    print("✅ Computer vision libraries loaded (OpenCV, PIL)")
except ImportError as e:
    VISION_AVAILABLE = False
    print(f"⚠️  Vision libraries not available: {e}")
    print("   VLM will use simplified target detection")

class VLMLiveTracker:
    def __init__(self, captcha_url="http://localhost:5001/"):
        self.captcha_url = captcha_url
        self.driver = None
        self.detailed_log = []
        self.log_file = "vlm_live_tracker_log.txt"
        self.start_time = None
        self.canvas_element = None
        self.tracking_active = False
        self.tracks = {}
        self.next_id = 0
        self.candidates = {}
        self.frame_idx = 0
        
    def setup_driver(self, stealth=True):
        """Initialize Chrome driver with stealth mode"""
        options = webdriver.ChromeOptions()
        
        if stealth:
            # Advanced anti-detection
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-extensions')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        
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
        
        print(f"✅ VLM Live Tracker initialized (Stealth: {stealth})")
    
    def navigate_to_captcha(self):
        """Navigate and start CAPTCHA"""
        self.driver.get(self.captcha_url)
        time.sleep(2)
        
        # Fill in transfer form
        recipient_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "recipient"))
        )
        recipient_input.clear()
        recipient_input.send_keys("Live Tracker Test")
        
        amount_input = self.driver.find_element(By.ID, "amount")
        amount_input.clear()
        amount_input.send_keys("750.00")
        
        time.sleep(0.5)
        
        # Click initiate transfer button
        initiate_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "initiateBtn"))
        )
        initiate_btn.click()
        time.sleep(2)
        
        # Get canvas element for live capture
        self.canvas_element = self.driver.find_element(By.ID, "motorCanvas")
        print("✅ Canvas element ready for live tracking")
    
    def create_kalman_filter(self, x: float, y: float):
        """Create Kalman filter for target tracking"""
        if not VISION_AVAILABLE:
            return None
            
        kf = cv2.KalmanFilter(4, 2)
        kf.transitionMatrix = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        kf.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float32)
        kf.processNoiseCov = np.eye(4, dtype=np.float32) * 1e-2
        kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 5e-1  # Higher noise for CAPTCHA
        kf.errorCovPost = np.eye(4, dtype=np.float32)
        kf.statePost = np.array([[x], [y], [0], [0]], dtype=np.float32)
        return kf
    
    def capture_canvas_frame(self):
        """Capture single frame from canvas like a camera"""
        if not VISION_AVAILABLE or not self.canvas_element:
            return None
            
        try:
            # Take screenshot of canvas element
            canvas_screenshot = self.canvas_element.screenshot_as_png
            
            # Convert to OpenCV format
            image = Image.open(io.BytesIO(canvas_screenshot))
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            return cv_image
            
        except Exception as e:
            print(f"  Frame capture failed: {e}")
            return None
    
    def detect_targets_in_frame(self, cv_image):
        """
        Detect colored CAPTCHA targets in current frame
        Modified for CAPTCHA target detection (not background subtraction)
        """
        if not VISION_AVAILABLE or cv_image is None:
            return []
        
        try:
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
            
            # Define color ranges for CAPTCHA targets
            color_ranges = [
                # Red targets
                ([0, 70, 50], [10, 255, 255]),
                ([170, 70, 50], [180, 255, 255]),
                # Blue targets  
                ([100, 70, 50], [130, 255, 255]),
                # Green targets
                ([40, 70, 50], [80, 255, 255]),
                # Orange targets
                ([10, 70, 50], [25, 255, 255]),
                # Purple targets
                ([130, 70, 50], [170, 255, 255])
            ]
            
            detections = []
            min_area = 200  # Minimum area for CAPTCHA targets
            
            for color_idx, (lower, upper) in enumerate(color_ranges):
                lower = np.array(lower)
                upper = np.array(upper)
                
                # Create mask for this color range
                mask = cv2.inRange(hsv, lower, upper)
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area < min_area:
                        continue
                    
                    # Check circularity (CAPTCHA targets are circular)
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter <= 0:
                        continue
                        
                    circularity = 4.0 * math.pi * area / (perimeter * perimeter)
                    if circularity < 0.4:  # Must be reasonably circular
                        continue
                    
                    # Get bounding box and center
                    x, y, w, h = cv2.boundingRect(contour)
                    cx = x + w // 2
                    cy = y + h // 2
                    
                    # Check aspect ratio (should be roughly square for circles)
                    aspect = w / float(h) if h > 0 else 1.0
                    if aspect < 0.6 or aspect > 1.7:
                        continue
                    
                    detections.append({
                        'cx': cx,
                        'cy': cy,
                        'bbox': (x, y, w, h),
                        'area': area,
                        'color_idx': color_idx,
                        'circularity': circularity
                    })
            
            return detections
            
        except Exception as e:
            print(f"  Target detection failed: {e}")
            return []
    
    def live_canvas_tracker(self, 
                           max_dist: float = 50.0,
                           max_misses: int = 10,
                           confirm_frames: int = 3,
                           merge_dist: float = 25.0,
                           stop_event: Optional[threading.Event] = None) -> Generator[Tuple[np.ndarray, List[Dict]], None, None]:
        """
        Live CAPTCHA canvas tracker - modified Kalman tracker for canvas
        """
        print("🎥 Starting live canvas tracking...")
        
        try:
            while True:
                if stop_event is not None and stop_event.is_set():
                    break
                    
                # Capture frame from canvas
                frame = self.capture_canvas_frame()
                if frame is None:
                    time.sleep(0.02)  # Short delay before retry
                    continue
                    
                self.frame_idx += 1
                
                # Detect targets in current frame
                raw_detections = self.detect_targets_in_frame(frame)
                
                # Merge nearby detections
                detections = self.merge_nearby_detections(raw_detections, merge_dist)
                
                # Predict positions for existing tracks
                predictions = {}
                for tid, track in self.tracks.items():
                    if track.get("kf"):
                        pred = track["kf"].predict()
                        px, py = float(pred[0, 0]), float(pred[1, 0])
                        predictions[tid] = (px, py)
                
                # Match detections to existing tracks
                matches, unmatched_dets, unmatched_tracks = self.associate_detections_to_tracks(
                    detections, predictions, max_dist)
                
                # Update matched tracks
                for tid, det_idx in matches:
                    detection = detections[det_idx]
                    cx, cy = detection['cx'], detection['cy']
                    
                    if self.tracks[tid].get("kf"):
                        meas = np.array([[cx], [cy]], dtype=np.float32)
                        self.tracks[tid]["kf"].correct(meas)
                        self.tracks[tid]["misses"] = 0
                        self.tracks[tid]["bbox"] = detection['bbox']
                        self.tracks[tid]["area"] = detection['area']
                        self.tracks[tid]["last_seen"] = self.frame_idx
                
                # Increment misses for unmatched tracks
                for tid in unmatched_tracks:
                    self.tracks[tid]["misses"] += 1
                
                # Handle unmatched detections - add to candidates
                for det_idx in unmatched_dets:
                    detection = detections[det_idx]
                    cx, cy = detection['cx'], detection['cy']
                    
                    # Create spatial key for candidate tracking
                    qx = int(round(cx / 15.0))
                    qy = int(round(cy / 15.0))
                    key = (qx, qy)
                    
                    entry = self.candidates.get(key)
                    if entry and self.frame_idx - entry["last_seen"] <= 3:
                        entry["count"] += 1
                        entry["last_seen"] = self.frame_idx
                        # Average the position
                        entry["cx"] = (entry["cx"] + cx) / 2
                        entry["cy"] = (entry["cy"] + cy) / 2
                    else:
                        self.candidates[key] = {
                            "count": 1,
                            "last_seen": self.frame_idx,
                            "cx": cx,
                            "cy": cy,
                            "bbox": detection['bbox'],
                            "area": detection['area']
                        }
                
                # Promote candidates to tracks
                to_promote = []
                for key, entry in list(self.candidates.items()):
                    if self.frame_idx - entry["last_seen"] > 5:
                        del self.candidates[key]
                        continue
                        
                    if entry["count"] >= confirm_frames:
                        cx, cy = entry["cx"], entry["cy"]
                        kf = self.create_kalman_filter(float(cx), float(cy))
                        
                        self.tracks[self.next_id] = {
                            "kf": kf,
                            "misses": 0,
                            "bbox": entry["bbox"],
                            "area": entry["area"],
                            "last_seen": self.frame_idx,
                            "confidence": 0.8
                        }
                        to_promote.append(self.next_id)
                        self.next_id += 1
                        del self.candidates[key]
                
                # Remove tracks with too many misses
                to_delete = [tid for tid, track in list(self.tracks.items()) 
                           if track["misses"] > max_misses]
                for tid in to_delete:
                    del self.tracks[tid]
                
                # Create readings output
                readings = []
                for tid, track in self.tracks.items():
                    if track.get("kf"):
                        state = track["kf"].statePost
                        cx = float(state[0, 0])
                        cy = float(state[1, 0])
                        vx = float(state[2, 0])
                        vy = float(state[3, 0])
                        
                        readings.append({
                            "id": int(tid),
                            "cx": cx,
                            "cy": cy,
                            "velocity_x": vx,
                            "velocity_y": vy,
                            "bbox": track.get("bbox"),
                            "area": track.get("area", 0),
                            "confidence": track.get("confidence", 0.5),
                            "age": self.frame_idx - (track.get("last_seen", self.frame_idx))
                        })
                
                yield (frame.copy(), readings)
                
                # Control frame rate
                time.sleep(0.03)  # ~30 FPS
                
        except Exception as e:
            print(f"Live tracking error: {e}")
        finally:
            print("🎥 Live canvas tracking stopped")
    
    def merge_nearby_detections(self, detections, merge_dist):
        """Merge nearby detections to avoid duplicates"""
        if len(detections) <= 1:
            return detections
            
        merged = []
        used = [False] * len(detections)
        
        for i, det_i in enumerate(detections):
            if used[i]:
                continue
                
            group = [det_i]
            used[i] = True
            
            for j in range(i + 1, len(detections)):
                if used[j]:
                    continue
                    
                det_j = detections[j]
                distance = math.hypot(det_i['cx'] - det_j['cx'], det_i['cy'] - det_j['cy'])
                
                if distance <= merge_dist:
                    group.append(det_j)
                    used[j] = True
            
            # Average the group
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Merge multiple detections
                avg_cx = sum(d['cx'] for d in group) / len(group)
                avg_cy = sum(d['cy'] for d in group) / len(group)
                max_area = max(d['area'] for d in group)
                
                # Use bounding box of largest detection
                largest_det = max(group, key=lambda d: d['area'])
                
                merged.append({
                    'cx': int(avg_cx),
                    'cy': int(avg_cy),
                    'bbox': largest_det['bbox'],
                    'area': max_area,
                    'color_idx': largest_det['color_idx'],
                    'circularity': largest_det['circularity']
                })
        
        return merged
    
    def associate_detections_to_tracks(self, detections, predictions, max_dist):
        """Associate detections to existing tracks"""
        matches = []
        unmatched_dets = set(range(len(detections)))
        unmatched_tracks = set(self.tracks.keys())
        
        # Find best matches
        for det_idx, detection in enumerate(detections):
            cx, cy = detection['cx'], detection['cy']
            best_tid = None
            best_dist = max_dist
            
            for tid in list(unmatched_tracks):
                if tid in predictions:
                    px, py = predictions[tid]
                    dist = math.hypot(cx - px, cy - py)
                    
                    if dist < best_dist:
                        best_dist = dist
                        best_tid = tid
            
            if best_tid is not None:
                matches.append((best_tid, det_idx))
                unmatched_tracks.discard(best_tid)
                unmatched_dets.discard(det_idx)
        
        return matches, list(unmatched_dets), list(unmatched_tracks)
    
    def create_live_visualization(self, frame, readings):
        """Create real-time visualization of tracked targets"""
        if not VISION_AVAILABLE or frame is None:
            return frame
            
        try:
            vis_frame = frame.copy()
            
            for reading in readings:
                cx, cy = int(reading['cx']), int(reading['cy'])
                target_id = reading['id']
                confidence = reading.get('confidence', 0.5)
                vx, vy = reading.get('velocity_x', 0), reading.get('velocity_y', 0)
                
                # Color based on confidence
                if confidence > 0.7:
                    color = (0, 255, 0)  # Green - high confidence
                elif confidence > 0.4:
                    color = (0, 255, 255)  # Yellow - medium confidence  
                else:
                    color = (0, 0, 255)  # Red - low confidence
                
                # Draw target center
                cv2.circle(vis_frame, (cx, cy), 8, color, 2)
                
                # Draw target ID
                cv2.putText(vis_frame, f'ID:{target_id}', (cx + 12, cy - 12),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # Draw confidence
                cv2.putText(vis_frame, f'C:{confidence:.2f}', (cx + 12, cy + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                # Draw velocity vector if significant
                speed = math.sqrt(vx*vx + vy*vy)
                if speed > 1.0:
                    end_x = int(cx + vx * 5)
                    end_y = int(cy + vy * 5)
                    cv2.arrowedLine(vis_frame, (cx, cy), (end_x, end_y), (255, 0, 255), 2)
                    cv2.putText(vis_frame, f'{speed:.1f}px/s', (cx - 20, cy + 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 255), 1)
                
                # Draw bounding box
                if reading.get('bbox'):
                    x, y, w, h = reading['bbox']
                    cv2.rectangle(vis_frame, (x, y), (x + w, y + h), color, 1)
            
            # Add frame info
            cv2.putText(vis_frame, f"Frame: {self.frame_idx}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(vis_frame, f"Tracks: {len(readings)}", (10, 55),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            return vis_frame
            
        except Exception as e:
            print(f"  Visualization failed: {e}")
            return frame
    
    def get_instructions_from_ui(self):
        """Get CAPTCHA instructions from the UI"""
        try:
            instruction_element = self.driver.find_element(By.ID, "instructionText")
            instruction_text = instruction_element.text.strip()
            print(f"📋 CAPTCHA Instructions: {instruction_text}")
            
            # Parse "Click targets in order: 3, 1, 4, 2"
            if "click targets in order:" in instruction_text.lower():
                order_part = instruction_text.lower().split("click targets in order:")[1].strip()
                sequence = [int(x.strip()) for x in order_part.split(",")]
                return sequence
            
            return None
            
        except Exception as e:
            print(f"  ⚠️ Could not get instructions: {e}")
            return None
    
    def generate_human_movement(self, start_x, start_y, end_x, end_y):
        """Generate human-like movement path"""
        # Generate control points for Bezier curve
        ctrl1_x = start_x + (end_x - start_x) * 0.25 + random.uniform(-30, 30)
        ctrl1_y = start_y + (end_y - start_y) * 0.25 + random.uniform(-30, 30)
        ctrl2_x = start_x + (end_x - start_x) * 0.75 + random.uniform(-30, 30)
        ctrl2_y = start_y + (end_y - start_y) * 0.75 + random.uniform(-30, 30)
        
        points = []
        num_points = random.randint(15, 25)
        
        for i in range(num_points):
            t = i / (num_points - 1)
            
            # Bezier curve calculation
            x = (1-t)**3 * start_x + \
                3*(1-t)**2*t * ctrl1_x + \
                3*(1-t)*t**2 * ctrl2_x + \
                t**3 * end_x
            y = (1-t)**3 * start_y + \
                3*(1-t)**2*t * ctrl1_y + \
                3*(1-t)*t**2 * ctrl2_y + \
                t**3 * end_y
            
            # Add slight tremor for realism
            x += random.uniform(-2, 2)
            y += random.uniform(-2, 2)
            
            points.append((int(x), int(y)))
        
        return points
    
    def predict_target_position(self, target, time_ahead):
        """Predict where a moving target will be"""
        current_x = target.get('cx', target.get('x', 0))
        current_y = target.get('cy', target.get('y', 0))
        velocity_x = target.get('velocity_x', 0)
        velocity_y = target.get('velocity_y', 0)
        
        pred_x = current_x + velocity_x * time_ahead * 30  # 30 FPS assumption
        pred_y = current_y + velocity_y * time_ahead * 30
        
        return pred_x, pred_y
    
    def click_target(self, target_x, target_y, current_x, current_y, start_time):
        """Click a target with human-like movement"""
        events = []
        
        # Generate realistic movement path
        path_points = self.generate_human_movement(current_x, current_y, target_x, target_y)
        
        # Execute movement
        for point_x, point_y in path_points:
            current_time = time.time() * 1000 - start_time
            events.append({"x": point_x, "y": point_y, "t": current_time, "type": "mousemove"})
            
            self.driver.execute_script(f"""
                var canvas = document.getElementById('motorCanvas');
                var rect = canvas.getBoundingClientRect();
                var event = new MouseEvent('mousemove', {{
                    clientX: rect.left + {point_x},
                    clientY: rect.top + {point_y},
                    bubbles: true
                }});
                canvas.dispatchEvent(event);
            """)
            
            time.sleep(random.uniform(0.008, 0.015))
        
        # Click the target
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
        
        return events, target_x, target_y
    
    def submit_verification(self, events, target_sequence, targets_hit):
        """Submit verification data"""
        try:
            # Prepare data
            verification_data = {
                "events": events,
                "targetSequence": target_sequence, 
                "targetsHit": targets_hit,
                "totalTime": events[-1]["t"] if events else 0,
                "userAgent": self.driver.execute_script("return navigator.userAgent;"),
                "timestamp": int(time.time() * 1000)
            }
            
            # Submit via JavaScript
            result = self.driver.execute_script("""
                return fetch('/verify-motor', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(arguments[0])
                }).then(r => r.json()).catch(e => ({success: false, error: e.message}));
            """, verification_data)
            
            return result.get('success', False) if isinstance(result, dict) else False
            
        except Exception as e:
            print(f"  ⚠️ Verification submission failed: {e}")
            return False
    
    def solve_captcha_with_live_tracking(self):
        """
        Solve CAPTCHA using live tracking - the main attack function
        """
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║                   VLM LIVE CAPTCHA SOLVER                           ║
║                                                                      ║
║  🎥 Real-time Canvas Capture + Target Clicking                      ║
║  🎯 Kalman Filter Target Tracking + Prediction                      ║  
║  🤖 Automated CAPTCHA Solving                                        ║
║  🧠 No DOM Exposure - Pure Computer Vision                           ║
╚══════════════════════════════════════════════════════════════════════╝
        """)
        
        try:
            self.setup_driver(stealth=True)
            self.navigate_to_captcha()
            
            # Wait for CAPTCHA to fully load
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "motorCanvas"))
            )
            time.sleep(3)
            
            # Get required sequence from instructions
            required_sequence = self.get_instructions_from_ui()
            if not required_sequence:
                print("❌ Could not get CAPTCHA instructions")
                return False
            
            print(f"🎯 Required clicking sequence: {required_sequence}")
            print("🎥 Starting live tracking to solve CAPTCHA...")
            
            # Track for a few seconds to detect all targets
            detection_time = 5.0  # seconds
            tracker_gen = self.live_canvas_tracker()
            
            start_time = time.time()
            start_time_ms = start_time * 1000
            frame_count = 0
            all_targets = {}
            
            # Collect target data from live tracking
            for frame, readings in tracker_gen:
                current_time = time.time()
                elapsed = current_time - start_time
                
                if elapsed >= detection_time:
                    print(f"\n🎯 Target detection complete ({frame_count} frames analyzed)")
                    break
                
                frame_count += 1
                
                # Store detected targets with their properties
                for reading in readings:
                    target_id = reading['id']
                    all_targets[target_id] = {
                        'x': reading['cx'],
                        'y': reading['cy'],
                        'velocity_x': reading.get('velocity_x', 0),
                        'velocity_y': reading.get('velocity_y', 0),
                        'confidence': reading.get('confidence', 0.5),
                        'area': reading.get('area', 0),
                        'last_seen': frame_count
                    }
                
                # Print detection progress
                if frame_count % 30 == 0:
                    print(f"📊 Frame {frame_count}: {len(readings)} targets tracked, {len(all_targets)} total detected")
                
                # Small delay to control frame rate
                time.sleep(0.03)
            
            # Now click targets in the required sequence using live tracking data
            if len(all_targets) == 0:
                print("❌ No targets detected during tracking phase")
                return False
                
            print(f"\n🎯 Detected {len(all_targets)} targets, preparing to click sequence: {required_sequence}")
            
            # Map target IDs to sequence numbers (assume targets are numbered by appearance order)
            target_list = list(all_targets.items())
            target_list.sort(key=lambda x: x[1]['last_seen'])  # Sort by when first detected
            
            events = []
            target_sequence = []
            targets_hit = 0
            current_x, current_y = 400, 300  # Start position
            
            # Click targets in required sequence
            for seq_num in required_sequence:
                if seq_num <= len(target_list):
                    target_id, target_data = target_list[seq_num - 1]  # seq_num is 1-based
                    
                    # Use prediction for moving targets
                    if abs(target_data.get('velocity_x', 0)) > 2 or abs(target_data.get('velocity_y', 0)) > 2:
                        pred_x, pred_y = self.predict_target_position(target_data, 0.5)
                        target_x, target_y = pred_x, pred_y
                        print(f"    🔮 Target #{seq_num} (ID:{target_id}) - predicted position: ({target_x:.1f}, {target_y:.1f})")
                    else:
                        target_x, target_y = target_data['x'], target_data['y']
                        print(f"    🎯 Target #{seq_num} (ID:{target_id}) - current position: ({target_x:.1f}, {target_y:.1f})")
                    
                    # Click the target with human-like movement
                    click_events, new_x, new_y = self.click_target(target_x, target_y, current_x, current_y, start_time_ms)
                    events.extend(click_events)
                    target_sequence.append(seq_num)
                    targets_hit += 1
                    current_x, current_y = new_x, new_y
                    
                    print(f"    ✅ Clicked target #{seq_num} successfully")
                    time.sleep(random.uniform(0.4, 0.8))
                else:
                    print(f"    ⚠️ Target #{seq_num} not found in detected targets")
            
            # Submit verification 
            print("\n� Submitting CAPTCHA solution...")
            verified = self.submit_verification(events, target_sequence, targets_hit)
            
            if verified:
                print("🎉 CAPTCHA SOLVED SUCCESSFULLY with Live Tracking!")
                return True
            else:
                print("❌ CAPTCHA solution rejected by server")
                return False
                
        except Exception as e:
            print(f"❌ Live CAPTCHA solving failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                
    def run_live_tracking_demo(self, duration_seconds=30):
        """
        Run live tracking demonstration (non-solving version)
        """
        try:
            self.setup_driver(stealth=True)
            self.navigate_to_captcha()
            
            # Wait for CAPTCHA to fully load
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "motorCanvas"))
            )
            time.sleep(3)
            
            print(f"🎥 Starting {duration_seconds}s live tracking demo...")
            
            # Create stop event for controlled shutdown
            stop_event = threading.Event()
            
            # Start live tracking
            tracker_gen = self.live_canvas_tracker(stop_event=stop_event)
            
            start_time = time.time()
            frame_count = 0
            saved_frames = 0
            
            for frame, readings in tracker_gen:
                current_time = time.time()
                elapsed = current_time - start_time
                
                if elapsed >= duration_seconds:
                    print(f"\n⏰ {duration_seconds}s tracking session complete")
                    stop_event.set()
                    break
                    
                frame_count += 1
                
                # Create visualization
                vis_frame = self.create_live_visualization(frame, readings)
                
                # Save sample frames
                if frame_count % 30 == 0:  # Save every 30th frame (~1 per second)
                    filename = f"live_demo_frame_{saved_frames:03d}.png"
                    cv2.imwrite(filename, vis_frame)
                    saved_frames += 1
                    print(f"📸 Saved frame: {filename}")
                
                # Print tracking stats
                if frame_count % 60 == 0:  # Every ~2 seconds
                    active_tracks = len(readings)
                    avg_confidence = sum(r.get('confidence', 0) for r in readings) / max(len(readings), 1)
                    print(f"🎯 Frame {frame_count}: {active_tracks} active tracks, avg confidence: {avg_confidence:.2f}")
                
                # Small delay to control frame rate
                time.sleep(0.02)
            
            print(f"\n📊 Demo Statistics:")
            print(f"   Total frames processed: {frame_count}")
            print(f"   Average FPS: {frame_count / elapsed:.1f}")
            print(f"   Frames saved: {saved_frames}")
            print(f"   Final active tracks: {len(self.tracks)}")
            
        except Exception as e:
            print(f"❌ Live tracking failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()

def main():
    print("🎥 VLM Live Canvas Tracker - Real-time CAPTCHA Solver")
    print("This uses continuous canvas capture to detect and click targets")
    
    tracker = VLMLiveTracker()
    
    # Choose mode
    mode = input("\nChoose mode:\n1. Solve CAPTCHA (default)\n2. Demo tracking only\nEnter choice (1/2): ").strip()
    
    if mode == "2":
        print("\n🎥 Running tracking demo...")
        tracker.run_live_tracking_demo(duration_seconds=20)
    else:
        print("\n🤖 Running CAPTCHA solver...")
        success = tracker.solve_captcha_with_live_tracking()
        if success:
            print("🎉 CAPTCHA solving completed successfully!")
        else:
            print("❌ CAPTCHA solving failed")

if __name__ == "__main__":
    main()
