import numpy as np

from config.user_profile import USER_PROFILE

from src.data_loader import load_indb

from src.food_pool import build_food_pools

from src.nutrient_targets import (
    calculate_nutrient_targets,
)

from src.diet_representation import (
    decode_chromosome,
    calculate_diet_totals,
)

from src.objectives import (
    evaluate_objectives,
)

from src.constraints import (
    evaluate_constraints,
    is_feasible,
)

from src.problem import DietOptimizationProblem


def main():

    print("\n" + "=" * 60)
    print("TESTING DIET OPTIMIZATION PROBLEM")
    print("=" * 60)

    df = load_indb()

    food_pools = build_food_pools(df)

    nutrient_targets = (
        calculate_nutrient_targets(
            USER_PROFILE
        )
    )

    problem = DietOptimizationProblem(
        food_pools=food_pools,
        nutrient_targets=nutrient_targets,
        existing_diet=USER_PROFILE[
            "existing_diet"
        ],
    )

    print()
    print(
        f"Decision variables: "
        f"{problem.n_var}"
    )

    print(
        f"Objectives: "
        f"{problem.n_obj}"
    )

    print(
        f"Inequality constraints: "
        f"{problem.n_ieq_constr}"
    )

    print("\nLower bounds:")
    print(problem.xl)

    print("\nUpper bounds:")
    print(problem.xu)

    # Generate one random chromosome inside
    # the optimization bounds.

    rng = np.random.default_rng(
        seed=42
    )

    chromosome = rng.uniform(
        low=problem.xl,
        high=problem.xu,
    )

    print("\n" + "=" * 60)
    print("RANDOM TEST CHROMOSOME")
    print("=" * 60)

    print(chromosome)

    diet = decode_chromosome(
        chromosome,
        food_pools,
    )

    print("\n" + "=" * 60)
    print("DECODED DIET")
    print("=" * 60)

    for meal_name, foods in (
        diet.items()
    ):

        print(
            f"\n{meal_name.upper()}"
        )

        for food in foods:

            print(
                f"- {food['food_name']} | "
                f"{food['servings']:.2f} "
                f"{food['serving_unit']}"
            )

    totals = calculate_diet_totals(
        diet
    )

    print("\n" + "=" * 60)
    print("DAILY TOTALS")
    print("=" * 60)

    for nutrient, value in (
        totals.items()
    ):
        print(
            f"{nutrient:<15}: "
            f"{value:.2f}"
        )

    objectives = evaluate_objectives(
        diet=diet,
        nutrient_targets=nutrient_targets,
        existing_diet=USER_PROFILE[
            "existing_diet"
        ],
    )

    print("\n" + "=" * 60)
    print("OBJECTIVE VALUES")
    print("=" * 60)

    objective_names = [
        "Nutrition deviation",
        "Existing diet deviation",
        "Diversity penalty",
        "Meal distribution deviation",
    ]

    for name, value in zip(
        objective_names,
        objectives,
    ):
        print(
            f"{name:<30}: "
            f"{value:.6f}"
        )

    constraints = (
        evaluate_constraints(
            diet=diet,
            nutrient_targets=nutrient_targets,
        )
    )

    print("\n" + "=" * 60)
    print("CONSTRAINT VALUES")
    print("=" * 60)

    for i, value in enumerate(
        constraints,
        start=1,
    ):
        print(
            f"G{i:02d}: "
            f"{value:.6f}"
        )

    print()

    if is_feasible(
        diet,
        nutrient_targets,
    ):
        print(
            "Candidate status: FEASIBLE"
        )
    else:
        print(
            "Candidate status: INFEASIBLE"
        )


if __name__ == "__main__":
    main()