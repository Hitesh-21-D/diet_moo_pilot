import numpy as np

from pymoo.core.problem import (
    ElementwiseProblem,
)

from src.diet_representation import (
    chromosome_length,
    decode_chromosome,
    MEAL_NAMES,
    FOOD_SLOTS_PER_MEAL,
    RAW_SERVING_MIN,
    RAW_SERVING_MAX,
)

from src.objectives import (
    evaluate_objectives,
)

from src.constraints import (
    evaluate_constraints,
)


class MOEADDietProblem(
    ElementwiseProblem
):

    def __init__(
        self,
        food_pools,
        nutrient_targets,
        existing_diet,
    ):

        self.food_pools = (
            food_pools
        )

        self.nutrient_targets = (
            nutrient_targets
        )

        self.existing_diet = (
            existing_diet
        )

        n_var = (
            chromosome_length()
        )

        lower_bounds = []
        upper_bounds = []

        for meal_name in MEAL_NAMES:

            pool_size = len(
                food_pools[
                    meal_name
                ]
            )

            for _ in range(
                FOOD_SLOTS_PER_MEAL
            ):

                lower_bounds.append(
                    0.0
                )

                upper_bounds.append(
                    float(
                        pool_size - 1
                    )
                )

                lower_bounds.append(
                    RAW_SERVING_MIN
                )

                upper_bounds.append(
                    RAW_SERVING_MAX
                )

        xl = np.asarray(
            lower_bounds,
            dtype=float,
        )

        xu = np.asarray(
            upper_bounds,
            dtype=float,
        )

        # pymoo MOEA/D does not support explicit
        # constrained Problem objects.
        #
        # Therefore n_ieq_constr remains zero.
        super().__init__(
            n_var=n_var,
            n_obj=4,
            n_ieq_constr=0,
            xl=xl,
            xu=xu,
        )

    def decode(
        self,
        x,
    ):

        return decode_chromosome(
            x,
            self.food_pools,
        )

    def _evaluate(
        self,
        x,
        out,
        *args,
        **kwargs,
    ):

        diet = self.decode(
            x
        )

        raw_objectives = (
            evaluate_objectives(
                diet=diet,
                nutrient_targets=(
                    self.nutrient_targets
                ),
                existing_diet=(
                    self.existing_diet
                ),
            )
        )

        constraints = (
            evaluate_constraints(
                diet=diet,
                nutrient_targets=(
                    self.nutrient_targets
                ),
            )
        )

        positive_violations = (
            np.maximum(
                constraints,
                0.0,
            )
        )

        total_violation = float(
            np.sum(
                positive_violations
            )
        )

        if total_violation > 0:

            penalty = (
                100.0
                + (
                    100.0
                    * total_violation
                )
            )

            penalized = (
                raw_objectives
                + penalty
            )

        else:

            penalized = (
                raw_objectives
            )

        out["F"] = penalized

        out[
            "raw_objectives"
        ] = raw_objectives

        out[
            "constraint_violation"
        ] = total_violation