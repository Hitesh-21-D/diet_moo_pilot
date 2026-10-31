from config.user_profile import USER_PROFILE

from src.data_loader import load_indb
from src.food_pool import build_food_pools

from src.nutrient_targets import (
    calculate_nutrient_targets,
)

from src.moead_problem import (
    MOEADDietProblem,
)

from src.diet_representation import (
    calculate_diet_totals,
)

from src.algorithms.moead import (
    run_moead,
)

from src.objectives import (
    evaluate_objectives,
)

from src.constraints import (
    is_feasible,
)

def print_diet(
    problem,
    chromosome,
    objective_values,
    diet_number,
):
    diet = problem.decode(
        chromosome
    )

    totals = calculate_diet_totals(
        diet
    )

    print("\n" + "=" * 70)
    print(
        f"PARETO DIET {diet_number}"
    )
    print("=" * 70)

    for meal_name, foods in (
        diet.items()
    ):

        print(
            f"\n{meal_name.upper()}"
        )

        for food in foods:

            if (
                food[
                    "food_code"
                ]
                == "NONE"
            ):
                continue

            print(
                f"  - {food['food_name']} | "
                f"{food['servings']:.2f} "
                f"{food['serving_unit']}"
            )

    print("\nDAILY NUTRIENT TOTALS")

    for nutrient, value in (
        totals.items()
    ):

        print(
            f"{nutrient:<15}: "
            f"{value:.2f}"
        )

    print("\nOBJECTIVES")

    objective_names = [
        "Nutrition deviation",
        "Existing diet deviation",
        "Diversity penalty",
        "Meal distribution deviation",
    ]

    for name, value in zip(
        objective_names,
        objective_values,
    ):

        print(
            f"{name:<30}: "
            f"{value:.6f}"
        )

def diet_signature(diet):
    """
    Create a hashable representation of a decoded diet.

    Two chromosomes that decode to the exact same foods
    and serving quantities will have the same signature.
    """

    signature = []

    for meal_name, foods in diet.items():

        meal_signature = []

        for food in foods:

            meal_signature.append(
                (
                    food["food_code"],
                    round(
                        food["servings"],
                        2,
                    ),
                )
            )

        signature.append(
            (
                meal_name,
                tuple(meal_signature),
            )
        )

    return tuple(signature)

def main():

    print("\n" + "=" * 70)
    print("MOEA/D DIET OPTIMIZATION")
    print("=" * 70)

    df = load_indb()

    food_pools = build_food_pools(
        df
    )

    nutrient_targets = (
        calculate_nutrient_targets(
            USER_PROFILE
        )
    )

    print("\nNUTRIENT TARGETS")

    for nutrient, value in (
        nutrient_targets.items()
    ):

        print(
            f"{nutrient:<15}: "
            f"{value:.2f}"
        )

    problem = MOEADDietProblem(
        food_pools=food_pools,
        nutrient_targets=nutrient_targets,
        existing_diet=USER_PROFILE[
            "existing_diet"
        ],
        penalty_factor=10.0,
    )

    result, runtime = run_moead(
        problem=problem,
        generations=180,
        seed=42,
        verbose=True,
    )

    print("\n" + "=" * 70)
    print("MOEA/D COMPLETE")
    print("=" * 70)

    print(
        f"Runtime: {runtime:.2f} seconds"
    )

    if result.X is None:
        print(
            "\nNo feasible Pareto solutions "
            "were discovered."
        )
        return

    print(
        f"MOEA/D candidate Pareto solutions: "
        f"{len(result.X)}"
    )

    feasible_unique = []

    seen_signatures = set()


    for i in range(
        len(result.X)
    ):

        diet = problem.decode(
            result.X[i]
        )

        if not is_feasible(
            diet,
            nutrient_targets,
        ):
            continue

        signature = diet_signature(
            diet
        )

        # Skip duplicate decoded diets.
        if signature in seen_signatures:
            continue

        seen_signatures.add(
            signature
        )

        raw_objectives = evaluate_objectives(
            diet=diet,
            nutrient_targets=nutrient_targets,
            existing_diet=USER_PROFILE[
                "existing_diet"
            ],
        )

        feasible_unique.append(
            (
                result.X[i],
                raw_objectives,
                diet,
            )
        )


    print(
        f"Unique feasible decoded diets: "
        f"{len(feasible_unique)}"
    )


    if len(feasible_unique) == 0:

        print(
            "\nMOEA/D returned no unique "
            "feasible diets."
        )

        return


    number_to_display = min(
        3,
        len(feasible_unique),
    )


    for i in range(
        number_to_display
    ):

        chromosome = (
            feasible_unique[i][0]
        )

        objectives = (
            feasible_unique[i][1]
        )

        print_diet(
            problem=problem,
            chromosome=chromosome,
            objective_values=objectives,
            diet_number=i + 1,
        )


if __name__ == "__main__":
    main()