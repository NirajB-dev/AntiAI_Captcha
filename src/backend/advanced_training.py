#Author: Niraj


#!/usr/bin/env python3
"""
Advanced Motor-Timing CAPTCHA Training System
Provides enhanced ML training capabilities with legitimate data collection
"""

import numpy as np
import json
import math
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import pickle
import os
from datetime import datetime
import statistics
from pathlib import Path

class AdvancedMotorCaptchaTrainer:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parents[2]
        self.training_data = []
        self.models = {}
        self.scalers = {}
        # Get project root directory (parent of src/)
        project_root = Path(__file__).resolve().parents[2]
        self.data_file = project_root / 'data' / 'captcha_training_data.json'
        self.models_dir = project_root / 'models'
        
        # Create directories if they don't exist
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.load_training_data()
        self.load_models()
    
    def extract_advanced_features(self, events, target_sequence, canvas_width, canvas_height):
        """Extract comprehensive features from event stream"""
        if len(events) < 3:
            return None
        
        # Basic preprocessing
        event_times = np.array([e['t'] for e in events])
        event_x = np.array([e['x'] for e in events])
        event_y = np.array([e['y'] for e in events])
        
        # Normalize coordinates
        event_x_norm = event_x / canvas_width
        event_y_norm = event_y / canvas_height
        
        features = []
        
        # 1. Timing Features
        inter_event_times = np.diff(event_times)
        features.extend([
            event_times[0],  # Initial delay
            np.mean(inter_event_times),
            np.std(inter_event_times),
            np.min(inter_event_times),
            np.max(inter_event_times),
            len(events)  # Total events
        ])
        
        # 2. Spatial Features
        distances = []
        for i in range(1, len(events)):
            dx = event_x[i] - event_x[i-1]
            dy = event_y[i] - event_y[i-1]
            distance = math.sqrt(dx*dx + dy*dy)
            distances.append(distance)
        
        distances = np.array(distances)
        features.extend([
            np.mean(distances),
            np.std(distances),
            np.sum(distances),  # Total path length
        ])
        
        # 3. Velocity Features
        velocities = []
        for i in range(len(distances)):
            if inter_event_times[i] > 0:
                velocity = distances[i] / inter_event_times[i]
                velocities.append(velocity)
        
        if velocities:
            velocities = np.array(velocities)
            features.extend([
                np.mean(velocities),
                np.std(velocities),
                np.max(velocities),
                np.min(velocities)
            ])
        else:
            features.extend([0, 0, 0, 0])
        
        # 4. Acceleration Features
        if len(velocities) > 1:
            accelerations = np.diff(velocities)
            features.extend([
                np.mean(accelerations),
                np.std(accelerations),
                np.max(np.abs(accelerations))
            ])
        else:
            features.extend([0, 0, 0])
        
        # 5. Direction Changes
        direction_changes = 0
        for i in range(2, len(event_x)):
            v1_x = event_x[i-1] - event_x[i-2]
            v1_y = event_y[i-1] - event_y[i-2]
            v2_x = event_x[i] - event_x[i-1]
            v2_y = event_y[i] - event_y[i-1]
            
            # Calculate angle between vectors
            dot_product = v1_x * v2_x + v1_y * v2_y
            mag1 = math.sqrt(v1_x**2 + v1_y**2)
            mag2 = math.sqrt(v2_x**2 + v2_y**2)
            
            if mag1 > 0 and mag2 > 0:
                cos_angle = dot_product / (mag1 * mag2)
                cos_angle = max(-1, min(1, cos_angle))  # Clamp to [-1, 1]
                angle = math.acos(cos_angle)
                
                if angle > math.pi / 4:  # 45 degrees
                    direction_changes += 1
        
        features.append(direction_changes)
        
        # 6. Pause Analysis
        pauses = sum(1 for dt in inter_event_times if dt > 100)  # Pauses > 100ms
        features.append(pauses)
        
        # 7. Rhythm Analysis
        if len(inter_event_times) > 2:
            # Coefficient of variation for timing regularity
            cv = np.std(inter_event_times) / np.mean(inter_event_times)
            features.append(cv)
        else:
            features.append(0)
        
        # 8. Target Efficiency
        if target_sequence:
            # Calculate efficiency based on direct path vs actual path
            total_direct_distance = 0
            for i in range(len(target_sequence) - 1):
                dx = target_sequence[i+1]['x'] - target_sequence[i]['x']
                dy = target_sequence[i+1]['y'] - target_sequence[i]['y']
                total_direct_distance += math.sqrt(dx*dx + dy*dy)
            
            efficiency = total_direct_distance / np.sum(distances) if np.sum(distances) > 0 else 0
            features.append(efficiency)
        else:
            features.append(0)
        
        return features
    
    def collect_training_sample(self, events, target_sequence, canvas_width, canvas_height, label, metadata=None):
        """Collect a training sample with label (0=automated, 1=human)"""
        try:
            features = self.extract_advanced_features(events, target_sequence, canvas_width, canvas_height)
            if features is None:
                return False
            
            sample = {
                'features': features,
                'label': label,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            self.training_data.append(sample)
            self.save_training_data()
            
            print(f"Collected training sample: {len(features)} features, label={label}")
            return True
            
        except Exception as e:
            print(f"Error collecting training sample: {e}")
            return False
    
    def train_ensemble_models(self):
        """Train multiple ML models on collected data"""
        if len(self.training_data) < 10:
            print("Insufficient training data (need at least 10 samples)")
            return False
        
        try:
            # Prepare data
            X = np.array([sample['features'] for sample in self.training_data])
            y = np.array([sample['label'] for sample in self.training_data])
            
            print(f"Training on {len(X)} samples with {X.shape[1]} features")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train multiple models
            models_to_train = {
                'random_forest': RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                ),
                'gradient_boosting': GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=6,
                    random_state=42
                ),
                'svm': SVC(
                    kernel='rbf',
                    probability=True,
                    random_state=42
                )
            }
            
            self.models = {}
            self.scalers = {}
            
            for name, model in models_to_train.items():
                print(f"Training {name}...")
                
                # Train model
                model.fit(X_train_scaled, y_train)
                
                # Evaluate
                train_score = model.score(X_train_scaled, y_train)
                test_score = model.score(X_test_scaled, y_test)
                
                print(f"{name} - Train: {train_score:.3f}, Test: {test_score:.3f}")
                
                # Save model
                self.models[name] = model
                self.scalers[name] = scaler
            
            # Save models to disk
            self.save_models()
            
            print("Model training completed successfully")
            return True
            
        except Exception as e:
            print(f"Error training models: {e}")
            return False
    
    def predict_advanced(self, events, target_sequence, canvas_width, canvas_height):
        """Make prediction using ensemble of trained models"""
        try:
            features = self.extract_advanced_features(events, target_sequence, canvas_width, canvas_height)
            if features is None:
                return 0.5, "Insufficient data for prediction"
            
            if not self.models:
                return 0.5, "No trained models available"
            
            # Get predictions from all models
            predictions = []
            for name, model in self.models.items():
                scaler = self.scalers.get(name)
                if scaler:
                    features_scaled = scaler.transform([features])
                    prob = model.predict_proba(features_scaled)[0][1]  # Probability of being human
                    predictions.append(prob)
            
            if predictions:
                # Ensemble average
                avg_prediction = np.mean(predictions)
                return avg_prediction, f"Ensemble prediction: {avg_prediction:.3f}"
            else:
                return 0.5, "No valid predictions available"
            
        except Exception as e:
            print(f"Error making prediction: {e}")
            return 0.5, f"Prediction error: {str(e)}"
    
    def save_training_data(self):
        """Save training data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.training_data, f, indent=2)
        except Exception as e:
            print(f"Error saving training data: {e}")
    
    def load_training_data(self):
        """Load training data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.training_data = json.load(f)
                print(f"Loaded {len(self.training_data)} existing training samples")
            else:
                self.training_data = []
        except Exception as e:
            print(f"Error loading training data: {e}")
            self.training_data = []
    
    def save_models(self):
        """Save trained models to disk"""
        try:
            for name, model in self.models.items():
                model_file = os.path.join(self.models_dir, f'{name}_advanced.pkl')
                scaler_file = os.path.join(self.models_dir, f'{name}_scaler_advanced.pkl')
                
                with open(model_file, 'wb') as f:
                    pickle.dump(model, f)
                
                scaler = self.scalers.get(name)
                if scaler:
                    with open(scaler_file, 'wb') as f:
                        pickle.dump(scaler, f)
            
            print("Models saved successfully")
        except Exception as e:
            print(f"Error saving models: {e}")
    
    def load_models(self):
        """Load trained models from disk"""
        try:
            self.models = {}
            self.scalers = {}
            
            model_files = [f for f in os.listdir(self.models_dir) if f.endswith('_advanced.pkl')] if os.path.exists(self.models_dir) else []
            
            for model_file in model_files:
                name = model_file.replace('_advanced.pkl', '')
                model_path = os.path.join(self.models_dir, model_file)
                scaler_path = os.path.join(self.models_dir, f'{name}_scaler_advanced.pkl')
                
                if os.path.exists(model_path):
                    with open(model_path, 'rb') as f:
                        self.models[name] = pickle.load(f)
                    
                    if os.path.exists(scaler_path):
                        with open(scaler_path, 'rb') as f:
                            self.scalers[name] = pickle.load(f)
            
            if self.models:
                print(f"Loaded {len(self.models)} advanced models")
            
        except Exception as e:
            print(f"Error loading models: {e}")
    
    def get_training_stats(self):
        """Get statistics about training data"""
        if not self.training_data:
            return {
                'total_samples': 0,
                'human_samples': 0,
                'automated_samples': 0,
                'feature_count': 0,
                'models_trained': 0
            }
        
        human_samples = sum(1 for s in self.training_data if s['label'] == 1)
        automated_samples = len(self.training_data) - human_samples
        
        return {
            'total_samples': len(self.training_data),
            'human_samples': human_samples,
            'automated_samples': automated_samples,
            'feature_count': len(self.training_data[0]['features']) if self.training_data else 0,
            'models_trained': len(self.models)
        }
