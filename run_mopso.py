from config.user_profile import USER_PROFILE

from src.data_loader import load_indb
from src.food_pool import build_food_pools

from src.nutrient_targets import (
    calculate_nutrient_targets,
)

from src.problem import (
    DietOptimizationProblem,
)

from src.diet_representation import (
    calculate_diet_totals,
)

from src.algorithms.mopso import (
    run_mopso,
)


def diet_signature(diet):

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

    for meal_name, foods in diet.items():

        print(
            f"\n{meal_name.upper()}"
        )

        for food in foods:

            print(
                f"  - "
                f"{food['food_name']} | "
                f"{food['servings']:.2f} "
                f"{food['serving_unit']}"
            )

    print("\nDAILY NUTRIENT TOTALS")

    for nutrient, value in totals.items():

        print(
            f"{nutrient:<15}: "
            f"{value:.2f}"
        )

    print("\nOBJECTIVES")

    names = [
        "Nutrition deviation",
        "Existing diet deviation",
        "Diversity penalty",
        "Meal distribution deviation",
    ]

    for name, value in zip(
        names,
        objective_values,
    ):

        print(
            f"{name:<30}: "
            f"{value:.6f}"
        )


def main():

    print("\n" + "=" * 70)
    print("MOPSO DIET OPTIMIZATION")
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

    problem = DietOptimizationProblem(
        food_pools=food_pools,
        nutrient_targets=nutrient_targets,
        existing_diet=USER_PROFILE[
            "existing_diet"
        ],
    )

    result, runtime = run_mopso(
        problem=problem,
        swarm_size=100,
        iterations=150,
        archive_size=100,
        seed=42,
        verbose=True,
    )

    print("\n" + "=" * 70)
    print("MOPSO COMPLETE")
    print("=" * 70)

    print(
        f"Runtime: "
        f"{runtime:.2f} seconds"
    )

    print(
        f"Function evaluations: "
        f"{result.evaluations}"
    )

    if (
        result.X is None
        or len(result.X) == 0
    ):

        print(
            "No feasible Pareto solutions "
            "were discovered."
        )

        return

    print(
        f"Pareto archive size: "
        f"{len(result.X)}"
    )

    # Remove solutions that become duplicates
    # after practical serving-size decoding.

    unique = []

    seen = set()

    for chromosome, objectives in zip(
        result.X,
        result.F,
    ):

        diet = problem.decode(
            chromosome
        )

        signature = diet_signature(
            diet
        )

        if signature in seen:
            continue

        seen.add(
            signature
        )

        unique.append(
            (
                chromosome,
                objectives,
            )
        )

    print(
        f"Unique feasible decoded diets: "
        f"{len(unique)}"
    )

    number_to_display = min(
        3,
        len(unique),
    )

    for i in range(
        number_to_display
    ):

        chromosome, objectives = (
            unique[i]
        )

        print_diet(
            problem=problem,
            chromosome=chromosome,
            objective_values=objectives,
            diet_number=i + 1,
        )


if __name__ == "__main__":
    main()