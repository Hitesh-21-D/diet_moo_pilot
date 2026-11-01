"""Meal-block crossover, categorical food mutation and discrete portion mutation."""
import numpy as np
from src.diet_representation import MEAL_NAMES, get_serving_rule
from src.algorithms.appo_initialization import _normalized_serving, _sample_serving_gene


def adaptive_rates(config, feasibility, uniqueness, stagnant):
    if not config.adaptation_enabled:
        return config.initial_crossover_rate, config.initial_mutation_rate
    s = min(stagnant / config.stagnation_window, 1.0)
    deficit = max(0.0, config.diversity_threshold-uniqueness) / max(config.diversity_threshold, 1e-12)
    mutation = config.initial_mutation_rate + 0.10*(1-feasibility) + 0.10*deficit + 0.10*s
    crossover = config.initial_crossover_rate + 0.05*feasibility - 0.10*deficit - 0.10*s
    return (float(np.clip(crossover, config.min_crossover_rate, config.max_crossover_rate)),
            float(np.clip(mutation, config.min_mutation_rate, config.max_mutation_rate)))


def offspring(a, b, context, config, rng, crossover, mutation):
    x = a.x.copy()
    if rng.random() < crossover:
        for meal in range(4):
            if rng.random() < 0.5:
                x[meal*6:meal*6+6] = b.x[meal*6:meal*6+6]
    for slot in range(12):
        if rng.random() >= mutation:
            continue
        m = MEAL_NAMES[slot//3]
        rows = context.rows[m]
        old = int(round(x[2*slot]))
        row = rows[old]
        if config.memory_enabled and rng.random() < config.habit_guided_mutation_probability:
            familiar = [i for i, r in enumerate(rows) if r['food_code'] in context.memory[m]
                        and (r['role'] == row['role'] or row['food_code'] == 'NONE')]
            if familiar:
                i = int(rng.choice(familiar))
                x[2*slot] = i
                x[2*slot+1] = _normalized_serving(context.memory[m][rows[i]['food_code']], get_serving_rule(rows[i]))
                continue
        if rng.random() < 0.5:
            compatible = [i for i, r in enumerate(rows) if i != old and
                          (r['role'] == row['role'] or row['food_code'] == 'NONE')]
            if compatible:
                x[2*slot] = rng.choice(compatible)
        else:
            x[2*slot+1] = _sample_serving_gene(rng, row)
    return x
