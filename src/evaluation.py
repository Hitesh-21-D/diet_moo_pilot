import numpy as np

from src.objectives import evaluate_objectives

from src.constraints import (
    is_feasible,
)


def diet_signature(diet):
    """
    Convert a decoded diet into a hashable representation.

    Two chromosomes are treated as the same practical diet
    when they contain the same foods and serving quantities,
    even if those foods appear in different chromosome slots.

    The optional NONE food is ignored.
    """

    signature = []

    for meal_name, foods in diet.items():

        meal_signature = []

        for food in foods:

            if (
                food["food_code"]
                == "NONE"
            ):
                continue

            meal_signature.append(
                (
                    food["food_code"],
                    round(
                        food["servings"],
                        2,
                    ),
                )
            )

        meal_signature.sort()

        signature.append(
            (
                meal_name,
                tuple(meal_signature),
            )
        )

    return tuple(signature)


def extract_unique_feasible_solutions(
    problem,
    chromosomes,
    nutrient_targets,
    existing_diet,
):
    """
    Convert an algorithm's solutions into a standardized
    feasible Pareto dataset.

    Important:
    All objective values are recomputed using our shared
    evaluate_objectives() function.

    This is especially important for MOEA/D because its
    internal F values contain constraint penalties.
    """

    unique_x = []
    unique_f = []
    unique_diets = []

    seen = set()

    if chromosomes is None:
        return (
            np.empty((0, problem.n_var)),
            np.empty((0, problem.n_obj)),
            [],
        )

    for chromosome in chromosomes:

        diet = problem.decode(
            chromosome
        )

        if not is_feasible(
            diet,
            nutrient_targets,
        ):
            continue

        signature = diet_signature(
            diet
        )

        if signature in seen:
            continue

        seen.add(
            signature
        )

        objectives = evaluate_objectives(
            diet=diet,
            nutrient_targets=nutrient_targets,
            existing_diet=existing_diet,
        )

        unique_x.append(
            np.asarray(
                chromosome,
                dtype=float,
            )
        )

        unique_f.append(
            objectives
        )

        unique_diets.append(
            diet
        )

    if len(unique_x) == 0:

        return (
            np.empty((0, problem.n_var)),
            np.empty((0, problem.n_obj)),
            [],
        )

    return (
        np.asarray(unique_x),
        np.asarray(unique_f),
        unique_diets,
    )


def calculate_feasibility_rate(
    problem,
    chromosomes,
    nutrient_targets,
):
    """
    Fraction of a final population/swarm satisfying all
    hard constraints in the current optimization problem.

    For the expanded pilot, this includes the revised
    nutrient, duplicate-food, active-food-count, and
    meal-role constraints.

    Returns a value between 0 and 1.
    """

    if chromosomes is None:
        return 0.0

    chromosomes = np.asarray(
        chromosomes
    )

    if len(chromosomes) == 0:
        return 0.0

    feasible_count = 0

    for chromosome in chromosomes:

        diet = problem.decode(
            chromosome
        )

        if is_feasible(
            diet,
            nutrient_targets,
        ):
            feasible_count += 1

    return (
        feasible_count
        / len(chromosomes)
    )


def intervention_count(
    diet,
    existing_diet,
):
    """
    Count practical dietary interventions relative to the
    user's existing diet.

    One intervention is counted when:

    1. A baseline food is removed.
    2. A new food is introduced.
    3. The quantity of a retained baseline food differs
    by at least 0.25 serving from the baseline.

    The 0.25 threshold is the intervention-count criterion;
    individual foods may use larger practical serving steps.

    The optional NONE food is ignored.

    This produces the T value used by PETQ.
    """

    interventions = 0

    for meal_name, generated_foods in diet.items():

        baseline_foods = existing_diet.get(
            meal_name,
            [],
        )

        baseline_map = {}

        for item in baseline_foods:

            code = item["food_code"]

            baseline_map[code] = (
                baseline_map.get(
                    code,
                    0.0,
                )
                + item["servings"]
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
                baseline_map.keys()
            )
            | set(
                generated_map.keys()
            )
        )

        for code in all_codes:

            baseline_amount = (
                baseline_map.get(
                    code,
                    0.0,
                )
            )

            generated_amount = (
                generated_map.get(
                    code,
                    0.0,
                )
            )

            # Newly introduced food
            if (
                baseline_amount == 0
                and generated_amount > 0
            ):
                interventions += 1

            # Removed baseline food
            elif (
                baseline_amount > 0
                and generated_amount == 0
            ):
                interventions += 1

            # Same food but meaningful serving change
            elif abs(
                baseline_amount
                - generated_amount
            ) >= 0.25:

                interventions += 1

    return interventions


def mean_intervention_count(
    diets,
    existing_diet,
):
    """
    Mean number of dietary interventions across an
    algorithm's feasible Pareto solutions.
    """

    if not diets:
        return 0.0

    counts = [
        intervention_count(
            diet,
            existing_diet,
        )
        for diet in diets
    ]

    return float(
        np.mean(
            counts
        )
    )