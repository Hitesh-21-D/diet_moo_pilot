"""One accounting gateway for every search-time candidate assessment."""
from dataclasses import dataclass
import numpy as np
from src.evaluation import diet_signature, intervention_count


@dataclass
class Candidate:
    x: np.ndarray
    f: np.ndarray
    g: np.ndarray
    cv: float
    signature: tuple
    interventions: int

    @property
    def feasible(self):
        # Strictly satisfy G <= 0; no positive violations are hidden.
        return bool(np.all(self.g <= 0))


class EvaluationBudget:
    def __init__(self, problem, limit):
        self.problem, self.limit, self.used = problem, int(limit), 0

    @property
    def remaining(self):
        return self.limit - self.used

    def evaluate(self, x):
        if not self.remaining:
            raise RuntimeError("Evaluation budget exhausted")
        self.used += 1
        out = {}
        self.problem._evaluate(np.asarray(x), out)
        f, g = np.asarray(out['F']), np.asarray(out['G'])
        if f.shape != (4,) or g.shape != (33,) or not np.all(np.isfinite(np.r_[f, g])):
            raise ValueError("Invalid shared problem evaluation")
        diet = self.problem.decode(x)
        return Candidate(np.array(x, copy=True), f, g, float(np.maximum(g, 0).sum()),
                         diet_signature(diet), intervention_count(diet, self.problem.existing_diet))
