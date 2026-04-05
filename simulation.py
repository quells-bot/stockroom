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
            if delivery.arrives_on <= self._current_day:
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
