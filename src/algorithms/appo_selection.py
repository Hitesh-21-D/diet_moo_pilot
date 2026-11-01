"""Feasibility-first Pareto survival with practical dietary diversity."""
import numpy as np
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from src.algorithms.mopso import crowding_distance


def diversity_scores(candidates, weight=0.3):
    n = len(candidates)
    if n <= 2:
        return np.ones(n)
    crowd = crowding_distance(np.array([c.f for c in candidates]))
    finite = np.isfinite(crowd)
    obj = np.ones(n)
    if finite.any():
        obj[finite] = crowd[finite] / max(float(crowd[finite].max()), 1e-12)
    if weight == 0:
        return obj
    maps = [{(m, food): amount for m, foods in c.signature for food, amount in foods}
            for c in candidates]
    keys = sorted(set().union(*(d.keys() for d in maps)))
    amounts = np.array([[d.get(k, 0) for k in keys] for d in maps])
    # Every coordinate scaled to [0,1]; presence and portion differences both count.
    amounts /= np.maximum(amounts.max(axis=0), 1e-12)
    distance = np.mean(np.abs(amounts[:, None, :] - amounts[None, :, :]), axis=2)
    np.fill_diagonal(distance, np.inf)
    nearest = distance.min(axis=1)
    decision = nearest / max(float(nearest.max()), 1e-12)
    return (1-weight)*obj + weight*decision


def survive(candidates, size, weight=0.3):
    feasible = [c for c in candidates if c.feasible]
    selected = []
    if feasible:
        fronts = NonDominatedSorting().do(np.array([c.f for c in feasible]))
        for front in fronts:
            group = [feasible[i] for i in front]
            scores = diversity_scores(group, weight)
            order = np.argsort(-scores, kind='stable')
            selected.extend(group[i] for i in order[:size-len(selected)])
            if len(selected) == size:
                break
    selected.extend(sorted((c for c in candidates if not c.feasible), key=lambda c: c.cv)
                    [:size-len(selected)])
    return selected


def select_parent(population, rng):
    a, b = [population[i] for i in rng.integers(len(population), size=2)]
    if a.feasible != b.feasible:
        return a if a.feasible else b
    if not a.feasible and a.cv != b.cv:
        return a if a.cv < b.cv else b
    if np.all(a.f <= b.f) and np.any(a.f < b.f):
        return a
    if np.all(b.f <= a.f) and np.any(b.f < a.f):
        return b
    return a if rng.random() < 0.5 else b
