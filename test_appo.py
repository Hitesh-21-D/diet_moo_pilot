"""APPO regression tests; run with python -m unittest test_appo -v."""
from dataclasses import replace
import copy
import unittest
from unittest.mock import patch
import numpy as np
from src.appo_experiments import make_problem
from src.algorithms.appo import run_appo
from src.algorithms.appo_config import APPOConfig
from src.algorithms.appo_budget import EvaluationBudget, Candidate
from src.algorithms.appo_repair import RepairContext, repair_candidate
from src.algorithms.appo_initialization import initialize_appo_population
from src.algorithms.appo_selection import survive
from src.algorithms.appo_archive import update_archive
from src.algorithms.appo_operators import offspring, adaptive_rates
from src.constraints import evaluate_constraints
from src.evaluation import diet_signature
from src.diet_representation import get_serving_rule
from src.diet_selector import select_final_diets


class APPOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.problem = make_problem()
        cls.context = RepairContext(cls.problem)

    def test_initialization_reproducibility_and_structure(self):
        config = APPOConfig(population_size=30)
        a = initialize_appo_population(self.problem, self.problem.existing_diet, config, np.random.default_rng(3))
        b = initialize_appo_population(self.problem, self.problem.existing_diet, config, np.random.default_rng(3))
        np.testing.assert_array_equal(a, b)
        for x in a:
            g = evaluate_constraints(self.problem.decode(x), self.problem.nutrient_targets)
            self.assertEqual(g.shape, (33,))
            self.assertTrue(np.all(g[9:] <= 0))

    def test_structural_repair_invalid_genes_and_portions(self):
        rng = np.random.default_rng(9)
        for x in [np.zeros(24), np.full(24, np.nan), np.full(24, np.inf),
                  *rng.uniform(-10, 30, (15, 24))]:
            fixed = self.context.structural(x)
            self.assertTrue(np.all(np.isfinite(fixed)))
            self.assertTrue(np.all((fixed >= self.problem.xl) & (fixed <= self.problem.xu)))
            diet = self.problem.decode(fixed)
            self.assertTrue(np.all(evaluate_constraints(diet, self.problem.nutrient_targets)[9:] <= 0))
            for foods in diet.values():
                for f in foods:
                    rule = get_serving_rule(f)
                    self.assertTrue(rule['min'] <= f['servings'] <= rule['max'])
                    if rule['step']:
                        level = (f['servings']-rule['min'])/rule['step']
                        self.assertAlmostEqual(level, round(level))

    def test_repair_budget_and_nonworsening(self):
        budget = EvaluationBudget(self.problem, 30)
        x = initialize_appo_population(self.problem, self.problem.existing_diet,
                                       APPOConfig(population_size=1))[0]
        initial = budget.evaluate(x)
        final, stats = repair_candidate(initial, budget, self.context, APPOConfig(), np.random.default_rng(42))
        self.assertLessEqual(final.cv, initial.cv)
        self.assertEqual(budget.used, 1+stats['repair_evaluations'])
        while budget.remaining:
            budget.evaluate(x)
        with self.assertRaises(RuntimeError):
            budget.evaluate(x)

    def test_feasibility_first_and_archive(self):
        def c(f, cv, key):
            return Candidate(np.zeros(24), np.array(f, dtype=float), np.array([cv]), max(cv, 0),
                             (('meal', ((str(key), 1.0),)),), 0)
        feasible = c([2, 2, 2, 2], 0, 1)
        infeasible = c([0, 0, 0, 0], .001, 2)
        self.assertIs(survive([infeasible, feasible], 1)[0], feasible)
        self.assertIs(survive([c([0]*4, .5, 3), infeasible], 1)[0], infeasible)
        tradeoff = c([1, 3, 1, 3], 0, 3)
        dominated = c([4]*4, 0, 4)
        archive = update_archive([], [feasible, infeasible, tradeoff, dominated, feasible], 100)
        self.assertEqual(len(archive), 2)
        self.assertEqual(len(update_archive([], archive, 1)), 1)

    def test_operators_and_ablation_switches(self):
        config = APPOConfig(population_size=2)
        X = initialize_appo_population(self.problem, self.problem.existing_diet, config)
        budget = EvaluationBudget(self.problem, 2)
        a, b = [budget.evaluate(x) for x in X]
        rng = np.random.default_rng(12)
        x = offspring(a, b, self.context, config, rng, 1, 0)
        for m in range(4):
            self.assertTrue(np.array_equal(x[m*6:m*6+6], a.x[m*6:m*6+6]) or
                            np.array_equal(x[m*6:m*6+6], b.x[m*6:m*6+6]))
        for _ in range(25):
            x = offspring(a, b, self.context, config, rng, .9, 1)
            self.assertTrue(np.all((x >= self.problem.xl) & (x <= self.problem.xu)))
            np.testing.assert_array_equal(x[::2], np.rint(x[::2]))
        self.assertNotEqual(adaptive_rates(config, 0, 0, 20), adaptive_rates(config, 1, 1, 0))
        disabled = replace(config, adaptation_enabled=False)
        self.assertEqual(adaptive_rates(disabled, 0, 0, 20), (.9, .2))
        # NoMemory must not read original memory for initialization or operators.
        no_memory = replace(config, memory_enabled=False)
        empty = {m: [] for m in self.problem.existing_diet}
        np.testing.assert_array_equal(initialize_appo_population(self.problem, empty, no_memory),
                                      initialize_appo_population(self.problem, self.problem.existing_diet, no_memory))
        context = copy.deepcopy(self.context)
        context.memory = {m: {} for m in context.memory}
        np.testing.assert_array_equal(offspring(a, b, context, no_memory, np.random.default_rng(7), .9, 1),
                                      offspring(a, b, self.context, no_memory, np.random.default_rng(7), .9, 1))
        unchanged, stats = repair_candidate(a, budget, self.context, replace(config, repair_enabled=False), rng)
        self.assertIs(unchanged, a)
        self.assertEqual(stats['repair_evaluations'], 0)

    def test_smoke_determinism_budget_and_returned_front(self):
        original = copy.deepcopy(self.problem.existing_diet)
        config = APPOConfig(population_size=20, max_evaluations=600, max_repair_attempts=6)
        a, _ = run_appo(self.problem, config, seed=42, verbose=False)
        b, _ = run_appo(self.problem, config, seed=42, verbose=False)
        self.assertEqual(a.evaluations, 600)
        self.assertGreater(len(a.history), 1)
        np.testing.assert_array_equal(a.X, b.X)
        np.testing.assert_array_equal(a.final_positions, b.final_positions)
        self.assertEqual(a.history, b.history)
        self.assertEqual(self.problem.existing_diet, original)
        self.assertEqual(a.X.shape[1], 24)
        self.assertEqual(a.F.shape, (len(a.X), 4))
        self.assertTrue(np.all(np.isfinite(a.F)))
        signatures = set()
        for x, f in zip(a.X, a.F):
            out = {}
            self.problem._evaluate(x, out)
            self.assertTrue(np.all(out['G'] <= 0))
            np.testing.assert_allclose(f, out['F'])
            signatures.add(diet_signature(self.problem.decode(x)))
        self.assertEqual(len(signatures), len(a.X))
        tiny, _ = run_appo(self.problem, replace(config, max_evaluations=1), verbose=False)
        self.assertEqual(tiny.evaluations, 1)
        self.assertEqual(tiny.final_positions.shape, (1, 24))

    def test_representative_categories(self):
        X = np.zeros((3, 24))
        F = np.array([[1, 3, 1, 3], [3, 1, 3, 1], [2, 2, 2, 2]])
        choices = select_final_diets(X, F, [{}, {}, {}])
        self.assertEqual([v['label'] for v in choices],
                         ['Best Nutritional Match', 'Minimum Dietary Change', 'Balanced Compromise'])

    def test_no_dual_diversity_is_disabled_in_both_paths(self):
        config = APPOConfig(population_size=2, max_evaluations=4, repair_enabled=False,
                            dual_diversity_enabled=False, adaptation_enabled=False)
        with patch('src.algorithms.appo.update_archive', wraps=update_archive) as archive, \
             patch('src.algorithms.appo.survive', wraps=survive) as selection:
            result, _ = run_appo(self.problem, config, verbose=False)
        self.assertTrue(archive.called and selection.called)
        self.assertTrue(all(call.args[-1] == 0 for call in archive.call_args_list))
        self.assertTrue(all(call.args[-1] == 0 for call in selection.call_args_list))
        self.assertTrue(all(rate == .2 for rate in result.mutation_history))
        self.assertTrue(all(rate == .9 for rate in result.crossover_history))


if __name__ == '__main__':
    unittest.main()
