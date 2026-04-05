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


def run_simulations(strategy_class: type[Strategy], n_runs: int = 10, **strategy_kwargs) -> SimulationSummary:
    runs = []
    for _ in range(n_runs):
        sim = Simulation(MENU, INGREDIENTS, strategy_class, **strategy_kwargs)
        result = sim.run()
        runs.append({
            "score": result.score,
            "final_budget": result.final_budget,
            "dissatisfaction": result.dissatisfaction,
        })
    average_score = sum(r["score"] for r in runs) / len(runs) if runs else 0.0
    return {"average_score": average_score, "runs": runs}


if __name__ == "__main__":
    from strategy import NaiveStrategy, AdvancedHeuristicStrategy, ForwardLookingHeuristicStrategy

    strategies = [NaiveStrategy, AdvancedHeuristicStrategy, ForwardLookingHeuristicStrategy]
    for strategy_class in strategies:
        result = run_simulations(strategy_class, n_runs=1000)
        print(f"{strategy_class.__name__}: avg={result['average_score']:.0f}")
