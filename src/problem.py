import numpy as np

from pymoo.core.problem import ElementwiseProblem

from src.diet_representation import (
    chromosome_length,
    decode_chromosome,
    MEAL_NAMES,
    FOOD_SLOTS_PER_MEAL,
    MIN_SERVINGS,
    MAX_SERVINGS,
)

from src.objectives import evaluate_objectives
from src.constraints import evaluate_constraints


class DietOptimizationProblem(ElementwiseProblem):
    """
    Shared multi-objective diet optimization problem.

    This exact problem definition will be used by:
    - NSGA-II
    - NSGA-III
    - MOEA/D
    - SPEA2

    MOPSO will use the same decision representation,
    objectives and constraints through a compatible wrapper.
    """

    def __init__(
        self,
        food_pools,
        nutrient_targets,
        existing_diet,
    ):

        self.food_pools = food_pools
        self.nutrient_targets = nutrient_targets
        self.existing_diet = existing_diet

        n_var = chromosome_length()

        lower_bounds = []
        upper_bounds = []

        for meal_name in MEAL_NAMES:

            pool_size = len(
                food_pools[meal_name]
            )

            if pool_size == 0:
                raise ValueError(
                    f"Food pool for {meal_name} is empty."
                )

            for _ in range(
                FOOD_SLOTS_PER_MEAL
            ):
                # Food index variable
                lower_bounds.append(0)
                upper_bounds.append(
                    pool_size - 1
                )

                # Serving variable
                lower_bounds.append(
                    MIN_SERVINGS
                )
                upper_bounds.append(
                    MAX_SERVINGS
                )

        xl = np.array(
            lower_bounds,
            dtype=float,
        )

        xu = np.array(
            upper_bounds,
            dtype=float,
        )

        # Nutrition constraints:
        #
        # Energy:
        #   lower + upper = 2
        #
        # Protein:
        #   lower + upper = 2
        #
        # Carbs:
        #   lower + upper = 2
        #
        # Fat:
        #   lower + upper = 2
        #
        # Fibre:
        #   lower only = 1
        #
        # Total nutrient constraints = 9
        #
        # Duplicate constraints:
        #   1 per meal = 4
        #
        # Total = 13
        n_ieq_constr = 13

        super().__init__(
            n_var=n_var,
            n_obj=4,
            n_ieq_constr=n_ieq_constr,
            xl=xl,
            xu=xu,
        )

    def decode(self, x):
        """
        Convert optimization vector into a diet.
        """

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
        """
        Evaluate one optimization candidate.
        """

        diet = self.decode(x)

        objectives = evaluate_objectives(
            diet=diet,
            nutrient_targets=self.nutrient_targets,
            existing_diet=self.existing_diet,
        )

        constraints = evaluate_constraints(
            diet=diet,
            nutrient_targets=self.nutrient_targets,
        )

        out["F"] = objectives
        out["G"] = np.array(
            constraints,
            dtype=float,
        )