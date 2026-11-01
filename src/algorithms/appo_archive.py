"""Feasible, practically unique external archive."""
import numpy as np
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from src.algorithms.appo_selection import diversity_scores


def update_archive(archive, candidates, capacity=100, weight=0.3):
    unique = {}
    for c in [*archive, *candidates]:
        if c.feasible:
            unique.setdefault(c.signature, c)
    values = list(unique.values())
    if not values:
        return []
    indices = NonDominatedSorting().do(np.array([c.f for c in values]), only_non_dominated_front=True)
    values = [values[i] for i in indices]
    # Recompute local diversity after each deletion.
    while len(values) > capacity:
        scores = diversity_scores(values, weight)
        del values[int(np.argmin(scores))]
    return values
