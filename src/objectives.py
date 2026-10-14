import numpy as np

from src.diet_representation import (
    calculate_diet_totals,
    calculate_meal_totals,
)


NUTRIENTS = [
    "energy_kcal",
    "protein_g",
    "carb_g",
    "fat_g",
    "fibre_g",
]


MEAL_ENERGY_TARGETS = {
    "breakfast": 0.25,
    "lunch": 0.30,
    "snack": 0.15,
    "dinner": 0.30,
}


def nutritional_deviation(diet, nutrient_targets):
    """
    Objective 1:
    Mean normalized deviation from the user's daily
    nutrient targets.

    Lower is better.
    """

    totals = calculate_diet_totals(diet)

    deviations = []

    for nutrient in NUTRIENTS:

        target = nutrient_targets[nutrient]
        actual = totals[nutrient]

        if target <= 0:
            continue

        deviation = abs(
            actual - target
        ) / target

        deviations.append(deviation)

    if not deviations:
        return 0.0

    return float(
        np.mean(deviations)
    )


def existing_diet_deviation(
    diet,
    existing_diet,
):
    """
    Objective 2:
    Measures how much the generated diet differs from
    the user's existing dietary pattern.

    This combines:
    1. food-code changes
    2. serving-size changes

    Lower is better.

    0.0 means the generated diet is effectively identical
    to the baseline dietary pattern.
    """

    meal_scores = []

    for meal_name, generated_foods in diet.items():

        baseline_foods = existing_diet.get(
            meal_name,
            [],
        )

        baseline_map = {
            item["food_code"]: item["servings"]
            for item in baseline_foods
        }

        generated_map = {}

        for item in generated_foods:

            code = item["food_code"]

            generated_map[code] = (
                generated_map.get(code, 0.0)
                + item["servings"]
            )

        all_codes = set(
            baseline_map.keys()
        ).union(
            generated_map.keys()
        )

        if not all_codes:
            meal_scores.append(0.0)
            continue

        food_change_scores = []

        for code in all_codes:

            baseline_servings = baseline_map.get(
                code,
                0.0,
            )

            generated_servings = generated_map.get(
                code,
                0.0,
            )

            denominator = max(
                baseline_servings,
                generated_servings,
                1.0,
            )

            difference = abs(
                baseline_servings
                - generated_servings
            ) / denominator

            food_change_scores.append(
                difference
            )

        meal_scores.append(
            float(
                np.mean(
                    food_change_scores
                )
            )
        )

    if not meal_scores:
        return 0.0

    return float(
        np.mean(meal_scores)
    )


def diversity_penalty(diet):
    """
    Objective 3:
    Penalizes repeated food selections.

    Diversity score:
        unique foods / total food selections

    Because the optimizer minimizes objectives:

        penalty = 1 - diversity

    Lower is better.
    """

    food_codes = []

    for foods in diet.values():

        for food in foods:
            food_codes.append(
                food["food_code"]
            )

    if not food_codes:
        return 1.0

    unique_foods = len(
        set(food_codes)
    )

    total_foods = len(food_codes)

    diversity = (
        unique_foods
        / total_foods
    )

    penalty = 1.0 - diversity

    return float(penalty)


def meal_distribution_deviation(diet):
    """
    Objective 4:
    Measures how closely daily energy is distributed
    according to the desired meal proportions.

    Target proportions:
        Breakfast = 25%
        Lunch     = 30%
        Snack     = 15%
        Dinner    = 30%

    Lower is better.
    """

    meal_totals = calculate_meal_totals(
        diet
    )

    total_energy = sum(
        meal["energy_kcal"]
        for meal in meal_totals.values()
    )

    if total_energy <= 0:
        return 1.0

    deviations = []

    for meal_name, target_fraction in (
        MEAL_ENERGY_TARGETS.items()
    ):

        actual_energy = (
            meal_totals[meal_name][
                "energy_kcal"
            ]
        )

        actual_fraction = (
            actual_energy
            / total_energy
        )

        deviations.append(
            abs(
                actual_fraction
                - target_fraction
            )
        )

    return float(
        np.mean(deviations)
    )


def evaluate_objectives(
    diet,
    nutrient_targets,
    existing_diet,
):
    """
    Return the four objective values for one candidate diet.

    All objectives are minimized.
    """

    f1 = nutritional_deviation(
        diet,
        nutrient_targets,
    )

    f2 = existing_diet_deviation(
        diet,
        existing_diet,
    )

    f3 = diversity_penalty(
        diet
    )

    f4 = meal_distribution_deviation(
        diet
    )

    return np.array(
        [
            f1,
            f2,
            f3,
            f4,
        ],
        dtype=float,
    )