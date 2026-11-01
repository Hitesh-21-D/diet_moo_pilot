"""Adaptive Personalized Pareto Optimization using the unchanged shared problem."""
from dataclasses import dataclass, replace
from time import perf_counter
import numpy as np
from src.algorithms.appo_config import APPOConfig
from src.algorithms.appo_initialization import initialize_appo_population
from src.algorithms.appo_budget import EvaluationBudget
from src.algorithms.appo_repair import RepairContext, repair_candidate
from src.algorithms.appo_selection import survive, select_parent
from src.algorithms.appo_archive import update_archive
from src.algorithms.appo_operators import offspring, adaptive_rates


@dataclass
class APPOResult:
    X: np.ndarray
    F: np.ndarray
    final_positions: np.ndarray
    evaluations: int
    history: list
    repair_statistics: list

    @property
    def feasibility_history(self):
        return [h['feasibility'] for h in self.history]

    @property
    def archive_size_history(self):
        return [h['archive_size'] for h in self.history]

    @property
    def mutation_history(self):
        return [h['mutation'] for h in self.history]

    @property
    def crossover_history(self):
        return [h['crossover'] for h in self.history]


def run_appo(problem, config=None, seed=42, verbose=True):
    start = perf_counter()
    config = config or APPOConfig()
    rng = np.random.default_rng(seed)
    budget = EvaluationBudget(problem, config.max_evaluations)
    if hasattr(problem, "formulation_version"):
        from src.algorithms import flexible_appo as operators
    else:
        from types import SimpleNamespace
        operators = SimpleNamespace(RepairContext=RepairContext, initialize_appo_population=initialize_appo_population, repair_candidate=repair_candidate, offspring=offspring)
    context = operators.RepairContext(problem)
    weight = config.decision_space_diversity_weight if config.dual_diversity_enabled else 0.0
    init_config = replace(config, population_size=min(config.population_size, config.max_evaluations))
    initial = operators.initialize_appo_population(problem, problem.existing_diet, init_config, rng)
    population = [budget.evaluate(x) for x in initial]
    archive, history, repairs = [], [], []
    for i, c in enumerate(population):
        population[i], stats = operators.repair_candidate(c, budget, context, config, rng)
        repairs.append(stats)
    archive = update_archive(archive, population, config.archive_size, weight)
    stagnant = 0
    cross, mutation = config.initial_crossover_rate, config.initial_mutation_rate

    def record(generation):
        history.append(dict(generation=generation, evaluations=budget.used,
                            feasibility=float(np.mean([c.feasible for c in population])),
                            unique_ratio=len({c.signature for c in population})/len(population),
                            archive_size=len(archive), mutation=mutation, crossover=cross,
                            min_cv=min(c.cv for c in population)))
        if verbose:
            print(f"APPO {generation:3d} | evaluations={budget.used} | feasible={history[-1]['feasibility']:.1%} | archive={len(archive)}", flush=True)
    record(0)
    generation = 0
    while budget.remaining:
        generation += 1
        cross, mutation = adaptive_rates(config, history[-1]['feasibility'], history[-1]['unique_ratio'], stagnant)
        children = []
        for _ in range(config.population_size):
            if not budget.remaining:
                break
            a, b = select_parent(population, rng), select_parent(population, rng)
            x = operators.offspring(a, b, context, config, rng, cross, mutation)
            child = budget.evaluate(x)
            child, stats = operators.repair_candidate(child, budget, context, config, rng)
            children.append(child)
            repairs.append(stats)
        previous = {c.signature for c in archive}
        archive = update_archive(archive, children, config.archive_size, weight)
        stagnant = stagnant+1 if previous == {c.signature for c in archive} else 0
        population = survive(population+children, config.population_size, weight)
        record(generation)
    result = APPOResult(np.array([c.x for c in archive]).reshape(-1, problem.n_var),
                        np.array([c.f for c in archive]).reshape(-1, 4),
                        np.array([c.x for c in population]), budget.used, history, repairs)
    return result, perf_counter()-start
