"""Audited serving catalogue for flexible-v2; the historical pilot is unchanged."""
from functools import lru_cache
import numpy as np
import pandas as pd
from src.data_loader import get_dataset_path, REQUIRED_COLUMNS, NUTRIENT_COLUMNS
from src.diet_representation import FOOD_SERVING_RULES

NUTRIENTS = ['energy_kcal', 'protein_g', 'carb_g', 'fat_g', 'fibre_g']
VERSION = 'flexible-v2'


def serving_rule(row):
    # Research portion assumptions, not clinical recommendations. Every row gets
    # an explicit rule, including units absent from the original pilot.
    code, unit = row['food_code'], row['servings_unit']
    if code in FOOD_SERVING_RULES:
        return dict(FOOD_SERVING_RULES[code])
    if unit in {'jar', 'glass jar', 'box'}:
        return dict(min=.05, max=.25, step=.05)
    if unit in {'cake', 'pie', 'flan', 'casserole dish', 'small casserole dish',
                'souffle dish', 'shallow dish', 'chicken', 'joint', 'fish'}:
        return dict(min=.125, max=.5, step=.125)
    if ('chutney' in row['food_name'].lower() or 'pickle' in row['food_name'].lower()) and unit in {'bowl', 'small bowl', 'plate'}:
        return dict(min=.125, max=.5, step=.125)
    if unit in {'egg', 'idli', 'biscuit', 'cookie', 'cookies', 'piece', 'chapati', 'roti'}:
        return dict(min=1., max=3., step=1.)
    if unit in {'tablespoon', 'teaspoon'}:
        return dict(min=.25, max=2., step=.25)
    # These two source rows are concentrated condiments, measured per g/ml.
    if code == 'OSR097':
        return dict(min=.5, max=5., step=.5)
    if code == 'OSR096':
        return dict(min=5., max=20., step=5.)
    return dict(min=.25, max=2., step=.25)


@lru_cache
def load_full_catalog():
    raw = pd.read_excel(get_dataset_path(), sheet_name='Nutrient Data')
    missing = set(REQUIRED_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f'Missing workbook columns: {sorted(missing)}')
    accepted, audit = [], []
    duplicate = raw.food_code.duplicated(keep=False)
    for index, source in raw.iterrows():
        reasons = []
        for key in ('food_code', 'food_name', 'servings_unit'):
            if pd.isna(source[key]) or not str(source[key]).strip():
                reasons.append('missing ' + key)
        values = pd.to_numeric(source[NUTRIENT_COLUMNS], errors='coerce').to_numpy(dtype=float)
        if not np.isfinite(values).all():
            reasons.append('incomplete or non-finite serving nutrients')
        elif (values < 0).any() or values[0] <= 0:
            reasons.append('negative nutrients or non-positive energy')
        elif (values > [1500, 100, 200, 100, 50]).any():
            reasons.append('serving plausibility threshold exceeded; source review required')
        if duplicate.iloc[index] or str(source.food_code).strip() == 'NONE':
            reasons.append('duplicate or reserved food code')
        audit.append(dict(excel_row=index+2, food_code=str(source.food_code),
                          food_name=str(source.food_name), included=not reasons,
                          reason='; '.join(reasons)))
        if reasons:
            continue
        row = dict(food_code=str(source.food_code).strip(), food_name=str(source.food_name).strip(),
                   servings_unit=str(source.servings_unit).strip().lower(), role='food',
                   **dict(zip(NUTRIENTS, values)))
        row['serving_rule'] = serving_rule(row)
        row['rule_basis'] = 'food override' if row['food_code'] in FOOD_SERVING_RULES else 'serving-unit research default'
        accepted.append(row)
    return pd.DataFrame(accepted), pd.DataFrame(audit)
