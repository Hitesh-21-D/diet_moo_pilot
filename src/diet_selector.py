import numpy as np


def select_nutrition_focused(F):
    """
    Diet with minimum nutritional deviation.

    Objective 0 = nutritional deviation.
    """

    return int(
        np.argmin(
            F[:, 0]
        )
    )


def select_habit_preserving(F):
    """
    Diet with minimum existing-diet deviation.

    Objective 1 = habit / dietary deviation.
    """

    return int(
        np.argmin(
            F[:, 1]
        )
    )


def select_balanced_compromise(F):
    """
    Select the solution closest to the ideal point
    after min-max normalization.

    All four objectives are treated equally.

    Lower normalized Euclidean distance is better.
    """

    ideal = np.min(
        F,
        axis=0,
    )

    nadir = np.max(
        F,
        axis=0,
    )

    denominator = (
        nadir - ideal
    )

    denominator = np.where(
        denominator < 1e-12,
        1.0,
        denominator,
    )

    normalized = (
        F - ideal
    ) / denominator

    distances = np.linalg.norm(
        normalized,
        axis=1,
    )

    return int(
        np.argmin(
            distances
        )
    )


def select_final_diets(
    X,
    F,
    diets,
):
    """
    Select three representative final outputs:

    1. Best Nutritional Match
    2. Minimum Dietary Change
    3. Balanced Compromise

    If two categories select the same solution,
    a different nearby solution is chosen when possible.
    """

    if len(F) == 0:
        return []

    selections = []

    nutrition_index = (
        select_nutrition_focused(F)
    )

    selections.append(
        {
            "label": "Best Nutritional Match",
            "index": nutrition_index,
        }
    )

    habit_index = (
        select_habit_preserving(F)
    )

    # Avoid duplicate final output where possible.
    if (
        habit_index == nutrition_index
        and len(F) > 1
    ):

        order = np.argsort(
            F[:, 1]
        )

        for index in order:

            if index != nutrition_index:
                habit_index = int(index)
                break

    selections.append(
        {
            "label": "Minimum Dietary Change",
            "index": habit_index,
        }
    )

    balanced_index = (
        select_balanced_compromise(F)
    )

    used = {
        item["index"]
        for item in selections
    }

    if (
        balanced_index in used
        and len(F) > len(used)
    ):

        ideal = np.min(
            F,
            axis=0,
        )

        nadir = np.max(
            F,
            axis=0,
        )

        denominator = (
            nadir - ideal
        )

        denominator = np.where(
            denominator < 1e-12,
            1.0,
            denominator,
        )

        normalized = (
            F - ideal
        ) / denominator

        distances = np.linalg.norm(
            normalized,
            axis=1,
        )

        order = np.argsort(
            distances
        )

        for index in order:

            if int(index) not in used:

                balanced_index = int(
                    index
                )

                break

    selections.append(
        {
            "label": "Balanced Compromise",
            "index": balanced_index,
        }
    )

    final = []

    for selection in selections:

        index = selection[
            "index"
        ]

        final.append(
            {
                "label": selection[
                    "label"
                ],
                "chromosome": X[index],
                "objectives": F[index],
                "diet": diets[index],
            }
        )

    return final