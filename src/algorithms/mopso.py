import time
from dataclasses import dataclass

import numpy as np

from src.objectives import evaluate_objectives
from src.constraints import evaluate_constraints


@dataclass
class MOPSOResult:
    X: np.ndarray
    F: np.ndarray
    evaluations: int
    final_positions: np.ndarray


def dominates(a, b):
    """
    Pareto dominance for minimization.

    a dominates b when:
    - a is no worse in every objective
    - a is strictly better in at least one objective
    """
    return (
        np.all(a <= b)
        and np.any(a < b)
    )


def total_constraint_violation(
    diet,
    nutrient_targets,
):
    """
    Sum only positive constraint violations.
    """

    constraints = evaluate_constraints(
        diet=diet,
        nutrient_targets=nutrient_targets,
    )

    return float(
        sum(
            max(0.0, value)
            for value in constraints
        )
    )


def constraint_dominates(
    f_a,
    cv_a,
    f_b,
    cv_b,
):
    """
    Deb-style feasibility-first comparison.

    1. Feasible beats infeasible.
    2. Between infeasible solutions, lower CV wins.
    3. Between feasible solutions, Pareto dominance applies.
    """

    a_feasible = cv_a <= 1e-12
    b_feasible = cv_b <= 1e-12

    if a_feasible and not b_feasible:
        return True

    if b_feasible and not a_feasible:
        return False

    if not a_feasible and not b_feasible:
        return cv_a < cv_b

    return dominates(
        f_a,
        f_b,
    )


def crowding_distance(F):
    """
    Calculate NSGA-II-style crowding distance.

    Used only for archive diversity and leader selection.
    """

    n = len(F)

    if n == 0:
        return np.array([])

    if n <= 2:
        return np.full(
            n,
            np.inf,
        )

    distances = np.zeros(n)

    n_obj = F.shape[1]

    for j in range(n_obj):

        order = np.argsort(
            F[:, j]
        )

        distances[order[0]] = np.inf
        distances[order[-1]] = np.inf

        f_min = F[order[0], j]
        f_max = F[order[-1], j]

        denominator = (
            f_max - f_min
        )

        if denominator <= 1e-12:
            continue

        for k in range(
            1,
            n - 1,
        ):

            previous_value = (
                F[
                    order[k - 1],
                    j,
                ]
            )

            next_value = (
                F[
                    order[k + 1],
                    j,
                ]
            )

            distances[
                order[k]
            ] += (
                next_value
                - previous_value
            ) / denominator

    return distances


def remove_duplicate_vectors(
    X,
    F,
    decimals=8,
):
    """
    Remove duplicate decision vectors.
    """

    if len(X) == 0:
        return X, F

    seen = set()

    unique_x = []
    unique_f = []

    for x, f in zip(
        X,
        F,
    ):

        key = tuple(
            np.round(
                x,
                decimals=decimals,
            )
        )

        if key in seen:
            continue

        seen.add(key)

        unique_x.append(x)
        unique_f.append(f)

    return (
        np.asarray(unique_x),
        np.asarray(unique_f),
    )


def non_dominated_indices(F):
    """
    Return indices belonging to the non-dominated set.
    """

    n = len(F)

    keep = []

    for i in range(n):

        dominated = False

        for j in range(n):

            if i == j:
                continue

            if dominates(
                F[j],
                F[i],
            ):
                dominated = True
                break

        if not dominated:
            keep.append(i)

    return np.array(
        keep,
        dtype=int,
    )


def update_archive(
    archive_x,
    archive_f,
    candidate_x,
    candidate_f,
    archive_size,
):
    """
    Add feasible candidates to the external archive,
    retain non-dominated solutions, and truncate using
    crowding distance.
    """

    if len(candidate_x) == 0:
        return (
            archive_x,
            archive_f,
        )

    if len(archive_x) == 0:

        combined_x = (
            candidate_x.copy()
        )

        combined_f = (
            candidate_f.copy()
        )

    else:

        combined_x = np.vstack(
            [
                archive_x,
                candidate_x,
            ]
        )

        combined_f = np.vstack(
            [
                archive_f,
                candidate_f,
            ]
        )

    combined_x, combined_f = (
        remove_duplicate_vectors(
            combined_x,
            combined_f,
        )
    )

    nd_indices = (
        non_dominated_indices(
            combined_f
        )
    )

    archive_x = (
        combined_x[
            nd_indices
        ]
    )

    archive_f = (
        combined_f[
            nd_indices
        ]
    )

    # Archive truncation
    if len(archive_x) > archive_size:

        distances = crowding_distance(
            archive_f
        )

        order = np.argsort(
            -distances
        )

        order = order[
            :archive_size
        ]

        archive_x = (
            archive_x[
                order
            ]
        )

        archive_f = (
            archive_f[
                order
            ]
        )

    return (
        archive_x,
        archive_f,
    )


def choose_leader(
    archive_x,
    archive_f,
    fallback_positions,
    fallback_cv,
    rng,
):
    """
    Choose a leader.

    Prefer less crowded regions of the Pareto archive.

    If the archive is still empty, use the particle
    with the lowest total constraint violation.
    """

    if len(archive_x) == 0:

        best_index = int(
            np.argmin(
                fallback_cv
            )
        )

        return (
            fallback_positions[
                best_index
            ]
        )

    distances = crowding_distance(
        archive_f
    )

    finite = np.isfinite(
        distances
    )

    if np.any(finite):

        finite_values = (
            distances[
                finite
            ]
        )

        replacement = (
            np.max(finite_values)
            + 1.0
        )

    else:

        replacement = 1.0

    weights = np.where(
        np.isfinite(distances),
        distances + 1e-6,
        replacement,
    )

    weight_sum = np.sum(
        weights
    )

    if weight_sum <= 0:

        index = rng.integers(
            0,
            len(archive_x),
        )

    else:

        probabilities = (
            weights
            / weight_sum
        )

        index = rng.choice(
            len(archive_x),
            p=probabilities,
        )

    return archive_x[index]


def evaluate_population(
    problem,
    positions,
):
    """
    Evaluate objectives and constraints for all particles.
    """

    objective_values = []
    constraint_values = []
    feasible_x = []
    feasible_f = []

    for x in positions:

        diet = problem.decode(x)

        f = evaluate_objectives(
            diet=diet,
            nutrient_targets=(
                problem.nutrient_targets
            ),
            existing_diet=(
                problem.existing_diet
            ),
        )

        cv = total_constraint_violation(
            diet=diet,
            nutrient_targets=(
                problem.nutrient_targets
            ),
        )

        objective_values.append(f)
        constraint_values.append(cv)

        if cv <= 1e-12:

            feasible_x.append(
                x.copy()
            )

            feasible_f.append(
                f.copy()
            )

    objective_values = np.asarray(
        objective_values
    )

    constraint_values = np.asarray(
        constraint_values
    )

    if feasible_x:

        feasible_x = np.asarray(
            feasible_x
        )

        feasible_f = np.asarray(
            feasible_f
        )

    else:

        feasible_x = np.empty(
            (
                0,
                positions.shape[1],
            )
        )

        feasible_f = np.empty(
            (
                0,
                4,
            )
        )

    return (
        objective_values,
        constraint_values,
        feasible_x,
        feasible_f,
    )


def run_mopso(
    problem,
    swarm_size=100,
    iterations=150,
    archive_size=100,
    seed=42,
    verbose=True,
):
    """
    Multi-Objective Particle Swarm Optimization.

    Evaluation budget:

        initial population = 100
        150 iterations x 100 particles = 15,000

        total = 15,100 evaluations

    This is approximately equal to the evaluation budget
    used by NSGA-II, NSGA-III and SPEA2.
    """

    rng = np.random.default_rng(
        seed
    )

    n_var = problem.n_var

    xl = np.asarray(
        problem.xl,
        dtype=float,
    )

    xu = np.asarray(
        problem.xu,
        dtype=float,
    )

    variable_range = (
        xu - xl
    )

    # --------------------------------------------
    # Initialize swarm
    # --------------------------------------------

    positions = rng.uniform(
        low=xl,
        high=xu,
        size=(
            swarm_size,
            n_var,
        ),
    )

    velocities = rng.uniform(
        low=(
            -0.1
            * variable_range
        ),
        high=(
            0.1
            * variable_range
        ),
        size=(
            swarm_size,
            n_var,
        ),
    )

    (
        F,
        CV,
        feasible_x,
        feasible_f,
    ) = evaluate_population(
        problem,
        positions,
    )

    evaluations = swarm_size

    # Personal bests
    pbest_x = (
        positions.copy()
    )

    pbest_f = (
        F.copy()
    )

    pbest_cv = (
        CV.copy()
    )

    # External Pareto archive
    archive_x = np.empty(
        (
            0,
            n_var,
        )
    )

    archive_f = np.empty(
        (
            0,
            problem.n_obj,
        )
    )

    archive_x, archive_f = (
        update_archive(
            archive_x,
            archive_f,
            feasible_x,
            feasible_f,
            archive_size,
        )
    )

    # PSO coefficients
    c1 = 1.5
    c2 = 1.5

    inertia_start = 0.9
    inertia_end = 0.4

    velocity_limit = (
        0.20
        * variable_range
    )

    start_time = time.perf_counter()

    # --------------------------------------------
    # Optimization loop
    # --------------------------------------------

    for iteration in range(
        1,
        iterations + 1,
    ):

        fraction = (
            iteration
            / iterations
        )

        inertia = (
            inertia_start
            - (
                inertia_start
                - inertia_end
            )
            * fraction
        )

        for i in range(
            swarm_size
        ):

            leader = choose_leader(
                archive_x=archive_x,
                archive_f=archive_f,
                fallback_positions=positions,
                fallback_cv=CV,
                rng=rng,
            )

            r1 = rng.random(
                n_var
            )

            r2 = rng.random(
                n_var
            )

            velocities[i] = (
                inertia
                * velocities[i]
                + c1
                * r1
                * (
                    pbest_x[i]
                    - positions[i]
                )
                + c2
                * r2
                * (
                    leader
                    - positions[i]
                )
            )

            velocities[i] = np.clip(
                velocities[i],
                -velocity_limit,
                velocity_limit,
            )

            positions[i] = (
                positions[i]
                + velocities[i]
            )

            positions[i] = np.clip(
                positions[i],
                xl,
                xu,
            )

        (
            F,
            CV,
            feasible_x,
            feasible_f,
        ) = evaluate_population(
            problem,
            positions,
        )

        evaluations += swarm_size

        # ----------------------------------------
        # Update personal bests
        # ----------------------------------------

        for i in range(
            swarm_size
        ):

            current_better = (
                constraint_dominates(
                    F[i],
                    CV[i],
                    pbest_f[i],
                    pbest_cv[i],
                )
            )

            previous_better = (
                constraint_dominates(
                    pbest_f[i],
                    pbest_cv[i],
                    F[i],
                    CV[i],
                )
            )

            if current_better:

                pbest_x[i] = (
                    positions[i].copy()
                )

                pbest_f[i] = (
                    F[i].copy()
                )

                pbest_cv[i] = (
                    CV[i]
                )

            elif not previous_better:

                # Both are mutually non-dominated.
                # Random replacement helps maintain
                # exploration.
                if rng.random() < 0.5:

                    pbest_x[i] = (
                        positions[i].copy()
                    )

                    pbest_f[i] = (
                        F[i].copy()
                    )

                    pbest_cv[i] = (
                        CV[i]
                    )

        # ----------------------------------------
        # Update Pareto archive
        # ----------------------------------------

        archive_x, archive_f = (
            update_archive(
                archive_x,
                archive_f,
                feasible_x,
                feasible_f,
                archive_size,
            )
        )

        if (
            verbose
            and (
                iteration == 1
                or iteration % 10 == 0
                or iteration == iterations
            )
        ):

            feasible_count = int(
                np.sum(
                    CV <= 1e-12
                )
            )

            print(
                f"Iteration "
                f"{iteration:3d}/{iterations} | "
                f"Evaluations: "
                f"{evaluations:5d} | "
                f"Feasible swarm: "
                f"{feasible_count:3d}/{swarm_size} | "
                f"Archive: "
                f"{len(archive_x):3d}"
            )

    runtime = (
        time.perf_counter()
        - start_time
    )

    return (
        MOPSOResult(
            X=archive_x,
            F=archive_f,
            evaluations=evaluations,
            final_positions=positions.copy(),

        ),
        runtime,
    )