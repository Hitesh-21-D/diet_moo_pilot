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

from src.algorithms.nsga2 import (
    run_nsga2,
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


def main():

    print("\n" + "=" * 70)
    print("NSGA-II DIET OPTIMIZATION")
    print("=" * 70)

    # ------------------------------------------------
    # Load data
    # ------------------------------------------------

    df = load_indb()

    food_pools = build_food_pools(
        df
    )

    # ------------------------------------------------
    # Calculate user nutrition targets
    # ------------------------------------------------

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

    # ------------------------------------------------
    # Create shared optimization problem
    # ------------------------------------------------

    problem = DietOptimizationProblem(
        food_pools=food_pools,
        nutrient_targets=nutrient_targets,
        existing_diet=USER_PROFILE[
            "existing_diet"
        ],
    )

    # ------------------------------------------------
    # Run NSGA-II
    # ------------------------------------------------

    result, runtime = run_nsga2(
        problem=problem,
        population_size=100,
        generations=150,
        seed=42,
        verbose=True,
    )

    print("\n" + "=" * 70)
    print("NSGA-II COMPLETE")
    print("=" * 70)

    print(
        f"Runtime: {runtime:.2f} seconds"
    )

    # ------------------------------------------------
    # Validate result
    # ------------------------------------------------

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

    # ------------------------------------------------
    # Display first few solutions
    #
    # This is temporary.
    # Later we will deliberately choose:
    #
    # 1. Nutrition-focused
    # 2. Minimum-intervention
    # 3. Balanced compromise
    # ------------------------------------------------

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