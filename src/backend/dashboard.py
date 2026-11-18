#Author: Niraj

#!/usr/bin/env python3
"""
CAPTCHA Analytics Dashboard
Web-based dashboard for visualizing CAPTCHA attempts, success rates, and attack patterns
"""

from flask import Flask, render_template, jsonify
from captcha_database import CaptchaDatabase
import json
import os
from datetime import datetime, timedelta

# Get the project root directory (2 levels up from this script)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
template_dir = os.path.join(project_root, 'templates')
static_dir = os.path.join(project_root, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/overview')
def get_overview():
    """Get overview statistics."""
    db = CaptchaDatabase()
    
    # Total counts
    db.cursor.execute("SELECT COUNT(*) as count FROM captcha_attempts")
    total_attempts = db.cursor.fetchone()['count']
    
    db.cursor.execute("SELECT COUNT(*) as count FROM captcha_attempts WHERE success = 1")
    total_successful = db.cursor.fetchone()['count']
    
    db.cursor.execute("SELECT COUNT(*) as count FROM attack_logs")
    total_attacks = db.cursor.fetchone()['count']
    
    db.cursor.execute("SELECT COUNT(*) as count FROM attack_logs WHERE success = 1")
    successful_attacks = db.cursor.fetchone()['count']
    
    # Puzzle stats
    db.cursor.execute("""
        SELECT COUNT(*) as count 
        FROM captcha_attempts 
        WHERE captcha_type = 'puzzle'
    """)
    puzzle_attempts = db.cursor.fetchone()['count']
    
    db.cursor.execute("""
        SELECT COUNT(*) as count 
        FROM captcha_attempts 
        WHERE captcha_type = 'puzzle' AND success = 1
    """)
    puzzle_solved = db.cursor.fetchone()['count']
    
    # Today's stats
    db.cursor.execute("""
        SELECT COUNT(*) as count 
        FROM captcha_attempts 
        WHERE DATE(timestamp) = DATE('now')
    """)
    today_attempts = db.cursor.fetchone()['count']
    
    # Calculate rates
    overall_success_rate = (total_successful / total_attempts * 100) if total_attempts > 0 else 0
    attack_success_rate = (successful_attacks / total_attacks * 100) if total_attacks > 0 else 0
    puzzle_success_rate = (puzzle_solved / puzzle_attempts * 100) if puzzle_attempts > 0 else 0
    
    db.close()
    
    return jsonify({
        'total_attempts': total_attempts,
        'total_successful': total_successful,
        'overall_success_rate': round(overall_success_rate, 1),
        'total_attacks': total_attacks,
        'successful_attacks': successful_attacks,
        'attack_success_rate': round(attack_success_rate, 1),
        'today_attempts': today_attempts,
        'puzzle_attempts': puzzle_attempts,
        'puzzle_solved': puzzle_solved,
        'puzzle_success_rate': round(puzzle_success_rate, 1)
    })

@app.route('/api/success_rates')
def get_success_rates():
    """Get success rates by user type."""
    db = CaptchaDatabase()
    
    db.cursor.execute("""
        SELECT 
            user_type,
            COUNT(*) as total,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
            ROUND(AVG(CASE WHEN success = 1 THEN 100.0 ELSE 0 END), 1) as success_rate
        FROM captcha_attempts
        GROUP BY user_type
    """)
    
    results = db.cursor.fetchall()
    db.close()
    
    data = {
        'labels': [row['user_type'] for row in results],
        'success_rates': [row['success_rate'] for row in results],
        'total_attempts': [row['total'] for row in results],
        'successful_attempts': [row['successful'] for row in results]
    }
    
    return jsonify(data)

@app.route('/api/attack_summary')
def get_attack_summary():
    """Get attack statistics by type."""
    db = CaptchaDatabase()
    
    db.cursor.execute("""
        SELECT 
            attack_type,
            attack_method,
            COUNT(*) as total,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
            ROUND(AVG(execution_time), 2) as avg_time,
            ROUND(AVG(targets_clicked), 1) as avg_targets
        FROM attack_logs
        GROUP BY attack_type, attack_method
        ORDER BY total DESC
    """)
    
    results = db.cursor.fetchall()
    db.close()
    
    attacks = []
    for row in results:
        success_rate = (row['successful'] / row['total'] * 100) if row['total'] > 0 else 0
        attacks.append({
            'type': row['attack_type'],
            'method': row['attack_method'],
            'total': row['total'],
            'successful': row['successful'],
            'success_rate': round(success_rate, 1),
            'avg_time': row['avg_time'],
            'avg_targets': row['avg_targets']
        })
    
    return jsonify(attacks)

@app.route('/api/timeline')
def get_timeline():
    """Get attempt timeline for last 7 days."""
    db = CaptchaDatabase()
    
    db.cursor.execute("""
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as total,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
        FROM captcha_attempts
        WHERE timestamp >= DATETIME('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date
    """)
    
    results = db.cursor.fetchall()
    db.close()
    
    data = {
        'dates': [row['date'] for row in results],
        'total': [row['total'] for row in results],
        'successful': [row['successful'] for row in results]
    }
    
    return jsonify(data)

@app.route('/api/recent_attempts')
def get_recent_attempts():
    """Get recent attempts."""
    limit = 20
    db = CaptchaDatabase()
    
    attempts = db.get_recent_attempts(limit=limit)
    db.close()
    
    formatted = []
    for attempt in attempts:
        formatted.append({
            'id': attempt['id'],
            'timestamp': attempt['timestamp'],
            'type': attempt['captcha_type'],
            'user_type': attempt['user_type'],
            'success': attempt['success'],
            'time': attempt['completion_time'],
            'attempts': attempt['attempts_used'],
            'reason': attempt['failure_reason']
        })
    
    return jsonify(formatted)

@app.route('/api/ml_detection_stats')
def get_ml_detection_stats():
    """Get ML detection statistics."""
    db = CaptchaDatabase()
    
    db.cursor.execute("""
        SELECT 
            is_bot,
            COUNT(*) as count,
            ROUND(AVG(confidence_score), 3) as avg_confidence,
            ROUND(AVG(speed_score), 3) as avg_speed,
            ROUND(AVG(linearity_score), 3) as avg_linearity,
            ROUND(AVG(timing_score), 3) as avg_timing
        FROM ml_detection
        GROUP BY is_bot
    """)
    
    results = db.cursor.fetchall()
    db.close()
    
    stats = {}
    for row in results:
        key = 'bot' if row['is_bot'] else 'human'
        stats[key] = {
            'count': row['count'],
            'avg_confidence': row['avg_confidence'],
            'avg_speed': row['avg_speed'],
            'avg_linearity': row['avg_linearity'],
            'avg_timing': row['avg_timing']
        }
    
    return jsonify(stats)

@app.route('/api/hourly_distribution')
def get_hourly_distribution():
    """Get attempt distribution by hour of day."""
    db = CaptchaDatabase()
    
    db.cursor.execute("""
        SELECT 
            CAST(strftime('%H', timestamp) AS INTEGER) as hour,
            COUNT(*) as count,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
        FROM captcha_attempts
        WHERE timestamp >= DATETIME('now', '-7 days')
        GROUP BY hour
        ORDER BY hour
    """)
    
    results = db.cursor.fetchall()
    db.close()
    
    data = {
        'hours': [row['hour'] for row in results],
        'counts': [row['count'] for row in results],
        'successful': [row['successful'] for row in results]
    }
    
    return jsonify(data)

@app.route('/api/refresh')
def refresh_stats():
    """Refresh all statistics (for real-time updates)."""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/captcha_breakdown')
def get_captcha_breakdown():
    """Get breakdown by CAPTCHA type (motor vs puzzle)."""
    db = CaptchaDatabase()
    
    db.cursor.execute("""
        SELECT 
            captcha_type,
            COUNT(*) as total,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
            ROUND(AVG(CASE WHEN success = 1 THEN 100.0 ELSE 0 END), 1) as success_rate,
            ROUND(AVG(completion_time), 2) as avg_time
        FROM captcha_attempts
        WHERE completion_time IS NOT NULL
        GROUP BY captcha_type
    """)
    
    results = db.cursor.fetchall()
    db.close()
    
    data = []
    for row in results:
        data.append({
            'type': row['captcha_type'],
            'total': row['total'],
            'successful': row['successful'],
            'success_rate': row['success_rate'],
            'avg_time': row['avg_time']
        })
    
    return jsonify(data)

if __name__ == '__main__':
    print("""
================================================================================
                    CAPTCHA ANALYTICS DASHBOARD
================================================================================
Starting web server...

Dashboard will be available at: http://localhost:5002

Features:
  - Real-time statistics overview
  - Success rate charts by user type
  - Attack pattern analysis
  - Timeline visualization
  - Recent attempts log
  - ML detection insights
  - Hourly activity distribution

Press Ctrl+C to stop the server.
================================================================================
""")
    
    app.run(host='0.0.0.0', port=5002, debug=True)
