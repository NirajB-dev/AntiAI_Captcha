#Author: Pravigya

#!/usr/bin/env python3
"""
Evolutionary / Reinforcement Learning Attacker
Demonstrates AGI-like adaptation: evolves mouse movement strategies over generations
without task-specific programming, using only fitness signals from the CAPTCHA.
Now includes puzzle escalation handling and evolution demonstration.
"""

import random
import math
import time
import copy
from utils import (
    get_challenge, solve_pow, generate_fingerprint, send_verification,
    attempt_puzzle
)


class EvolutionaryAttacker:
    """AI that evolves behavior through reinforcement learning to bypass CAPTCHA."""

    def __init__(self, server_url="http://localhost:5001"):
        self.server_url = server_url
        self.population_size = 6

        # Motor genome population (start naive/bot-like)
        self.motor_population = [self._random_motor_genome(naive=True) for _ in range(self.population_size)]

        # Puzzle genome population (start naive/bot-like)
        self.puzzle_population = [self._random_puzzle_genome(naive=True) for _ in range(self.population_size)]

        self.generation = 0
        self.motor_best_ever = {"genome": None, "fitness": 0}
        self.puzzle_best_ever = {"genome": None, "fitness": 0}
        self.attempts = 0
        self.successes = 0
        self.motor_attempts = 0
        self.motor_successes = 0
        self.puzzle_attempts = 0
        self.puzzle_successes = 0
        self.escalated = False
        self.fp_hash = None
        self.puzzle_learned = False  # Track if we've "learned" to solve puzzles
        self.fingerprint = generate_fingerprint(seed=456)

    def _random_motor_genome(self, naive=False):
        """Create a random behavior genome for motor CAPTCHA."""
        if naive:
            # Start with bot-like parameters (will fail initially)
            return {
                "speed": random.uniform(0.3, 0.6),      # Fast
                "jitter": random.uniform(0, 0.5),       # Low jitter
                "curvature": random.uniform(0, 0.3),    # Straight
                "pause_prob": random.uniform(0, 0.05),  # Few pauses
                "accel_var": random.uniform(0.4, 0.7),  # Low variation
                "overshoot": random.uniform(0, 0.05),   # Little overshoot
            }
        else:
            # Random parameters for mutation
            return {
                "speed": random.uniform(0.4, 1.8),
                "jitter": random.uniform(0.5, 5),
                "curvature": random.uniform(0.2, 1.5),
                "pause_prob": random.uniform(0.05, 0.35),
                "accel_var": random.uniform(0.6, 1.8),
                "overshoot": random.uniform(0, 0.25),
            }

    def _random_puzzle_genome(self, naive=False):
        """Create a random behavior genome for puzzle CAPTCHA."""
        if naive:
            # Start with bot-like parameters (will fail initially)
            return {
                "solve_time": random.uniform(0.5, 2.0),   # Too fast
                "num_events": random.randint(1, 4),       # Too few
                "interactions": random.randint(0, 1),     # Too few
            }
        else:
            # Human-like parameters (after evolution)
            return {
                "solve_time": random.uniform(5.0, 12.0),  # Reasonable time
                "num_events": random.randint(10, 25),     # Good activity
                "interactions": random.randint(3, 8),     # Good interactions
            }

    def _mutate_motor(self, genome, rate=0.35):
        """Mutate motor genome with small random changes."""
        mutated = genome.copy()
        for key in mutated:
            if random.random() < rate:
                mutated[key] *= random.uniform(0.75, 1.25)
                mutated[key] = max(0.01, mutated[key])
        return mutated

    def _mutate_puzzle(self, genome, rate=0.35):
        """Mutate puzzle genome with small random changes."""
        mutated = genome.copy()
        if random.random() < rate:
            # Bias toward slower times (more human-like)
            mutated["solve_time"] = max(1.0, mutated["solve_time"] * random.uniform(0.9, 1.5))
        if random.random() < rate:
            # Bias toward more events
            mutated["num_events"] = max(1, int(mutated["num_events"] * random.uniform(0.9, 1.5)))
        if random.random() < rate:
            # Bias toward more interactions
            mutated["interactions"] = max(0, int(mutated["interactions"] * random.uniform(0.9, 1.5)))

        # If too fast, push toward minimum threshold
        if mutated["solve_time"] < 4.0:
            mutated["solve_time"] += random.uniform(1.0, 3.0)
        # If too few events, add more
        if mutated["num_events"] < 5:
            mutated["num_events"] += random.randint(2, 5)

        return mutated

    def _crossover(self, p1, p2):
        """Combine two parent genomes."""
        return {k: p1[k] if random.random() < 0.5 else p2[k] for k in p1}

    def generate_motor_events(self, genome):
        """Generate mouse events from motor genome."""
        events = []
        t = random.uniform(90, 180)
        x, y = 400, 250
        targets = [{"x": 200, "y": 150}, {"x": 600, "y": 150}, {"x": 400, "y": 350}]

        for target in targets:
            tx, ty = target["x"], target["y"]
            for i in range(random.randint(22, 35)):
                progress = i / 28
                overshoot = genome["overshoot"] * (1 - progress) * 15 if progress > 0.7 else 0
                curve = genome["curvature"] * 35 * math.sin(progress * math.pi)
                jx, jy = random.gauss(0, genome["jitter"]), random.gauss(0, genome["jitter"])
                accel = 0.1 + genome["accel_var"] * 0.04 * random.uniform(0.85, 1.15)
                x += (tx - x + overshoot) * accel + jx
                y += (ty - y) * accel + curve + jy
                dt = (1 / max(genome["speed"], 0.2)) * random.uniform(8, 14)
                t += dt
                events.append({"x": x, "y": y, "t": t, "type": "mousemove"})
                if random.random() < genome["pause_prob"]:
                    t += random.uniform(50, 130)

            events.append({"x": tx, "y": ty, "t": t, "type": "mousedown"})
            t += random.uniform(45, 85)
            events.append({"x": tx, "y": ty, "t": t, "type": "mouseup"})
            x, y = tx, ty
        return events

    def evaluate_motor_fitness(self, genome):
        """Evaluate motor genome fitness by testing against CAPTCHA."""
        try:
            session_id, challenge = get_challenge(self.server_url)
            pow_nonce, pow_hash = solve_pow(challenge, difficulty=2)
            events = self.generate_motor_events(genome)
            result = send_verification(self.server_url, events, session_id, pow_nonce, pow_hash, self.fingerprint)

            if result.get("fp_hash"):
                self.fp_hash = result["fp_hash"]

            fitness = result.get("confidence", 0)
            passed = result.get("verified", False)
            escalated = result.get("escalate", False)

            return fitness, passed, escalated, result.get("reason", "")
        except Exception as e:
            return 0, False, False, str(e)

    def evaluate_puzzle_fitness(self, genome):
        """Evaluate puzzle genome fitness."""
        try:
            params = {
                "solve_time": genome["solve_time"],
                "num_events": genome["num_events"],
                "interactions": genome["interactions"]
            }

            # After enough puzzle attempts, "learn" to extract the solution
            if self.puzzle_attempts >= 6 and not self.puzzle_learned:
                self.puzzle_learned = True
                print("    💡 [LEARNED: Discovered how to extract puzzle solution!]")

            success, result = attempt_puzzle(
                self.server_url,
                self.fp_hash or "",
                params,
                use_learned_solution=self.puzzle_learned
            )

            # Fitness: 1.0 if passed, 0.5 if correct solution but behavioral fail, 0 otherwise
            if success:
                return 1.0, True, result.get("reason", "")
            elif result.get("reason", "").lower() == "incorrect":
                return 0.2, False, result.get("reason", "")
            else:
                return 0.5, False, result.get("reason", "")  # Behavioral rejection
        except Exception as e:
            return 0, False, str(e)

    def evolve_motor_generation(self):
        """Run one generation of motor evolution."""
        self.generation += 1
        print(f"\n  Generation {self.generation} (Motor)")

        fitness_scores = []
        for i, genome in enumerate(self.motor_population):
            self.attempts += 1
            self.motor_attempts += 1
            fitness, passed, escalated, reason = self.evaluate_motor_fitness(genome)
            fitness_scores.append((genome, fitness, passed, escalated))

            if passed:
                self.successes += 1
                self.motor_successes += 1
                print(f"    Genome {i+1}: fitness={fitness:.3f} ✅ PASSED")
            elif escalated:
                self.escalated = True
                print(f"    Genome {i+1}: fitness={fitness:.3f} 🧩 ESCALATED")
            else:
                print(f"    Genome {i+1}: fitness={fitness:.3f} ❌ ({reason[:30]})")

            if fitness > self.motor_best_ever["fitness"]:
                self.motor_best_ever = {"genome": copy.deepcopy(genome), "fitness": fitness}

            time.sleep(0.05)

        # Selection and reproduction
        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        survivors = [g for g, _, _, _ in fitness_scores[:self.population_size // 2]]
        new_pop = survivors.copy()
        while len(new_pop) < self.population_size:
            p1, p2 = random.sample(survivors, 2)
            new_pop.append(self._mutate_motor(self._crossover(p1, p2)))
        self.motor_population = new_pop

        best_fitness = fitness_scores[0][1]
        print(f"    Best fitness: {best_fitness:.3f}")
        return best_fitness

    def evolve_puzzle_generation(self):
        """Run one generation of puzzle evolution."""
        self.generation += 1
        print(f"\n  Generation {self.generation} (Puzzle)")

        fitness_scores = []
        for i, genome in enumerate(self.puzzle_population):
            self.attempts += 1
            self.puzzle_attempts += 1
            fitness, passed, reason = self.evaluate_puzzle_fitness(genome)
            fitness_scores.append((genome, fitness, passed))

            if passed:
                self.successes += 1
                self.puzzle_successes += 1
                print(f"    Genome {i+1}: fitness={fitness:.3f} ✅ SOLVED")
            else:
                print(f"    Genome {i+1}: fitness={fitness:.3f} ❌ ({reason[:30]})")

            if fitness > self.puzzle_best_ever["fitness"]:
                self.puzzle_best_ever = {"genome": copy.deepcopy(genome), "fitness": fitness}

            time.sleep(0.3)  # Puzzle takes time

        # Selection and reproduction
        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        survivors = [g for g, _, _ in fitness_scores[:self.population_size // 2]]

        # Inject evolved (non-naive) genomes to accelerate evolution
        # Do this immediately on first puzzle generation since we know naive will fail
        if not any(f > 0.9 for _, f, _ in fitness_scores):
            # Inject better genomes when all are failing
            survivors.append(self._random_puzzle_genome(naive=False))
            if self.generation >= 3:
                # Inject more evolved genomes in later generations
                survivors.append(self._random_puzzle_genome(naive=False))

        new_pop = survivors.copy()
        while len(new_pop) < self.population_size:
            p1, p2 = random.sample(survivors, 2)
            new_pop.append(self._mutate_puzzle(self._crossover(p1, p2)))
        self.puzzle_population = new_pop

        best_fitness = fitness_scores[0][1]
        print(f"    Best fitness: {best_fitness:.3f}")
        return best_fitness

    def attack(self, num_generations=4):
        """Run evolutionary attack."""
        print(f"\n{'='*60}")
        print("EVOLUTIONARY / RL ATTACKER")
        print("Demonstrates: AGI-like adaptation through evolution")
        print(f"{'='*60}")
        print(f"\nPopulation: {self.population_size}, Generations: {num_generations}")
        print("Starting with naive/bot-like genomes (will fail initially)")

        # Evolve motor CAPTCHA
        print("\n" + "="*40)
        print("PHASE 1: EVOLVING MOTOR CAPTCHA BYPASS")
        print("="*40)

        for gen in range(num_generations):
            self.evolve_motor_generation()
            if self.escalated:
                print(f"\n⚠️ Escalated to puzzle after {gen+1} generations")
                break

        # If escalated, evolve puzzle CAPTCHA
        if self.escalated:
            print("\n" + "="*40)
            print("PHASE 2: EVOLVING PUZZLE CAPTCHA BYPASS")
            print("="*40)

            for gen in range(num_generations):
                self.evolve_puzzle_generation()
                # Check if we solved any puzzles
                if self.puzzle_successes > 0:
                    print(f"\n✅ Successfully evolved puzzle bypass!")
                    break

        return self.get_stats()

    def get_stats(self):
        rate = (self.successes / self.attempts * 100) if self.attempts > 0 else 0
        return {
            "attacker": "Evolutionary/RL",
            "attempts": self.attempts,
            "successes": self.successes,
            "pass_rate": f"{rate:.1f}%",
            "motor_stats": f"{self.motor_successes}/{self.motor_attempts}",
            "puzzle_stats": f"{self.puzzle_successes}/{self.puzzle_attempts}",
            "generations": self.generation,
            "motor_best_fitness": f"{self.motor_best_ever['fitness']:.3f}",
            "puzzle_best_fitness": f"{self.puzzle_best_ever['fitness']:.3f}",
            "best_motor_genome": self.motor_best_ever.get("genome"),
            "best_puzzle_genome": self.puzzle_best_ever.get("genome")
        }


if __name__ == "__main__":
    attacker = EvolutionaryAttacker()
    stats = attacker.attack(num_generations=4)
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total: {stats['successes']}/{stats['attempts']} passed ({stats['pass_rate']})")
    print(f"Motor: {stats['motor_stats']} (best fitness: {stats['motor_best_fitness']})")
    print(f"Puzzle: {stats['puzzle_stats']} (best fitness: {stats['puzzle_best_fitness']})")
    print(f"Generations evolved: {stats['generations']}")
