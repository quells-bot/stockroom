# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
This repository contains a restaurant inventory management simulation. A `Simulation` engine runs a 60-day cycle; pluggable `Strategy` classes decide how much of each ingredient to order each day. The score is `final_budget - dissatisfaction`.

## Core Components
- `simulation.py`: The `Simulation` engine and `Strategy` ABC. Handles daily cycles: receiving deliveries, expiring inventory, generating customers, and processing orders. Also defines `DayState`, `SimulationResult`, and related dataclasses.
- `strategy.py`: Ordering strategy implementations. See `STRATEGY.md` when working here.
- `menu.py`: Defines `INGREDIENTS` (costs, shelf lives) and `MENU` items (recipes, prices).
- `runner.py`: Runs multiple simulations across all strategies and reports average scores.

## Running Simulations
```bash
python runner.py
```

## Development Guidelines

- Any file may be modified except where task-specific instructions say otherwise.
- `tests/*.py` are reserved for simulation correctness tests — do not add new test files there.
- When working on strategies specifically, follow `STRATEGY.md`.

## Strategy Interface

`Strategy` subclasses receive `menu` and `ingredients` at construction, plus any keyword arguments forwarded from `Simulation` / `run_simulations`. Implement:
- `__init__(self, menu, ingredients, **kwargs)`
- `initial_order(self, budget) -> dict[str, int]`
- `decide_orders(self, state: DayState) -> dict[str, int]`
