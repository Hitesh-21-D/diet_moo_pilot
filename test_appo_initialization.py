
import numpy as np

from config.user_profile import USER_PROFILE

from src.data_loader import load_indb
from src.food_pool import build_food_pools
from src.nutrient_targets import calculate_nutrient_targets
from src.problem import DietOptimizationProblem

from src.algorithms.appo_config import (
    DEFAULT_APPO_CONFIG,
)
from src.algorithms.appo_initialization import (
    initialize_appo_population,
)

from src.constraints import (
    evaluate_constraints,
    is_feasible,
)

from src.evaluation import diet_signature


def print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def active_foods(meal):
    return [
        food
        for food in meal
        if food["food_code"] != "NONE"
        and food["servings"] > 0
    ]


def role_valid(diet):
    """
    Check the final 33-constraint meal-role
    structure independently of nutrient values.
    """

    for meal_name, foods in diet.items():

        active = active_foods(foods)

        if not 2 <= len(active) <= 3:
            return False

        codes = [
            food["food_code"]
            for food in active
        ]

        if len(codes) != len(set(codes)):
            return False

        roles = [
            food["role"]
            for food in active
        ]

        if meal_name == "breakfast":

            if roles.count("main") != 1:
                return False

        elif meal_name in ("lunch", "dinner"):

            if roles.count("staple") != 1:
                return False

            if roles.count("protein_curry") != 1:
                return False

        elif meal_name == "snack":

            if roles.count("snack_item") < 1:
                return False

            if roles.count("beverage") > 1:
                return False

    return True


def retained_food_count(
    diet,
    existing_diet,
):
    """Count retained baseline foods, meal by meal."""

    retained = 0

    for meal_name, original_foods in existing_diet.items():

        original_codes = {
            item["food_code"]
            for item in original_foods
        }

        generated_codes = {
            item["food_code"]
            for item in active_foods(
                diet[meal_name]
            )
        }

        retained += len(
            original_codes.intersection(
                generated_codes
            )
        )

    return retained


def main():

    print_section(
        "APPO INITIALIZATION VALIDATION"
    )

    df = load_indb()

    food_pools = build_food_pools(df)

    targets = calculate_nutrient_targets(
        USER_PROFILE
    )

    problem = DietOptimizationProblem(
        food_pools,
        targets,
        USER_PROFILE["existing_diet"],
    )

    config = DEFAULT_APPO_CONFIG

    rng = np.random.default_rng(
        config.seed
    )

    population = initialize_appo_population(
        problem=problem,
        existing_diet=USER_PROFILE["existing_diet"],
        config=config,
        rng=rng,
    )

    print_section("POPULATION SHAPE")

    print(
        "Population shape:",
        population.shape,
    )

    print(
        "Expected shape:",
        (
            config.population_size,
            problem.n_var,
        ),
    )

    assert population.shape == (
        config.population_size,
        problem.n_var,
    )

    assert np.all(
        population >= problem.xl - 1e-12
    ), "Lower chromosome bound violated."

    assert np.all(
        population <= problem.xu + 1e-12
    ), "Upper chromosome bound violated."

    print("Bounds validation: PASSED")

    print_section("MEAL STRUCTURE VALIDATION")

    structural_count = 0
    feasible_count = 0

    signatures = set()
    retained_counts = []

    decoded_diets = []

    for chromosome in population:

        diet = problem.decode(chromosome)

        decoded_diets.append(diet)

        signatures.add(
            diet_signature(diet)
        )

        if role_valid(diet):
            structural_count += 1

        if is_feasible(diet, targets):
            feasible_count += 1

        retained_counts.append(
            retained_food_count(
                diet,
                USER_PROFILE["existing_diet"],
            )
        )

    print(
        "Structurally valid:",
        structural_count,
        "/",
        config.population_size,
    )

    print(
        "Fully feasible:",
        feasible_count,
        "/",
        config.population_size,
    )

    print(
        "Unique decoded diets:",
        len(signatures),
    )

    assert structural_count == config.population_size, (
        "Some APPO initial diets violate meal structure."
    )

    print_section("HABIT RETENTION")

    habit_count = round(
        config.population_size
        * config.baseline_seed_fraction
    )

    habit_retention = retained_counts[
        :habit_count
    ]

    random_retention = retained_counts[
        habit_count:
    ]

    print(
        "Habit-guided population:",
        habit_count,
    )

    print(
        "Role-guided population:",
        config.population_size - habit_count,
    )

    print(
        "Mean retained baseline foods (habit-guided):",
        round(
            float(np.mean(habit_retention)),
            2,
        ),
    )

    print(
        "Mean retained baseline foods (role-guided):",
        round(
            float(np.mean(random_retention)),
            2,
        ),
    )

    print_section("FIRST HABIT-GUIDED DIET")

    example = decoded_diets[0]

    for meal_name, foods in example.items():

        print(
            "\n" + meal_name.upper()
        )

        for food in active_foods(foods):

            print(
                f"  - {food['food_name']} "
                f"| {food['servings']:.2f} "
                f"{food['serving_unit']}"
            )

    print_section("FINAL VALIDATION")

    print(
        "Decision variables:",
        problem.n_var,
    )

    print(
        "Objectives:",
        problem.n_obj,
    )

    print(
        "Constraints:",
        problem.n_ieq_constr,
    )

    assert problem.n_var == 24
    assert problem.n_obj == 4
    assert problem.n_ieq_constr == 33

    print("\nAPPO INITIALIZATION TEST PASSED")


if __name__ == "__main__":
    main()
