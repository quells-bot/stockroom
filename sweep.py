"""Parameter sweep to find optimal tunable values under the reputation system."""

import itertools
from menu import MENU, INGREDIENTS
from simulation import Simulation

N_RUNS = 200


def avg_score(strategy_class, **kwargs):
    total = 0
    for _ in range(N_RUNS):
        sim = Simulation(MENU, INGREDIENTS, strategy_class, **kwargs)
        total += sim.run().score
    return total / N_RUNS


# --- NaiveStrategy: sweep days_of_stock ---
print("=== NaiveStrategy: days_of_stock ===")
from strategy import NaiveStrategy

# Monkey-patch to accept parameter
import strategy as strat

for days in [2, 3, 4, 5, 6, 7]:
    # Patch the constant inline
    orig_init = NaiveStrategy.__init__
    orig_initial = NaiveStrategy.initial_order
    orig_decide = NaiveStrategy.decide_orders

    class NaiveSweep(NaiveStrategy):
        _days = days
        def __init__(self, menu, ingredients, **kw):
            super().__init__(menu, ingredients)
        def initial_order(self, budget):
            order = {}
            total = 0
            for name, daily in self._daily_estimate.items():
                qty = daily * self._days
                cost = qty * self.ingredients[name].cost
                if total + cost <= budget:
                    order[name] = qty
                    total += cost
            return order
        def decide_orders(self, state):
            order = {}
            total = 0
            for name, daily in self._daily_estimate.items():
                on_hand = state.inventory.get(name, 0)
                pending = sum(d.quantity for d in state.pending_deliveries if d.ingredient == name)
                target = daily * self._days
                need = target - on_hand - pending
                if need > 0:
                    cost = need * self.ingredients[name].cost
                    if total + cost <= state.budget:
                        order[name] = need
                        total += cost
            return order

    score = avg_score(NaiveSweep)
    print(f"  days={days}: avg={score:.0f}")


# --- AdvancedHeuristicStrategy: days_of_stock ---
print("\n=== AdvancedHeuristicStrategy: days_of_stock ===")
from strategy import AdvancedHeuristicStrategy

for days in [2, 3, 4, 5, 6, 7]:
    class AdvancedSweep(AdvancedHeuristicStrategy):
        _days = days
        def __init__(self, menu, ingredients, **kw):
            super().__init__(menu, ingredients)
        def initial_order(self, budget):
            order = {}
            total = 0
            for name, daily in self._daily_estimate.items():
                qty = int(daily * self._days)
                cost = qty * self.ingredients[name].cost
                if total + cost <= budget:
                    order[name] = qty
                    total += cost
            return order
        def decide_orders(self, state):
            order = {}
            total = 0
            for name, daily in self._daily_estimate.items():
                on_hand = state.inventory.get(name, 0)
                pending = sum(d.quantity for d in state.pending_deliveries if d.ingredient == name)
                target = int(daily * self._days)
                need = target - on_hand - pending
                if need > 0:
                    cost = need * self.ingredients[name].cost
                    if total + cost <= state.budget:
                        order[name] = need
                        total += cost
            return order

    score = avg_score(AdvancedSweep)
    print(f"  days={days}: avg={score:.0f}")


# --- ForwardLookingHeuristicStrategy: forecast_window × safety_multiplier ---
print("\n=== ForwardLookingHeuristicStrategy: forecast_window × safety_multiplier ===")
from strategy import ForwardLookingHeuristicStrategy

for window, safety in itertools.product([3, 4, 5, 6], [1.0, 1.5, 2.0, 2.5, 3.0]):
    class FLSweep(ForwardLookingHeuristicStrategy):
        _window = window
        _safety = safety
        def __init__(self, menu, ingredients, **kw):
            super().__init__(menu, ingredients)
        def decide_orders(self, state):
            order = {}
            total = 0
            for name in self.ingredients:
                on_hand = state.inventory.get(name, 0)
                pending = sum(d.quantity for d in state.pending_deliveries if d.ingredient == name)
                forecasted_demand = self._forecast_demand(self._window, state.day, name)
                safety_buffer = int(self._daily_estimate[name] * self._safety)
                projected_stock = on_hand + pending - forecasted_demand
                need = safety_buffer - projected_stock
                if need > 0:
                    cost = need * self.ingredients[name].cost
                    if total + cost <= state.budget:
                        order[name] = int(round(need))
                        total += cost
            return order

    score = avg_score(FLSweep)
    print(f"  window={window}, safety={safety:.1f}: avg={score:.0f}")


# --- BayesianAdaptiveStrategy: forecast_window × safety_multiplier ---
print("\n=== BayesianAdaptiveStrategy: forecast_window × safety_multiplier ===")
from strategy import BayesianAdaptiveStrategy

for window, safety in itertools.product([3, 4, 5, 6, 7], [1.0, 1.5, 2.0, 2.5, 3.0]):
    class BayesSweep(BayesianAdaptiveStrategy):
        _window = window
        _safety = safety
        def __init__(self, menu, ingredients, **kw):
            super().__init__(menu, ingredients)
        def decide_orders(self, state):
            self._update(state)
            forecasted = {name: 0.0 for name in self.ingredients}
            for offset in range(1, self._window + 1):
                future_day = state.day + offset
                dow = self.DAY_NAMES[future_day % 7]
                for name in self.ingredients:
                    forecasted[name] += self._estimate_demand(name, dow)

            order = {}
            total = 0
            for name in self.ingredients:
                on_hand = state.inventory.get(name, 0)
                pending = sum(d.quantity for d in state.pending_deliveries if d.ingredient == name)
                shelf_life = self.ingredients[name].shelf_life
                if shelf_life < self._window:
                    usable_fraction = shelf_life / self._window
                    effective_on_hand = on_hand * usable_fraction
                else:
                    effective_on_hand = on_hand
                safety_stock = max(1, int(self._safety * forecasted[name] ** 0.5))
                target = int(forecasted[name]) + safety_stock
                need = target - int(effective_on_hand) - pending
                if need > 0:
                    cost = need * self.ingredients[name].cost
                    if total + cost <= state.budget:
                        order[name] = need
                        total += cost
            return order

    score = avg_score(BayesSweep)
    print(f"  window={window}, safety={safety:.1f}: avg={score:.0f}")
