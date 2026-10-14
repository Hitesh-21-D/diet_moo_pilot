from pathlib import Path

import pandas as pd

from src.diet_representation import (
    calculate_diet_totals,
)

from src.evaluation import (
    intervention_count,
)

from src.diet_selector import (
    select_final_diets,
)


OBJECTIVE_NAMES = [
    "nutrition_deviation",
    "habit_deviation",
    "diversity_penalty",
    "meal_distribution_deviation",
]


def get_output_root():
    return (
        Path(__file__)
        .resolve()
        .parent
        .parent
        / "outputs"
    )


def ensure_output_folders():

    root = get_output_root()

    diets_folder = (
        root / "diets"
    )

    metrics_folder = (
        root / "metrics"
    )

    diets_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    metrics_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        root,
        diets_folder,
        metrics_folder,
    )


def save_metrics_csv(metrics):

    _, _, metrics_folder = (
        ensure_output_folders()
    )

    rows = []

    for algorithm, values in (
        metrics.items()
    ):

        row = {
            "algorithm": algorithm,
        }

        row.update(values)

        rows.append(row)

    df = pd.DataFrame(
        rows
    )

    file_path = (
        metrics_folder
        / "algorithm_comparison.csv"
    )

    df.to_csv(
        file_path,
        index=False,
    )

    return file_path


def create_diet_rows(
    algorithm_name,
    selected_diets,
    existing_diet,
):
    """
    Convert selected diets into tabular rows.
    """

    rows = []

    for selection in (
        selected_diets
    ):

        label = selection[
            "label"
        ]

        diet = selection[
            "diet"
        ]

        objectives = selection[
            "objectives"
        ]

        totals = (
            calculate_diet_totals(
                diet
            )
        )

        interventions = (
            intervention_count(
                diet,
                existing_diet,
            )
        )

        for meal_name, foods in (
            diet.items()
        ):

            for food in foods:

                row = {
                    "algorithm": (
                        algorithm_name
                    ),

                    "diet_type": label,

                    "meal": meal_name,

                    "food_code": (
                        food[
                            "food_code"
                        ]
                    ),

                    "food_name": (
                        food[
                            "food_name"
                        ]
                    ),

                    "servings": (
                        food[
                            "servings"
                        ]
                    ),

                    "serving_unit": (
                        food[
                            "serving_unit"
                        ]
                    ),

                    "food_energy_kcal": (
                        food[
                            "energy_kcal"
                        ]
                    ),

                    "food_protein_g": (
                        food[
                            "protein_g"
                        ]
                    ),

                    "food_carb_g": (
                        food[
                            "carb_g"
                        ]
                    ),

                    "food_fat_g": (
                        food[
                            "fat_g"
                        ]
                    ),

                    "food_fibre_g": (
                        food[
                            "fibre_g"
                        ]
                    ),

                    "daily_energy_kcal": (
                        totals[
                            "energy_kcal"
                        ]
                    ),

                    "daily_protein_g": (
                        totals[
                            "protein_g"
                        ]
                    ),

                    "daily_carb_g": (
                        totals[
                            "carb_g"
                        ]
                    ),

                    "daily_fat_g": (
                        totals[
                            "fat_g"
                        ]
                    ),

                    "daily_fibre_g": (
                        totals[
                            "fibre_g"
                        ]
                    ),

                    "nutrition_deviation": (
                        objectives[0]
                    ),

                    "habit_deviation": (
                        objectives[1]
                    ),

                    "diversity_penalty": (
                        objectives[2]
                    ),

                    "meal_distribution_deviation": (
                        objectives[3]
                    ),

                    "intervention_count": (
                        interventions
                    ),
                }

                rows.append(
                    row
                )

    return rows


def save_final_diets(
    standardized,
    existing_diet,
):
    """
    Select and save the three official diet outputs
    for every algorithm.
    """

    _, diets_folder, _ = (
        ensure_output_folders()
    )

    all_rows = []

    selected_by_algorithm = {}

    for algorithm_name, values in (
        standardized.items()
    ):

        X = values["X"]
        F = values["F"]
        diets = values[
            "diets"
        ]

        selected = (
            select_final_diets(
                X=X,
                F=F,
                diets=diets,
            )
        )

        selected_by_algorithm[
            algorithm_name
        ] = selected

        rows = create_diet_rows(
            algorithm_name=algorithm_name,
            selected_diets=selected,
            existing_diet=existing_diet,
        )

        all_rows.extend(
            rows
        )

        safe_name = (
            algorithm_name
            .lower()
            .replace("/", "_")
            .replace("-", "_")
        )

        algorithm_df = (
            pd.DataFrame(
                rows
            )
        )

        algorithm_df.to_csv(
            diets_folder
            / f"{safe_name}_final_diets.csv",
            index=False,
        )

    combined_df = pd.DataFrame(
        all_rows
    )

    combined_path = (
        diets_folder
        / "all_final_diets.csv"
    )

    combined_df.to_csv(
        combined_path,
        index=False,
    )

    return (
        selected_by_algorithm,
        combined_path,
    )


def print_selected_diets(
    selected_by_algorithm,
    existing_diet,
):

    for (
        algorithm_name,
        selections
    ) in selected_by_algorithm.items():

        print(
            "\n"
            + "=" * 90
        )

        print(
            f"{algorithm_name} "
            f"- FINAL DIET OUTPUTS"
        )

        print(
            "=" * 90
        )

        for selection in selections:

            print(
                "\n"
                + "-" * 80
            )

            print(
                selection["label"]
            )

            print(
                "-" * 80
            )

            diet = selection[
                "diet"
            ]

            for meal_name, foods in (
                diet.items()
            ):

                print(
                    f"\n"
                    f"{meal_name.upper()}"
                )

                for food in foods:

                    print(
                        f"  - "
                        f"{food['food_name']} | "
                        f"{food['servings']:.2f} "
                        f"{food['serving_unit']}"
                    )

            totals = (
                calculate_diet_totals(
                    diet
                )
            )

            print(
                "\nDAILY NUTRITION"
            )

            for nutrient, value in (
                totals.items()
            ):

                print(
                    f"{nutrient:<15}: "
                    f"{value:.2f}"
                )

            objectives = selection[
                "objectives"
            ]

            print(
                "\nOBJECTIVES"
            )

            for name, value in zip(
                OBJECTIVE_NAMES,
                objectives,
            ):

                print(
                    f"{name:<30}: "
                    f"{value:.6f}"
                )

            interventions = (
                intervention_count(
                    diet,
                    existing_diet,
                )
            )

            print(
                f"\nInterventions: "
                f"{interventions}"
            )