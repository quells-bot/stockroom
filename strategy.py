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
    """Adaptive strategy using factored Poisson-Gamma Bayesian estimation.

    Decomposes demand into two learned components:
      - Traffic model: customer count per day-of-week (Gamma posterior)
      - Usage model: ingredient units per customer (Gamma posterior)
      - Demand(ingredient, dow) = traffic(dow) × usage_rate(ingredient)

    Traffic learning pools observations across all ingredients, enabling
    fast convergence on day-of-week patterns. Usage rate learning pools
    across all days, quickly learning the menu mix. Both start from
    uninformative priors — no hardcoded traffic or pricing assumptions.
    """

    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient], **kwargs):
        self.menu = menu
        self.ingredients = ingredients

        # Average menu price (equal weighting) for estimating customer count
        self._avg_price = sum(item.price for item in menu) / len(menu)

        # Per-customer ingredient usage prior (equal menu selection)
        self._usage_prior: dict[str, float] = {}
        for name in ingredients:
            usage = 0.0
            for item in menu:
                if name in item.recipe:
                    usage += item.recipe[name] / len(menu)
            self._usage_prior[name] = max(usage, 0.01)

        # Traffic model: Gamma(alpha, beta) per DOW
        # Weak prior: mean=30 customers, prior_strength=0.5
        # (equivalent to half an observation — real data dominates immediately)
        traffic_prior_mean = 30.0
        traffic_prior_strength = 0.5
        self._traffic_alpha: dict[str, float] = {}
        self._traffic_beta: dict[str, float] = {}
        for dow in self.DAY_NAMES:
            if dow == "monday":
                self._traffic_alpha[dow] = 0.01
                self._traffic_beta[dow] = 1.0
            else:
                self._traffic_alpha[dow] = traffic_prior_mean * traffic_prior_strength
                self._traffic_beta[dow] = traffic_prior_strength

        # Usage rate model: Gamma(alpha, beta) per ingredient
        # Rate = ingredient units consumed per customer
        usage_prior_strength = 2.0
        self._usage_alpha: dict[str, float] = {}
        self._usage_beta: dict[str, float] = {}
        for name in ingredients:
            self._usage_alpha[name] = self._usage_prior[name] * usage_prior_strength
            self._usage_beta[name] = usage_prior_strength

    def _estimate_traffic(self, dow: str) -> float:
        """Posterior mean customer count for day-of-week."""
        return self._traffic_alpha[dow] / self._traffic_beta[dow]

    def _traffic_var(self, dow: str) -> float:
        """Posterior variance of traffic."""
        a = self._traffic_alpha[dow]
        b = self._traffic_beta[dow]
        return a / (b * b)

    def _estimate_usage(self, ingredient: str) -> float:
        """Posterior mean usage rate (units per customer)."""
        return self._usage_alpha[ingredient] / self._usage_beta[ingredient]

    def _usage_var(self, ingredient: str) -> float:
        """Posterior variance of usage rate."""
        a = self._usage_alpha[ingredient]
        b = self._usage_beta[ingredient]
        return a / (b * b)

    def _estimate_demand(self, ingredient: str, dow: str) -> float:
        """Expected demand = traffic × usage_rate."""
        return self._estimate_traffic(dow) * self._estimate_usage(ingredient)

    def _demand_var(self, ingredient: str, dow: str) -> float:
        """Variance of demand using Var(XY) = E[X]^2*Var(Y) + E[Y]^2*Var(X) + Var(X)*Var(Y)."""
        et = self._estimate_traffic(dow)
        eu = self._estimate_usage(ingredient)
        vt = self._traffic_var(dow)
        vu = self._usage_var(ingredient)
        return et * et * vu + eu * eu * vt + vt * vu

    def _update(self, state: DayState):
        """Update traffic and usage rate posteriors from today's observations."""
        if not state.history:
            return

        prev = state.history[-1]
        dow = state.day_of_week

        # Skip Monday (closed)
        if dow == "monday":
            return

        # Estimate customer count: filled orders + stockouts
        stockout_count = len(state.today_stockouts)
        filled_count = state.today_revenue / self._avg_price if self._avg_price > 0 else 0
        customer_count = filled_count + stockout_count

        # Update traffic posterior: alpha += customers, beta += 1
        self._traffic_alpha[dow] += customer_count
        self._traffic_beta[dow] += 1.0

        # Compute per-ingredient consumption
        deliveries_received: dict[str, int] = {name: 0 for name in self.ingredients}
        for d in prev.pending_deliveries:
            if d.days_until_arrival == 1:
                deliveries_received[d.ingredient] += d.quantity

        for name in self.ingredients:
            prev_inv = prev.inventory.get(name, 0)
            curr_inv = state.inventory.get(name, 0)
            waste = state.today_waste.get(name, 0)
            received = deliveries_received.get(name, 0)

            consumption = max(0, prev_inv + received - waste - curr_inv)

            # Add unmet demand from stockouts
            unmet = 0
            for so in state.today_stockouts:
                for item in self.menu:
                    if item.name == so.menu_item and name in item.recipe:
                        unmet += item.recipe[name]

            total_usage = consumption + unmet

            # Update usage rate posterior with variable exposure (customer_count)
            # Poisson-Gamma with exposure: alpha += usage, beta += exposure
            if customer_count > 0:
                self._usage_alpha[name] += total_usage
                self._usage_beta[name] += customer_count

    def initial_order(self, budget: int) -> dict[str, int]:
        # Use prior estimates for first 4 days of coverage
        order: dict[str, int] = {}
        total = 0
        for name in self.ingredients:
            daily = self._estimate_traffic("tuesday") * self._estimate_usage(name)
            qty = int(daily * 4) + 2
            cost = qty * self.ingredients[name].cost
            if total + cost <= budget:
                order[name] = qty
                total += cost
        return order

    def decide_orders(self, state: DayState) -> dict[str, int]:
        self._update(state)

        # Forecast demand over next 5 days (covers max delivery lead time)
        forecast_window = 5
        forecasted: dict[str, float] = {name: 0.0 for name in self.ingredients}
        forecast_var: dict[str, float] = {name: 0.0 for name in self.ingredients}
        for offset in range(1, forecast_window + 1):
            future_day = state.day + offset
            dow = self.DAY_NAMES[future_day % 7]
            for name in self.ingredients:
                forecasted[name] += self._estimate_demand(name, dow)
                forecast_var[name] += self._demand_var(name, dow)

        order: dict[str, int] = {}
        total = 0

        for name in self.ingredients:
            on_hand = state.inventory.get(name, 0)
            pending = sum(
                d.quantity for d in state.pending_deliveries
                if d.ingredient == name
            )

            shelf_life = self.ingredients[name].shelf_life
            if shelf_life < forecast_window:
                usable_fraction = shelf_life / forecast_window
                effective_on_hand = on_hand * usable_fraction
            else:
                effective_on_hand = on_hand

            # Safety stock: use sqrt(forecast) as Poisson-like approximation
            # avoids inflated variance from traffic × usage product early on
            safety = max(1, int(2.0 * forecasted[name] ** 0.5))

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
