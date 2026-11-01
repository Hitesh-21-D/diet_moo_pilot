import time

from pymoo.algorithms.moo.spea2 import SPEA2, SPEA2Survival
from pymoo.optimize import minimize
from pymoo.termination import get_termination


def run_spea2(
    problem,
    population_size=100,
    generations=150,
    seed=42,
    verbose=True,
):
    """
    Run SPEA2 on the shared constrained diet problem.
    """

    algorithm = SPEA2(
        pop_size=population_size,
        # Flexible one-meal days have a constant distribution objective. The
        # bundled normalized survival divides by zero on constant objectives.
        # These four objectives are already dimensionless; raw-distance SPEA2
        # is used consistently for every flexible-v2 pattern.
        **({'survival': SPEA2Survival(normalize=False)} if hasattr(problem, 'formulation_version') else {}),
    )

    termination = get_termination(
        "n_gen",
        generations,
    )

    start_time = time.perf_counter()

    result = minimize(
        problem,
        algorithm,
        termination,
        seed=seed,
        save_history=False,
        verbose=verbose,
    )

    runtime = (
        time.perf_counter()
        - start_time
    )

    return result, runtime
