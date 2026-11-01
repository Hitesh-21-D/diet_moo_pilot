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


def nutritional_deviation(
    diet,
    nutrient_targets,
):

    totals = calculate_diet_totals(
        diet
    )

    deviations = []

    for nutrient in NUTRIENTS:

        target = nutrient_targets[
            nutrient
        ]

        actual = totals[
            nutrient
        ]

        if target <= 0:
            continue

        deviation = (
            abs(
                actual - target
            )
            / target
        )

        deviations.append(
            deviation
        )

    return float(
        np.mean(
            deviations
        )
    )


def existing_diet_deviation(
    diet,
    existing_diet,
):

    meal_scores = []

    for meal_name, generated_foods in (
        diet.items()
    ):

        baseline_foods = (
            existing_diet.get(
                meal_name,
                [],
            )
        )

        baseline_map = {}

        for item in baseline_foods:

            code = item[
                "food_code"
            ]

            baseline_map[
                code
            ] = (
                baseline_map.get(
                    code,
                    0.0,
                )
                + item[
                    "servings"
                ]
            )

        generated_map = {}

        for item in generated_foods:

            code = item[
                "food_code"
            ]

            if code == "NONE":
                continue

            generated_map[
                code
            ] = (
                generated_map.get(
                    code,
                    0.0,
                )
                + item[
                    "servings"
                ]
            )

        all_codes = (
            set(
                baseline_map
                .keys()
            )
            |
            set(
                generated_map
                .keys()
            )
        )

        if not all_codes:

            meal_scores.append(
                0.0
            )

            continue

        food_differences = []

        for code in all_codes:

            baseline_servings = (
                baseline_map.get(
                    code,
                    0.0,
                )
            )

            generated_servings = (
                generated_map.get(
                    code,
                    0.0,
                )
            )

            denominator = max(
                baseline_servings,
                generated_servings,
                1.0,
            )

            difference = (
                abs(
                    baseline_servings
                    - generated_servings
                )
                / denominator
            )

            food_differences.append(
                difference
            )

        meal_scores.append(
            np.mean(
                food_differences
            )
        )

    return float(
        np.mean(
            meal_scores
        )
    )


def diversity_penalty(
    diet
):

    food_codes = []

    for foods in diet.values():

        for food in foods:

            code = food[
                "food_code"
            ]

            if code == "NONE":
                continue

            food_codes.append(
                code
            )

    if len(food_codes) == 0:

        return 1.0

    unique_count = len(
        set(
            food_codes
        )
    )

    total_count = len(
        food_codes
    )

    return float(
        1.0
        - (
            unique_count
            / total_count
        )
    )


def meal_distribution_deviation(
    diet
):

    meal_totals = (
        calculate_meal_totals(
            diet
        )
    )

    total_energy = sum(
        totals[
            "energy_kcal"
        ]
        for totals
        in meal_totals.values()
    )

    if total_energy <= 0:

        return 1.0

    deviations = []

    for (
        meal_name,
        target_fraction
    ) in MEAL_ENERGY_TARGETS.items():

        actual_fraction = (
            meal_totals[
                meal_name
            ][
                "energy_kcal"
            ]
            / total_energy
        )

        deviations.append(
            abs(
                actual_fraction
                - target_fraction
            )
        )

    return float(
        np.mean(
            deviations
        )
    )


def evaluate_objectives(
    diet,
    nutrient_targets,
    existing_diet,
):

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

    f4 = (
        meal_distribution_deviation(
            diet
        )
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