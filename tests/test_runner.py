from runner import run_simulations
from strategy import NaiveStrategy


def test_run_simulations_returns_average():
    result = run_simulations(NaiveStrategy, n_runs=3)
    assert "average_score" in result
    assert "runs" in result
    assert len(result["runs"]) == 3
    assert isinstance(result["average_score"], float)


def test_run_simulations_default_10_runs():
    result = run_simulations(NaiveStrategy)
    assert len(result["runs"]) == 10


def test_each_run_has_score_breakdown():
    result = run_simulations(NaiveStrategy, n_runs=1)
    run = result["runs"][0]
    assert "score" in run
    assert "final_budget" in run
    assert "dissatisfaction" in run
