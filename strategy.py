# strategy.py — Modify this file to implement your ordering strategy.
# NaiveStrategy below is a working reference implementation you can study and replace.

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
            self._daily_estimate[name] = int(usage) + 1  # +1 safety buffer

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
                d.quantity for d in state.pending_deliveries
                if d.ingredient == name
            )
            target = daily * 3
            need = target - on_hand - pending
            if need > 0:
                cost = need * self.ingredients[name].cost
                if total + cost <= state.budget:
                    order[name] = need
                    total += cost
        return order


class AdvancedHeuristicStrategy(Strategy):
    """Improved heuristic strategy with accurate demand estimation."""
    
    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient]):
        self.menu = menu
        self.ingredients = ingredients
        self._daily_estimate: dict[str, float] = {}
        
        # Calculate average daily orders over the week
        # Traffic: monday:0, tue:20-30 (avg25), wed:25, thu:30-45 (avg37.5), fri:37.5, sat:45-60 (avg52.5), sun:52.5
        # Average per day: (0+25+25+37.5+37.5+52.5+52.5)/7 = 262.5/7 = 37.5
        avg_daily_orders = 37.5
        
        # Calculate menu choice weights (proportional to 1/price)
        weights = [1.0 / item.price for item in menu]
        total_weight = sum(weights)
        choice_probs = [w / total_weight for w in weights]
        
        # Expected orders per menu item per day
        expected_orders = [
            avg_daily_orders * prob for prob in choice_probs
        ]
        
        # Calculate expected daily usage per ingredient
        for name in ingredients:
            usage = 0.0
            for item, exp_order in zip(menu, expected_orders):
                if name in item.recipe:
                    usage += exp_order * item.recipe[name]
            # Add small safety buffer
            self._daily_estimate[name] = usage + 1.0

    def initial_order(self, budget: int) -> dict[str, int]:
        # Buy 4 days worth to increase safety margin
        order: dict[str, int] = {}
        total = 0
        for name, daily in self._daily_estimate.items():
            qty = int(daily * 4)
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
                d.quantity for d in state.pending_deliveries
                if d.ingredient == name
            )
            target = int(daily * 4)
            need = target - on_hand - pending
            if need > 0:
                cost = need * self.ingredients[name].cost
                if total + cost <= state.budget:
                    order[name] = need
                    total += cost
        return order


class DefaultStrategy(AdvancedHeuristicStrategy):
    pass