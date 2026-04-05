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
    sim = make_sim()
    assert sim._day_of_week(1) == "monday"
    assert sim._day_of_week(2) == "tuesday"
    assert sim._day_of_week(7) == "sunday"
    assert sim._day_of_week(8) == "monday"  # wraps back to monday


def test_monday_no_customers():
    sim = make_sim()
    sim._current_day = 1  # monday
    customers = sim._generate_customers()
    assert customers == []


def test_initial_order_delivered_before_day_1():
    checked = []

    class BuyBeefStrategy(Strategy):
        def __init__(self, menu, ingredients):
            self.menu = menu
            self.ingredients = ingredients

        def initial_order(self, budget):
            return {"beef": 5}

        def decide_orders(self, state):
            if state.day == 1:
                checked.append(state.inventory["beef"])
            return {}

    random.seed(0)
    sim = Simulation(MENU, INGREDIENTS, BuyBeefStrategy)
    sim.run()
    assert len(checked) == 1
    assert checked[0] == 5


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


def test_naive_strategy_earns_positive_revenue():
    from strategy import NaiveStrategy
    random.seed(0)
    sim = Simulation(MENU, INGREDIENTS, NaiveStrategy)
    result = sim.run()
    assert result.final_budget > Simulation.STARTING_BUDGET
