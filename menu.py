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
    "bun": Ingredient("bun", cost=50, shelf_life=3),
    "beef": Ingredient("beef", cost=200, shelf_life=4),
    "chicken": Ingredient("chicken", cost=250, shelf_life=3),
    "lettuce": Ingredient("lettuce", cost=10, shelf_life=3),
    "tomato": Ingredient("tomato", cost=80, shelf_life=5),
    "cheese": Ingredient("cheese", cost=45, shelf_life=7),
    "parmesan": Ingredient("parmesan", cost=80, shelf_life=10),
    "pasta": Ingredient("pasta", cost=100, shelf_life=30),
    "croutons": Ingredient("croutons", cost=150, shelf_life=14),
}

MENU: list[MenuItem] = [
    MenuItem("Burger", price=1200, recipe={"bun": 1, "beef": 1, "lettuce": 1, "tomato": 1}),
    MenuItem("Cheeseburger", price=1500, recipe={"bun": 1, "beef": 1, "lettuce": 1, "tomato": 1, "cheese": 1}),
    MenuItem("Grilled Chicken Sandwich", price=1300, recipe={"bun": 1, "chicken": 1, "lettuce": 1, "tomato": 1}),
    MenuItem("Cheese Chicken Sandwich", price=1600, recipe={"bun": 1, "chicken": 1, "lettuce": 1, "tomato": 1, "cheese": 1}),
    MenuItem("Caesar Salad", price=1000, recipe={"lettuce": 1, "chicken": 1, "parmesan": 1, "croutons": 1}),
    MenuItem("Pasta Bolognese", price=1500, recipe={"pasta": 1, "beef": 1, "tomato": 1, "parmesan": 1}),
]

if __name__ == "__main__":
    for item in MENU:
        price = item.price
        cost = sum([INGREDIENTS[i].cost for i in item.recipe])
        margin = (price - cost) / cost
        print(f"{item.name} ({price}): costs {cost} ({margin})")
