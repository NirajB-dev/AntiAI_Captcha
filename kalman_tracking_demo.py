#Author: Niraj

#!/usr/bin/env python3
"""
VLM Tracking Demo - Shows how the Kalman filter tracking works
Demonstrates the tracking visualization without needing a running CAPTCHA
"""

import cv2
import numpy as np
import time
import random
import math

def create_demo_tracking():
    """
    Create a demonstration of the Kalman tracking system
    """
    print("🎯 VLM Kalman Tracking Demonstration")
    print("="*50)
    
    # Create a demo canvas
    canvas_width, canvas_height = 700, 350
    canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
    
    # Create some simulated moving targets
    targets = []
    colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 0)]  # Red, Green, Blue, Yellow
    
    for i in range(4):
        # Create Kalman filter
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
        kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1e-1
        kf.errorCovPost = np.eye(4, dtype=np.float32)
        
        # Initial position and velocity
        x = random.randint(50, canvas_width - 50)
        y = random.randint(50, canvas_height - 50)
        vx = random.uniform(-3, 3)
        vy = random.uniform(-3, 3)
        
        kf.statePost = np.array([[x], [y], [vx], [vy]], dtype=np.float32)
        
        targets.append({
            'id': i + 1,
            'kalman': kf,
            'color': colors[i],
            'trail': [],  # Store trail of positions
            'true_pos': [x, y],  # Actual position (for simulation)
            'true_vel': [vx, vy]  # Actual velocity
        })
    
    print(f"Created {len(targets)} simulated targets with Kalman filters")
    print("Watch how the system tracks and predicts target movements!")
    print("Green circles = current position")
    print("Blue circles = predicted position (0.5s future)")
    print("Lines = velocity vectors")
    print("Trails = movement history")
    print("\nPress 'q' to quit, 's' to save screenshot")
    
    frame_count = 0
    
    try:
        while True:
            # Create fresh canvas
            canvas.fill(0)
            
            # Update and draw each target
            for target in targets:
                target_id = target['id']
                color = target['color']
                kf = target['kalman']
                
                # Simulate true movement (what the "real" target is doing)
                true_x, true_y = target['true_pos']
                true_vx, true_vy = target['true_vel']
                
                # Add some randomness to movement
                true_vx += random.uniform(-0.2, 0.2)
                true_vy += random.uniform(-0.2, 0.2)
                
                # Bounce off walls
                if true_x <= 30 or true_x >= canvas_width - 30:
                    true_vx *= -1
                if true_y <= 30 or true_y >= canvas_height - 30:
                    true_vy *= -1
                
                # Update true position
                true_x += true_vx
                true_y += true_vy
                target['true_pos'] = [true_x, true_y]
                target['true_vel'] = [true_vx, true_vy]
                
                # Predict with Kalman filter
                prediction = kf.predict()
                pred_x, pred_y = float(prediction[0, 0]), float(prediction[1, 0])
                
                # Create noisy measurement (simulating detection uncertainty)
                noise_x = random.uniform(-2, 2)
                noise_y = random.uniform(-2, 2)
                measured_x = true_x + noise_x
                measured_y = true_y + noise_y
                
                # Correct Kalman filter with measurement
                measurement = np.array([[measured_x], [measured_y]], dtype=np.float32)
                kf.correct(measurement)
                
                # Get corrected state
                state = kf.statePost
                filtered_x = float(state[0, 0])
                filtered_y = float(state[1, 0])
                filtered_vx = float(state[2, 0])
                filtered_vy = float(state[3, 0])
                
                # Add to trail
                target['trail'].append((int(filtered_x), int(filtered_y)))
                if len(target['trail']) > 20:  # Keep last 20 positions
                    target['trail'].pop(0)
                
                # Draw trail
                for i in range(1, len(target['trail'])):
                    alpha = i / len(target['trail'])
                    trail_color = tuple(int(c * alpha) for c in color)
                    cv2.line(canvas, target['trail'][i-1], target['trail'][i], trail_color, 2)
                
                # Draw current position (filtered)
                cv2.circle(canvas, (int(filtered_x), int(filtered_y)), 12, color, 2)
                cv2.putText(canvas, f'{target_id}', (int(filtered_x-8), int(filtered_y+5)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Draw true position (for comparison - normally we wouldn't know this)
                cv2.circle(canvas, (int(true_x), int(true_y)), 6, (128, 128, 128), 1)
                
                # Draw velocity vector
                if abs(filtered_vx) > 0.5 or abs(filtered_vy) > 0.5:
                    end_x = int(filtered_x + filtered_vx * 15)
                    end_y = int(filtered_y + filtered_vy * 15)
                    cv2.arrowedLine(canvas, (int(filtered_x), int(filtered_y)), 
                                   (end_x, end_y), (255, 255, 255), 2)
                
                # Draw predicted future position (0.5 seconds ahead)
                future_x = filtered_x + (filtered_vx * 30)  # 0.5 seconds * 60 fps
                future_y = filtered_y + (filtered_vy * 30)
                cv2.circle(canvas, (int(future_x), int(future_y)), 8, (255, 200, 100), 2)
                cv2.line(canvas, (int(filtered_x), int(filtered_y)), 
                        (int(future_x), int(future_y)), (255, 200, 100), 1)
                
                # Draw target info
                info_y = 30 + (target_id - 1) * 25
                info_text = f"Target {target_id}: Pos({filtered_x:.1f},{filtered_y:.1f}) Vel({filtered_vx:.1f},{filtered_vy:.1f})"
                cv2.putText(canvas, info_text, (10, info_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Add frame info
            cv2.putText(canvas, f"Frame: {frame_count}", (10, canvas_height - 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(canvas, "VLM Kalman Tracking Demo", (10, canvas_height - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(canvas, "Press 'q' to quit, 's' to save", (10, canvas_height - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            
            # Show the canvas
            cv2.imshow("VLM Kalman Tracking Demo", canvas)
            
            # Handle keyboard input
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f"kalman_tracking_demo_frame_{frame_count}.png"
                cv2.imwrite(filename, canvas)
                print(f"Screenshot saved as {filename}")
            
            frame_count += 1
            
            # Slow down the demo
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    
    finally:
        cv2.destroyAllWindows()
        print(f"\n🎯 Demo completed after {frame_count} frames")
        print("This demonstrates how the VLM attacker tracks CAPTCHA targets in real-time!")

if __name__ == "__main__":
    # Check if OpenCV is available
    try:
        import cv2
        import numpy as np
        create_demo_tracking()
    except ImportError:
        print("❌ OpenCV not available. Please install: pip install opencv-python")
