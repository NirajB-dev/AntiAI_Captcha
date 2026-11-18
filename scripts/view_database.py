#Author: Niraj


#!/usr/bin/env python3
"""
Database Viewer and Analytics Tool
View and analyze CAPTCHA attempt data
"""

from captcha_database import CaptchaDatabase
import sys

def show_menu():
    """Display menu options."""
    print("\n" + "="*70)
    print("  CAPTCHA DATABASE VIEWER")
    print("="*70)
    print("1. View recent attempts")
    print("2. View success rates")
    print("3. View attack summary")
    print("4. View all statistics")
    print("5. Export to CSV")
    print("6. View specific attempt details")
    print("7. Clear old data (>30 days)")
    print("8. Exit")
    print("="*70)

def view_recent_attempts(db):
    """Display recent attempts."""
    limit = input("How many recent attempts to show? (default 10): ").strip()
    limit = int(limit) if limit else 10
    
    print("\n--- Recent Attempts ---")
    attempts = db.get_recent_attempts(limit=limit)
    
    if not attempts:
        print("No attempts found.")
        return
    
    for attempt in attempts:
        status = "✓ SUCCESS" if attempt['success'] else "✗ FAILED"
        print(f"\nID: {attempt['id']} | {attempt['timestamp']}")
        print(f"  Type: {attempt['captcha_type']} | User: {attempt['user_type']}")
        print(f"  Status: {status}")
        print(f"  Time: {attempt['completion_time']:.2f}s" if attempt['completion_time'] else "  Time: N/A")
        print(f"  Attempts: {attempt['attempts_used']}")
        if attempt['failure_reason']:
            print(f"  Reason: {attempt['failure_reason']}")
        if attempt['metadata']:
            print(f"  Metadata: {attempt['metadata']}")

def view_success_rates(db):
    """Display success rate statistics."""
    days = input("Number of days to analyze (default 7): ").strip()
    days = int(days) if days else 7
    
    print(f"\n--- Success Rates (Last {days} Days) ---")
    stats = db.get_success_rate(days=days)
    
    if not stats:
        print("No data found for this period.")
        return
    
    for stat in stats:
        print(f"\n{stat['captcha_type']} - {stat['user_type']}:")
        print(f"  Success Rate: {stat['avg_success_rate']:.1f}%")
        print(f"  Total Attempts: {stat['total']}")
        print(f"  Successful: {stat['successful']}")
        print(f"  Avg Completion Time: {stat['avg_time']:.2f}s" if stat['avg_time'] else "  Avg Time: N/A")

def view_attack_summary(db):
    """Display attack statistics."""
    days = input("Number of days to analyze (default 7): ").strip()
    days = int(days) if days else 7
    
    print(f"\n--- Attack Summary (Last {days} Days) ---")
    attacks = db.get_attack_summary(days=days)
    
    if not attacks:
        print("No attack data found for this period.")
        return
    
    for attack in attacks:
        success_rate = (attack['successful'] / attack['total_attempts'] * 100 
                       if attack['total_attempts'] > 0 else 0)
        print(f"\n{attack['attack_type']} - {attack['attack_method']}:")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Total Attempts: {attack['total_attempts']}")
        print(f"  Successful: {attack['successful']}")
        print(f"  Avg Execution Time: {attack['avg_execution_time']:.2f}s" if attack['avg_execution_time'] else "  Avg Time: N/A")
        print(f"  Avg Targets Clicked: {attack['avg_targets_clicked']:.1f}" if attack['avg_targets_clicked'] else "  Avg Targets: N/A")

def view_all_statistics(db):
    """Display all statistics."""
    db.print_statistics()

def export_data(db):
    """Export table to CSV."""
    print("\n--- Export to CSV ---")
    print("Available tables:")
    print("  1. captcha_attempts")
    print("  2. attack_logs")
    print("  3. motor_events")
    print("  4. ml_detection")
    print("  5. success_stats")
    
    choice = input("Enter table number: ").strip()
    
    table_map = {
        '1': 'captcha_attempts',
        '2': 'attack_logs',
        '3': 'motor_events',
        '4': 'ml_detection',
        '5': 'success_stats'
    }
    
    table_name = table_map.get(choice)
    if not table_name:
        print("Invalid choice.")
        return
    
    output_file = input(f"Output filename (default: {table_name}.csv): ").strip()
    output_file = output_file if output_file else f"{table_name}.csv"
    
    db.export_to_csv(table_name, output_file)

def view_attempt_details(db):
    """View detailed information about a specific attempt."""
    attempt_id = input("Enter attempt ID: ").strip()
    
    if not attempt_id:
        print("No ID provided.")
        return
    
    # Get attempt
    db.cursor.execute("SELECT * FROM captcha_attempts WHERE id = ?", (attempt_id,))
    attempt = db.cursor.fetchone()
    
    if not attempt:
        print(f"No attempt found with ID {attempt_id}")
        return
    
    print(f"\n--- Attempt Details (ID: {attempt_id}) ---")
    print(f"Timestamp: {attempt['timestamp']}")
    print(f"CAPTCHA Type: {attempt['captcha_type']}")
    print(f"User Type: {attempt['user_type']}")
    print(f"Success: {'YES' if attempt['success'] else 'NO'}")
    print(f"Completion Time: {attempt['completion_time']:.2f}s" if attempt['completion_time'] else "N/A")
    print(f"Attempts Used: {attempt['attempts_used']}")
    if attempt['failure_reason']:
        print(f"Failure Reason: {attempt['failure_reason']}")
    if attempt['metadata']:
        print(f"Metadata: {attempt['metadata']}")
    
    # Get related motor events
    db.cursor.execute("""
        SELECT * FROM motor_events 
        WHERE attempt_id = ? 
        ORDER BY sequence_number
    """, (attempt_id,))
    events = db.cursor.fetchall()
    
    if events:
        print(f"\nMotor Events ({len(events)} events):")
        for event in events:
            print(f"  [{event['sequence_number']}] {event['event_type']} - "
                  f"Target {event['target_id']} at ({event['x_coord']}, {event['y_coord']}) "
                  f"@ {event['time_offset']:.2f}s")
    
    # Get ML detection
    db.cursor.execute("""
        SELECT * FROM ml_detection WHERE attempt_id = ?
    """, (attempt_id,))
    ml = db.cursor.fetchone()
    
    if ml:
        print(f"\nML Detection:")
        print(f"  Is Bot: {'YES' if ml['is_bot'] else 'NO'}")
        print(f"  Confidence: {ml['confidence_score']:.2%}" if ml['confidence_score'] else "  Confidence: N/A")
        print(f"  Speed Score: {ml['speed_score']:.2f}" if ml['speed_score'] else "")
        print(f"  Linearity Score: {ml['linearity_score']:.2f}" if ml['linearity_score'] else "")
        print(f"  Timing Score: {ml['timing_score']:.2f}" if ml['timing_score'] else "")
        print(f"  Model: {ml['prediction_model']}" if ml['prediction_model'] else "")

def clear_old_data(db):
    """Clear data older than 30 days."""
    confirm = input("Delete all data older than 30 days? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    # Delete old records
    db.cursor.execute("""
        DELETE FROM captcha_attempts 
        WHERE timestamp < DATETIME('now', '-30 days')
    """)
    attempts_deleted = db.cursor.rowcount
    
    db.cursor.execute("""
        DELETE FROM attack_logs 
        WHERE timestamp < DATETIME('now', '-30 days')
    """)
    attacks_deleted = db.cursor.rowcount
    
    db.cursor.execute("""
        DELETE FROM success_stats 
        WHERE date < DATE('now', '-30 days')
    """)
    stats_deleted = db.cursor.rowcount
    
    db.conn.commit()
    
    print(f"\nDeleted:")
    print(f"  {attempts_deleted} old attempts")
    print(f"  {attacks_deleted} old attacks")
    print(f"  {stats_deleted} old statistics")

def main():
    """Main viewer loop."""
    db_path = "captcha_analytics.db"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    print(f"\nConnecting to database: {db_path}")
    
    try:
        db = CaptchaDatabase(db_path)
    except Exception as e:
        print(f"Error opening database: {e}")
        return
    
    while True:
        show_menu()
        choice = input("\nEnter your choice (1-8): ").strip()
        
        try:
            if choice == '1':
                view_recent_attempts(db)
            elif choice == '2':
                view_success_rates(db)
            elif choice == '3':
                view_attack_summary(db)
            elif choice == '4':
                view_all_statistics(db)
            elif choice == '5':
                export_data(db)
            elif choice == '6':
                view_attempt_details(db)
            elif choice == '7':
                clear_old_data(db)
            elif choice == '8':
                print("\nClosing database...")
                break
            else:
                print("Invalid choice. Please enter 1-8.")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
    
    db.close()
    print("Goodbye!")

if __name__ == '__main__':
    main()
