"""APPO operators for dynamic meal blocks; every repair trial is budgeted."""
import numpy as np
from src.algorithms.appo_initialization import _normalized_serving


class RepairContext:
    def __init__(self, problem):
        self.problem = problem
        self.memory = {m: {problem.by_code[f['food_code']]: f['servings'] for f in foods}
                       for m, foods in problem.existing_diet.items()}
        self.slot_meals = [m for m, count in problem.slots.items() for _ in range(count)]

    def structural(self, x, memory=True):
        p = self.problem
        x = np.clip(np.nan_to_num(x), p.xl, p.xu)
        for m, block in p.blocks.items():
            pairs = x[block].reshape(-1, 2)
            seen = set()
            for pair in pairs:
                i = int(round(pair[0]))
                pair[0] = i if i not in seen else len(p.rows)
                if i < len(p.rows) and pair[1] >= .25:
                    seen.add(i)
            if len(pairs) and all(pair[0] == len(p.rows) or pair[1] < .25 for pair in pairs):
                pairs[0, 0] = next(iter(self.memory[m])) if memory else 0
                pairs[0, 1] = .5
        return x


def initialize_appo_population(problem, existing_diet, config, rng):
    context = RepairContext(problem)
    population = []
    for n in range(config.population_size):
        x = rng.uniform(problem.xl, problem.xu)
        for m, block in problem.blocks.items():
            pairs = x[block].reshape(-1, 2)
            if not len(pairs):
                continue
            if config.memory_enabled and n < config.population_size*config.baseline_seed_fraction:
                pairs[:, 0] = len(problem.rows)
                for j, (i, amount) in enumerate(context.memory[m].items()):
                    pairs[j] = i, .25+.75*_normalized_serving(amount, problem.rows[i]['serving_rule'])
                    if n:
                        pairs[j, 1] = np.clip(pairs[j, 1]+rng.normal(0, .15), 0, 1)
            else:
                count = int(rng.integers(1, len(pairs)+1))
                pairs[count:, 0] = len(problem.rows)
        population.append(context.structural(x, config.memory_enabled))
    return np.array(population)


def offspring(a, b, context, config, rng, crossover, mutation):
    p = context.problem
    x = a.x.copy()
    if rng.random() < crossover:
        for block in p.blocks.values():
            if rng.random() < .5:
                x[block] = b.x[block]
    for slot, m in enumerate(context.slot_meals):
        if rng.random() >= mutation:
            continue
        if config.memory_enabled and rng.random() < config.habit_guided_mutation_probability:
            i = int(rng.choice(list(context.memory[m])))
            x[2*slot:2*slot+2] = i, .25+.75*_normalized_serving(context.memory[m][i], p.rows[i]['serving_rule'])
        elif rng.random() < .5:
            x[2*slot] = rng.integers(len(p.rows)+1)
        else:
            x[2*slot+1] = rng.random()
    return x


def repair_candidate(candidate, budget, context, config, rng):
    stats = dict(initial_cv=candidate.cv, final_cv=candidate.cv, feasible=candidate.feasible,
                 accepted_modifications=0, repair_evaluations=0, food_substitutions=0,
                 serving_adjustments=0, structural_modifications=0)
    if config.repair_enabled:
        for attempt in range(config.max_repair_attempts):
            if not budget.remaining or candidate.feasible:
                break
            x = context.structural(candidate.x, config.memory_enabled)
            structural = not np.array_equal(x, candidate.x)
            substitution = False
            if not structural:
                slot = int(rng.integers(len(context.slot_meals)))
                substitution = attempt >= config.max_repair_attempts//2
                if substitution:
                    x[2*slot] = rng.integers(len(context.problem.rows)+1)
                else:
                    x[2*slot+1] = np.clip(x[2*slot+1]+rng.choice([-.15, .15]), 0, 1)
            if np.array_equal(x, candidate.x):
                continue
            trial = budget.evaluate(x)
            stats['repair_evaluations'] += 1
            def key(c):
                return (c.cv, c.interventions, c.f[1], c.f[0]) if config.memory_enabled else (c.cv, c.f[0])
            if key(trial) < key(candidate):
                candidate = trial
                stats['accepted_modifications'] += 1
                stats['structural_modifications' if structural else 'food_substitutions' if substitution else 'serving_adjustments'] += 1
    stats.update(final_cv=candidate.cv, feasible=candidate.feasible)
    return candidate, stats
