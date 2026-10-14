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


class MOEADDietProblem(ElementwiseProblem):
    """
    MOEA/D-compatible version of the diet problem.

    pymoo's MOEA/D implementation does not directly support
    inequality constraints.

    Therefore, the SAME constraints are evaluated and their
    positive violations are converted into an additive penalty
    applied to all four objectives.

    The underlying objectives and constraints themselves are
    unchanged.
    """

    def __init__(
        self,
        food_pools,
        nutrient_targets,
        existing_diet,
        penalty_factor=10.0,
    ):

        self.food_pools = food_pools
        self.nutrient_targets = nutrient_targets
        self.existing_diet = existing_diet
        self.penalty_factor = penalty_factor

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

                lower_bounds.append(0)
                upper_bounds.append(
                    pool_size - 1
                )

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

        super().__init__(
            n_var=n_var,
            n_obj=4,
            n_ieq_constr=0,
            xl=xl,
            xu=xu,
        )

    def decode(self, x):
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

        # Only positive values represent violations.
        positive_violations = [
            max(0.0, value)
            for value in constraints
        ]

        total_violation = sum(
            positive_violations
        )

        # Feasibility-first penalty strategy.
        #
        # Feasible candidate:
        #     keep original four objectives.
        #
        # Infeasible candidate:
        #     apply a large common penalty, with additional
        #     pressure proportional to total constraint violation.
        #
        # This ensures that once feasible diets are discovered,
        # they are strongly preferred over infeasible diets.

        if total_violation > 0:

            penalty = (
                100.0
                + (100.0 * total_violation)
            )

            penalized_objectives = (
                objectives + penalty
            )

        else:

            penalized_objectives = objectives


        out["F"] = penalized_objectives

        out["raw_objectives"] = objectives

        out["constraint_violation"] = (
            total_violation
        )

        # Save raw values for convenience/debugging.
        out["raw_objectives"] = objectives
        out["constraint_violation"] = (
            total_violation
        )