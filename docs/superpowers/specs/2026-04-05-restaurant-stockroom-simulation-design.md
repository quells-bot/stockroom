# Restaurant Stockroom Simulation — Design Spec

## Overview

A Python simulation of a restaurant stockroom designed as a playground for an AI agent to test ordering strategies. The agent modifies a single file (`strategy.py`) which defines a strategy class, instantiates the simulation harness, runs it, and receives a score.

## Architecture

Four modules following a layered approach:

- **`menu.py`** — Static data: menu items, ingredients, recipes, costs, shelf lives
- **`simulation.py`** — Day loop, order processing, delivery system, inventory management
- **`strategy.py`** — Strategy protocol (ABC) and the agent's implementation. This is the only file the agent modifies.
- **`runner.py`** — Entry point. Imports the strategy, runs 10 simulations, averages scores, prints results.

## Data Model

### Ingredient

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Identifier |
| `cost` | `int` | Per-unit purchase price |
| `shelf_life` | `int` | Days before expiry (from delivery) |

### MenuItem

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Display name |
| `price` | `int` | Customer-facing price |
| `recipe` | `dict[str, int]` | Ingredient name -> quantity consumed per order |

### Inventory (internal)

Tracked per ingredient as a sorted list of expiry days, one entry per unit. Example: 3 tomatoes expiring day 5 and 2 expiring day 8 = `[5, 5, 5, 8, 8]`.

- **Usage**: pop from front (FIFO — oldest used first)
- **Expiry**: filter out entries where `expiry <= current_day`

### PendingDelivery (internal)

| Field | Type | Description |
|-------|------|-------------|
| `ingredient` | `str` | What was ordered |
| `quantity` | `int` | How many units |
| `ordered_on` | `int` | Day number when ordered |
| `arrives_on` | `int` | `ordered_on + randint(3, 5)` |

The strategy sees pending deliveries without `arrives_on` — just ingredient, quantity, and days since ordered.

## Menu

Six items, nine ingredients. Every ingredient appears in at least two dishes.

### Menu Items

| Item | Price | Recipe |
|------|-------|--------|
| Burger | $12 | 1 bun, 1 beef, 1 lettuce, 1 tomato |
| Cheeseburger | $14 | 1 bun, 1 beef, 1 lettuce, 1 tomato, 1 cheese |
| Grilled Chicken Sandwich | $13 | 1 bun, 1 chicken, 1 lettuce, 1 tomato |
| Cheese Chicken Sandwich | $15 | 1 bun, 1 chicken, 1 lettuce, 1 tomato, 1 cheese |
| Caesar Salad | $10 | 1 lettuce, 1 chicken, 1 parmesan, 1 croutons |
| Pasta Bolognese | $15 | 1 pasta, 1 beef, 1 tomato, 1 parmesan |

### Ingredients

| Ingredient | Cost | Shelf Life |
|------------|------|------------|
| Bun | $1 | 3 days |
| Beef | $3 | 4 days |
| Chicken | $3 | 3 days |
| Lettuce | $1 | 3 days |
| Tomato | $1 | 5 days |
| Cheese | $2 | 7 days |
| Parmesan | $2 | 10 days |
| Pasta | $1 | 30 days |
| Croutons | $1 | 14 days |

### Order Probability

Menu item selection is weighted inversely proportional to price (`weight = 1/price`, normalized). Approximate probabilities:

| Item | Price | ~Probability |
|------|-------|-------------|
| Caesar Salad | $10 | 19.5% |
| Burger | $12 | 16.2% |
| Grilled Chicken Sandwich | $13 | 15.0% |
| Cheeseburger | $14 | 13.9% |
| Cheese Chicken Sandwich | $15 | 13.0% |
| Pasta Bolognese | $15 | 13.0% |

## Simulation Rules

### Parameters

- **Duration**: 60 days
- **Starting budget**: $1000
- **Runs per score**: 10 (averaged)

### Day Loop

Each day executes these steps in order:

1. **Receive deliveries** — Pending deliveries where `arrives_on == today` add units to the ingredient's expiry list. Each unit gets expiry day `today + shelf_life`.
2. **Expire inventory** — Filter out entries where `expiry <= today`. Count removed units as waste.
3. **If Monday, skip to step 6** — Restaurant is closed. No customers.
4. **Generate customers** — Random uniform count based on day of week:
   - Tue-Wed: 20-30 orders
   - Thu-Fri: 30-45 orders
   - Sat-Sun: 45-60 orders
   - Each customer selects a menu item using inverse-price weighting.
5. **Fill orders** — For each order:
   - If all ingredients available: consume them (pop from front of each ingredient's list), add menu item price to day's revenue.
   - If any ingredient missing: increment dissatisfaction counter by half the menu item price. Order is not filled.
6. **Call `strategy.decide_orders(state)`** — Strategy returns `dict[str, int]` (ingredient name -> quantity to order). If total cost exceeds remaining budget, the entire order is silently dropped. Otherwise, deduct cost from budget and create pending deliveries with random arrival days (`today + randint(3, 5)`).

### Scoring

```
score = final_budget - dissatisfaction_penalty
```

- `final_budget` is the remaining cash after 60 days (starting budget minus ingredient costs plus revenue)
- `dissatisfaction_penalty` is the accumulated half-price penalties from stockouts
- The penalty affects the score but NOT the day-to-day budget
- Final reported score is the average across 10 runs

## Strategy Interface

```python
from abc import ABC, abstractmethod

class Strategy(ABC):
    def __init__(self, menu: list[MenuItem], ingredients: list[Ingredient]):
        """Called once with static game data."""

    @abstractmethod
    def initial_order(self, budget: int) -> dict[str, int]:
        """Return initial ingredient order. Delivered before day 1.
        Silently dropped if total cost exceeds budget."""

    @abstractmethod
    def decide_orders(self, state: DayState) -> dict[str, int]:
        """Called at end of each day. Return ingredient orders."""
```

### DayState

| Field | Type | Description |
|-------|------|-------------|
| `day` | `int` | Current day (1-60) |
| `day_of_week` | `str` | e.g., "monday", "tuesday" |
| `budget` | `int` | Remaining cash |
| `inventory` | `dict[str, int]` | Ingredient -> unexpired unit count |
| `pending_deliveries` | `list[PendingDelivery]` | Each has: ingredient, quantity, days_until_arrival |
| `today_revenue` | `int` | Revenue earned today |
| `today_waste` | `dict[str, int]` | Ingredient -> units expired today |
| `today_stockouts` | `list[StockoutEvent]` | Each has: menu item name, price |
| `history` | `list[DayState]` | All previous days' states |

### PendingDelivery (strategy-visible)

| Field | Type | Description |
|-------|------|-------------|
| `ingredient` | `str` | What was ordered |
| `quantity` | `int` | How many units |
| `days_until_arrival` | `int` | Estimated days until delivery arrives |

### StockoutEvent

| Field | Type | Description |
|-------|------|-------------|
| `menu_item` | `str` | Name of the menu item that couldn't be filled |
| `price` | `int` | Price of that menu item |

## File Structure

```
auto/
  menu.py          # Ingredient, MenuItem definitions and menu data
  simulation.py    # Simulation class with day loop
  strategy.py      # Strategy ABC + agent's implementation
  runner.py        # Entry point: run 10 sims, average, print
```
