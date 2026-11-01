import time

from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.optimize import minimize
from pymoo.termination import get_termination
from pymoo.util.ref_dirs import get_reference_directions


def run_nsga3(
    problem,
    population_size=100,
    generations=150,
    seed=42,
    verbose=True,
):
    """
    Run NSGA-III on the shared diet optimization problem.

    The problem has 4 objectives, so NSGA-III requires
    4-dimensional reference directions.
    """

    ref_dirs = get_reference_directions(
        "das-dennis",
        problem.n_obj,
        n_partitions=4,
    )

    algorithm = NSGA3(
        pop_size=population_size,
        ref_dirs=ref_dirs,
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