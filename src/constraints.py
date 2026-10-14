from src.diet_representation import (
    calculate_diet_totals,
)


# Acceptable nutrition ranges for the pilot.
#
# Values are expressed as proportions of the
# calculated target.

NUTRIENT_BOUNDS = {
    "energy_kcal": (
        0.90,
        1.10,
    ),

    "protein_g": (
        0.90,
        1.15,
    ),

    "carb_g": (
        0.80,
        1.20,
    ),

    "fat_g": (
        0.80,
        1.20,
    ),

    # Fibre only requires a minimum in this pilot.
    "fibre_g": (
        0.80,
        None,
    ),
}


def nutrient_constraint_violations(
    diet,
    nutrient_targets,
):
    """
    Calculate normalized constraint violations.

    pymoo expects constraints in the form:

        G <= 0

    Therefore:

        <= 0  -> feasible
        > 0   -> constraint violated
    """

    totals = calculate_diet_totals(
        diet
    )

    violations = []

    for nutrient, bounds in (
        NUTRIENT_BOUNDS.items()
    ):

        target = nutrient_targets[
            nutrient
        ]

        actual = totals[
            nutrient
        ]

        lower_fraction, upper_fraction = (
            bounds
        )

        lower_limit = (
            target
            * lower_fraction
        )

        # Lower-bound constraint
        #
        # feasible:
        # actual >= lower_limit
        #
        # violation:
        # lower_limit - actual > 0

        lower_violation = (
            lower_limit
            - actual
        ) / target

        violations.append(
            lower_violation
        )

        if upper_fraction is not None:

            upper_limit = (
                target
                * upper_fraction
            )

            # Upper-bound constraint
            #
            # feasible:
            # actual <= upper_limit
            #
            # violation:
            # actual - upper_limit > 0

            upper_violation = (
                actual
                - upper_limit
            ) / target

            violations.append(
                upper_violation
            )

    return violations


def duplicate_meal_constraint(diet):
    """
    Require all food slots within a meal to contain
    different foods.

    With 3 food slots:

        3 unique foods -> feasible
        2 unique foods -> violation
        1 unique food  -> larger violation

    Constraint rule:
        <= 0 -> feasible
        > 0  -> violated
    """

    violations = []

    for foods in diet.values():

        codes = [
            food["food_code"]
            for food in foods
        ]

        unique_count = len(
            set(codes)
        )

        violation = (
            3 - unique_count
        )

        violations.append(
            float(violation)
        )

    return violations


def evaluate_constraints(
    diet,
    nutrient_targets,
):
    """
    Return all hard-constraint values.

    Constraint rule:
        value <= 0 -> feasible
        value > 0  -> violated
    """

    constraints = []

    constraints.extend(
        nutrient_constraint_violations(
            diet,
            nutrient_targets,
        )
    )

    constraints.extend(
        duplicate_meal_constraint(
            diet
        )
    )

    return constraints


def is_feasible(
    diet,
    nutrient_targets,
):
    """
    Convenience function for checking whether a
    candidate diet satisfies every hard constraint.
    """

    constraints = evaluate_constraints(
        diet,
        nutrient_targets,
    )

    return all(
        value <= 0
        for value in constraints
    )