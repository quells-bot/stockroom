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
class PendingDeliveryInfo:
    ingredient: str
    quantity: int
    days_until_arrival: int


@dataclass
class DayState:
    day: int
    day_of_week: str
    budget: int
    inventory: dict[str, int]
    pending_deliveries: list[PendingDeliveryInfo]
    today_revenue: int
    today_waste: dict[str, int]
    today_stockouts: list[StockoutEvent]
    history: list["DayState"] = field(default_factory=list)


@dataclass
class SimulationResult:
    score: int
    final_budget: int
    dissatisfaction: int
    days_simulated: int


class Strategy(ABC):
    @abstractmethod
    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient], **kwargs):
        pass

    @abstractmethod
    def initial_order(self, budget: int) -> dict[str, int]:
        pass

    @abstractmethod
    def decide_orders(self, state: DayState) -> dict[str, int]:
        pass


class Simulation:
    DURATION = 60
    STARTING_BUDGET = 100000
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

    def __init__(self, menu: list[MenuItem], ingredients: dict[str, Ingredient], strategy_class: type[Strategy], **strategy_kwargs):
        self._menu = menu
        self._ingredients = ingredients
        self._strategy = strategy_class(menu, ingredients, **strategy_kwargs)
        self._budget = self.STARTING_BUDGET
        self._inventory: dict[str, list[int]] = {name: [] for name in ingredients}
        self._pending_deliveries: list[PendingDelivery] = []
        self._dissatisfaction = 0
        self._current_day = 0
        self._menu_weights = [1.0 / item.price for item in menu]
        self._traffic = {dow: list(bounds) for dow, bounds in self.TRAFFIC.items()}

    def _receive_deliveries(self):
        remaining = []
        for delivery in self._pending_deliveries:
            if delivery.arrives_on <= self._current_day:
                shelf_life = self._ingredients[delivery.ingredient].shelf_life
                expiry = delivery.arrives_on + shelf_life
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

    def _day_of_week(self, day: int) -> str:
        return self.DAY_NAMES[day % 7]

    def _generate_customers(self) -> list[MenuItem]:
        dow = self._day_of_week(self._current_day)
        low, high = self._traffic[dow]
        if low == 0 and high == 0:
            return []
        count = random.randint(low, high)
        return random.choices(self._menu, weights=self._menu_weights, k=count)

    def _update_reputation(self, stockouts: list[StockoutEvent]):
        open_days = [d for d, bounds in self._traffic.items() if bounds[0] > 0 or bounds[1] > 0]
        if not open_days:
            return
        if stockouts:
            for _ in stockouts:
                dow = random.choice(open_days)
                self._traffic[dow][0] = max(0, self._traffic[dow][0] - 1)
                self._traffic[dow][1] = max(0, self._traffic[dow][1] - 1)
                open_days = [d for d, bounds in self._traffic.items() if bounds[0] > 0 or bounds[1] > 0]
                if not open_days:
                    return
        else:
            if random.random() < 0.10:
                dow = random.choice(open_days)
                self._traffic[dow][0] += 1
                self._traffic[dow][1] += 1

    def _build_day_state(self, revenue: int, waste: dict[str, int], stockouts: list[StockoutEvent], history: list[DayState]) -> DayState:
        inventory_counts = {name: len(expiry_list) for name, expiry_list in self._inventory.items()}
        visible_deliveries = [
            PendingDeliveryInfo(ingredient=pd.ingredient, quantity=pd.quantity, days_until_arrival=pd.arrives_on - self._current_day)
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

            # 6. Update reputation based on stockouts
            self._update_reputation(stockouts)

            # 7. Strategy decides orders
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
