# Restaurant Stockroom Simulation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python simulation harness where an AI agent can test restaurant ingredient ordering strategies and receive a composite score.

**Architecture:** Four modules — `menu.py` (data types and static menu), `simulation.py` (day loop engine), `strategy.py` (ABC + sample implementation), `runner.py` (multi-run scorer). The strategy class is initialized with static data and called each day with dynamic state.

**Tech Stack:** Python 3.12+, dataclasses, stdlib only (random, abc). pytest for testing.

**Spec:** `docs/superpowers/specs/2026-04-05-restaurant-stockroom-simulation-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `menu.py` | `Ingredient`, `MenuItem` dataclasses; `INGREDIENTS` and `MENU` constants |
| `simulation.py` | `DayState`, `PendingDelivery`, `StockoutEvent` dataclasses; `Simulation` class with day loop |
| `strategy.py` | `Strategy` ABC; `NaiveStrategy` sample implementation |
| `runner.py` | `run(strategy_class, n_runs) -> float`; `__main__` entry point |
| `tests/test_menu.py` | Tests for menu data integrity |
| `tests/test_simulation.py` | Tests for simulation day loop mechanics |
| `tests/test_runner.py` | Tests for multi-run scoring |

---

### Task 1: Menu Data Types and Constants

**Files:**
- Create: `menu.py`
- Create: `tests/test_menu.py`

- [ ] **Step 1: Write failing tests for menu data**

Create `tests/test_menu.py`:

```python
from menu import Ingredient, MenuItem, INGREDIENTS, MENU


def test_ingredient_fields():
    bun = INGREDIENTS["bun"]
    assert bun.name == "bun"
    assert bun.cost == 1
    assert bun.shelf_life == 3


def test_all_ingredients_exist():
    expected = {"bun", "beef", "chicken", "lettuce", "tomato", "cheese", "parmesan", "pasta", "croutons"}
    assert set(INGREDIENTS.keys()) == expected


def test_menu_item_fields():
    burger = next(m for m in MENU if m.name == "Burger")
    assert burger.price == 12
    assert burger.recipe == {"bun": 1, "beef": 1, "lettuce": 1, "tomato": 1}


def test_all_menu_items_exist():
    names = {m.name for m in MENU}
    expected = {"Burger", "Cheeseburger", "Grilled Chicken Sandwich", "Cheese Chicken Sandwich", "Caesar Salad", "Pasta Bolognese"}
    assert names == expected


def test_all_recipe_ingredients_are_valid():
    for item in MENU:
        for ingredient_name in item.recipe:
            assert ingredient_name in INGREDIENTS, f"{item.name} uses unknown ingredient {ingredient_name}"


def test_every_ingredient_used_in_at_least_two_dishes():
    usage_count: dict[str, int] = {name: 0 for name in INGREDIENTS}
    for item in MENU:
        for ingredient_name in item.recipe:
            usage_count[ingredient_name] += 1
    for name, count in usage_count.items():
        assert count >= 2, f"{name} only used in {count} dish(es)"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_menu.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'menu'`

- [ ] **Step 3: Implement menu.py**

Create `menu.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Ingredient:
    name: str
    cost: int
    shelf_life: int


@dataclass(frozen=True)
class MenuItem:
    name: str
    price: int
    recipe: dict[str, int]


INGREDIENTS: dict[str, Ingredient] = {
    "bun": Ingredient("bun", cost=1, shelf_life=3),
    "beef": Ingredient("beef", cost=3, shelf_life=4),
    "chicken": Ingredient("chicken", cost=3, shelf_life=3),
    "lettuce": Ingredient("lettuce", cost=1, shelf_life=3),
    "tomato": Ingredient("tomato", cost=1, shelf_life=5),
    "cheese": Ingredient("cheese", cost=2, shelf_life=7),
    "parmesan": Ingredient("parmesan", cost=2, shelf_life=10),
    "pasta": Ingredient("pasta", cost=1, shelf_life=30),
    "croutons": Ingredient("croutons", cost=1, shelf_life=14),
}

MENU: list[MenuItem] = [
    MenuItem("Burger", price=12, recipe={"bun": 1, "beef": 1, "lettuce": 1, "tomato": 1}),
    MenuItem("Cheeseburger", price=14, recipe={"bun": 1, "beef": 1, "lettuce": 1, "tomato": 1, "cheese": 1}),
    MenuItem("Grilled Chicken Sandwich", price=13, recipe={"bun": 1, "chicken": 1, "lettuce": 1, "tomato": 1}),
    MenuItem("Cheese Chicken Sandwich", price=15, recipe={"bun": 1, "chicken": 1, "lettuce": 1, "tomato": 1, "cheese": 1}),
    MenuItem("Caesar Salad", price=10, recipe={"lettuce": 1, "chicken": 1, "parmesan": 1, "croutons": 1}),
    MenuItem("Pasta Bolognese", price=15, recipe={"pasta": 1, "beef": 1, "tomato": 1, "parmesan": 1}),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_menu.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add menu.py tests/test_menu.py
git commit -m "feat: add menu data types and restaurant menu constants"
```

---

### Task 2: Simulation Data Types and Core Mechanics

**Files:**
- Create: `simulation.py`
- Create: `tests/test_simulation.py`

This task builds the data types (`DayState`, `PendingDelivery`, `StockoutEvent`, `Strategy` ABC) and the core simulation mechanics: delivery receiving, inventory expiry, and order filling. The day loop itself comes in Task 3.

- [ ] **Step 1: Write failing tests for data types and inventory mechanics**

Create `tests/test_simulation.py`:

```python
import random
from simulation import (
    DayState,
    PendingDelivery,
    StockoutEvent,
    Strategy,
    Simulation,
)
from menu import INGREDIENTS, MENU


class DoNothingStrategy(Strategy):
    def __init__(self, menu, ingredients):
        self.menu = menu
        self.ingredients = ingredients

    def initial_order(self, budget):
        return {}

    def decide_orders(self, state):
        return {}


def make_sim(strategy_class=DoNothingStrategy):
    return Simulation(MENU, INGREDIENTS, strategy_class)


def test_pending_delivery_fields():
    pd = PendingDelivery(ingredient="beef", quantity=5, ordered_on=1, arrives_on=4)
    assert pd.ingredient == "beef"
    assert pd.quantity == 5
    assert pd.ordered_on == 1
    assert pd.arrives_on == 4


def test_stockout_event_fields():
    se = StockoutEvent(menu_item="Burger", price=12)
    assert se.menu_item == "Burger"
    assert se.price == 12


def test_receive_deliveries():
    sim = make_sim()
    sim._pending_deliveries = [
        PendingDelivery("beef", 3, ordered_on=1, arrives_on=4),
        PendingDelivery("bun", 2, ordered_on=2, arrives_on=5),
    ]
    sim._current_day = 4
    sim._receive_deliveries()
    # beef should have 3 units with expiry = 4 + 4 = 8
    assert sim._inventory["beef"] == [8, 8, 8]
    # bun not yet arrived
    assert sim._inventory["bun"] == []
    # beef delivery removed from pending, bun remains
    assert len(sim._pending_deliveries) == 1
    assert sim._pending_deliveries[0].ingredient == "bun"


def test_expire_inventory():
    sim = make_sim()
    sim._inventory["tomato"] = [3, 5, 5, 7]
    sim._current_day = 5
    waste = sim._expire_inventory()
    # days 3 and 5 expire (expiry <= current_day)
    assert sim._inventory["tomato"] == [7]
    assert waste == {"tomato": 3}


def test_expire_inventory_nothing_expired():
    sim = make_sim()
    sim._inventory["pasta"] = [30, 35, 40]
    sim._current_day = 5
    waste = sim._expire_inventory()
    assert sim._inventory["pasta"] == [30, 35, 40]
    assert waste == {}


def test_fill_order_success():
    sim = make_sim()
    sim._inventory["bun"] = [10, 10]
    sim._inventory["beef"] = [10, 10]
    sim._inventory["lettuce"] = [10, 10]
    sim._inventory["tomato"] = [10, 10]
    burger = next(m for m in MENU if m.name == "Burger")
    filled = sim._fill_order(burger)
    assert filled is True
    assert sim._inventory["bun"] == [10]
    assert sim._inventory["beef"] == [10]
    assert sim._inventory["lettuce"] == [10]
    assert sim._inventory["tomato"] == [10]


def test_fill_order_stockout():
    sim = make_sim()
    sim._inventory["bun"] = [10]
    sim._inventory["beef"] = []  # out of beef
    sim._inventory["lettuce"] = [10]
    sim._inventory["tomato"] = [10]
    burger = next(m for m in MENU if m.name == "Burger")
    filled = sim._fill_order(burger)
    assert filled is False
    # inventory unchanged on stockout
    assert sim._inventory["bun"] == [10]
    assert sim._inventory["lettuce"] == [10]
    assert sim._inventory["tomato"] == [10]


def test_place_order_within_budget():
    sim = make_sim()
    sim._budget = 100
    sim._current_day = 1
    random.seed(42)
    sim._place_order({"beef": 3, "bun": 5})
    # cost = 3*3 + 5*1 = 14
    assert sim._budget == 86
    assert len(sim._pending_deliveries) == 2
    for pd in sim._pending_deliveries:
        assert pd.ordered_on == 1
        assert 4 <= pd.arrives_on <= 6  # 1 + randint(3,5)


def test_place_order_exceeds_budget():
    sim = make_sim()
    sim._budget = 5
    sim._current_day = 1
    sim._place_order({"beef": 3})  # cost = 9, exceeds 5
    assert sim._budget == 5  # unchanged
    assert len(sim._pending_deliveries) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_simulation.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement simulation data types and core mechanics**

Create `simulation.py`:

```python
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from menu import Ingredient, MenuItem


@dataclass
class PendingDelivery:
    ingredient: str
    quantity: int
    ordered_on: int
    arrives_on: int


@dataclass
class StockoutEvent:
    menu_item: str
    price: int


@dataclass
class DayState:
    day: int
    day_of_week: str
    budget: int
    inventory: dict[str, int]
    pending_deliveries: list[dict]
    today_revenue: int
    today_waste: dict[str, int]
    today_stockouts: list[StockoutEvent]
    history: list["DayState"] = field(default_factory=list)


class Strategy(ABC):
    @abstractmethod
    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient]):
        pass

    @abstractmethod
    def initial_order(self, budget: int) -> dict[str, int]:
        pass

    @abstractmethod
    def decide_orders(self, state: DayState) -> dict[str, int]:
        pass


class Simulation:
    DURATION = 60
    STARTING_BUDGET = 1000
    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    TRAFFIC = {
        "monday": (0, 0),
        "tuesday": (20, 30),
        "wednesday": (20, 30),
        "thursday": (30, 45),
        "friday": (30, 45),
        "saturday": (45, 60),
        "sunday": (45, 60),
    }

    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient], strategy_class: type[Strategy]):
        self._menu = menu
        self._ingredients = ingredients
        self._strategy = strategy_class(menu, ingredients)
        self._budget = self.STARTING_BUDGET
        self._inventory: dict[str, list[int]] = {name: [] for name in ingredients}
        self._pending_deliveries: list[PendingDelivery] = []
        self._dissatisfaction = 0
        self._current_day = 0
        self._menu_weights = [1.0 / item.price for item in menu]

    def _receive_deliveries(self):
        remaining = []
        for delivery in self._pending_deliveries:
            if delivery.arrives_on == self._current_day:
                shelf_life = self._ingredients[delivery.ingredient].shelf_life
                expiry = self._current_day + shelf_life
                self._inventory[delivery.ingredient].extend([expiry] * delivery.quantity)
            else:
                remaining.append(delivery)
        self._pending_deliveries = remaining

    def _expire_inventory(self) -> dict[str, int]:
        waste: dict[str, int] = {}
        for name, expiry_list in self._inventory.items():
            unexpired = [e for e in expiry_list if e > self._current_day]
            expired_count = len(expiry_list) - len(unexpired)
            if expired_count > 0:
                waste[name] = expired_count
            self._inventory[name] = unexpired
        return waste

    def _fill_order(self, item: MenuItem) -> bool:
        for ingredient_name, qty in item.recipe.items():
            if len(self._inventory[ingredient_name]) < qty:
                return False
        for ingredient_name, qty in item.recipe.items():
            for _ in range(qty):
                self._inventory[ingredient_name].pop(0)
        return True

    def _place_order(self, order: dict[str, int]):
        total_cost = sum(
            self._ingredients[name].cost * qty
            for name, qty in order.items()
        )
        if total_cost > self._budget:
            return
        self._budget -= total_cost
        for name, qty in order.items():
            arrives_on = self._current_day + random.randint(3, 5)
            self._pending_deliveries.append(
                PendingDelivery(name, qty, self._current_day, arrives_on)
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_simulation.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add simulation.py tests/test_simulation.py
git commit -m "feat: add simulation data types and core inventory mechanics"
```

---

### Task 3: Simulation Day Loop and Scoring

**Files:**
- Modify: `simulation.py`
- Modify: `tests/test_simulation.py`

Adds the `run()` method that executes the 60-day loop, calls the strategy, and returns the score.

- [ ] **Step 1: Write failing tests for the day loop**

Append to `tests/test_simulation.py`:

```python
class FixedOrderStrategy(Strategy):
    """Orders a fixed amount of each ingredient every day."""
    def __init__(self, menu, ingredients):
        self.menu = menu
        self.ingredients = ingredients

    def initial_order(self, budget):
        return {name: 5 for name in self.ingredients}

    def decide_orders(self, state):
        return {name: 3 for name in self.ingredients}


def test_day_of_week_sequence():
    """Day 1 should be a tuesday (first open day after monday)."""
    sim = make_sim()
    # Day 1 = index 0 in the loop. Day number maps to DAY_NAMES[(day - 1) % 7].
    # We need to verify the mapping is consistent.
    assert Simulation.DAY_NAMES[0] == "monday"
    assert Simulation.DAY_NAMES[1] == "tuesday"
    assert Simulation.DAY_NAMES[6] == "sunday"


def test_monday_no_customers():
    """On Monday (day 1, 8, 15, ...) the restaurant is closed."""
    sim = make_sim()
    sim._current_day = 1  # monday
    low, high = Simulation.TRAFFIC["monday"]
    assert low == 0 and high == 0


def test_initial_order_delivered_before_day_1():
    """Initial order should be in inventory when the simulation starts."""
    class BuyBeefStrategy(Strategy):
        def __init__(self, menu, ingredients):
            self.menu = menu
            self.ingredients = ingredients

        def initial_order(self, budget):
            return {"beef": 5}

        def decide_orders(self, state):
            # On day 1, check that beef is in inventory
            if state.day == 1:
                assert state.inventory["beef"] == 5
            return {}

    random.seed(0)
    sim = Simulation(MENU, INGREDIENTS, BuyBeefStrategy)
    sim.run()


def test_simulation_runs_60_days():
    random.seed(0)
    sim = make_sim()
    result = sim.run()
    assert result.days_simulated == 60


def test_simulation_result_has_score():
    random.seed(0)
    sim = Simulation(MENU, INGREDIENTS, FixedOrderStrategy)
    result = sim.run()
    assert hasattr(result, "score")
    assert hasattr(result, "final_budget")
    assert hasattr(result, "dissatisfaction")
    assert result.score == result.final_budget - result.dissatisfaction


def test_do_nothing_strategy_has_zero_revenue():
    random.seed(0)
    sim = make_sim()  # DoNothingStrategy
    result = sim.run()
    assert result.final_budget == Simulation.STARTING_BUDGET
    # All orders are stockouts since no inventory
    assert result.dissatisfaction > 0
    assert result.score < Simulation.STARTING_BUDGET
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_simulation.py::test_simulation_runs_60_days -v`
Expected: FAIL — `AttributeError: 'Simulation' object has no attribute 'run'`

- [ ] **Step 3: Implement the day loop and run method**

Add to `simulation.py` at the top, after existing imports:

```python
from dataclasses import dataclass, field
```

Add `SimulationResult` dataclass after `DayState`:

```python
@dataclass
class SimulationResult:
    score: int
    final_budget: int
    dissatisfaction: int
    days_simulated: int
```

Add the `run` method to the `Simulation` class:

```python
    def _day_of_week(self, day: int) -> str:
        return self.DAY_NAMES[(day - 1) % 7]

    def _generate_customers(self) -> list[MenuItem]:
        dow = self._day_of_week(self._current_day)
        low, high = self.TRAFFIC[dow]
        if low == 0 and high == 0:
            return []
        count = random.randint(low, high)
        return random.choices(self._menu, weights=self._menu_weights, k=count)

    def _build_day_state(self, revenue: int, waste: dict[str, int], stockouts: list[StockoutEvent], history: list[DayState]) -> DayState:
        inventory_counts = {name: len(expiry_list) for name, expiry_list in self._inventory.items()}
        visible_deliveries = [
            {"ingredient": pd.ingredient, "quantity": pd.quantity, "days_since_ordered": self._current_day - pd.ordered_on}
            for pd in self._pending_deliveries
        ]
        return DayState(
            day=self._current_day,
            day_of_week=self._day_of_week(self._current_day),
            budget=self._budget,
            inventory=inventory_counts,
            pending_deliveries=visible_deliveries,
            today_revenue=revenue,
            today_waste=waste,
            today_stockouts=stockouts,
            history=list(history),
        )

    def run(self) -> "SimulationResult":
        # Process initial order
        initial = self._strategy.initial_order(self._budget)
        if initial:
            total_cost = sum(self._ingredients[name].cost * qty for name, qty in initial.items())
            if total_cost <= self._budget:
                self._budget -= total_cost
                for name, qty in initial.items():
                    shelf_life = self._ingredients[name].shelf_life
                    expiry = 1 + shelf_life  # delivered "before day 1", inventory as of day 1
                    self._inventory[name].extend([expiry] * qty)

        history: list[DayState] = []

        for day in range(1, self.DURATION + 1):
            self._current_day = day

            # 1. Receive deliveries
            self._receive_deliveries()

            # 2. Expire inventory
            waste = self._expire_inventory()

            # 3-5. Generate and fill orders (skip if Monday)
            revenue = 0
            stockouts: list[StockoutEvent] = []
            orders = self._generate_customers()
            for item in orders:
                if self._fill_order(item):
                    revenue += item.price
                    self._budget += item.price
                else:
                    self._dissatisfaction += item.price // 2
                    stockouts.append(StockoutEvent(item.name, item.price))

            # 6. Strategy decides orders
            state = self._build_day_state(revenue, waste, stockouts, history)
            order = self._strategy.decide_orders(state)
            if order:
                self._place_order(order)

            history.append(state)

        return SimulationResult(
            score=self._budget - self._dissatisfaction,
            final_budget=self._budget,
            dissatisfaction=self._dissatisfaction,
            days_simulated=self.DURATION,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_simulation.py -v`
Expected: All 14 tests PASS

- [ ] **Step 5: Commit**

```bash
git add simulation.py tests/test_simulation.py
git commit -m "feat: add simulation day loop, customer generation, and scoring"
```

---

### Task 4: Strategy ABC and Naive Sample Strategy

**Files:**
- Create: `strategy.py`

This creates the file the agent will modify. It re-exports the `Strategy` ABC from `simulation.py` and provides a `NaiveStrategy` as a working example.

- [ ] **Step 1: Write failing test**

Append to `tests/test_simulation.py`:

```python
def test_naive_strategy_earns_positive_revenue():
    from strategy import NaiveStrategy
    random.seed(0)
    sim = Simulation(MENU, INGREDIENTS, NaiveStrategy)
    result = sim.run()
    assert result.final_budget > Simulation.STARTING_BUDGET
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_simulation.py::test_naive_strategy_earns_positive_revenue -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategy'`

- [ ] **Step 3: Implement strategy.py**

Create `strategy.py`:

```python
from simulation import Strategy, DayState
from menu import MenuItem, Ingredient


class NaiveStrategy(Strategy):
    """Simple strategy: keep ~3 days of each ingredient in stock."""

    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient]):
        self.menu = menu
        self.ingredients = ingredients
        # Estimate daily usage per ingredient from menu
        # Rough: assume ~35 orders/day, uniform across 6 items ≈ 6 each
        self._daily_estimate: dict[str, int] = {}
        orders_per_item = 35 / len(menu)
        for name in ingredients:
            usage = sum(
                item.recipe.get(name, 0) * orders_per_item
                for item in menu
            )
            self._daily_estimate[name] = int(usage) + 1

    def initial_order(self, budget: int) -> dict[str, int]:
        # Buy 3 days worth
        order: dict[str, int] = {}
        total = 0
        for name, daily in self._daily_estimate.items():
            qty = daily * 3
            cost = qty * self.ingredients[name].cost
            if total + cost <= budget:
                order[name] = qty
                total += cost
        return order

    def decide_orders(self, state: DayState) -> dict[str, int]:
        order: dict[str, int] = {}
        total = 0
        for name, daily in self._daily_estimate.items():
            on_hand = state.inventory.get(name, 0)
            pending = sum(
                d["quantity"] for d in state.pending_deliveries
                if d["ingredient"] == name
            )
            target = daily * 3
            need = target - on_hand - pending
            if need > 0:
                cost = need * self.ingredients[name].cost
                if total + cost <= state.budget:
                    order[name] = need
                    total += cost
        return order
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_simulation.py::test_naive_strategy_earns_positive_revenue -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strategy.py tests/test_simulation.py
git commit -m "feat: add Strategy ABC re-export and NaiveStrategy sample"
```

---

### Task 5: Runner (Multi-Run Scoring and Entry Point)

**Files:**
- Create: `runner.py`
- Create: `tests/test_runner.py`

- [ ] **Step 1: Write failing tests for runner**

Create `tests/test_runner.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'runner'`

- [ ] **Step 3: Implement runner.py**

Create `runner.py`:

```python
from menu import MENU, INGREDIENTS
from simulation import Simulation, Strategy


def run_simulations(strategy_class: type[Strategy], n_runs: int = 10) -> dict:
    runs = []
    for _ in range(n_runs):
        sim = Simulation(MENU, INGREDIENTS, strategy_class)
        result = sim.run()
        runs.append({
            "score": result.score,
            "final_budget": result.final_budget,
            "dissatisfaction": result.dissatisfaction,
        })
    average_score = sum(r["score"] for r in runs) / len(runs)
    return {"average_score": average_score, "runs": runs}


if __name__ == "__main__":
    from strategy import NaiveStrategy

    result = run_simulations(NaiveStrategy)
    print(f"Average score: {result['average_score']:.0f}")
    print()
    for i, run in enumerate(result["runs"], 1):
        print(f"  Run {i:2d}: score={run['score']:6d}  budget={run['final_budget']:6d}  dissatisfaction={run['dissatisfaction']:5d}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_runner.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Run the full simulation as a smoke test**

Run: `python runner.py`
Expected: Output showing 10 runs with scores and an average. Scores should be positive (the naive strategy should earn more than it loses).

- [ ] **Step 6: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS (should be ~18 tests total)

- [ ] **Step 7: Commit**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: add runner with multi-run scoring and CLI entry point"
```
