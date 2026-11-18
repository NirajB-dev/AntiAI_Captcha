#Author: Niraj


#!/usr/bin/env python3
"""
SQLite Database Module for CAPTCHA Analytics
Stores attempt logs, success rates, and attack patterns
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

class CaptchaDatabase:
    """
    Manages SQLite database for CAPTCHA attempt tracking and analytics.
    """
    
    def __init__(self, db_path="captcha_analytics.db"):
        """
        Initialize database connection and create tables if they don't exist.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.cursor = self.conn.cursor()
        self._create_tables()
        print(f"[DB] Connected to database: {db_path}")
    
    def _create_tables(self):
        """
        Create all necessary database tables if they don't exist.
        """
        # Table 1: CAPTCHA Attempts
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS captcha_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                captcha_type TEXT NOT NULL,
                user_type TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                completion_time REAL,
                attempts_used INTEGER,
                failure_reason TEXT,
                metadata TEXT
            )
        """)
        
        # Table 2: Attack Logs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS attack_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                attack_type TEXT NOT NULL,
                attack_method TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                execution_time REAL,
                targets_clicked INTEGER,
                detection_method TEXT,
                error_message TEXT,
                full_log TEXT
            )
        """)
        
        # Table 3: Motor CAPTCHA Events
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS motor_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                target_id INTEGER,
                x_coord INTEGER,
                y_coord INTEGER,
                time_offset REAL,
                sequence_number INTEGER,
                FOREIGN KEY (attempt_id) REFERENCES captcha_attempts(id)
            )
        """)
        
        # Table 4: ML Detection Results
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_detection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_bot BOOLEAN NOT NULL,
                confidence_score REAL,
                speed_score REAL,
                linearity_score REAL,
                timing_score REAL,
                prediction_model TEXT,
                FOREIGN KEY (attempt_id) REFERENCES captcha_attempts(id)
            )
        """)
        
        # Table 5: Success Rate Statistics (aggregated)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS success_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE DEFAULT CURRENT_DATE,
                captcha_type TEXT NOT NULL,
                user_type TEXT NOT NULL,
                total_attempts INTEGER DEFAULT 0,
                successful_attempts INTEGER DEFAULT 0,
                success_rate REAL,
                avg_completion_time REAL,
                UNIQUE(date, captcha_type, user_type)
            )
        """)
        
        # Table 6: Puzzle CAPTCHA Events (tile swaps)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS puzzle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                tile_from INTEGER,
                tile_to INTEGER,
                move_number INTEGER,
                time_offset REAL,
                FOREIGN KEY (attempt_id) REFERENCES captcha_attempts(id)
            )
        """)
        
        self.conn.commit()
        print("[DB] All tables created/verified")
    
    def log_captcha_attempt(self, captcha_type, user_type, success, 
                           completion_time=None, attempts_used=1, 
                           failure_reason=None, metadata=None):
        """
        Log a CAPTCHA attempt to the database.
        
        Args:
            captcha_type: Type of CAPTCHA (e.g., 'motor', 'puzzle')
            user_type: User type (e.g., 'human', 'bot', 'llm_attack')
            success: Boolean indicating if attempt was successful
            completion_time: Time taken to complete (seconds)
            attempts_used: Number of attempts used
            failure_reason: Reason for failure if applicable
            metadata: Additional metadata as dictionary
            
        Returns:
            int: ID of the inserted record
        """
        metadata_json = json.dumps(metadata) if metadata else None
        
        self.cursor.execute("""
            INSERT INTO captcha_attempts 
            (captcha_type, user_type, success, completion_time, 
             attempts_used, failure_reason, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (captcha_type, user_type, success, completion_time, 
              attempts_used, failure_reason, metadata_json))
        
        self.conn.commit()
        attempt_id = self.cursor.lastrowid
        
        # Update aggregated stats
        self._update_success_stats(captcha_type, user_type)
        
        return attempt_id
    
    def log_attack(self, attack_type, attack_method, success, 
                   execution_time=None, targets_clicked=0,
                   detection_method=None, error_message=None, full_log=None):
        """
        Log an attack attempt to the database.
        
        Args:
            attack_type: Type of attack (e.g., 'simple_bot', 'llm_gemini')
            attack_method: Method used (e.g., 'straight_lines', 'bezier_curves')
            success: Boolean indicating if attack was successful
            execution_time: Time taken to execute attack
            targets_clicked: Number of targets clicked
            detection_method: How targets were detected
            error_message: Error message if failed
            full_log: Complete log output as text
            
        Returns:
            int: ID of the inserted record
        """
        self.cursor.execute("""
            INSERT INTO attack_logs 
            (attack_type, attack_method, success, execution_time,
             targets_clicked, detection_method, error_message, full_log)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (attack_type, attack_method, success, execution_time,
              targets_clicked, detection_method, error_message, full_log))
        
        self.conn.commit()
        return self.cursor.lastrowid
    
    def log_motor_event(self, attempt_id, event_type, target_id=None,
                       x_coord=None, y_coord=None, time_offset=None,
                       sequence_number=None):
        """
        Log a motor CAPTCHA event (click, movement, etc.).
        
        Args:
            attempt_id: ID of the parent CAPTCHA attempt
            event_type: Type of event ('click', 'move', 'miss', 'hit')
            target_id: Target number that was interacted with
            x_coord: X coordinate of event
            y_coord: Y coordinate of event
            time_offset: Time offset from attempt start (seconds)
            sequence_number: Order in sequence
        """
        self.cursor.execute("""
            INSERT INTO motor_events
            (attempt_id, event_type, target_id, x_coord, y_coord, 
             time_offset, sequence_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (attempt_id, event_type, target_id, x_coord, y_coord,
              time_offset, sequence_number))
        
        self.conn.commit()
    
    def log_puzzle_event(self, attempt_id, event_type, tile_from=None,
                        tile_to=None, move_number=None, time_offset=None):
        """
        Log a puzzle CAPTCHA event (tile swap, move, etc.).
        
        Args:
            attempt_id: ID of the parent CAPTCHA attempt
            event_type: Type of event ('swap', 'move', 'solve', 'fail')
            tile_from: Tile position moving from
            tile_to: Tile position moving to
            move_number: Order in sequence of moves
            time_offset: Time offset from attempt start (seconds)
        """
        self.cursor.execute("""
            INSERT INTO puzzle_events
            (attempt_id, event_type, tile_from, tile_to, 
             move_number, time_offset)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (attempt_id, event_type, tile_from, tile_to,
              move_number, time_offset))
        
        self.conn.commit()
    
    def log_ml_detection(self, attempt_id, is_bot, confidence_score=None,
                        speed_score=None, linearity_score=None,
                        timing_score=None, prediction_model=None):
        """
        Log ML detection results for an attempt.
        
        Args:
            attempt_id: ID of the CAPTCHA attempt
            is_bot: Boolean indicating if classified as bot
            confidence_score: Overall confidence (0-1)
            speed_score: Speed analysis score
            linearity_score: Movement linearity score
            timing_score: Timing pattern score
            prediction_model: Name of ML model used
        """
        self.cursor.execute("""
            INSERT INTO ml_detection
            (attempt_id, is_bot, confidence_score, speed_score,
             linearity_score, timing_score, prediction_model)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (attempt_id, is_bot, confidence_score, speed_score,
              linearity_score, timing_score, prediction_model))
        
        self.conn.commit()
    
    def _update_success_stats(self, captcha_type, user_type):
        """
        Update aggregated success statistics for today.
        
        Args:
            captcha_type: Type of CAPTCHA
            user_type: Type of user
        """
        # Calculate stats from today's attempts
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(CASE WHEN success = 1 THEN completion_time END) as avg_time
            FROM captcha_attempts
            WHERE DATE(timestamp) = DATE('now')
            AND captcha_type = ?
            AND user_type = ?
        """, (captcha_type, user_type))
        
        row = self.cursor.fetchone()
        total = row['total']
        successful = row['successful'] or 0
        avg_time = row['avg_time']
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # Insert or update stats
        self.cursor.execute("""
            INSERT INTO success_stats 
            (date, captcha_type, user_type, total_attempts, 
             successful_attempts, success_rate, avg_completion_time)
            VALUES (DATE('now'), ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, captcha_type, user_type) 
            DO UPDATE SET
                total_attempts = ?,
                successful_attempts = ?,
                success_rate = ?,
                avg_completion_time = ?
        """, (captcha_type, user_type, total, successful, success_rate, avg_time,
              total, successful, success_rate, avg_time))
        
        self.conn.commit()
    
    def get_success_rate(self, captcha_type=None, user_type=None, days=7):
        """
        Get success rate statistics for a time period.
        
        Args:
            captcha_type: Filter by CAPTCHA type (None for all)
            user_type: Filter by user type (None for all)
            days: Number of days to look back
            
        Returns:
            dict: Success rate statistics
        """
        query = """
            SELECT 
                captcha_type,
                user_type,
                SUM(total_attempts) as total,
                SUM(successful_attempts) as successful,
                AVG(success_rate) as avg_success_rate,
                AVG(avg_completion_time) as avg_time
            FROM success_stats
            WHERE date >= DATE('now', '-' || ? || ' days')
        """
        
        params = [days]
        conditions = []
        
        if captcha_type:
            conditions.append("captcha_type = ?")
            params.append(captcha_type)
        
        if user_type:
            conditions.append("user_type = ?")
            params.append(user_type)
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " GROUP BY captcha_type, user_type"
        
        self.cursor.execute(query, params)
        results = self.cursor.fetchall()
        
        return [dict(row) for row in results]
    
    def get_attack_summary(self, days=7):
        """
        Get summary of attack attempts.
        
        Args:
            days: Number of days to look back
            
        Returns:
            dict: Attack statistics by type
        """
        self.cursor.execute("""
            SELECT 
                attack_type,
                attack_method,
                COUNT(*) as total_attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(execution_time) as avg_execution_time,
                AVG(targets_clicked) as avg_targets_clicked
            FROM attack_logs
            WHERE timestamp >= DATETIME('now', '-' || ? || ' days')
            GROUP BY attack_type, attack_method
            ORDER BY total_attempts DESC
        """, (days,))
        
        results = self.cursor.fetchall()
        return [dict(row) for row in results]
    
    def get_recent_attempts(self, limit=10, captcha_type=None):
        """
        Get recent CAPTCHA attempts.
        
        Args:
            limit: Maximum number of records to return
            captcha_type: Filter by CAPTCHA type (None for all)
            
        Returns:
            list: Recent attempt records
        """
        query = "SELECT * FROM captcha_attempts"
        params = []
        
        if captcha_type:
            query += " WHERE captcha_type = ?"
            params.append(captcha_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        self.cursor.execute(query, params)
        results = self.cursor.fetchall()
        
        return [dict(row) for row in results]
    
    def export_to_csv(self, table_name, output_file):
        """
        Export a table to CSV file.
        
        Args:
            table_name: Name of table to export
            output_file: Output CSV file path
        """
        import csv
        
        self.cursor.execute(f"SELECT * FROM {table_name}")
        rows = self.cursor.fetchall()
        
        if not rows:
            print(f"[DB] No data to export from {table_name}")
            return
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([description[0] for description in self.cursor.description])
            # Write data
            writer.writerows(rows)
        
        print(f"[DB] Exported {len(rows)} rows to {output_file}")
    
    def print_statistics(self):
        """
        Print summary statistics to console.
        """
        print("\n" + "="*70)
        print("  CAPTCHA DATABASE STATISTICS")
        print("="*70)
        
        # Overall counts
        self.cursor.execute("SELECT COUNT(*) as count FROM captcha_attempts")
        total_attempts = self.cursor.fetchone()['count']
        
        self.cursor.execute("SELECT COUNT(*) as count FROM attack_logs")
        total_attacks = self.cursor.fetchone()['count']
        
        print(f"\nTotal CAPTCHA Attempts: {total_attempts}")
        print(f"Total Attack Logs: {total_attacks}")
        
        # Success rates by type
        print("\n--- Success Rates (Last 7 Days) ---")
        stats = self.get_success_rate(days=7)
        for stat in stats:
            print(f"{stat['captcha_type']} - {stat['user_type']}: "
                  f"{stat['avg_success_rate']:.1f}% "
                  f"({stat['successful']}/{stat['total']} attempts)")
        
        # Attack summary
        print("\n--- Attack Summary (Last 7 Days) ---")
        attacks = self.get_attack_summary(days=7)
        for attack in attacks:
            success_rate = (attack['successful'] / attack['total_attempts'] * 100 
                          if attack['total_attempts'] > 0 else 0)
            print(f"{attack['attack_type']} ({attack['attack_method']}): "
                  f"{success_rate:.1f}% success "
                  f"({attack['successful']}/{attack['total_attempts']} attempts)")
        
        print("="*70 + "\n")
    
    def close(self):
        """
        Close database connection.
        """
        self.conn.close()
        print("[DB] Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """
    Demo usage of the database module.
    """
    print("""
================================================================================
                    CAPTCHA DATABASE MODULE DEMO
================================================================================
This module provides SQLite database functionality for tracking:
  - CAPTCHA attempts and success rates
  - Attack logs and patterns
  - Motor CAPTCHA events
  - ML detection results
  - Aggregated statistics
================================================================================
""")
    
    # Initialize database
    db = CaptchaDatabase("captcha_analytics.db")
    
    # Example: Log some sample data
    print("\n[DEMO] Logging sample CAPTCHA attempts...")
    
    # Human attempt - successful
    attempt_id1 = db.log_captcha_attempt(
        captcha_type='motor',
        user_type='human',
        success=True,
        completion_time=12.5,
        attempts_used=1
    )
    print(f"  Logged human attempt (ID: {attempt_id1})")
    
    # Bot attempt - failed
    attempt_id2 = db.log_captcha_attempt(
        captcha_type='motor',
        user_type='bot',
        success=False,
        completion_time=3.2,
        attempts_used=3,
        failure_reason='ML detection - straight line movement'
    )
    print(f"  Logged bot attempt (ID: {attempt_id2})")
    
    # LLM attack - successful
    attempt_id3 = db.log_captcha_attempt(
        captcha_type='motor',
        user_type='llm_attack',
        success=True,
        completion_time=8.7,
        attempts_used=1,
        metadata={'model': 'gemini-2.5-flash', 'detection': 'DOM extraction'}
    )
    print(f"  Logged LLM attack (ID: {attempt_id3})")
    
    # Log attack details
    print("\n[DEMO] Logging attack details...")
    attack_id = db.log_attack(
        attack_type='llm_gemini',
        attack_method='bezier_curves',
        success=True,
        execution_time=8.7,
        targets_clicked=5,
        detection_method='DOM extraction'
    )
    print(f"  Logged attack (ID: {attack_id})")
    
    # Log ML detection
    print("\n[DEMO] Logging ML detection result...")
    db.log_ml_detection(
        attempt_id=attempt_id2,
        is_bot=True,
        confidence_score=0.95,
        speed_score=0.98,
        linearity_score=0.92,
        timing_score=0.88,
        prediction_model='XGBoost'
    )
    print("  ML detection logged")
    
    # Display statistics
    db.print_statistics()
    
    # Get recent attempts
    print("\n[DEMO] Recent attempts:")
    recent = db.get_recent_attempts(limit=5)
    for attempt in recent:
        status = "✓" if attempt['success'] else "✗"
        print(f"  {status} {attempt['captcha_type']} - {attempt['user_type']} "
              f"({attempt['completion_time']:.1f}s)")
    
    # Close database
    db.close()
    
    print("\n[DEMO] Demo complete. Database saved to: captcha_analytics.db")
    print("You can view the database using SQLite browser or command line tools.")


if __name__ == '__main__':
    main()
