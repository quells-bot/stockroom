---
name: advanced-heuristic-strategy-design
description: Design for an improved ordering strategy using dynamic demand forecasting and perishability-aware buffers.
type: project
---

# Design: Advanced Heuristic Strategy

## Overview
This design document outlines an improved ordering strategy for the restaurant inventory management simulation. The goal is to outperform the `NaiveStrategy` by accounting for traffic fluctuations, ingredient perishability, and delivery lead times.

## Objectives
- Maximize the simulation score (`final_budget - dissatisfaction`).
- Minimize `today_waste` by adjusting buffers for short-lived ingredients.
- Minimize `dissatisfaction` by ensuring sufficient stock for high-traffic periods.

## Architecture

### 1. Dynamic Demand Forecasting
Instead of assuming a constant daily demand, the strategy will:
- **Base Demand Calculation**: In `__init__`, calculate a baseline daily usage for each ingredient. This is done by weighting each `MenuItem`'s recipe by its probability of being ordered (using the inverse of its price, as defined in `simulation.py`).
- **Traffic-Aware Windowing**: When calculating the required order in `decide_orders`, the strategy will forecast demand for the entire delivery window (up to 5 days ahead). It will use the `TRAFFIC` patterns (higher on weekends) to adjust the expected number of customers for each day in that window.

### 2. Perishability-Aware Safety Buffer
The strategy will replace the fixed 3-day buffer with a dynamic one:
- **Buffer Calculation**: The buffer (number of extra days of stock to hold) will be inversely proportional to the ingredient's `shelf_life`.
- **Logic**:
    - **Short Shelf Life**: A tighter buffer (e.g., 1-2 days) to prevent `today_waste` from over-ordering.
    - **Long Shelf Life**: A larger buffer (e.g., 5-7 days) to prioritize preventing `dissatisfaction` at a lower risk of waste.

### 3. Inventory Gap Analysis
The ordering logic will follow this formula for each ingredient:
`Target_Inventory = Expected_Demand(current_day to current_day + 5) + Safety_Buffer`
`Order_Quantity = Max(0, Target_Inventory - On_Hand - Pending_Deliveries)`

### 4. Budget-Constrained Ordering
To respect the `budget` constraint:
- Calculate the cost of the ideal `Order_Quantity` for all ingredients.
- If `Total_Cost > Budget`, prioritize ingredients based on a "Criticality Score".
- **Criticality Score**: A combination of (a) the ingredient's usage in high-margin menu items and (b) how close the current `on_hand` is to zero.

## Implementation Details

### Class Structure
- `class AdvancedHeuristicStrategy(Strategy)`: The new implementation.
- `DefaultStrategy` will be updated to inherit from `AdvancedHeuristicStrategy`.

### Constraints & Rules
- **No Hard-coding**: Must use `menu.py` and `simulation.py` constants for costs, weights, and traffic.
- **Generic Logic**: Must work regardless of changes to the `MENU` or `INGREDIENTS`.

## Testing Plan
- Run `python runner.py` to compare the average score of `AdvancedHeuristicStrategy` against `NaiveStrategy`.
- Verify that `today_waste` does not significantly increase compared to the naive approach.
- Verify that `today_stockouts` decreases.