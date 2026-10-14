import numpy as np

from pymoo.indicators.hv import HV
from pymoo.indicators.igd import IGD


EPSILON = 1e-12


def dominates(a, b):
    """
    Pareto dominance for minimization.
    """

    return (
        np.all(a <= b)
        and np.any(a < b)
    )


def non_dominated_front(F):
    """
    Extract the non-dominated objective vectors from
    a combined objective matrix.
    """

    if F is None or len(F) == 0:

        return np.empty(
            (
                0,
                4,
            )
        )

    F = np.asarray(
        F,
        dtype=float,
    )

    keep = []

    for i in range(
        len(F)
    ):

        dominated = False

        for j in range(
            len(F)
        ):

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

    return F[
        np.asarray(
            keep,
            dtype=int,
        )
    ]


def build_empirical_reference_front(
    fronts,
):
    """
    Construct the empirical reference Pareto front.

    fronts:
        Dictionary such as:

        {
            "NSGA-II": F1,
            "NSGA-III": F2,
            ...
        }

    All feasible objective vectors from all algorithms
    are combined and non-dominated sorting is applied.
    """

    valid_fronts = [
        front
        for front in fronts.values()
        if front is not None
        and len(front) > 0
    ]

    if not valid_fronts:

        raise ValueError(
            "No valid objective fronts were supplied."
        )

    combined = np.vstack(
        valid_fronts
    )

    return non_dominated_front(
        combined
    )


def get_normalization_bounds(
    fronts,
):
    """
    Calculate common ideal and nadir points using the union
    of all algorithm outputs.

    Every algorithm must use the exact same normalization.
    """

    valid_fronts = [
        front
        for front in fronts.values()
        if front is not None
        and len(front) > 0
    ]

    combined = np.vstack(
        valid_fronts
    )

    ideal = np.min(
        combined,
        axis=0,
    )

    nadir = np.max(
        combined,
        axis=0,
    )

    return ideal, nadir


def normalize_front(
    F,
    ideal,
    nadir,
):
    """
    Min-max normalization using global bounds.

    Values normally fall in [0, 1].
    """

    denominator = (
        nadir - ideal
    )

    denominator = np.where(
        denominator < EPSILON,
        1.0,
        denominator,
    )

    return (
        F - ideal
    ) / denominator


def calculate_hypervolume(
    normalized_front,
):
    """
    Hypervolume using a common reference point.

    Since objectives are globally normalized, 1.1 in every
    dimension lies beyond the observed nadir.
    """

    if len(normalized_front) == 0:
        return 0.0

    reference_point = np.full(
        normalized_front.shape[1],
        1.1,
    )

    indicator = HV(
        ref_point=reference_point
    )

    return float(
        indicator(
            normalized_front
        )
    )


def calculate_igd(
    normalized_front,
    normalized_reference_front,
):
    """
    Inverted Generational Distance.

    Lower is better.
    """

    if len(normalized_front) == 0:
        return float("inf")

    indicator = IGD(
        normalized_reference_front
    )

    return float(
        indicator(
            normalized_front
        )
    )


def calculate_spacing(
    normalized_front,
):
    """
    Generalized spacing metric.

    For each Pareto solution, calculate the Euclidean
    distance to its nearest neighboring solution.

    The standard deviation of these distances is returned.

    Lower is better:
        lower spacing -> more uniformly distributed solutions.
    """

    if len(normalized_front) <= 1:
        return 0.0

    nearest_distances = []

    for i in range(
        len(normalized_front)
    ):

        distances = []

        for j in range(
            len(normalized_front)
        ):

            if i == j:
                continue

            distance = np.linalg.norm(
                normalized_front[i]
                - normalized_front[j]
            )

            distances.append(
                distance
            )

        nearest_distances.append(
            min(distances)
        )

    return float(
        np.std(
            nearest_distances
        )
    )


def calculate_petq(
    hv,
    igd,
    mean_interventions,
):
    """
    Proposed Personalized Efficient Trade-off Quality metric.

        PETQ = HV /
               (IGD * ln(1 + T))

    where:

        HV  = Hypervolume
        IGD = Inverted Generational Distance
        T   = mean number of dietary interventions

    Higher is better.
    """

    safe_igd = max(
        igd,
        EPSILON,
    )

    intervention_term = np.log(
        1.0
        + mean_interventions
    )

    intervention_term = max(
        intervention_term,
        EPSILON,
    )

    return float(
        hv
        / (
            safe_igd
            * intervention_term
        )
    )