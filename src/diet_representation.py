import numpy as np


MEAL_NAMES = [
    "breakfast",
    "lunch",
    "snack",
    "dinner",
]


# Number of food slots available in every meal.
FOOD_SLOTS_PER_MEAL = 3


# Allowed number of servings per selected food.
MIN_SERVINGS = 0.25
MAX_SERVINGS = 2.0


def chromosome_length():
    """
    Each food slot contains two values:

    1. food index
    2. number of servings

    4 meals x 3 slots x 2 variables = 24 variables
    """

    return (
        len(MEAL_NAMES)
        * FOOD_SLOTS_PER_MEAL
        * 2
    )


def decode_chromosome(chromosome, food_pools):
    """
    Convert a numeric chromosome into a human-readable diet.

    Chromosome layout:

        food_index, servings,
        food_index, servings,
        ...

    Food indices are rounded to integers and clipped to
    the valid range of each meal-specific food pool.
    """

    diet = {}

    position = 0

    for meal_name in MEAL_NAMES:

        pool = food_pools[meal_name]

        meal_foods = []

        for _ in range(FOOD_SLOTS_PER_MEAL):

            raw_food_index = chromosome[position]
            raw_servings = chromosome[position + 1]

            position += 2

            food_index = int(
                round(raw_food_index)
            )

            food_index = int(
                np.clip(
                    food_index,
                    0,
                    len(pool) - 1,
                )
            )

            servings = float(
                np.clip(
                    raw_servings,
                    MIN_SERVINGS,
                    MAX_SERVINGS,
                )
            )

            servings = round(servings * 4) / 4

            food = pool.iloc[food_index]

            meal_foods.append(
                {
                    "food_code": food["food_code"],
                    "food_name": food["food_name"],
                    "serving_unit": food["servings_unit"],
                    "servings": servings,

                    "energy_kcal": (
                        food["energy_kcal"]
                        * servings
                    ),

                    "protein_g": (
                        food["protein_g"]
                        * servings
                    ),

                    "carb_g": (
                        food["carb_g"]
                        * servings
                    ),

                    "fat_g": (
                        food["fat_g"]
                        * servings
                    ),

                    "fibre_g": (
                        food["fibre_g"]
                        * servings
                    ),
                }
            )

        diet[meal_name] = meal_foods

    return diet


def calculate_diet_totals(diet):
    """
    Calculate full-day nutrient totals.
    """

    totals = {
        "energy_kcal": 0.0,
        "protein_g": 0.0,
        "carb_g": 0.0,
        "fat_g": 0.0,
        "fibre_g": 0.0,
    }

    for meal_foods in diet.values():

        for food in meal_foods:

            for nutrient in totals:

                totals[nutrient] += food[nutrient]

    return totals


def calculate_meal_totals(diet):
    """
    Calculate nutrient totals separately for each meal.
    """

    meal_totals = {}

    for meal_name, foods in diet.items():

        totals = {
            "energy_kcal": 0.0,
            "protein_g": 0.0,
            "carb_g": 0.0,
            "fat_g": 0.0,
            "fibre_g": 0.0,
        }

        for food in foods:

            for nutrient in totals:

                totals[nutrient] += food[nutrient]

        meal_totals[meal_name] = totals

    return meal_totals