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


class AdvancedHeuristicStrategy(Strategy):
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

    def initial_order(self, budget: int) -> dict[str, int]:
        # Logic for day 0 order
        order: dict[str, int] = {}
        total_cost = 0
        for name, demand in self._daily_base_demand.items():
            # Target 5 days worth for initial order
            qty = int(demand * 5)
            cost = qty * self.ingredients[name].cost
            if total_cost + cost <= budget:
                order[name] = qty
                total_cost += cost
        return order

    def decide_orders(self, state: DayState) -> dict[str, int]:
        order: dict[str, int] = {}
        total_cost = 0
        
        # Traffic multiplier based on day of week
        # Weekend (Sat, Sun) has higher traffic (4					
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
