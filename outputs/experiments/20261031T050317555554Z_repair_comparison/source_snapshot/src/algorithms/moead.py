import time

from pymoo.algorithms.moo.moead import MOEAD
from pymoo.optimize import minimize
from pymoo.termination import get_termination
from pymoo.util.ref_dirs import get_reference_directions


def run_moead(
    problem,
    generations=150,
    seed=42,
    verbose=True,
):
    """
    Run MOEA/D on the shared diet optimization problem.

    MOEA/D decomposes the multi-objective problem into
    multiple scalar subproblems using reference directions.
    """

    ref_dirs = get_reference_directions(
        "das-dennis",
        problem.n_obj,
        n_partitions=6,
    )

    algorithm = MOEAD(
        ref_dirs=ref_dirs,
        n_neighbors=20,
        prob_neighbor_mating=0.7,
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