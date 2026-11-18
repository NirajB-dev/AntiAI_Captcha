#Author: Niraj


#!/usr/bin/env python3
"""
Advanced Motor-Timing CAPTCHA Verification Server
Multi-layered security system with ML-based human movement analysis
"""

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import numpy as np
import json
import math
import hashlib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import pickle
import os
from datetime import datetime
import secrets
from pathlib import Path
import time
import random
import threading
import uuid
import string
import sys

# Add parent directory to path for database import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from captcha_database import CaptchaDatabase

# Import our layers
from pow import ProofOfWorkVerifier
from fingerprint import FingerprintAnalyzer
from advanced_training import AdvancedMotorCaptchaTrainer
from security_config import get_config

# Load security configuration
SECURITY_CONFIG = get_config()
INITIAL_ML_THRESHOLD = SECURITY_CONFIG.get('ml_threshold', 0.55)
print(f"🔒 Security Level: {SECURITY_CONFIG.get('name', 'CUSTOM')}")

# ============================================================================
# SESSION TRACKING (In-Memory) - Tracks attempts by fingerprint hash
# ============================================================================
SESSION_STORE = {}  # {fingerprint_hash: {attempts: int, created_at: float, escalated: bool}}
SESSION_LOCK = threading.Lock()
SESSION_EXPIRY = 1800  # 30 minutes

# Adaptive threshold tracking for system evolution
RECENT_RESULTS = []  # List of (timestamp, passed: bool, confidence: float)
RESULTS_LOCK = threading.Lock()
ADAPTIVE_THRESHOLD_ADJUSTMENT = 0.0  # Current adjustment to base threshold

def get_fingerprint_hash(fingerprint):
    """Generate a stable hash from fingerprint data."""
    # Use stable fingerprint fields
    stable_fields = {
        'ua': fingerprint.get('ua', ''),
        'platform': fingerprint.get('platform', ''),
        'cores': fingerprint.get('cores', 0),
        'screen': fingerprint.get('screen', ''),
        'canvas': fingerprint.get('canvas', ''),
        'webgl': fingerprint.get('webgl', ''),
    }
    fp_string = json.dumps(stable_fields, sort_keys=True)
    return hashlib.sha256(fp_string.encode()).hexdigest()[:16]

def cleanup_expired_sessions():
    """Remove expired sessions."""
    now = time.time()
    with SESSION_LOCK:
        expired = [k for k, v in SESSION_STORE.items() if now - v['created_at'] > SESSION_EXPIRY]
        for k in expired:
            del SESSION_STORE[k]

def get_or_create_session(fingerprint_hash):
    """Get existing session or create new one."""
    cleanup_expired_sessions()
    with SESSION_LOCK:
        if fingerprint_hash not in SESSION_STORE:
            SESSION_STORE[fingerprint_hash] = {
                'attempts': 0,
                'created_at': time.time(),
                'escalated': False
            }
        return SESSION_STORE[fingerprint_hash]

def increment_session_attempts(fingerprint_hash):
    """Increment attempt count and check for escalation."""
    with SESSION_LOCK:
        if fingerprint_hash in SESSION_STORE:
            SESSION_STORE[fingerprint_hash]['attempts'] += 1
            attempts = SESSION_STORE[fingerprint_hash]['attempts']
            max_attempts = SECURITY_CONFIG.get('max_attempts', 3)
            if attempts >= max_attempts:
                SESSION_STORE[fingerprint_hash]['escalated'] = True
                return True, attempts  # Should escalate
            return False, attempts
        return False, 0

def reset_session(fingerprint_hash):
    """Reset session after successful verification."""
    with SESSION_LOCK:
        if fingerprint_hash in SESSION_STORE:
            del SESSION_STORE[fingerprint_hash]

def update_adaptive_threshold(passed, confidence):
    """Update adaptive threshold based on recent results (system evolution)."""
    global ADAPTIVE_THRESHOLD_ADJUSTMENT
    now = time.time()

    with RESULTS_LOCK:
        # Add new result
        RECENT_RESULTS.append((now, passed, confidence))

        # Keep only last 5 minutes of results
        cutoff = now - 300
        RECENT_RESULTS[:] = [(t, p, c) for t, p, c in RECENT_RESULTS if t > cutoff]

        # Need at least 10 results to make adjustments
        if len(RECENT_RESULTS) < 10:
            return

        # Calculate rejection rate
        rejections = sum(1 for _, p, _ in RECENT_RESULTS if not p)
        rejection_rate = rejections / len(RECENT_RESULTS)

        # If rejection rate > 70%, likely under attack - harden slightly
        if rejection_rate > 0.7:
            ADAPTIVE_THRESHOLD_ADJUSTMENT = min(0.10, ADAPTIVE_THRESHOLD_ADJUSTMENT + 0.02)
            print(f"⚠️ System hardening: threshold adjustment +{ADAPTIVE_THRESHOLD_ADJUSTMENT:.2f}")
        # If rejection rate < 30% and we've hardened, ease back
        elif rejection_rate < 0.3 and ADAPTIVE_THRESHOLD_ADJUSTMENT > 0:
            ADAPTIVE_THRESHOLD_ADJUSTMENT = max(0, ADAPTIVE_THRESHOLD_ADJUSTMENT - 0.01)
            print(f"✅ System easing: threshold adjustment +{ADAPTIVE_THRESHOLD_ADJUSTMENT:.2f}")

def get_current_threshold():
    """Get current ML threshold with adaptive adjustment."""
    base = SECURITY_CONFIG.get('ml_threshold', 0.55)
    return min(0.90, base + ADAPTIVE_THRESHOLD_ADJUSTMENT)  # Cap at 0.90

app = Flask(__name__, static_folder='.')
app.secret_key = secrets.token_hex(32)
CORS(app)

# Global variables for ML models
model = None  # Original RandomForest model
scaler = None
xgb_model = None  # New XGBoost model
xgb_scaler = None

# Get project root directory (parent of src/)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize database for logging all CAPTCHA attempts
db_path = os.path.join(project_root, 'captcha_analytics.db')
print(f"📊 Initializing CAPTCHA analytics database: {db_path}")

model_file = os.path.join(project_root, 'models', 'motor_captcha_model.pkl')
scaler_file = os.path.join(project_root, 'models', 'motor_captcha_scaler.pkl')
xgb_model_file = os.path.join(project_root, 'models', 'mouse_model_xgb_5.pkl')

# Initialize layers
pow_verifier = ProofOfWorkVerifier()
fp_analyzer = FingerprintAnalyzer()
advanced_trainer = AdvancedMotorCaptchaTrainer()

class MotorCaptchaVerifier:
    def __init__(self):
        self.load_or_create_model()
        self.load_xgb_model()
    
    def load_xgb_model(self):
        """Load XGBoost model for advanced bot detection"""
        global xgb_model, xgb_scaler
        
        if os.path.exists(xgb_model_file):
            try:
                with open(xgb_model_file, 'rb') as f:
                    xgb_model = pickle.load(f)
                print("✅ Loaded XGBoost model (mouse_model_xgb_5.pkl)")
                print("   Features: jitter, speed (mean/std/max), acceleration (mean/std/max), jerk (mean/std/max), curvature")
                print("   Thresholds: BOT < 0.20 | UNSURE 0.20-0.60 | HUMAN > 0.60")
            except Exception as e:
                print(f"⚠️  Failed to load XGBoost model: {e}")
                xgb_model = None
        else:
            print("⚠️  XGBoost model not found at:", xgb_model_file)
            xgb_model = None
    
    def load_or_create_model(self):
        """Load existing model or create a new one"""
        global model, scaler
        
        if os.path.exists(model_file) and os.path.exists(scaler_file):
            try:
                with open(model_file, 'rb') as f:
                    model = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    scaler = pickle.load(f)
                print("Loaded existing ML model")
            except:
                self.create_new_model()
        else:
            self.create_new_model()
    
    def create_new_model(self):
        """Create a new RandomForest model with synthetic training data"""
        global model, scaler
        
        # Generate synthetic training data
        # Human-like patterns: noisy, variable timing, natural curves
        # Automated patterns: perfect timing, straight lines, zero jitter
        
        n_samples = 1000
        X_train = []
        y_train = []
        
        for i in range(n_samples):
            if i < n_samples // 2:
                # Human-like features
                features = self.generate_human_features()
                label = 1  # Human
            else:
                # Automated-like features
                features = self.generate_automated_features()
                label = 0  # Automated
            
            X_train.append(features)
            y_train.append(label)
        
        X_train = np.array(X_train)
        y_train = np.array(y_train)
        
        # Normalize features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        
        # Train RandomForest
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train_scaled, y_train)
        
        # Create models directory if it doesn't exist
        models_dir = os.path.dirname(model_file)
        os.makedirs(models_dir, exist_ok=True)
        
        # Save model
        with open(model_file, 'wb') as f:
            pickle.dump(model, f)
        with open(scaler_file, 'wb') as f:
            pickle.dump(scaler, f)
        
        print("Created new ML model")
    
    def generate_human_features(self):
        """Generate synthetic human-like features (including direct target-to-target movements)"""
        return [
            np.random.uniform(50, 400),      # reaction_latency (ms) - wider range
            np.random.uniform(5, 80),        # avg_inter_event_time (ms) - allow faster movements
            np.random.uniform(0.01, 1.2),   # path_curvature - allow straighter paths
            np.random.uniform(0.3, 4.0),    # avg_velocity - wider range
            np.random.uniform(0.05, 2.0),   # avg_acceleration - allow more variation
            np.random.uniform(0.005, 0.8),  # avg_jerk - lower minimum
            np.random.uniform(0, 20),       # num_corrections - allow zero corrections
            np.random.uniform(0.1, 8.0),    # jitter_std - allow lower jitter for direct movements
            np.random.uniform(0.1, 1.2),    # velocity_variance - wider range
            np.random.uniform(0.01, 0.5),   # acceleration_variance - allow lower values
        ]
    
    def generate_automated_features(self):
        """Generate synthetic automated-pattern features"""
        return [
            np.random.uniform(0, 20),       # reaction_latency (very fast or very slow)
            np.random.uniform(0, 5),        # avg_inter_event_time (too regular)
            np.random.uniform(0, 0.1),      # path_curvature (straight lines)
            np.random.uniform(0, 0.5),       # avg_velocity (too constant)
            np.random.uniform(0, 0.1),       # avg_acceleration (zero)
            np.random.uniform(0, 0.01),      # avg_jerk (zero)
            np.random.uniform(0, 1),        # num_corrections (none)
            np.random.uniform(0, 0.1),      # jitter_std (zero jitter)
            np.random.uniform(0, 0.1),      # velocity_variance (constant)
            np.random.uniform(0, 0.05),     # acceleration_variance (zero)
        ]
    
    def extract_features(self, events, target_sequence, canvas_width, canvas_height):
        """Extract explainable features from event stream"""
        if len(events) < 3:
            return None
        
        # Convert events to numpy array for easier processing
        event_times = [e['t'] for e in events]
        event_x = [e['x'] for e in events]
        event_y = [e['y'] for e in events]
        
        # Normalize coordinates to [0, 1]
        event_x_norm = [x / canvas_width for x in event_x]
        event_y_norm = [y / canvas_height for y in event_y]
        
        # 1. Reaction Latency (time to first interaction)
        reaction_latency = event_times[0] if event_times else 0
        
        # 2. Inter-event times
        inter_event_times = []
        for i in range(1, len(event_times)):
            inter_event_times.append(event_times[i] - event_times[i-1])
        avg_inter_event_time = np.mean(inter_event_times) if inter_event_times else 0
        
        # 3. Path Curvature
        path_curvature = self.calculate_path_curvature(event_x_norm, event_y_norm)
        
        # 4. Velocity (pixels per ms)
        velocities = []
        for i in range(1, len(events)):
            dt = event_times[i] - event_times[i-1]
            if dt > 0:
                dx = event_x[i] - event_x[i-1]
                dy = event_y[i] - event_y[i-1]
                distance = math.sqrt(dx*dx + dy*dy)
                velocity = distance / dt
                velocities.append(velocity)
        avg_velocity = np.mean(velocities) if velocities else 0
        velocity_variance = np.var(velocities) if velocities else 0
        
        # 5. Acceleration
        accelerations = []
        for i in range(2, len(velocities)):
            dt = inter_event_times[i] if i < len(inter_event_times) else 1
            if dt > 0:
                dv = velocities[i] - velocities[i-1]
                acceleration = dv / dt
                accelerations.append(acceleration)
        avg_acceleration = np.mean(accelerations) if accelerations else 0
        acceleration_variance = np.var(accelerations) if accelerations else 0
        
        # 6. Jerk (rate of change of acceleration)
        jerks = []
        for i in range(1, len(accelerations)):
            dt = inter_event_times[i+1] if i+1 < len(inter_event_times) else 1
            if dt > 0:
                da = accelerations[i] - accelerations[i-1]
                jerk = da / dt
                jerks.append(jerk)
        avg_jerk = np.mean(jerks) if jerks else 0
        
        # 7. Corrections (direction reversals)
        num_corrections = self.count_corrections(event_x_norm, event_y_norm)
        
        # 8. Jitter (small random movements)
        jitter_std = self.calculate_jitter(event_x_norm, event_y_norm)
        
        features = [
            reaction_latency,
            avg_inter_event_time,
            path_curvature,
            avg_velocity,
            avg_acceleration,
            avg_jerk,
            num_corrections,
            jitter_std,
            velocity_variance,
            acceleration_variance
        ]
        
        return features
    
    def calculate_path_curvature(self, x_coords, y_coords):
        """Calculate average curvature of the path"""
        if len(x_coords) < 3:
            return 0
        
        curvatures = []
        for i in range(1, len(x_coords) - 1):
            # Calculate angle change
            dx1 = x_coords[i] - x_coords[i-1]
            dy1 = y_coords[i] - y_coords[i-1]
            dx2 = x_coords[i+1] - x_coords[i]
            dy2 = y_coords[i+1] - y_coords[i]
            
            angle1 = math.atan2(dy1, dx1)
            angle2 = math.atan2(dy2, dx2)
            
            angle_diff = abs(angle2 - angle1)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            
            curvatures.append(angle_diff)
        
        return np.mean(curvatures) if curvatures else 0
    
    def count_corrections(self, x_coords, y_coords):
        """Count direction reversals (corrections)"""
        if len(x_coords) < 3:
            return 0
        
        corrections = 0
        for i in range(1, len(x_coords) - 1):
            dx1 = x_coords[i] - x_coords[i-1]
            dx2 = x_coords[i+1] - x_coords[i]
            
            # Direction reversal in x
            if dx1 * dx2 < 0:
                corrections += 1
            
            dy1 = y_coords[i] - y_coords[i-1]
            dy2 = y_coords[i+1] - y_coords[i]
            
            # Direction reversal in y
            if dy1 * dy2 < 0:
                corrections += 1
        
        return corrections
    
    def calculate_jitter(self, x_coords, y_coords):
        """Calculate standard deviation of small movements (jitter)"""
        if len(x_coords) < 2:
            return 0
        
        movements = []
        for i in range(1, len(x_coords)):
            dx = x_coords[i] - x_coords[i-1]
            dy = y_coords[i] - y_coords[i-1]
            distance = math.sqrt(dx*dx + dy*dy)
            movements.append(distance)
        
        return np.std(movements) if movements else 0
    
    def extract_xgb_features(self, events, canvas_width, canvas_height):
        """Extract 11 features for XGBoost model
        
        Features:
        1. jitter_index - Standard deviation of small movements
        2. speed_mean - Average velocity
        3. speed_std - Standard deviation of velocity
        4. speed_max - Maximum velocity
        5. acc_mean - Average acceleration
        6. acc_std - Standard deviation of acceleration
        7. acc_max - Maximum acceleration
        8. jerk_mean - Average jerk (rate of acceleration change)
        9. jerk_std - Standard deviation of jerk
        10. jerk_max - Maximum jerk
        11. curvature - Average path curvature
        
        Returns:
            dict with 11 float features
        """
        if len(events) < 3:
            return None
        
        # Extract coordinates and times
        event_times = np.array([e['t'] for e in events])
        event_x = np.array([e['x'] for e in events])
        event_y = np.array([e['y'] for e in events])
        
        # Normalize coordinates
        event_x_norm = event_x / canvas_width
        event_y_norm = event_y / canvas_height
        
        # Calculate velocities (pixels per ms)
        velocities = []
        for i in range(1, len(events)):
            dt = event_times[i] - event_times[i-1]
            if dt > 0:
                dx = event_x[i] - event_x[i-1]
                dy = event_y[i] - event_y[i-1]
                distance = math.sqrt(dx*dx + dy*dy)
                velocity = distance / dt
                velocities.append(velocity)
        
        velocities = np.array(velocities) if velocities else np.array([0])
        
        # Calculate accelerations
        accelerations = []
        inter_event_times = np.diff(event_times)
        for i in range(1, len(velocities)):
            dt = inter_event_times[i] if i < len(inter_event_times) else 1
            if dt > 0:
                dv = velocities[i] - velocities[i-1]
                acceleration = dv / dt
                accelerations.append(acceleration)
        
        accelerations = np.array(accelerations) if accelerations else np.array([0])
        
        # Calculate jerk (rate of change of acceleration)
        jerks = []
        for i in range(1, len(accelerations)):
            dt = inter_event_times[i+1] if i+1 < len(inter_event_times) else 1
            if dt > 0:
                da = accelerations[i] - accelerations[i-1]
                jerk = da / dt
                jerks.append(jerk)
        
        jerks = np.array(jerks) if jerks else np.array([0])
        
        # Calculate jitter index (std of small movements)
        jitter = self.calculate_jitter(event_x_norm, event_y_norm)
        
        # Calculate curvature
        curvature = self.calculate_path_curvature(event_x_norm, event_y_norm)
        
        # Build feature dictionary
        features = {
            "jitter_index": float(jitter),
            "speed_mean":   float(np.mean(velocities)),
            "speed_std":    float(np.std(velocities)),
            "speed_max":    float(np.max(velocities)),
            "acc_mean":     float(np.mean(accelerations)),
            "acc_std":      float(np.std(accelerations)),
            "acc_max":      float(np.max(np.abs(accelerations))),
            "jerk_mean":    float(np.mean(jerks)),
            "jerk_std":     float(np.std(jerks)),
            "jerk_max":     float(np.max(np.abs(jerks))),
            "curvature":    float(curvature),
        }
        
        return features
    
    def apply_rules_layer(self, features):
        """Rules-based filtering to reject obviously automated patterns (human-friendly)"""
        reaction_latency, avg_inter_event_time, path_curvature, avg_velocity, \
        avg_acceleration, avg_jerk, num_corrections, jitter_std, \
        velocity_variance, acceleration_variance = features
        
        # Rule 1: Only block extremely suspicious behavior - humans can have direct movements
        # Allow straight paths as long as there's some natural variation
        
        # Rule 2: Impossible reaction times (< 5ms is suspiciously fast)
        if reaction_latency < 5:
            return False, "Impossibly fast reaction time"
        
        # Rule 3: Only block extremely precise timing (sub-millisecond precision)
        # Humans moving target-to-target can have consistent but not mechanical timing
        if avg_inter_event_time > 0 and avg_inter_event_time < 0.5:
            return False, "Sub-millisecond precision timing detected"
        
        # Rule 4: Allow direct movements - humans often move efficiently between targets
        # Only block if ALL indicators suggest automation
        perfect_movement_score = 0
        
        if jitter_std < 0.0001:  # Completely zero jitter
            perfect_movement_score += 1
        if path_curvature < 0.0001:  # Perfectly straight
            perfect_movement_score += 1  
        if acceleration_variance < 0.0001:  # Constant velocity
            perfect_movement_score += 1
        if num_corrections == 0 and path_curvature < 0.001:  # No corrections + straight
            perfect_movement_score += 1
            
        # Only reject if multiple automation indicators are present
        if perfect_movement_score >= 3:
            return False, "Multiple automation indicators detected"
        
        return True, "Passed rules layer"
    
    def classify(self, features):
        """Use ML classifier to score the trial"""
        global model, scaler
        
        if model is None or scaler is None:
            return 0.5, "Model not available"
        
        # Normalize features
        features_array = np.array(features).reshape(1, -1)
        features_scaled = scaler.transform(features_array)
        
        # Get probability of being human. If a pickled model is incompatible with the
        # current sklearn version (e.g., missing attributes like monotonic_cst),
        # rebuild a fresh model on synthetic data so verification can proceed.
        try:
            prob_human = model.predict_proba(features_scaled)[0][1]
        except AttributeError as e:
            print(f"Incompatible model detected ({e}); rebuilding model.")
            self.create_new_model()
            features_scaled = scaler.transform(features_array)
            prob_human = model.predict_proba(features_scaled)[0][1]
        
        return prob_human, f"ML score: {prob_human:.3f}"
    
    def classify_xgb(self, features_dict):
        """Classify using XGBoost model with bot detection thresholds
        
        Thresholds:
        - BOT (< 0.20): ≈98% synthetic bots
        - UNSURE (0.20-0.60): ≈1.5% humanish jitter bots
        - HUMAN (> 0.60): ≈96.2% real humans
        
        Returns:
            (score, category, message)
        """
        global xgb_model
        
        if xgb_model is None:
            return None, "UNAVAILABLE", "XGBoost model not loaded"
        
        try:
            # Convert features dict to array (order matters!)
            feature_array = np.array([[
                features_dict["jitter_index"],
                features_dict["speed_mean"],
                features_dict["speed_std"],
                features_dict["speed_max"],
                features_dict["acc_mean"],
                features_dict["acc_std"],
                features_dict["acc_max"],
                features_dict["jerk_mean"],
                features_dict["jerk_std"],
                features_dict["jerk_max"],
                features_dict["curvature"],
            ]])
            
            # Get prediction probability
            score = float(xgb_model.predict_proba(feature_array)[0][1])
            
            # Classify based on thresholds
            if score < 0.20:
                category = "BOT"
                message = f"🤖 BOT detected (score: {score:.3f}) - Synthetic bot pattern"
            elif score < 0.60:
                category = "UNSURE"
                message = f"⚠️ UNSURE (score: {score:.3f}) - Humanish jitter bot or unusual pattern"
            else:
                category = "HUMAN"
                message = f"✅ HUMAN verified (score: {score:.3f}) - Real human movement"
            
            return score, category, message
            
        except Exception as e:
            return None, "ERROR", f"XGBoost classification error: {e}"
    
    def verify(self, events, target_sequence, targets_hit, canvas_width, canvas_height):
        """Main verification pipeline"""
        # Check if all targets were hit
        if targets_hit < len(target_sequence):
            return {
                'verified': False,
                'reason': 'Not all targets hit - please try again',
                'escalate': False
            }
        
        # Extract features
        features = self.extract_features(events, target_sequence, canvas_width, canvas_height)
        if features is None:
            return {
                'verified': False,
                'reason': 'Insufficient data - please try again',
                'escalate': False
            }
        
        # Apply rules layer
        rules_passed, rules_message = self.apply_rules_layer(features)
        if not rules_passed:
            return {
                'verified': False,
                'reason': rules_message,
                'escalate': False
            }
        
        # ML classification
        ml_score, ml_message = self.classify(features)
        
        # Get security thresholds
        ml_threshold = SECURITY_CONFIG.get('ml_threshold', 0.55)
        
        # Extract feature values for detailed feedback (from features array)
        # Features: [avg_speed, total_distance, avg_inter_event_time, jitter_std, 
        #            path_curvature, acceleration_variance, num_corrections, avg_pause]
        avg_speed = features[0] if len(features) > 0 else 0
        total_distance = features[1] if len(features) > 1 else 0
        avg_pause = features[7] if len(features) > 7 else 0
        jitter_std = features[3] if len(features) > 3 else 0
        path_curvature = features[4] if len(features) > 4 else 0
        
        # Build detailed feedback
        feedback_details = []
        
        # Analyze specific aspects
        if avg_speed > 2000:
            feedback_details.append("Movement too fast (looks automated)")
        elif avg_speed < 50:
            feedback_details.append("Movement too slow or minimal")
            
        if total_distance < 150:
            feedback_details.append("Not enough mouse movement between targets")
        elif total_distance > 5000:
            feedback_details.append("Excessive wandering detected")
            
        if avg_pause > 500:
            feedback_details.append("Too many long pauses between movements")
        elif avg_pause < 5:
            feedback_details.append("No natural pauses - movements too robotic")
            
        if jitter_std < 0.0001 and path_curvature < 0.001:
            feedback_details.append("Movement patterns appear mechanical")
        
        # Decision logic with detailed feedback
        if ml_score >= ml_threshold:
            # Accept as human
            return {
                'verified': True,
                'reason': f"✅ Natural human movement detected",
                'escalate': False,
                'confidence': ml_score,
                'details': {
                    'score': f"{ml_score:.3f}",
                    'threshold': f"{ml_threshold:.2f}",
                    'status': 'PASS',
                    'speed': f"{avg_speed:.0f} px/s",
                    'distance': f"{total_distance:.0f} px",
                    'events': len(events)
                }
            }
        elif ml_score >= (ml_threshold - 0.10):
            # Close - give second chance with tips
            tips = []
            if avg_speed > 1500:
                tips.append("Slow down your movements slightly")
            if total_distance < 200:
                tips.append("Move more naturally - add some curves")
            if not tips:
                tips.append("Try moving with more natural variation")
                
            return {
                'verified': False,
                'reason': f"⚠️ Almost there! Try again with more natural movement",
                'escalate': False,
                'confidence': ml_score,
                'details': {
                    'score': f"{ml_score:.3f}",
                    'threshold': f"{ml_threshold:.2f}",
                    'gap': f"{(ml_threshold - ml_score):.3f}",
                    'status': 'RETRY',
                    'tips': tips
                }
            }
        else:
            # Failed - provide helpful guidance
            suggestions = []
            if avg_speed > 2000:
                suggestions.append("Slow down - move at a comfortable pace")
            if total_distance < 150:
                suggestions.append("Move your mouse more naturally between targets")
            if avg_pause < 5:
                suggestions.append("Take brief, natural pauses between movements")
            if not suggestions:
                suggestions.append("Try moving more like a human - with curves and slight hesitations")
                
            return {
                'verified': False,
                'reason': f"❌ Movement doesn't match human patterns",
                'escalate': False,
                'confidence': ml_score,
                'details': {
                    'score': f"{ml_score:.3f}",
                    'threshold': f"{ml_threshold:.2f}",
                    'status': 'FAIL',
                    'issues': feedback_details if feedback_details else ['Movement patterns appear automated'],
                    'suggestions': suggestions
                }
            }

# Initialize verifier
verifier = MotorCaptchaVerifier()

@app.route('/')
def index():
    return send_from_directory('../frontend', 'motor_captcha.html')

@app.route('/<path:path>')
def serve_static(path):
    # Try frontend directory first
    if path.endswith('.html'):
        # Check if it's in the attacker subfolder
        attacker_path = os.path.join('../frontend/attacker', path)
        if os.path.exists(os.path.join(os.path.dirname(__file__), attacker_path)):
            return send_from_directory('../frontend/attacker', path)
        return send_from_directory('../frontend', path)
    # Try static directories for JS files
    elif path.endswith('.js'):
        # Check attacker JS folder first
        if path.startswith('attacker/') or 'attack_visualizer' in path:
            return send_from_directory('../../static/js/attacker', path.replace('attacker/', ''))
        return send_from_directory('../../static/js', path)
    # Try static directories for CSS
    elif path.endswith('.css'):
        return send_from_directory('../../static/css', path)
    else:
        return send_from_directory('../../static', path)

@app.route('/get-challenge', methods=['GET'])
def get_challenge():
    """Generate PoW challenge for client"""
    session_id = secrets.token_hex(16)
    challenge = pow_verifier.generate_challenge(session_id)
    return jsonify({
        'session_id': session_id,
        'challenge': challenge
    })

@app.route('/verify-motor-captcha', methods=['POST'])
def verify_captcha():
    try:
        data = request.json

        # Extract data
        events = data.get('events', [])
        target_sequence = data.get('targetSequence', [])
        targets_hit = data.get('targetsHit', 0)
        canvas_width = data.get('canvasWidth', 800)
        canvas_height = data.get('canvasHeight', 500)

        # Layer 1: Fingerprint Analysis
        fingerprint = data.get('fingerprint', {})
        fp_risk, fp_flags = fp_analyzer.analyze(fingerprint)
        fp_hash = get_fingerprint_hash(fingerprint)

        # Get or create session for this fingerprint
        session_data = get_or_create_session(fp_hash)

        # Check if already escalated to puzzle
        if session_data.get('escalated', False):
            return jsonify({
                'verified': False,
                'reason': 'Maximum motor CAPTCHA attempts exceeded',
                'escalate': True,
                'attempts': session_data['attempts'],
                'fp_hash': fp_hash
            })

        # Layer 2: PoW Verification
        session_id = data.get('session_id', '')
        pow_nonce = data.get('pow_nonce', 0)
        pow_hash = data.get('pow_hash', '')
        pow_difficulty = pow_verifier.get_difficulty(fp_risk)

        pow_valid, pow_msg = pow_verifier.verify(
            session_id, pow_nonce, pow_hash, pow_difficulty
        )

        if not pow_valid:
            return jsonify({
                'verified': False,
                'reason': 'Invalid proof-of-work',
                'escalate': False
            })

        # Layer 3: Motor Timing Analysis
        result = verifier.verify(
            events, target_sequence, targets_hit,
            canvas_width, canvas_height
        )

        # Layer 4: XGBoost Bot Detection (NEW - High Accuracy Model)
        try:
            xgb_features = verifier.extract_xgb_features(events, canvas_width, canvas_height)
            if xgb_features:
                xgb_score, xgb_category, xgb_message = verifier.classify_xgb(xgb_features)

                if xgb_score is not None:
                    result['xgb_score'] = xgb_score
                    result['xgb_category'] = xgb_category
                    result['xgb_message'] = xgb_message
                    result['xgb_features'] = xgb_features

                    # CRITICAL: If XGBoost detects BOT, override other results
                    if xgb_category == "BOT":
                        result['verified'] = False
                        result['reason'] = f"🤖 {xgb_message}"
                        print(f"⚠️ XGBoost BOT DETECTION: {xgb_message}")

                    # If XGBoost is UNSURE, flag for review but don't auto-reject
                    elif xgb_category == "UNSURE":
                        if result.get('verified', False):
                            result['warning'] = xgb_message
                            print(f"⚠️ XGBoost UNSURE: {xgb_message}")

                    # If XGBoost confirms HUMAN, boost confidence
                    elif xgb_category == "HUMAN" and result.get('verified', False):
                        result['reason'] = f"✅ Verified by both models - {xgb_message}"
                        print(f"✅ XGBoost HUMAN: {xgb_message}")
        except Exception as e:
            print(f"XGBoost analysis error: {e}")
            result['xgb_error'] = str(e)

        # Optional: Use advanced ML if available
        use_advanced = data.get('use_advanced', False)
        if use_advanced:
            try:
                advanced_score, advanced_msg = advanced_trainer.predict_advanced(
                    events, target_sequence, canvas_width, canvas_height
                )
                result['advanced_score'] = advanced_score
                result['advanced_message'] = advanced_msg

                # Combine scores (weighted average)
                if 'confidence' in result:
                    combined_score = 0.7 * result['confidence'] + 0.3 * advanced_score
                    result['combined_confidence'] = combined_score

                    # Use configurable combined threshold
                    combined_threshold = SECURITY_CONFIG.get('combined_threshold', 0.68)

                    # Update verification based on combined score
                    if combined_score >= combined_threshold:
                        result['verified'] = True
                        result['reason'] = f"Combined ML verification (Score: {combined_score:.3f} >= {combined_threshold:.2f})"
                    else:
                        result['verified'] = False
                        result['reason'] = f"Combined ML score below threshold ({combined_score:.3f} < {combined_threshold:.2f})"
            except Exception as e:
                print(f"Advanced ML error: {e}")
                result['advanced_error'] = str(e)

        # Combine all scores with configurable fingerprint threshold
        fingerprint_risk_max = SECURITY_CONFIG.get('fingerprint_risk_max', 0.6)

        if fp_risk > fingerprint_risk_max or len(fp_flags) > 2:
            result['verified'] = False
            result['reason'] = f"High risk fingerprint: {', '.join(fp_flags)} (Risk: {fp_risk:.2f} > {fingerprint_risk_max:.2f})"

        result['fp_risk'] = fp_risk
        result['fp_flags'] = fp_flags
        result['fp_hash'] = fp_hash

        # Update adaptive threshold (system evolution)
        confidence = result.get('confidence', 0.5)
        update_adaptive_threshold(result.get('verified', False), confidence)

        # Log to database
        try:
            db = CaptchaDatabase(db_path)
            
            # Determine user type based on comprehensive bot detection
            user_type = 'human'  # Default assumption
            
            # Check multiple bot indicators
            bot_indicators = []
            
            # XGBoost detection
            if result.get('xgb_category') == 'BOT':
                bot_indicators.append('xgb_bot')
                user_type = 'bot'
            elif result.get('xgb_category') == 'UNSURE':
                bot_indicators.append('xgb_unsure')
            
            # Fingerprint risk analysis
            if fp_risk > 0.65:  # Lower threshold for more detection
                bot_indicators.append('high_fp_risk')
                user_type = 'bot'
            
            # Check specific fingerprint flags
            high_risk_flags = ['webdriver_detected', 'headless_browser', 'selenium_detected']
            if any(flag in fp_flags for flag in high_risk_flags):
                bot_indicators.append('automation_detected')
                user_type = 'bot'
            
            # Check if verification explicitly failed due to bot patterns
            if not result.get('verified', False):
                reason = result.get('reason', '').lower()
                if any(keyword in reason for keyword in ['bot', 'automated', 'robotic', 'mechanical']):
                    bot_indicators.append('pattern_bot')
                    user_type = 'bot'
            
            # Override: If verification failed AND has suspicious fingerprint, likely bot
            if not result.get('verified', False) and (fp_risk > 0.5 or len(fp_flags) > 1):
                user_type = 'bot'
                bot_indicators.append('failed_suspicious')
            
            # Log detection reasoning
            if user_type == 'bot':
                print(f"🤖 User classified as BOT: {', '.join(bot_indicators)} (fp_risk: {fp_risk:.2f})")
            
            # Calculate completion time from events
            completion_time = None
            if events and len(events) > 0:
                start_time = events[0].get('t', 0)
                end_time = events[-1].get('t', 0)
                completion_time = (end_time - start_time) / 1000.0  # Convert ms to seconds
            
            # Determine failure reason
            failure_reason = None
            if not result.get('verified', False):
                failure_reason = result.get('reason', 'Unknown')
            
            # Log the attempt
            attempt_id = db.log_captcha_attempt(
                captcha_type='motor',
                user_type=user_type,
                success=result.get('verified', False),
                completion_time=completion_time,
                attempts_used=data.get('attempt_number', 1),
                failure_reason=failure_reason,
                metadata={
                    'fp_risk': fp_risk,
                    'fp_flags': fp_flags,
                    'xgb_score': result.get('xgb_score'),
                    'xgb_category': result.get('xgb_category'),
                    'targets_hit': targets_hit,
                    'total_targets': len(target_sequence),
                    'bot_indicators': bot_indicators if user_type == 'bot' else [],
                    'detection_confidence': result.get('confidence', 0.0),
                    'fp_hash': fp_hash[:8]  # First 8 chars for tracking
                }
            )
            
            # Log motor events
            for i, event in enumerate(events):
                if event.get('type') == 'hit':
                    db.log_motor_event(
                        attempt_id=attempt_id,
                        event_type='hit',
                        target_id=event.get('targetId'),
                        x_coord=int(event.get('x', 0)),
                        y_coord=int(event.get('y', 0)),
                        time_offset=(event.get('t', 0) - events[0].get('t', 0)) / 1000.0,
                        sequence_number=i+1
                    )
            
            # Log ML detection if bot was detected
            if user_type == 'bot' and result.get('xgb_score') is not None:
                xgb_features = result.get('xgb_features', {})
                db.log_ml_detection(
                    attempt_id=attempt_id,
                    is_bot=True,
                    confidence_score=1.0 - result.get('xgb_score', 0),  # Convert to bot confidence
                    speed_score=xgb_features.get('speed_mean'),
                    linearity_score=xgb_features.get('jitter_index'),
                    timing_score=xgb_features.get('acc_mean'),
                    prediction_model='XGBoost'
                )
            
            db.close()
            print(f"📊 Logged attempt {attempt_id}: {user_type} - {'✓' if result.get('verified') else '✗'}")
            
        except Exception as e:
            print(f"⚠️  Database logging error: {e}")
            # Don't fail the request if logging fails

        # Handle verification result with session tracking
        if result.get('verified', False):
            # Success - reset session and allow through
            reset_session(fp_hash)
            result['escalate'] = False
            print(f"✅ Verification PASSED for {fp_hash}")

            # Self-training: Log high-confidence human data
            if confidence > 0.75 and result.get('xgb_score', 0) > 0.70:
                try:
                    advanced_trainer.collect_training_sample(
                        events, target_sequence, canvas_width, canvas_height,
                        label=1, metadata={'source': 'auto_verified', 'confidence': confidence}
                    )
                    print(f"📊 Collected training sample (confidence: {confidence:.2f})")
                except Exception as e:
                    print(f"Training collection error: {e}")
        else:
            # Failure - increment attempts and check for escalation
            should_escalate, attempts = increment_session_attempts(fp_hash)
            result['attempts'] = attempts
            result['max_attempts'] = SECURITY_CONFIG.get('max_attempts', 3)

            if should_escalate:
                result['escalate'] = True
                result['reason'] = f"Motor CAPTCHA failed {attempts} times - switching to puzzle verification"
                print(f"🧩 Escalating {fp_hash} to puzzle after {attempts} failures")
            else:
                result['escalate'] = False
                remaining = SECURITY_CONFIG.get('max_attempts', 3) - attempts
                print(f"❌ Verification FAILED for {fp_hash} - {remaining} attempts remaining")

        result['current_threshold'] = get_current_threshold()
        print(f"Final verification result: verified={result.get('verified')}, escalate={result.get('escalate')}")
        return jsonify(result)

    except Exception as e:
        print(f"Verification error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'verified': False,
            'reason': f'Server error: {str(e)}',
            'escalate': False
        }), 500

@app.route('/collect-training-data', methods=['POST'])
def collect_training_data():
    """Collect labeled training data for model improvement"""
    try:
        data = request.json
        
        events = data.get('events', [])
        target_sequence = data.get('targetSequence', [])
        canvas_width = data.get('canvasWidth', 800)
        canvas_height = data.get('canvasHeight', 500)
        label = data.get('label', 1)  # 1=human, 0=automated
        metadata = data.get('metadata', {})
        
        success = advanced_trainer.collect_training_sample(
            events, target_sequence, canvas_width, canvas_height, label, metadata
        )
        
        return jsonify({
            'success': success,
            'total_samples': len(advanced_trainer.training_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/train-advanced-model', methods=['POST'])
def train_advanced_model():
    """Trigger advanced model training"""
    try:
        success = advanced_trainer.train_ensemble_models()
        return jsonify({
            'success': success,
            'training_samples': len(advanced_trainer.training_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify-advanced', methods=['POST'])
def verify_advanced():
    """Use advanced ML model for verification"""
    try:
        data = request.json
        
        events = data.get('events', [])
        target_sequence = data.get('targetSequence', [])
        canvas_width = data.get('canvasWidth', 800)
        canvas_height = data.get('canvasHeight', 500)
        
        score, message = advanced_trainer.predict_advanced(
            events, target_sequence, canvas_width, canvas_height
        )
        
        return jsonify({
            'score': score,
            'message': message,
            'verified': score >= 0.6
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/training-stats', methods=['GET'])
def training_stats():
    """Get training statistics"""
    try:
        stats = advanced_trainer.get_training_stats()
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/training-interface')
def training_interface():
    """Serve training interface"""
    return send_from_directory('../frontend', 'training_interface.html')

@app.route('/attack_visualizer.html')
def attack_visualizer():
    """Serve attack visualizer interface"""
    return send_from_directory('../frontend/attacker', 'attack_visualizer.html')

@app.route('/security/config', methods=['GET'])
def get_security_config():
    """Get current security configuration"""
    try:
        from security_config import CONFIG_DESCRIPTIONS
        
        config_with_descriptions = {
            'current_config': SECURITY_CONFIG,
            'descriptions': CONFIG_DESCRIPTIONS,
            'available_levels': {
                'LOW': 'Easy for users, less secure (testing)',
                'MEDIUM': 'Balanced security (recommended)',
                'HIGH': 'Strong security (financial apps)',
                'MAXIMUM': 'Very strict (critical systems)'
            }
        }
        
        return jsonify(config_with_descriptions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/security/test', methods=['POST'])
def test_security():
    """Test if a given score would pass current security settings"""
    try:
        data = request.json
        test_score = data.get('score', 0.5)
        
        ml_threshold = SECURITY_CONFIG.get('ml_threshold', 0.65)
        advanced_threshold = SECURITY_CONFIG.get('advanced_threshold', 0.70)
        combined_threshold = SECURITY_CONFIG.get('combined_threshold', 0.68)
        
        results = {
            'test_score': test_score,
            'thresholds': {
                'ml_threshold': ml_threshold,
                'advanced_threshold': advanced_threshold,
                'combined_threshold': combined_threshold
            },
            'would_pass': {
                'ml_verification': test_score >= ml_threshold,
                'advanced_verification': test_score >= advanced_threshold,
                'combined_verification': test_score >= combined_threshold
            },
            'security_level': SECURITY_CONFIG.get('name', 'CUSTOM'),
            'recommendation': 'PASS' if test_score >= ml_threshold else 'FAIL'
        }
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Lightweight health check for deployment verification"""
    model_exists = os.path.exists(model_file)
    scaler_exists = os.path.exists(scaler_file)
    xgb_exists = os.path.exists(xgb_model_file)
    
    return jsonify({
        'status': 'ok',
        'security_level': SECURITY_CONFIG.get('name', 'CUSTOM'),
        'model_loaded': model is not None,
        'scaler_loaded': scaler is not None,
        'model_path': str(model_file),
        'scaler_path': str(scaler_file),
        'model_files_present': model_exists and scaler_exists,
        'xgb_model_loaded': xgb_model is not None,
        'xgb_model_path': str(xgb_model_file),
        'xgb_model_present': xgb_exists,
        'xgb_thresholds': {
            'bot': '< 0.20 (98% bots)',
            'unsure': '0.20-0.60 (1.5% humanish bots)',
            'human': '> 0.60 (96.2% humans)'
        },
        'advanced_models_loaded': bool(getattr(advanced_trainer, 'models', {})),
        'training_samples_cached': len(getattr(advanced_trainer, 'training_data', []))
    })


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "security_level": SECURITY_CONFIG.get('name', 'CUSTOM'),
        "current_threshold": get_current_threshold(),
        "threshold_adjustment": ADAPTIVE_THRESHOLD_ADJUSTMENT,
        "active_sessions": len(SESSION_STORE),
        "recent_results": len(RECENT_RESULTS)
    })


@app.route('/security/config')
def security_config_endpoint():
    """Get current security configuration."""
    return jsonify({
        "config": SECURITY_CONFIG,
        "current_threshold": get_current_threshold(),
        "adaptive_adjustment": ADAPTIVE_THRESHOLD_ADJUSTMENT,
        "initial_threshold": INITIAL_ML_THRESHOLD
    })


# =============================================================================
# STANDARDIZED API v1 (for interoperability)
# =============================================================================

@app.route('/api/v1/challenge', methods=['GET'])
def api_v1_challenge():
    """Get a CAPTCHA challenge (standardized API)."""
    session_id = secrets.token_urlsafe(16)
    challenge = pow_verifier.create_challenge(session_id)
    num_targets = random.randint(
        SECURITY_CONFIG.get('min_targets', 3),
        SECURITY_CONFIG.get('min_targets', 3) + 2
    )
    target_sequence = list(range(1, num_targets + 1))

    return jsonify({
        "session_id": session_id,
        "pow_challenge": challenge,
        "pow_difficulty": SECURITY_CONFIG.get('pow_difficulty_base', 4),
        "target_sequence": target_sequence,
        "timeout_seconds": 30,
        "canvas_size": {"width": 800, "height": 500}
    })


@app.route('/api/v1/solve', methods=['POST'])
def api_v1_solve():
    """Submit CAPTCHA solution (standardized API)."""
    # This is an alias for verify-motor-captcha with cleaner response
    data = request.json

    # Forward to existing verification logic
    result = verify_captcha()

    # Parse the response and return standardized format
    if isinstance(result, tuple):
        response_data = result[0].get_json()
        status_code = result[1]
    else:
        response_data = result.get_json()
        status_code = 200

    return jsonify({
        "success": response_data.get("verified", False),
        "escalate_to_puzzle": response_data.get("escalate", False),
        "confidence": response_data.get("confidence", 0),
        "reason": response_data.get("reason", ""),
        "session_info": {
            "fp_hash": response_data.get("fp_hash", ""),
            "attempts": response_data.get("attempts", 0),
            "max_attempts": response_data.get("max_attempts", 3)
        }
    }), status_code


@app.route('/api/v1/status', methods=['GET'])
def api_v1_status():
    """Get system status (standardized API)."""
    return jsonify({
        "healthy": True,
        "security_level": SECURITY_CONFIG.get('name', 'CUSTOM'),
        "motor_captcha": {
            "threshold": get_current_threshold(),
            "min_events": SECURITY_CONFIG.get('min_events', 15),
            "min_targets": SECURITY_CONFIG.get('min_targets', 3)
        },
        "puzzle_captcha": {
            "min_solve_time": 4.0,
            "min_events": 5,
            "min_interactions": 2
        },
        "escalation": {
            "max_motor_attempts": SECURITY_CONFIG.get('max_attempts', 3)
        }
    })


# Global puzzle storage (for database feature branch compatibility)
PUZZLES = {}

@app.route("/api/check", methods=["POST"])
def api_check():
    """Puzzle verification endpoint from database feature branch"""
    data = request.get_json(silent=True) or {}
    pid = data.get("id")
    order = data.get("order")
    meta = PUZZLES.get(pid)
    if not meta or not isinstance(order, list) or len(order) != len(meta["solution"]):
        return jsonify({"ok": False, "reason": "invalid"}), 400
    
    solved = [int(x) for x in order] == meta["solution"]
    
    # Calculate completion time
    completion_time = None
    if meta.get('ts'):
        completion_time = time.time() - meta['ts']
    
    # Log puzzle attempt to database
    try:
        db = CaptchaDatabase(db_path)
        
        # Determine user type (puzzle is usually escalation from failed motor attempts)
        user_type = 'human'  # Default to human for puzzle attempts
        
        attempt_id = db.log_captcha_attempt(
            captcha_type='puzzle',
            user_type=user_type,
            success=solved,
            completion_time=completion_time,
            attempts_used=1,
            failure_reason='Incorrect tile arrangement' if not solved else None,
            metadata={
                'puzzle_id': pid,
                'grid_size': meta.get('grid', 3),
                'tiles_count': len(meta['solution']),
                'submitted_order': order,
                'correct_order': meta['solution'],
                'moves_made': len(order)
            }
        )
        
        db.close()
        print(f"📊 Logged puzzle attempt {attempt_id}: {'✓ SOLVED' if solved else '✗ FAILED'} (Time: {completion_time:.1f}s)")
        
    except Exception as e:
        print(f"⚠️  Database logging error (puzzle): {e}")
        # Don't fail the request if logging fails
    
    if not solved:
        return jsonify({"ok": False, "reason": "incorrect"})
    
    code = secrets.token_urlsafe(16)
    return jsonify({"ok": solved, 'code': code})


if __name__ == '__main__':
    import sys
    
    # Try different ports if 5000 is in use
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    print("Starting CAPTCHA Server...")
    print(f"Server running at http://localhost:{port}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=True)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n⚠️  Port {port} is already in use.")
            print("Trying alternative port 5001...")
            app.run(host='0.0.0.0', port=5001, debug=True)
        else:
            raise