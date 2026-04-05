from typing import TypedDict

from menu import MENU, INGREDIENTS
from simulation import Simulation, Strategy


class RunResult(TypedDict):
    score: int
    final_budget: int
    dissatisfaction: int


class SimulationSummary(TypedDict):
    average_score: float
    runs: list[RunResult]


def run_simulations(strategy_class: type[Strategy], n_runs: int = 10) -> SimulationSummary:
    runs = []
    for _ in range(n_runs):
        sim = Simulation(MENU, INGREDIENTS, strategy_class)
        result = sim.run()
        runs.append({
            "score": result.score,
            "final_budget": result.final_budget,
            "dissatisfaction": result.dissatisfaction,
        })
    average_score = sum(r["score"] for r in runs) / len(runs) if runs else 0.0
    return {"average_score": average_score, "runs": runs}


if __name__ == "__main__":
    from strategy import NaiveStrategy

    result = run_simulations(NaiveStrategy, n_runs=100)
    print(f"Average score: {result['average_score']:.0f}")
    print()
    for i, run in enumerate(result["runs"], 1):
        print(f"  Run {i:2d}: score={run['score']:6d}  budget={run['final_budget']:6d}  dissatisfaction={run['dissatisfaction']:5d}")
