import numpy as np

from config.user_profile import USER_PROFILE

from src.data_loader import load_indb
from src.food_pool import build_food_pools
from src.nutrient_targets import calculate_nutrient_targets

from src.problem import DietOptimizationProblem
from src.moead_problem import MOEADDietProblem

from src.algorithms.nsga2 import run_nsga2
from src.algorithms.nsga3 import run_nsga3
from src.algorithms.moead import run_moead
from src.algorithms.spea2 import run_spea2
from src.algorithms.mopso import run_mopso

from src.evaluation import (
    extract_unique_feasible_solutions,
    calculate_feasibility_rate,
    mean_intervention_count,
)

from src.metrics import (
    build_empirical_reference_front,
    get_normalization_bounds,
    normalize_front,
    calculate_hypervolume,
    calculate_igd,
    calculate_spacing,
    calculate_petq,
)

from src.report import (
    save_metrics_csv,
    save_final_diets,
    print_selected_diets,
)

def get_final_population(result):
    """
    Extract the final population decision vectors from
    a pymoo result object when available.
    """

    if hasattr(result, "pop") and result.pop is not None:

        X = result.pop.get("X")

        if X is not None:
            return np.asarray(X)

    return None


def run_experiment():
    print("\n" + "=" * 80)
    print("PERSONALIZED DIET MOO PILOT - FIVE ALGORITHM COMPARISON")
    print("=" * 80)

    # ------------------------------------------------------------
    # Shared dataset and user inputs
    # ------------------------------------------------------------

    df = load_indb()

    food_pools = build_food_pools(df)

    nutrient_targets = calculate_nutrient_targets(
        USER_PROFILE
    )

    existing_diet = USER_PROFILE[
        "existing_diet"
    ]

    print("\nNUTRIENT TARGETS")

    for nutrient, value in nutrient_targets.items():
        print(
            f"{nutrient:<15}: "
            f"{value:.2f}"
        )

    # ------------------------------------------------------------
    # Standard constrained problem
    # ------------------------------------------------------------

    standard_problem = DietOptimizationProblem(
        food_pools=food_pools,
        nutrient_targets=nutrient_targets,
        existing_diet=existing_diet,
    )

    # ------------------------------------------------------------
    # MOEA/D compatibility problem
    # ------------------------------------------------------------

    moead_problem = MOEADDietProblem(
        food_pools=food_pools,
        nutrient_targets=nutrient_targets,
        existing_diet=existing_diet,
    )

    raw_results = {}
    runtimes = {}
    final_populations = {}

    # ============================================================
    # NSGA-II
    # ============================================================

    # print("\n" + "=" * 80)
    # print("RUNNING NSGA-II")
    # print("=" * 80)

    result, runtime = run_nsga2(
        problem=standard_problem,
        population_size=100,
        generations=150,
        seed=42,
        verbose=False,
    )

    raw_results["NSGA-II"] = result
    runtimes["NSGA-II"] = runtime
    final_populations["NSGA-II"] = (
        get_final_population(result)
    )

    # ============================================================
    # NSGA-III
    # ============================================================

    # print("\n" + "=" * 80)
    # print("RUNNING NSGA-III")
    # print("=" * 80)

    result, runtime = run_nsga3(
        problem=standard_problem,
        population_size=100,
        generations=150,
        seed=42,
        verbose=False,
    )

    raw_results["NSGA-III"] = result
    runtimes["NSGA-III"] = runtime
    final_populations["NSGA-III"] = (
        get_final_population(result)
    )

    # ============================================================
    # MOEA/D
    # ============================================================

    # print("\n" + "=" * 80)
    # print("RUNNING MOEA/D")
    # print("=" * 80)

    result, runtime = run_moead(
        problem=moead_problem,
        generations=180,
        seed=42,
        verbose=False,
    )

    raw_results["MOEA/D"] = result
    runtimes["MOEA/D"] = runtime
    final_populations["MOEA/D"] = (
        get_final_population(result)
    )

    # ============================================================
    # SPEA2
    # ============================================================

    # print("\n" + "=" * 80)
    # print("RUNNING SPEA2")
    # print("=" * 80)

    result, runtime = run_spea2(
        problem=standard_problem,
        population_size=100,
        generations=150,
        seed=42,
        verbose=False,
    )

    raw_results["SPEA2"] = result
    runtimes["SPEA2"] = runtime
    final_populations["SPEA2"] = (
        get_final_population(result)
    )

    # ============================================================
    # MOPSO
    # ============================================================

    # print("\n" + "=" * 80)
    # print("RUNNING MOPSO")
    # print("=" * 80)

    result, runtime = run_mopso(
        problem=standard_problem,
        swarm_size=100,
        iterations=150,
        archive_size=100,
        seed=42,
        verbose=False,
    )

    raw_results["MOPSO"] = result
    runtimes["MOPSO"] = runtime

    final_populations["MOPSO"] = (
        result.final_positions
    )

    # ============================================================
    # Standardize feasible outputs
    # ============================================================

    standardized = {}

    for algorithm_name, result in (
        raw_results.items()
    ):

        if algorithm_name == "MOEA/D":
            problem = moead_problem
        else:
            problem = standard_problem

        X, F, diets = (
            extract_unique_feasible_solutions(
                problem=problem,
                chromosomes=result.X,
                nutrient_targets=nutrient_targets,
                existing_diet=existing_diet,
            )
        )

        standardized[
            algorithm_name
        ] = {
            "X": X,
            "F": F,
            "diets": diets,
        }

        print(
            f"\n{algorithm_name:<10} | "
            f"Unique feasible Pareto diets: "
            f"{len(X)}"
        )

    # ============================================================
    # Empirical reference front
    # ============================================================

    fronts = {
        name: values["F"]
        for name, values
        in standardized.items()
    }

    reference_front = (
        build_empirical_reference_front(
            fronts
        )
    )

    ideal, nadir = (
        get_normalization_bounds(
            fronts
        )
    )

    normalized_reference = (
        normalize_front(
            reference_front,
            ideal,
            nadir,
        )
    )

    print(
        "\nEmpirical reference front size: "
        f"{len(reference_front)}"
    )

    # ============================================================
    # Calculate algorithm metrics
    # ============================================================

    metrics = {}

    for algorithm_name in (
        standardized.keys()
    ):

        values = standardized[
            algorithm_name
        ]

        F = values["F"]
        diets = values["diets"]

        if len(F) == 0:

            metrics[
                algorithm_name
            ] = {
                "HV": 0.0,
                "IGD": float("inf"),
                "Spacing": float("inf"),
                "Feasibility": 0.0,
                "MeanNutritionDeviation": float("inf"),
                "MeanHabitDeviation": float("inf"),
                "MeanDiversityPenalty": float("inf"),
                "MeanMealDeviation": float("inf"),
                "MeanInterventions": float("inf"),
                "Runtime": runtimes[
                    algorithm_name
                ],
                "PETQ": 0.0,
            }

            continue

        normalized_F = normalize_front(
            F,
            ideal,
            nadir,
        )

        hv = calculate_hypervolume(
            normalized_F
        )

        igd = calculate_igd(
            normalized_F,
            normalized_reference,
        )

        spacing = calculate_spacing(
            normalized_F
        )

        if algorithm_name == "MOEA/D":
            feasibility_problem = (
                moead_problem
            )
        else:
            feasibility_problem = (
                standard_problem
            )

        feasibility = (
            calculate_feasibility_rate(
                problem=feasibility_problem,
                chromosomes=final_populations[
                    algorithm_name
                ],
                nutrient_targets=nutrient_targets,
            )
        )

        mean_interventions = (
            mean_intervention_count(
                diets=diets,
                existing_diet=existing_diet,
            )
        )

        mean_f = np.mean(
            F,
            axis=0,
        )

        petq = calculate_petq(
            hv=hv,
            igd=igd,
            mean_interventions=(
                mean_interventions
            ),
        )

        metrics[
            algorithm_name
        ] = {
            "HV": hv,
            "IGD": igd,
            "Spacing": spacing,
            "Feasibility": feasibility,
            "MeanNutritionDeviation": (
                float(mean_f[0])
            ),
            "MeanHabitDeviation": (
                float(mean_f[1])
            ),
            "MeanDiversityPenalty": (
                float(mean_f[2])
            ),
            "MeanMealDeviation": (
                float(mean_f[3])
            ),
            "MeanInterventions": (
                mean_interventions
            ),
            "Runtime": runtimes[
                algorithm_name
            ],
            "PETQ": petq,
        }

    # ============================================================
    # Print comparison table
    # ============================================================

    print("\n" + "=" * 110)
    print("ALGORITHM COMPARISON")
    print("=" * 110)

    header = (
        f"{'Algorithm':<12}"
        f"{'HV':>10}"
        f"{'IGD':>10}"
        f"{'Spacing':>12}"
        f"{'Feas.%':>10}"
        f"{'Nut.Dev':>10}"
        f"{'Habit.Dev':>12}"
        f"{'Interv.':>10}"
        f"{'Runtime':>10}"
        f"{'PETQ':>14}"
    )

    print(header)
    print("-" * len(header))

    for name, m in metrics.items():

        print(
            f"{name:<12}"
            f"{m['HV']:>10.4f}"
            f"{m['IGD']:>10.4f}"
            f"{m['Spacing']:>12.4f}"
            f"{m['Feasibility'] * 100:>9.1f}%"
            f"{m['MeanNutritionDeviation']:>10.4f}"
            f"{m['MeanHabitDeviation']:>12.4f}"
            f"{m['MeanInterventions']:>10.2f}"
            f"{m['Runtime']:>10.2f}"
            f"{m['PETQ']:>14.4f}"
        )

    # ============================================================
    # Save final experiment outputs
    # ============================================================

    metrics_path = save_metrics_csv(
        metrics
    )

    (
        selected_diets,
        diets_path,
    ) = save_final_diets(
        standardized=standardized,
        existing_diet=existing_diet,
    )

    print_selected_diets(
        selected_by_algorithm=selected_diets,
        existing_diet=existing_diet,
    )

    print("\n" + "=" * 80)
    print("FILES SAVED")
    print("=" * 80)

    print(
        f"Metrics: {metrics_path}"
    )

    print(
        f"Final diets: {diets_path}"
    )

    return {
        "results": raw_results,
        "standardized": standardized,
        "metrics": metrics,
        "reference_front": reference_front,
        "ideal": ideal,
        "nadir": nadir,
        "nutrient_targets": nutrient_targets,
        "standard_problem": standard_problem,
        "moead_problem": moead_problem,
    }


if __name__ == "__main__":
    run_experiment()