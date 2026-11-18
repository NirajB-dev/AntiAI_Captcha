#Author: Niraj

#!/usr/bin/env python3


"""
Mock Data Generator for CAPTCHA Analytics Dashboard
Adds realistic sample data to test dashboard functionality
"""

import sys
import os
import random
from datetime import datetime, timedelta
import json

# Add the project root to the path to import database module
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.backend.captcha_database import CaptchaDatabase

def generate_mock_data():
    """Generate comprehensive mock data for dashboard testing."""
    
    print("🔄 Generating mock data for CAPTCHA Analytics Dashboard...")
    
    db = CaptchaDatabase()
    
    # Define realistic data patterns
    user_types = ['human', 'bot', 'llm_attack', 'computer_vision']
    captcha_types = ['motor']  # Only motor since puzzle was removed
    attack_types = ['automated', 'ml_vision', 'computer_vision', 'llm_based']
    attack_methods = ['opencv_detection', 'claude_vision', 'selenium_automation', 'direct_clicks', 'linear_movement']
    
    # Success rates by user type (realistic patterns)
    success_rates = {
        'human': 0.87,          # Humans succeed most of the time
        'bot': 0.23,            # Basic bots mostly fail
        'llm_attack': 0.42,     # LLM attacks sometimes work
        'computer_vision': 0.68  # CV attacks often succeed
    }
    
    failure_reasons = [
        'Movement patterns automated',
        'Fingerprint risk too high', 
        'Invalid proof-of-work',
        'Impossible reaction time',
        'Multiple automation indicators',
        'XGBoost BOT detection',
        'Session limit exceeded',
        'Timeout expired'
    ]
    
    print("📊 Adding CAPTCHA attempts...")
    
    # Generate 150 CAPTCHA attempts over the last 30 days
    attempt_ids = []
    for i in range(150):
        # Random timestamp within last 30 days (more recent = more activity)
        if i < 50:
            # Last 3 days - high activity
            days_ago = random.uniform(0, 3)
        elif i < 100:
            # Last 2 weeks - medium activity  
            days_ago = random.uniform(3, 14)
        else:
            # Last month - lower activity
            days_ago = random.uniform(14, 30)
            
        timestamp = datetime.now() - timedelta(days=days_ago)
        
        # Select user type with realistic distribution
        user_type_weights = [0.60, 0.20, 0.12, 0.08]  # More humans than bots
        user_type = random.choices(user_types, weights=user_type_weights)[0]
        
        captcha_type = 'motor'  # Only motor CAPTCHAs
        
        # Determine success based on user type probability
        success = random.random() < success_rates[user_type]
        
        # Generate realistic completion times
        if success:
            if user_type == 'human':
                completion_time = random.uniform(12.5, 45.0)  # Humans take 12-45 seconds
            elif user_type == 'bot':
                completion_time = random.uniform(1.2, 8.0)    # Fast bots (when they succeed)
            elif user_type == 'computer_vision':
                completion_time = random.uniform(4.5, 12.0)   # CV is consistent
            else:  # llm_attack
                completion_time = random.uniform(18.0, 35.0)  # LLM takes time to process
        else:
            completion_time = random.uniform(1.0, 20.0)  # Failed attempts vary widely
        
        # Attempts used (bots might retry more)
        attempts_used = 1 if success else random.randint(1, 4)
        if user_type == 'bot' and not success:
            attempts_used = random.randint(2, 6)
        
        # Failure reason for unsuccessful attempts
        failure_reason = None if success else random.choice(failure_reasons)
        
        # Metadata with ML scores and detection info
        metadata = {
            'ml_score': random.uniform(0.15, 0.95) if user_type == 'human' else random.uniform(0.05, 0.65),
            'xgb_score': random.uniform(0.65, 0.95) if user_type == 'human' else random.uniform(0.05, 0.45),
            'fingerprint_risk': random.uniform(0.1, 0.4) if user_type == 'human' else random.uniform(0.3, 0.8),
            'targets_hit': random.randint(3, 5),
            'reaction_latency': random.uniform(80, 350) if user_type == 'human' else random.uniform(5, 150),
            'browser': random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
            'platform': random.choice(['Windows', 'macOS', 'Linux']),
            'screen_resolution': random.choice(['1920x1080', '1366x768', '1440x900', '2560x1440'])
        }
        
        # Log the attempt
        attempt_id = db.log_captcha_attempt(
            captcha_type=captcha_type,
            user_type=user_type,
            success=success,
            completion_time=completion_time,
            attempts_used=attempts_used,
            failure_reason=failure_reason,
            metadata=metadata
        )
        
        attempt_ids.append((attempt_id, user_type, success, metadata))
        
        if (i + 1) % 25 == 0:
            print(f"   Added {i + 1}/150 CAPTCHA attempts...")
    
    print("⚔️  Adding attack logs...")
    
    # Generate attack logs for bot attempts
    attack_count = 0
    for attempt_id, user_type, success, metadata in attempt_ids:
        if user_type in ['bot', 'llm_attack', 'computer_vision'] and random.random() < 0.8:
            attack_type = random.choice(attack_types)
            
            # Match attack method to user type for realism
            if user_type == 'computer_vision':
                attack_method = random.choice(['opencv_detection', 'selenium_automation'])
            elif user_type == 'llm_attack':
                attack_method = random.choice(['claude_vision', 'selenium_automation'])
            else:  # bot
                attack_method = random.choice(['direct_clicks', 'linear_movement', 'selenium_automation'])
            
            execution_time = metadata.get('completion_time', random.uniform(2.0, 15.0))
            targets_clicked = metadata.get('targets_hit', random.randint(2, 6))
            
            # Error messages for failed attacks
            error_messages = [
                'Movement detection failed',
                'Fingerprint analysis blocked',
                'ML model rejected pattern', 
                'Session rate limited',
                'PoW verification failed',
                None  # Some succeed without errors
            ]
            
            error_message = None if success else random.choice(error_messages)
            
            db.log_attack(
                attack_type=attack_type,
                attack_method=attack_method,
                success=success,
                execution_time=execution_time,
                targets_clicked=targets_clicked,
                detection_method=f"{user_type}_detection",
                error_message=error_message,
                full_log=f"Attack attempt using {attack_method} - {'SUCCESS' if success else 'BLOCKED'}"
            )
            
            attack_count += 1
    
    print(f"   Added {attack_count} attack log entries...")
    
    print("🧠 Adding ML detection data...")
    
    # Add ML detection data for most attempts
    ml_detection_count = 0
    for attempt_id, user_type, success, metadata in attempt_ids:
        if random.random() < 0.85:  # 85% of attempts have ML detection
            is_bot = user_type in ['bot', 'llm_attack', 'computer_vision']
            
            # Generate realistic ML scores based on user type
            if is_bot:
                confidence = random.uniform(0.75, 0.98)      # High confidence bot detection
                speed_score = random.uniform(0.8, 1.0)      # Bots are fast/consistent
                linearity_score = random.uniform(0.7, 0.95) # Bots move more linearly
                timing_score = random.uniform(0.65, 0.9)    # Regular timing patterns
            else:  # human
                confidence = random.uniform(0.15, 0.45)     # Low bot confidence
                speed_score = random.uniform(0.2, 0.65)     # Humans vary speed
                linearity_score = random.uniform(0.1, 0.4)  # Natural curved movement
                timing_score = random.uniform(0.15, 0.5)    # Irregular human timing
            
            # Add some noise/edge cases
            if random.random() < 0.1:  # 10% edge cases
                confidence = random.uniform(0.45, 0.65)     # Uncertain cases
            
            db.log_ml_detection(
                attempt_id=attempt_id,
                is_bot=is_bot,
                confidence_score=confidence,
                speed_score=speed_score,
                linearity_score=linearity_score,
                timing_score=timing_score,
                prediction_model=random.choice(['RandomForest_v2.1', 'XGBoost_v1.3', 'Ensemble_v1.0'])
            )
            
            ml_detection_count += 1
    
    print(f"   Added {ml_detection_count} ML detection records...")
    
    print("🎯 Adding motor events...")
    
    # Add detailed motor events for some attempts
    motor_event_count = 0
    for attempt_id, user_type, success, metadata in attempt_ids[:50]:  # First 50 for performance
        if random.random() < 0.7:  # 70% have detailed events
            num_targets = metadata.get('targets_hit', random.randint(3, 5))
            
            for target_num in range(num_targets):
                # Realistic target coordinates
                x_coord = random.randint(120, 580)  # Canvas margins
                y_coord = random.randint(120, 380)
                
                # Timing progression
                time_offset = target_num * random.uniform(2.5, 8.0)
                
                db.log_motor_event(
                    attempt_id=attempt_id,
                    event_type='target_click',
                    target_id=target_num + 1,
                    x_coord=x_coord,
                    y_coord=y_coord,
                    time_offset=time_offset,
                    sequence_number=target_num + 1
                )
                
                motor_event_count += 1
    
    print(f"   Added {motor_event_count} motor event records...")
    
    # Generate some success stats aggregates
    print("📈 Generating success statistics...")
    
    # Calculate daily stats for last 7 days
    for days_back in range(7):
        date = (datetime.now() - timedelta(days=days_back)).date()
        
        for user_type in user_types:
            # Simulate daily activity patterns
            if days_back < 2:  # Recent days - more activity
                total_attempts = random.randint(8, 25)
            elif days_back < 5:  # Mid-week
                total_attempts = random.randint(5, 15)
            else:  # Older days
                total_attempts = random.randint(2, 10)
            
            successful_attempts = int(total_attempts * success_rates[user_type])
            success_rate = (successful_attempts / total_attempts) * 100 if total_attempts > 0 else 0
            avg_completion_time = random.uniform(8.0, 30.0)
            
            # Insert into success_stats table (if it exists)
            try:
                db.cursor.execute("""
                    INSERT OR REPLACE INTO success_stats 
                    (date, captcha_type, user_type, total_attempts, successful_attempts, success_rate, avg_completion_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (date, 'motor', user_type, total_attempts, successful_attempts, success_rate, avg_completion_time))
            except Exception as e:
                pass  # Table might not exist, skip
    
    db.conn.commit()
    db.close()
    
    print("\n✅ Mock data generation completed!")
    print(f"""
📊 Generated Data Summary:
   • 150 CAPTCHA attempts (various user types)
   • {attack_count} attack log entries  
   • {ml_detection_count} ML detection records
   • {motor_event_count} motor event details
   • 7 days of aggregated statistics
   
🌐 Dashboard should now show populated data at:
   http://localhost:5002
   
💡 Tip: Run this script multiple times to add more data!
""")

if __name__ == "__main__":
    generate_mock_data()
