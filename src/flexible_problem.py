"""Versioned, variable-meal formulation shared by all six optimizers."""
import numpy as np
from pymoo.core.problem import ElementwiseProblem
from src.full_catalog import load_full_catalog, NUTRIENTS, VERSION
from src.constraints import nutrient_constraint_violations
from src.diet_representation import calculate_diet_totals, calculate_meal_totals, quantize_servings
from src.objectives import nutritional_deviation, existing_diet_deviation, diversity_penalty


class FlexibleDietProblem(ElementwiseProblem):
    formulation_version = VERSION

    def __init__(self, nutrient_targets, existing_diet):
        self.nutrient_targets, self.existing_diet = nutrient_targets, existing_diet
        self.rows = load_full_catalog()[0].to_dict('records')
        self.by_code = {r['food_code']: i for i, r in enumerate(self.rows)}
        self.meals = list(existing_diet)
        self.slots = {m: len(items)+2 if items else 0 for m, items in existing_diet.items()}
        self.blocks, cursor = {}, 0
        for meal, count in self.slots.items():
            self.blocks[meal] = slice(cursor, cursor+2*count)
            cursor += 2*count
        if not cursor or cursor > 512:
            raise ValueError('Record food in at least one meal; at most 256 search slots per day (recorded dishes plus two per non-empty meal).')
        energies = {m: sum(self.rows[self.by_code[f['food_code']]]['energy_kcal']*f['servings'] for f in foods)
                    for m, foods in existing_diet.items()}
        total = sum(energies.values())
        self.energy_shares = {m: e/total for m, e in energies.items()}
        self.constraint_labels = ['energy lower', 'energy upper', 'protein lower', 'protein upper',
                                  'carbohydrate lower', 'carbohydrate upper', 'fat lower', 'fat upper', 'fibre lower']
        for m in self.meals:
            self.constraint_labels.extend([f'{m}: minimum dishes', f'{m}: maximum dishes',
                                           f'{m}: duplicate foods', f'{m}: food and portion validity'])
        super().__init__(n_var=cursor, n_obj=4, n_ieq_constr=len(self.constraint_labels),
                         xl=np.zeros(cursor), xu=np.tile([len(self.rows), 1.], cursor//2))

    def decode(self, x):
        diet = {}
        for meal, block in self.blocks.items():
            foods = []
            for index, raw in np.asarray(x)[block].reshape(-1, 2):
                i = int(np.clip(round(index), 0, len(self.rows)))
                # A dedicated portion-gene interval encodes an absent dish, so
                # empty slots remain reachable even in an 818-food catalogue.
                if i == len(self.rows) or raw < .25:
                    continue
                row = self.rows[i]
                rule = row['serving_rule']
                amount = quantize_servings((raw-.25)/.75, rule['min'], rule['max'], rule['step'])
                foods.append(dict(food_code=row['food_code'], food_name=row['food_name'], role='food',
                                  serving_unit=row['servings_unit'], servings=amount,
                                  **{k: row[k]*amount for k in NUTRIENTS}))
            diet[meal] = foods
        return diet

    def constraints(self, diet):
        values = list(nutrient_constraint_violations(diet, self.nutrient_targets))
        for meal in self.meals:
            foods = diet.get(meal, [])
            codes = [f['food_code'] for f in foods]
            invalid = 0
            for f in foods:
                if f['food_code'] not in self.by_code:
                    invalid += 1
                    continue
                r = self.rows[self.by_code[f['food_code']]]['serving_rule']
                q = f['servings']
                invalid += int(not np.isfinite(q) or q < r['min']-1e-9 or q > r['max']+1e-9
                               or abs((q-r['min'])/r['step']-round((q-r['min'])/r['step'])) > 1e-8)
            values.extend([int(self.slots[meal]>0)-len(foods), len(foods)-self.slots[meal],
                           len(codes)-len(set(codes)), invalid])
        return np.asarray(values, dtype=float)

    def objectives(self, diet):
        energies = calculate_meal_totals(diet)
        total = calculate_diet_totals(diet)['energy_kcal']
        distribution = np.mean([abs(energies[m]['energy_kcal']/total-self.energy_shares[m]) for m in self.meals]) if total else 1.
        return np.array([nutritional_deviation(diet, self.nutrient_targets),
                         existing_diet_deviation(diet, self.existing_diet), diversity_penalty(diet), distribution])

    def _evaluate(self, x, out, *args, **kwargs):
        diet = self.decode(x)
        out['F'], out['G'] = self.objectives(diet), self.constraints(diet)

    def metadata(self):
        return dict(formulation_version=VERSION, formulation=f'{VERSION}: {self.n_var} variables / 4 objectives / {self.n_ieq_constr} inequalities',
                    meal_slots=self.slots, meal_energy_shares=self.energy_shares, constraint_labels=self.constraint_labels,
                    catalog_size=len(self.rows), portion_policy='Explicit food overrides and serving-unit research defaults; see catalogue audit')


class PenalizedFlexibleProblem(ElementwiseProblem):
    def __init__(self, problem):
        self.base = problem
        super().__init__(n_var=problem.n_var, n_obj=4, n_ieq_constr=0, xl=problem.xl, xu=problem.xu)

    def _evaluate(self, x, out, *args, **kwargs):
        raw = {}
        self.base._evaluate(x, raw)
        cv = np.maximum(raw['G'], 0).sum()
        out['F'] = raw['F'] + (100+100*cv if cv else 0)
        out['raw_objectives'], out['constraint_violation'] = raw['F'], cv
