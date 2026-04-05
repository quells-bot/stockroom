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
    MenuItem("Grilled Chicken Sandwich", price=13, recipe={"bun": 1, "chicken": 1, "lettuce": 1, "tomato": 1, "pasta": 1}),
    MenuItem("Cheese Chicken Sandwich", price=15, recipe={"bun": 1, "chicken": 1, "lettuce": 1, "tomato": 1, "cheese": 1}),
    MenuItem("Caesar Salad", price=10, recipe={"lettuce": 1, "chicken": 1, "parmesan": 1, "croutons": 1}),
    MenuItem("Pasta Bolognese", price=15, recipe={"pasta": 1, "beef": 1, "tomato": 1, "parmesan": 1, "croutons": 1}),
]
