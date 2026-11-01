import copy
import numpy as np
import pytest
from src.full_catalog import load_full_catalog
from src.flexible_problem import FlexibleDietProblem
from src.nutrient_targets import calculate_nutrient_targets
from config.user_profile import USER_PROFILE
from backend.catalog import validate_diet
from tests_web.test_api import setup


def test_catalog_coverage_and_rules():
    foods, audit = load_full_catalog()
    assert len(audit) == 1014 and len(foods) == int(audit.included.sum()) == 818
    assert foods.food_code.is_unique
    assert (audit.loc[~audit.included, 'reason'].str.len()>0).all()
    for food in foods.to_dict('records'):
        validate_diet({'Custom meal': [dict(food_code=food['food_code'], servings=1)]})
        r = food['serving_rule']
        assert 0 < r['min'] <= r['max'] and r['step'] > 0


@pytest.mark.parametrize('count', [1, 2, 5, 8, 20])
def test_variable_meals_and_dishes(count):
    codes = load_full_catalog()[0].food_code.tolist()
    diet = {f'Meal {i+1}': [dict(food_code=c, servings=1) for c in codes[i:i+1+i%5]] for i in range(count)}
    diet['Skipped'] = []
    validate_diet(diet)
    p = FlexibleDietProblem(calculate_nutrient_targets(USER_PROFILE), diet)
    assert p.n_var == 2*sum(len(f)+2 for f in diet.values() if f)
    assert p.n_ieq_constr == 9+4*len(diet)
    x = np.random.default_rng(123).uniform(p.xl, p.xu)
    x[1] = .75
    decoded = p.decode(x)
    assert list(decoded) == list(diet) and decoded['Skipped'] == []
    out = {}; p._evaluate(x, out)
    assert len(out['G']) == p.n_ieq_constr and np.isfinite(out['F']).all()
    broken = copy.deepcopy(decoded)
    broken['Meal 1'][0]['servings'] = 999
    assert p.constraints(broken)[12] > 0
    assert sum(p.energy_shares.values()) == pytest.approx(1)


def test_custom_day_snapshot_and_food_endpoint(signed):
    setup(signed, 1)
    foods = signed.get('/api/foods').json()['all']
    assert len(foods)==818
    day = dict(label='Flexible', date='2026-10-31', diet={'Brunch': [dict(food_code=foods[100]['food_code'], servings=1)], 'Late snack': []})
    saved = signed.post('/api/submissions', json=dict(title='Flexible', days=[day]))
    assert saved.status_code==201
    response = signed.post('/api/experiments', json=dict(day_ids=[saved.json()['days'][0]['id']], algorithms=['APPO'], budget=100))
    assert response.status_code==201
    snapshot = signed.get('/api/experiments/'+response.json()['experiment_ids'][0]).json()['snapshot']
    assert snapshot['formulation_version']=='flexible-v2'
    assert snapshot['meal_slots']=={'Brunch':3,'Late snack':0}
    assert len(snapshot['constraint_labels'])==17


def test_more_than_twelve_dishes_and_every_food_decodes():
    foods = load_full_catalog()[0].to_dict('records')
    diet = {'Custom': [dict(food_code=f['food_code'], servings=1) for f in foods[:15]]}
    validate_diet(diet)
    p = FlexibleDietProblem(calculate_nutrient_targets(USER_PROFILE), diet)
    assert p.slots['Custom']==17
    x = p.xu.copy()  # sentinel food indices: all slots absent
    for i, food in enumerate(foods):
        x[:2] = i, .75
        decoded = p.decode(x)
        assert len(decoded['Custom'])==1
        assert decoded['Custom'][0]['food_code']==food['food_code']
        assert p.constraints(decoded)[-1]==0
    x[1] = .1
    assert p.decode(x)['Custom']==[]
