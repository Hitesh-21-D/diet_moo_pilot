"""Actual six-algorithm execution with versioned, variable-meal inputs."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from config.user_profile import USER_PROFILE
from src.nutrient_targets import calculate_nutrient_targets
from src.flexible_problem import FlexibleDietProblem
from src.appo_experiments import execute, ALGORITHMS

output = Path('outputs/verification/flexible-v2.json')
output.parent.mkdir(exist_ok=True, parents=True)
results = []
original = USER_PROFILE['existing_diet']
flat = [f for foods in original.values() for f in foods]
patterns = {
    'one-meal': {'Main meal': flat},
    'five-meals': {**original, 'Late snack': [flat[0]]},
}
# Merge any repeated dishes when combining the pilot into one eating occasion.
merged = {}
for f in flat:
    merged[f['food_code']] = merged.get(f['food_code'], 0)+f['servings']
patterns['one-meal']['Main meal'] = [dict(food_code=c, servings=q) for c,q in merged.items()]
for pattern, diet in patterns.items():
    problem = FlexibleDietProblem(calculate_nutrient_targets(USER_PROFILE), diet)
    for name in ALGORITHMS:
        run = execute(problem, name, 15000, 42)
        for x, f, d in zip(run['X'],run['F'],run['diets']):
            assert list(d)==list(diet)
            assert np.all(problem.constraints(d)<=0)
            np.testing.assert_allclose(f, problem.objectives(d))
            assert problem.decode(x)==d
        record = dict(pattern=pattern, algorithm=name, evaluations=run['evaluations'],
                      feasible_diets=len(run['diets']), runtime=run['runtime'],
                      feasibility=run['feasibility'], **problem.metadata())
        results.append(record)
        output.write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(pattern, name, record['evaluations'], record['feasible_diets'], flush=True)
