from menu import Ingredient, MenuItem, INGREDIENTS, MENU


def test_ingredient_fields():
    bun = INGREDIENTS["bun"]
    assert bun.name == "bun"
    assert bun.cost == 1
    assert bun.shelf_life == 3


def test_all_ingredients_exist():
    expected = {"bun", "beef", "chicken", "lettuce", "tomato", "cheese", "parmesan", "pasta", "croutons"}
    assert set(INGREDIENTS.keys()) == expected


def test_menu_item_fields():
    burger = next(m for m in MENU if m.name == "Burger")
    assert burger.price == 12
    assert burger.recipe == {"bun": 1, "beef": 1, "lettuce": 1, "tomato": 1}


def test_all_menu_items_exist():
    names = {m.name for m in MENU}
    expected = {"Burger", "Cheeseburger", "Grilled Chicken Sandwich", "Cheese Chicken Sandwich", "Caesar Salad", "Pasta Bolognese"}
    assert names == expected


def test_all_recipe_ingredients_are_valid():
    for item in MENU:
        for ingredient_name in item.recipe:
            assert ingredient_name in INGREDIENTS, f"{item.name} uses unknown ingredient {ingredient_name}"


def test_every_ingredient_used_in_at_least_two_dishes():
    usage_count: dict[str, int] = {name: 0 for name in INGREDIENTS}
    for item in MENU:
        for ingredient_name in item.recipe:
            usage_count[ingredient_name] += 1
    for name, count in usage_count.items():
        assert count >= 2, f"{name} only used in {count} dish(es)"
