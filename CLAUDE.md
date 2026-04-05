# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
This repository contains a restaurant inventory management simulation. The goal is to implement an ordering `Strategy` that maximizes a score (calculated as `final_budget - dissatisfaction`) over a 60-day period.

## Core Components
- `simulation.py`: Contains the `Simulation` engine, which handles daily cycles (receiving deliveries, expiring inventory, generating customers, and processing orders).
- `strategy.py`: The primary place for development. You implement a class inheriting from `Strategy` to decide how much of each ingredient to order.
- `menu.py`: Defines the `INGREDIENT` list, their costs and shelf lives, and the `MENU` items with their recipes and prices.
- `runner.py`: A script to run multiple simulations of a given strategy to evaluate its performance and stability.

## Development Workflow

### Running Simulations
To evaluate a strategy, run the `runner.py` script. It executes a specified number of simulation runs and prints the average score and individual run details.
```bash
python runner.py
```

### Implementing a New Strategy

You **MUST NOT** modify any files other than `strategy.py`. You are allowed to read other files but **MUST NOT** modify them.

You **MUST NOT** hard-code prices, ingredients, or menu items in your strategy. These are subject to change and your strategy algorithm should be generic across any menu. You **MAY** hard-code things to take the day-of-week traffic variability and delivery lead time into account, as these are fixed (but subject to random variation). You **MAY** introduce mutable state into your strategy class.

1. Open `strategy.py`.
2. Create a new class that inherits from `Strategy` (or `NaiveStrategy` for a simpler starting point).
3. Implement `__init__`, `initial_order`, and `decide_orders`.
4. Update `DefaultStrategy` inherit from your new class.
5. Run `python runner.py` to test.

### Key Simulation Parameters
- **Duration**: 60 days.
- **Starting Budget**: 100,000.
- **Traffic**: Varies by day of the week (higher on weekends).
- **Delivery Lead Time**: 3 to 5 days.
- **Score**: `final_budget - dissatisfaction`.
- **Dissatisfaction**: Occurs when a customer's order cannot be fulfilled due to missing ingredients.

## Testing
Tests are located in the `tests/` directory. Use `pytest` to run them.
```bash
pytest
```
