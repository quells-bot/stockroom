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


class BayesianAdaptiveStrategy(Strategy):
    """Adaptive strategy using Poisson-Gamma Bayesian demand estimation.

    Maintains per-ingredient, per-day-of-week demand posteriors that update
    each day based on observed consumption and stockouts. Orders are placed
    to cover forecasted demand over the delivery window plus safety stock
    derived from posterior uncertainty.
    """

    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient], **kwargs):
        self.menu = menu
        self.ingredients = ingredients

        # Compute prior demand estimate per ingredient (average day)
        # Equal weighting across menu items — no assumption about ordering bias
        items_per_day = 37.5 / len(menu)
        self._prior_daily: dict[str, float] = {}
        for name in ingredients:
            usage = 0.0
            for item in menu:
                if name in item.recipe:
                    usage += items_per_day * item.recipe[name]
            self._prior_daily[name] = max(usage, 0.1)

        # Gamma posterior parameters per ingredient per day-of-week
        # Gamma(alpha, beta): mean = alpha/beta, var = alpha/beta^2
        # Weak prior: 2 pseudo-observations so real data dominates quickly
        prior_strength = 2.0
        self._alpha: dict[str, dict[str, float]] = {}
        self._beta: dict[str, dict[str, float]] = {}
        for name in ingredients:
            self._alpha[name] = {}
            self._beta[name] = {}
            for dow in self.DAY_NAMES:
                # Monday has no traffic — very tight prior around 0
                if dow == "monday":
                    self._alpha[name][dow] = 0.01
                    self._beta[name][dow] = 1.0
                else:
                    self._alpha[name][dow] = self._prior_daily[name] * prior_strength
                    self._beta[name][dow] = prior_strength

    def _estimate_demand(self, ingredient: str, dow: str) -> float:
        """Posterior mean demand for ingredient on day-of-week."""
        return self._alpha[ingredient][dow] / self._beta[ingredient][dow]

    def _estimate_std(self, ingredient: str, dow: str) -> float:
        """Posterior standard deviation of demand."""
        a = self._alpha[ingredient][dow]
        b = self._beta[ingredient][dow]
        return (a / (b * b)) ** 0.5

    def _update_demand(self, state: DayState):
        """Update Bayesian estimates from observed consumption + stockouts."""
        if not state.history:
            return

        prev = state.history[-1]

        # Deliveries received today: those with days_until_arrival == 1 yesterday
        deliveries_received: dict[str, int] = {name: 0 for name in self.ingredients}
        for d in prev.pending_deliveries:
            if d.days_until_arrival == 1:
                deliveries_received[d.ingredient] += d.quantity

        for name in self.ingredients:
            prev_inv = prev.inventory.get(name, 0)
            curr_inv = state.inventory.get(name, 0)
            waste = state.today_waste.get(name, 0)
            received = deliveries_received.get(name, 0)

            # consumption = what we had + what arrived - what expired - what remains
            consumption = prev_inv + received - waste - curr_inv
            consumption = max(consumption, 0)

            # Add unmet demand from stockouts
            unmet = 0
            for so in state.today_stockouts:
                for item in self.menu:
                    if item.name == so.menu_item and name in item.recipe:
                        unmet += item.recipe[name]

            total_demand = consumption + unmet

            # Poisson-Gamma conjugate update: alpha += obs, beta += 1
            dow = state.day_of_week
            self._alpha[name][dow] += total_demand
            self._beta[name][dow] += 1.0

    def initial_order(self, budget: int) -> dict[str, int]:
        # Cover first 4 days (deliveries from day-1 orders arrive day 4-6)
        order: dict[str, int] = {}
        total = 0
        for name in self.ingredients:
            qty = int(self._prior_daily[name] * 4) + 2
            cost = qty * self.ingredients[name].cost
            if total + cost <= budget:
                order[name] = qty
                total += cost
        return order

    def decide_orders(self, state: DayState) -> dict[str, int]:
        self._update_demand(state)

        # Forecast demand over next 5 days (covers max delivery lead time)
        forecast_window = 5
        forecasted: dict[str, float] = {name: 0.0 for name in self.ingredients}
        forecast_var: dict[str, float] = {name: 0.0 for name in self.ingredients}
        for offset in range(1, forecast_window + 1):
            future_day = state.day + offset
            dow = self.DAY_NAMES[future_day % 7]
            for name in self.ingredients:
                forecasted[name] += self._estimate_demand(name, dow)
                # Variance of sum = sum of variances (independent days)
                forecast_var[name] += self._estimate_std(name, dow) ** 2

        order: dict[str, int] = {}
        total = 0

        # Account for shelf life: on-hand stock of perishables may expire
        # before the forecast window ends, reducing effective coverage
        for name in self.ingredients:
            on_hand = state.inventory.get(name, 0)
            pending = sum(
                d.quantity for d in state.pending_deliveries
                if d.ingredient == name
            )

            shelf_life = self.ingredients[name].shelf_life
            # Discount on-hand stock for perishables: assume uniform expiry
            # spread, so only a fraction covers the full forecast window
            if shelf_life < forecast_window:
                usable_fraction = shelf_life / forecast_window
                effective_on_hand = on_hand * usable_fraction
            else:
                effective_on_hand = on_hand

            # Safety stock: ~1.5 sigma covers ~93% of demand scenarios
            safety = max(1, int(4.0 * forecast_var[name] ** 0.5))

            target = int(forecasted[name]) + safety
            need = target - int(effective_on_hand) - pending

            if need > 0:
                cost = need * self.ingredients[name].cost
                if total + cost <= state.budget:
                    order[name] = need
                    total += cost

        return order


class ForwardLookingHeuristicStrategy(Strategy):
    """Strategy that forecasts demand 4 days ahead based on day-of-week patterns."""
    
    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    TRAFFIC = {
        "monday": 0,
        "tuesday": 25,
        "wednesday": 25,
        "thursday": 38,
        "friday": 38,
        "saturday": 53,
        "sunday": 53,
    }
    
    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient]):
        self.menu = menu
        self.ingredients = ingredients
        self._daily_estimate: dict[str, float] = {}
        
        avg_daily_orders = 37.5
        
        weights = [1.0 / item.price for item in menu]
        total_weight = sum(weights)
        choice_probs = [w / total_weight for w in weights]
        
        expected_orders = [avg_daily_orders * prob for prob in choice_probs]
        
        for name in ingredients:
            usage = 0.0
            for item, exp_order in zip(menu, expected_orders):
                if name in item.recipe:
                    usage += exp_order * item.recipe[name]
            self._daily_estimate[name] = usage + 1.0
    
    def _get_expected_traffic(self, day_offset: int, current_day: int) -> int:
        dow = self.DAY_NAMES[(current_day + day_offset) % 7]
        return self.TRAFFIC[dow]
    
    def _forecast_demand(self, day_offset: int, current_day: int, ingredient: str) -> float:
        total_demand = 0.0
        for offset in range(1, day_offset + 1):
            future_dow = self.DAY_NAMES[(current_day + offset) % 7]
            daily_customers = self.TRAFFIC[future_dow]
            for item in self.menu:
                if ingredient in item.recipe:
                    usage_rate = item.recipe[ingredient]
                    price_weight = 1.0 / item.price
                    total_demand += daily_customers * (price_weight / sum(1.0 / i.price for i in self.menu)) * usage_rate
        return total_demand
    
    def initial_order(self, budget: int) -> dict[str, int]:
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
        
        for name in self.ingredients:
            on_hand = state.inventory.get(name, 0)
            pending = sum(
                d.quantity for d in state.pending_deliveries
                if d.ingredient == name
            )
            
            forecasted_demand = self._forecast_demand(4, state.day, name)
            
            safety_buffer = int(self._daily_estimate[name] * 2)
            
            projected_stock = on_hand + pending - forecasted_demand
            need = safety_buffer - projected_stock
            
            if need > 0:
                cost = need * self.ingredients[name].cost
                if total + cost <= state.budget:
                    order[name] = int(round(need))
                    total += cost
        
        return order
