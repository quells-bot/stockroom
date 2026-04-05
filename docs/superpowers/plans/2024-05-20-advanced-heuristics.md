# Advanced Heuristics Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a sophisticated ordering strategy that dynamically adjusts to demand patterns, delivery lead times, and ingredient shelf life to maximize the simulation score.

**Architecture:** The strategy will move beyond simple fixed-day buffers. It will use a "safety stock" approach that considers the probability of stockouts based on the variance in daily traffic, the known lead time (3-5 days), and the risk of expiration (shelf life). It will also factor in the day-of-week traffic patterns (higher on weekends) to preemptively increase orders before peak periods.

**Tech Stack:** Python, standard libraries.

---

### Task 1: Establish Baseline and Heuristic Design

**Files:**
- Create: `docs/superpowers/plans/2024-05-20-advanced-heuristics.md`
- Modify: `strategy.py`

- [ ] **Step 1: Create a scratchpad script to test demand forecasting logic**

```python
# test_forecast.py
from menu import MENU, INGREDIENT
from simulation import DayState

def test_forecast_logic():
    # Mock a DayState
    state = DayState(
        day=10,
        day_of_week="friday",
        budget=10000,
        inventory={"bun": 5, "beef": 5},
        pending_deliveries=[{"ingredient": "bun", "quantity": 10, "days_until_arrival": 2}],
        today_revenue=0,
        today_waste={},
        today_stockouts=[]
    )
    # Implement a simple check: if today is Friday, we need more for Saturday/Sunday
    print(f"Testing forecast for {state.day_of_week}")
    # TODO: Implement logic to calculate required qty for upcoming weekend
    # For now, just return a dummy value
    return 10

if __name__ == "__main__":
    print(f"Forecasted need: {test_forecast_logic()}")
```

- [ ] **Step 2: Run test script to verify environment**

Run: `python test_forecast.py`
Expected: `Testing forecast for friday` \n `Forecasted need: 10`

- [ ] **Step 3: Define the `AdvancedHeuristicStrategy` class structure in `strategy.py`**

```python
from simulation import Strategy, DayState
from menu import MenuItem, Ingredient

class AdvancedHeuristicStrategy(Strategy):
    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient]):
        self.menu = menu
        self.ingredients = ingredients
        # Pre-calculate daily demand weights
        self.demand_weights = {} 
        # Logic to estimate demand per ingredient...

    def initial_order(self, budget: int) -> dict[str, int]:
        # Logic for day 0 order
        return {}

    def decide_orders(self, state: DayState) -> dict[str, int]:
        # Logic for daily replenishment
        return {}
```

- [ ] **Step 4: Commit structure**

```bash
git add strategy.py
git commit -m "feat: add AdvancedHeuristicStrategy structure"
```

### Task 2: Implement Demand Forecasting & Buffer Logic

**Files:**
- Modify: `strategy.py`

- [ ] **Step 1: Implement `__init__` with demand estimation**

```python
    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient]):
        self.menu = menu
        self.ingredients = ingredients
        self._daily_base_demand: dict[str, float] = {}
        
        # Calculate average demand per ingredient based on menu prices/weights
        # Using the weights from Simulation._generate_customers (1/price)
        total_weight = sum(1.0 / item.price for item in menu)
        
        for name in ingredients:
            usage = 0.0
            for item in menu:
                if name in item.recipe:
                    # weight * quantity
                    usage += (1.0 / item.price) * item.recipe[name]
            # Scale usage to an estimated daily count (e.g., avg traffic is ~35)
            # Avg traffic approx: (sum of low + sum of high) / 7
            self._daily_base_demand[name] = usage * 35 
```

- [ ] **Step 2: Implement `decide_orders` with lead-time and weekend awareness**

```python
    def decide_orders(self, state: DayState) -> dict[int, int]:
        order: dict[str, int] = {}
        total_cost = 0
        
        # Traffic multiplier based on day of week
        # Weekend (Sat, Sun) has higher traffic (45-60) vs Mon (0)
        dow_multipliers = {
            "monday": 0.5, "tuesday": 1.0, "wednesday": 1.0, 
            "thursday": 1.2, "friday": 1.2, "saturday": 1.7, "sunday": 1.7
        }
        multiplier = dow_multipliers.get(state.day_of_week, 1.0)

        for name, base_demand in self._daily_base_demand.items():
            on_hand = state.inventory.get(name, 0)
            pending = sum(d["quantity"] for d in state.pending_deliveries if d["ingredient"] == name)
            
            # Target: cover next 5 days (max lead time) * multiplier + safety buffer
            # Safety buffer scales with shelf life (don't overbuy perishable)
            shelf_life = self.ingredients[name].shelf_life
            target_days = 5 
            
            target_qty = int(base_demand * multiplier * target_days)
            
            # Adjust target if shelf life is short to avoid waste
            if shelf_life < target_days:
                target_qty = int(base_demand * multiplier * shelf_life)

            need = target_qty - on_hand - pending
            
            if need > 0:
                cost = need * self.ingredients[name].cost
                if total_cost + cost <= state.budget:
                    order[name] = need
                    total_cost += cost
        return order
```

- [ ] **Step 3: Run `runner.py` to verify improvement over NaiveStrategy**

Run: `python runner.py`
Expected: Higher average score than `NaiveStrategy`.

- [ ] **Step 4: Commit final implementation**

```bash
git add strategy.py
git commit -m "feat: implement advanced heuristic strategy"
```