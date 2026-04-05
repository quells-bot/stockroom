# STRATEGY.md

This file provides guidance for implementing new ordering strategies.

## Overview
The goal is to implement an ordering `Strategy` that maximizes a score (calculated as `final_budget - dissatisfaction`) over a 60-day period.

## Implementing a New Strategy

You **MUST NOT** modify any files other than `strategy.py`. You are allowed to read other files but **MUST NOT** modify them.

You **MUST NOT** hard-code prices, ingredients, or menu items in your strategy. These are subject to change and your strategy algorithm should be generic across any menu. You **MAY** hard-code things to take the day-of-week traffic variability and delivery lead time into account, as these are fixed (but subject to random variation). You **MAY** introduce mutable state into your strategy class.

1. Open `strategy.py`.
2. Create a new class that inherits from `Strategy` (or `NaiveStrategy` for a simpler starting point).
3. Implement `__init__`, `initial_order`, and `decide_orders`.
4. Run `python runner.py` to test.

### Key Simulation Parameters
- **Duration**: 60 days.
- **Starting Budget**: 100,000.
- **Traffic**: Varies by day of the week (higher on weekends).
- **Delivery Lead Time**: 3 to 5 days.
- **Score**: `final_budget - dissatisfaction`.
- **Dissatisfaction**: Occurs when a customer's order cannot be fulfilled due to missing ingredients.

## Testing

You **MUST NOT** write any new pytest tests in `tests/*.py`. These are reserved for testing the simulation.

If you need to test something for your new strategy, write some throwaway script to test that portion.

Your key metric for gauging the effectiveness of your strategy is the output from `runner.py`.
