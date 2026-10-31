import numpy as np

from src.diet_representation import (
    calculate_diet_totals,
)


# ============================================================
# Nutrient constraints
# ============================================================

NUTRIENT_BOUNDS = {

    "energy_kcal": {
        "lower": 0.90,
        "upper": 1.10,
    },

    "protein_g": {
        "lower": 0.90,
        "upper": 1.15,
    },

    "carb_g": {
        "lower": 0.80,
        "upper": 1.20,
    },

    "fat_g": {
        "lower": 0.80,
        "upper": 1.20,
    },

    "fibre_g": {
        "lower": 0.80,
        "upper": None,
    },
}


# ============================================================
# Meal composition
# ============================================================
#
# Every meal must contain either 2 or 3 actual foods.
# NONE does not count as an active food.
# ============================================================

MIN_ACTIVE_FOODS = {
    "breakfast": 2,
    "lunch": 2,
    "snack": 2,
    "dinner": 2,
}


MAX_ACTIVE_FOODS = {
    "breakfast": 3,
    "lunch": 3,
    "snack": 3,
    "dinner": 3,
}


# ============================================================
# Role-based meal constraints
# ============================================================
#
# These are deliberately simple.
#
# Breakfast:
#   exactly one main item
#
# Lunch:
#   exactly one staple
#   at least one protein/dal/curry
#
# Snack:
#   at least one snack item
#   no more than one beverage
#
# Dinner:
#   exactly one staple
#   at least one protein/dal/curry
# ============================================================


def nutrient_constraint_violations(
    diet,
    nutrient_targets,
):

    totals = calculate_diet_totals(
        diet
    )

    violations = []

    for (
        nutrient,
        bounds
    ) in NUTRIENT_BOUNDS.items():

        actual = totals[
            nutrient
        ]

        target = nutrient_targets[
            nutrient
        ]

        lower = bounds[
            "lower"
        ]

        upper = bounds[
            "upper"
        ]

        # Lower bound:
        # actual >= lower * target
        #
        # pymoo convention:
        # G <= 0 means feasible

        lower_limit = (
            lower
            * target
        )

        lower_violation = (
            lower_limit
            - actual
        ) / max(
            target,
            1e-12,
        )

        violations.append(
            lower_violation
        )

        if upper is not None:

            upper_limit = (
                upper
                * target
            )

            upper_violation = (
                actual
                - upper_limit
            ) / max(
                target,
                1e-12,
            )

            violations.append(
                upper_violation
            )

    return violations


def active_foods(
    meal_foods
):

    return [
        food
        for food in meal_foods
        if (
            food[
                "food_code"
            ]
            != "NONE"
            and
            food[
                "servings"
            ]
            > 0
        )
    ]


def duplicate_meal_constraint(
    meal_foods
):

    active = active_foods(
        meal_foods
    )

    codes = [
        food[
            "food_code"
        ]
        for food in active
    ]

    duplicate_count = (
        len(codes)
        - len(
            set(
                codes
            )
        )
    )

    # 0 = feasible
    # >0 = duplicates exist

    return float(
        duplicate_count
    )


def active_food_count_constraints(
    meal_name,
    meal_foods,
):

    active = active_foods(
        meal_foods
    )

    count = len(
        active
    )

    minimum = (
        MIN_ACTIVE_FOODS[
            meal_name
        ]
    )

    maximum = (
        MAX_ACTIVE_FOODS[
            meal_name
        ]
    )

    # count >= minimum
    lower_violation = (
        minimum
        - count
    )

    # count <= maximum
    upper_violation = (
        count
        - maximum
    )

    return [
        float(
            lower_violation
        ),
        float(
            upper_violation
        ),
    ]


def count_role(
    meal_foods,
    role,
):

    active = active_foods(
        meal_foods
    )

    return sum(
        1
        for food in active
        if (
            food.get(
                "role"
            )
            == role
        )
    )


def breakfast_role_constraints(
    meal_foods
):

    main_count = count_role(
        meal_foods,
        "main",
    )

    # Exactly one main:
    #
    # main >= 1
    # main <= 1

    return [
        float(
            1 - main_count
        ),

        float(
            main_count - 1
        ),
    ]


def lunch_role_constraints(
    meal_foods,
):

    staple_count = count_role(
        meal_foods,
        "staple",
    )

    protein_count = count_role(
        meal_foods,
        "protein_curry",
    )

    return [

        # At least one staple
        float(
            1 - staple_count
        ),

        # At most one staple
        float(
            staple_count - 1
        ),

        # At least one dal/curry/protein
        float(
            1 - protein_count
        ),

        # At most one dal/curry/protein
        float(
            protein_count - 1
        ),
    ]


def snack_role_constraints(
    meal_foods
):

    snack_count = count_role(
        meal_foods,
        "snack_item",
    )

    beverage_count = count_role(
        meal_foods,
        "beverage",
    )

    return [

        # At least one actual snack
        float(
            1 - snack_count
        ),

        # At most one beverage
        float(
            beverage_count - 1
        ),
    ]


def dinner_role_constraints(
    meal_foods,
):

    staple_count = count_role(
        meal_foods,
        "staple",
    )

    protein_count = count_role(
        meal_foods,
        "protein_curry",
    )

    return [

        # At least one staple
        float(
            1 - staple_count
        ),

        # At most one staple
        float(
            staple_count - 1
        ),

        # At least one dal/curry/protein
        float(
            1 - protein_count
        ),

        # At most one dal/curry/protein
        float(
            protein_count - 1
        ),
    ]


def meal_role_constraints(
    diet
):

    violations = []

    violations.extend(
        breakfast_role_constraints(
            diet[
                "breakfast"
            ]
        )
    )

    violations.extend(
        lunch_role_constraints(
            diet[
                "lunch"
            ]
        )
    )

    violations.extend(
        snack_role_constraints(
            diet[
                "snack"
            ]
        )
    )

    violations.extend(
        dinner_role_constraints(
            diet[
                "dinner"
            ]
        )
    )

    return violations


def evaluate_constraints(
    diet,
    nutrient_targets,
):

    constraints = []

    # --------------------------------------------------------
    # Nutrient constraints
    #
    # Energy:   lower + upper = 2
    # Protein:  lower + upper = 2
    # Carbs:    lower + upper = 2
    # Fat:      lower + upper = 2
    # Fibre:    lower only    = 1
    #
    # Total = 9
    # --------------------------------------------------------

    constraints.extend(
        nutrient_constraint_violations(
            diet,
            nutrient_targets,
        )
    )

    # --------------------------------------------------------
    # Duplicate-food constraints
    #
    # 1 per meal = 4
    # --------------------------------------------------------

    for meal_foods in (
        diet.values()
    ):

        constraints.append(
            duplicate_meal_constraint(
                meal_foods
            )
        )

    # --------------------------------------------------------
    # Active food-count constraints
    #
    # lower + upper for each meal
    # 2 × 4 = 8
    # --------------------------------------------------------

    for meal_name, meal_foods in (
        diet.items()
    ):

        constraints.extend(
            active_food_count_constraints(
                meal_name,
                meal_foods,
            )
        )

    # --------------------------------------------------------
    # Meal-role constraints
    #
    # Breakfast = 2
    # Lunch     = 3
    # Snack     = 2
    # Dinner    = 3
    #
    # Total = 10
    # --------------------------------------------------------

    constraints.extend(
        meal_role_constraints(
            diet
        )
    )

    return np.asarray(
        constraints,
        dtype=float,
    )


def constraint_count():

    # Nutrients        = 9
    # Duplicates       = 4
    # Food counts      = 8
    # Meal roles       = 12
    # ---------------------
    # Total            = 33

    return 33


def is_feasible(
    diet,
    nutrient_targets,
    tolerance=1e-12,
):

    constraints = (
        evaluate_constraints(
            diet,
            nutrient_targets,
        )
    )

    return bool(
        np.all(
            constraints
            <= tolerance
        )
    )