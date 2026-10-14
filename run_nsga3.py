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

from src.algorithms.nsga3 import (
    run_nsga3,
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


def main():

    print("\n" + "=" * 70)
    print("NSGA-III DIET OPTIMIZATION")
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

    result, runtime = run_nsga3(
        problem=problem,
        population_size=100,
        generations=150,
        seed=42,
        verbose=True,
    )

    print("\n" + "=" * 70)
    print("NSGA-III COMPLETE")
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
        f"Pareto solutions found: "
        f"{len(result.X)}"
    )

    number_to_display = min(
        3,
        len(result.X),
    )

    for i in range(
        number_to_display
    ):

        print_diet(
            problem=problem,
            chromosome=result.X[i],
            objective_values=result.F[i],
            diet_number=i + 1,
        )


if __name__ == "__main__":
    main()