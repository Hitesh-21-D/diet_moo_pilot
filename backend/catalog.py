from functools import lru_cache
import hashlib
from src.data_loader import load_indb, get_dataset_path
from src.food_pool import build_food_pools
from src.diet_representation import get_serving_rule, MEAL_NAMES

@lru_cache
def pools():
    return build_food_pools(load_indb())

def catalog():
    from src.full_catalog import load_full_catalog
    rows = load_full_catalog()[0].to_dict('records')
    return {'all': rows}


def validate_diet(diet, allow_empty=False):
    from src.full_catalog import load_full_catalog
    if not diet or any(not m.strip() or m != m.strip() or len(m)>80 for m in diet):
        raise ValueError('Use at least one meal with a non-empty name of at most 80 characters')
    if len({m.casefold() for m in diet}) != len(diet):
        raise ValueError('Meal names must be unique (ignoring letter case)')
    slots = sum(len(items)+2 for items in diet.values() if items)
    if len(diet)>256 or slots>256:
        raise ValueError('This local app supports up to 256 meal names and 256 search slots (foods plus two per non-empty meal) per day')
    if not allow_empty and not slots:
        raise ValueError('Add at least one food before saving a day')
    allowed = set(load_full_catalog()[0].food_code)
    for meal, items in diet.items():
        codes = [i['food_code'] for i in items]
        if len(codes) != len(set(codes)):
            raise ValueError('Combine repeated foods into one quantity per meal')
        if not set(codes) <= allowed:
            raise ValueError(f'Unsupported food in {meal}')


def decoded_input(diet):
    from src.full_catalog import load_full_catalog, NUTRIENTS
    rows = load_full_catalog()[0].set_index('food_code')
    result = {}
    for meal, items in diet.items():
        result[meal] = []
        for item in items:
            row = rows.loc[item['food_code']].to_dict()
            result[meal].append(dict(food_code=item['food_code'], food_name=row['food_name'],
                serving_unit=row['servings_unit'], servings=item['servings'], role=row['role'],
                **{k:float(row[k])*item['servings'] for k in NUTRIENTS}))
    return result


def dataset_hash():
    return hashlib.sha256(get_dataset_path().read_bytes()).hexdigest()
