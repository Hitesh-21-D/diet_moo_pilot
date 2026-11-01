"""Bounded structural, portion and role-compatible substitution repair."""
from itertools import combinations
import numpy as np
from src.diet_representation import MEAL_NAMES, get_serving_rule, quantize_servings
from src.algorithms.appo_initialization import _normalized_serving


def valid_roles(meal, rows):
    roles = [r['role'] for r in rows]
    if meal == 'breakfast':
        return roles.count('main') == 1
    if meal in ('lunch', 'dinner'):
        return roles.count('staple') == roles.count('protein_curry') == 1
    return roles.count('snack_item') >= 1 and roles.count('beverage') <= 1


class RepairContext:
    """Immutable food metadata and stable original-diet memory for a run."""
    def __init__(self, problem):
        self.rows = {m: p.to_dict('records') for m, p in problem.food_pools.items()}
        self.memory = {m: {f['food_code']: float(f['servings'])
                          for f in problem.existing_diet.get(m, [])} for m in MEAL_NAMES}
        self.combinations = {}
        for m, rows in self.rows.items():
            active = [i for i, r in enumerate(rows) if r['food_code'] != 'NONE']
            self.combinations[m] = [c for n in (2, 3) for c in combinations(active, n)
                                    if valid_roles(m, [rows[i] for i in c])]
            if not self.combinations[m]:
                raise ValueError(f'{m}: no valid meal composition')

    def structural(self, x, memory=True):
        x = np.asarray(x, dtype=float).copy()
        if x.shape != (24,):
            raise ValueError('Expected 24 genes')
        x = np.nan_to_num(x, nan=0, posinf=1, neginf=0)
        for mi, m in enumerate(MEAL_NAMES):
            rows = self.rows[m]
            block = x[mi*6:mi*6+6].reshape(3, 2)
            block[:, 0] = np.clip(np.rint(block[:, 0]), 0, len(rows)-1)
            block[:, 1] = np.clip(block[:, 1], 0, 1)
            old = [int(v) for v in block[:, 0]]
            active = [i for i in old if rows[i]['food_code'] != 'NONE']
            if len(set(active)) != len(active) or len(active) < 2 or not valid_roles(m, [rows[i] for i in active]):
                # Minimize food additions/removals first, baseline substitutions second.
                def key(c):
                    edits = len(set(active) ^ set(c)) + len(active)-len(set(active))
                    familiar = sum(rows[i]['food_code'] in self.memory[m] for i in c) if memory else 0
                    return edits, -familiar, c
                chosen = list(min(self.combinations[m], key=key))
                empty = next(i for i, r in enumerate(rows) if r['food_code'] == 'NONE')
                chosen += [empty] * (3-len(chosen))
                # Preserve existing pairs where possible; only fill displaced slots.
                unused = chosen.copy()
                for j, i in enumerate(old):
                    if i in unused:
                        unused.remove(i)
                    else:
                        block[j, 0] = -1
                for j in range(3):
                    if block[j, 0] < 0:
                        i = unused.pop(0)
                        block[j, 0] = i
                        r = rows[i]
                        preferred = self.memory[m].get(r['food_code']) if memory else None
                        block[j, 1] = _normalized_serving(preferred, get_serving_rule(r)) if preferred is not None else 0.5
            for j in range(3):
                rule = get_serving_rule(rows[int(block[j, 0])])
                amount = quantize_servings(block[j, 1], rule['min'], rule['max'], rule['step'])
                block[j, 1] = _normalized_serving(amount, rule)
        return x


def repair_candidate(candidate, budget, context, config, rng):
    initial = candidate
    stats = dict(initial_cv=candidate.cv, final_cv=candidate.cv, feasible=candidate.feasible,
                 accepted_modifications=0, repair_evaluations=0, food_substitutions=0,
                 serving_adjustments=0, structural_modifications=0)
    if not config.repair_enabled:
        return candidate, stats
    fixed = context.structural(candidate.x, config.memory_enabled)
    if not np.array_equal(fixed, candidate.x) and budget.remaining:
        trial = budget.evaluate(fixed)
        stats['repair_evaluations'] += 1
        # Structural fixes may alter nutrition; retain only if total CV improves.
        if trial.cv <= candidate.cv:
            candidate = trial
            stats['structural_modifications'] += 1
            stats['accepted_modifications'] += 1
    for attempt in range(config.max_repair_attempts):
        if not budget.remaining or candidate.feasible:
            break
        x = candidate.x.copy()
        slot = int(rng.integers(12))
        m = MEAL_NAMES[slot//3]
        rows = context.rows[m]
        i = int(round(x[2*slot]))
        row = rows[i]
        if row['food_code'] == 'NONE':
            continue
        substitution = attempt >= config.max_repair_attempts // 2
        if substitution:
            used = set(x[(slot//3)*6:(slot//3)*6+6:2].astype(int))
            options = [j for j, r in enumerate(rows) if r['role'] == row['role'] and j not in used]
            if not options:
                continue
            if config.memory_enabled and rng.random() < 0.5:
                familiar = [j for j in options if rows[j]['food_code'] in context.memory[m]]
                options = familiar or options
            x[2*slot] = rng.choice(options)
        else:
            rule = get_serving_rule(row)
            step = rule['step'] / max(rule['max']-rule['min'], 1e-12)
            x[2*slot+1] = np.clip(x[2*slot+1] + rng.choice([-1, 1])*step, 0, 1)
        if np.array_equal(x, candidate.x):
            continue
        trial = budget.evaluate(x)
        stats['repair_evaluations'] += 1
        def key(c):
            return (c.cv, c.interventions, c.f[1], c.f[0]) if config.memory_enabled else (c.cv, c.f[0])
        if key(trial) < key(candidate):
            candidate = trial
            stats['accepted_modifications'] += 1
            stats['food_substitutions' if substitution else 'serving_adjustments'] += 1
    stats.update(final_cv=candidate.cv, feasible=candidate.feasible)
    assert candidate.cv <= initial.cv
    return candidate, stats
