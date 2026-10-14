import time

from pymoo.algorithms.moo.spea2 import SPEA2
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