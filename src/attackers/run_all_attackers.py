#Author: Pravigya

#!/usr/bin/env python3
"""
Unified Attacker Runner
Runs all 3 AI attackers and displays comparative results.
Demonstrates: Sycophancy, Prompting, and AGI concepts.
"""

import sys
import time
from datetime import datetime

from sycophantic_attacker import SycophancyAttacker
from prompt_probing_attacker import PromptProbingAttacker
from evolutionary_attacker import EvolutionaryAttacker


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          ANTI-AI CAPTCHA - AI ATTACKER DEMONSTRATION             ║
║                                                                  ║
║  Demonstrates AI concepts from the rubric:                       ║
║  1. SYCOPHANCY  - Blindly adapts to please the system            ║
║  2. PROMPTING   - Probes model to learn decision boundaries      ║
║  3. AGI         - Evolves strategies without specific training   ║
║                                                                  ║
║  Each attacker:                                                  ║
║  - Starts with naive/bot-like behavior (will fail initially)    ║
║  - Learns from feedback and adapts                               ║
║  - Handles escalation to puzzle CAPTCHA                          ║
║  - Shows evolution over time                                     ║
╚══════════════════════════════════════════════════════════════════╝
""")


def run_all_attackers(server_url="http://localhost:5001"):
    """Run all attackers and collect results."""
    print_banner()
    print(f"Target server: {server_url}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = []

    # 1. Sycophantic Attacker
    print("\n" + "─" * 60)
    print("ATTACKER 1: Sycophantic Learner")
    print("─" * 60)
    try:
        stats1 = SycophancyAttacker(server_url).attack(max_attempts=12)
        results.append(stats1)
    except Exception as e:
        print(f"Error: {e}")
        results.append({"attacker": "Sycophantic Learner", "error": str(e)})

    time.sleep(1)

    # 2. Prompt Probing Attacker
    print("\n" + "─" * 60)
    print("ATTACKER 2: Prompt Probing")
    print("─" * 60)
    try:
        stats2 = PromptProbingAttacker(server_url).attack(exploit_attempts=8)
        results.append(stats2)
    except Exception as e:
        print(f"Error: {e}")
        results.append({"attacker": "Prompt Probing", "error": str(e)})

    time.sleep(1)

    # 3. Evolutionary Attacker
    print("\n" + "─" * 60)
    print("ATTACKER 3: Evolutionary/RL")
    print("─" * 60)
    try:
        stats3 = EvolutionaryAttacker(server_url).attack(num_generations=3)
        results.append(stats3)
    except Exception as e:
        print(f"Error: {e}")
        results.append({"attacker": "Evolutionary/RL", "error": str(e)})

    print_summary(results)
    return results


def print_summary(results):
    """Print comparative summary."""
    print("\n")
    print("╔" + "═" * 70 + "╗")
    print("║" + " ATTACK RESULTS SUMMARY ".center(70) + "║")
    print("╠" + "═" * 70 + "╣")

    for r in results:
        if "error" in r:
            print(f"║  {r['attacker']:<25} ERROR: {r['error'][:35]:<35} ║")
        else:
            motor = r.get('motor_stats', 'N/A')
            puzzle = r.get('puzzle_stats', 'N/A')
            print(f"║  {r['attacker']:<25} Total: {r['successes']:>2}/{r['attempts']:<3} ({r['pass_rate']:>5})          ║")
            print(f"║  {'':<25} Motor: {motor:<10} Puzzle: {puzzle:<10}      ║")

    print("╠" + "═" * 70 + "╣")
    print("║  KEY OBSERVATIONS:                                                   ║")
    print("║  • All attackers started with naive/bot-like behavior                ║")
    print("║  • Each attacker adapted/evolved based on system feedback            ║")
    print("║  • Escalation to puzzle triggered after motor CAPTCHA failures       ║")
    print("║  • System evolved thresholds in response to attack patterns          ║")
    print("╠" + "═" * 70 + "╣")
    print("║  AI CONCEPTS DEMONSTRATED:                                           ║")
    print("║  SYCOPHANCY: Blind adaptation to 'please' the system                 ║")
    print("║  PROMPTING:  Probing to learn and exploit model biases               ║")
    print("║  AGI:        Evolution without task-specific programming             ║")
    print("╚" + "═" * 70 + "╝")
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    server = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5001"
    run_all_attackers(server)
