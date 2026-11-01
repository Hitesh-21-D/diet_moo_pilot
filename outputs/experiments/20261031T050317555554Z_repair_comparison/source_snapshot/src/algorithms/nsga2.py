import time

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.termination import get_termination


def run_nsga2(
    problem,
    population_size=100,
    generations=150,
    seed=42,
    verbose=True,
):
    """
    Run NSGA-II on the shared diet optimization problem.

    Parameters
    ----------
    problem:
        DietOptimizationProblem instance.

    population_size:
        Number of individuals in each generation.

    generations:
        Number of evolutionary generations.

    seed:
        Random seed for reproducibility.

    verbose:
        Whether pymoo should print optimization progress.

    Returns
    -------
    result:
        pymoo optimization result.

    runtime:
        Execution time in seconds.
    """

    algorithm = NSGA2(
        pop_size=population_size,
        eliminate_duplicates=True,
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