"""Independently audit a completed paired repair comparison and write its report."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from src.appo_experiments import make_problem
from src.evaluation import diet_signature


def summarize(directory):
    root = Path(directory)
    metadata = json.loads((root/'manifest.json').read_text())
    configurations = metadata['configurations']
    full, disabled = configurations['APPO'], configurations['APPO-NoRepair']
    differences = [key for key in full if full[key] != disabled[key]]
    assert differences == ['repair_enabled'], differences
    assert full['repair_enabled'] and not disabled['repair_enabled']
    metrics = pd.read_csv(root/'metrics'/'repair_comparison.csv')
    assert not metrics.duplicated(['Algorithm', 'Seed']).any()
    expected = {(name, seed) for name in configurations for seed in metadata['seeds']}
    assert set(zip(metrics.Algorithm, metrics.Seed)) == expected
    problem = make_problem()
    diagnostics = []
    for name, seed in sorted(expected):
        stem = f'{name}_{seed}'
        with np.load(root/'raw'/f'{stem}.npz', allow_pickle=False) as data:
            X, F, final = data['X'], data['F'], data['final_positions']
            assert int(data['evaluations']) == metadata['requested_budget']
        assert F.shape == (len(X), 4) and np.isfinite(F).all()
        assert X.shape == (len(F), 24)
        assert np.isfinite(final).all()
        assert np.all((final >= problem.xl) & (final <= problem.xu))
        signatures = set()
        for x, f in zip(X, F):
            out = {}
            problem._evaluate(x, out)
            assert np.all(out['G'] <= 0)
            np.testing.assert_allclose(f, out['F'], rtol=1e-12, atol=1e-12)
            signatures.add(diet_signature(problem.decode(x)))
        assert len(signatures) == len(X)
        if len(F):
            assert len(NonDominatedSorting().do(F, only_non_dominated_front=True)) == len(F)
        row = metrics[(metrics.Algorithm == name) & (metrics.Seed == seed)].iloc[0]
        assert row.UniqueFeasibleDiets == len(X)
        assert row.Evaluations == metadata['requested_budget']
        feasible = 0
        for x in final:
            out = {}
            problem._evaluate(x, out)
            feasible += bool(np.all(out['G'] <= 0))
        np.testing.assert_allclose(row.Feasibility, feasible/len(final))
        folder = root/'appo'/stem
        repairs = pd.read_csv(folder/'repair_statistics.csv')
        history = pd.read_csv(folder/'run_history.csv')
        trials = int(repairs.repair_evaluations.sum())
        assert len(repairs)+trials == metadata['requested_budget']
        assert np.all(repairs.final_cv <= repairs.initial_cv)
        assert history.evaluations.iloc[-1] == metadata['requested_budget']
        if name == 'APPO-NoRepair':
            assert trials == 0
        diagnostics.append(dict(Algorithm=name, Seed=seed, RepairEvaluations=trials,
                                RepairBudgetFraction=trials/metadata['requested_budget'],
                                Generations=int(history.generation.max())))
    diagnostics = pd.DataFrame(diagnostics)
    diagnostics.to_csv(root/'metrics'/'repair_budget_audit.csv', index=False)
    lines = ['# Full-budget APPO repair comparison', '',
             f"Seeds: {metadata['seeds']}. Each run used exactly {metadata['requested_budget']:,} evaluations.", '',
             'Only repair_enabled differs between variants. Original objectives, constraints, initialization, '
             'memory, adaptation and diversity settings are preserved. All runs passed independent checks of '
             'budget accounting, original objective values, all 33 constraints, practical uniqueness and '
             'Pareto non-dominance. Final population feasibility was recomputed.', '',
             'Metrics use one empirical reference front and one normalization across all paired runs. '
             'Their numerical values are not directly comparable with previous experiments using other fronts.', '',
             '| Metric | APPO mean ± sample SD | NoRepair mean ± sample SD |',
             '|---|---:|---:|']
    for metric in ['UniqueFeasibleDiets', 'HV', 'IGD', 'Spacing', 'PETQ', 'Feasibility',
                   'MeanNutritionDeviation', 'MeanHabitDeviation', 'MeanInterventions', 'Runtime', 'Evaluations']:
        values = []
        for name in ['APPO', 'APPO-NoRepair']:
            series = metrics.loc[metrics.Algorithm == name, metric]
            values.append(f'{series.mean():.6f} ± {series.std():.6f}')
        lines.append(f'| {metric} | {values[0]} | {values[1]} |')
    lines.extend(['', '## Paired seed outcomes', '',
                  '| Seed | APPO HV | NoRepair HV | APPO PETQ | NoRepair PETQ |', '|---|---:|---:|---:|---:|'])
    for seed in metadata['seeds']:
        pair = metrics[metrics.Seed == seed].set_index('Algorithm')
        lines.append(f"| {seed} | {pair.loc['APPO','HV']:.6f} | {pair.loc['APPO-NoRepair','HV']:.6f} | "
                     f"{pair.loc['APPO','PETQ']:.6f} | {pair.loc['APPO-NoRepair','PETQ']:.6f} |")
    lines.extend(['', '## Repair cost', ''])
    for name, group in diagnostics.groupby('Algorithm'):
        lines.append(f"- {name}: mean repair budget share {group.RepairBudgetFraction.mean():.1%}; "
                     f"mean completed generations {group.Generations.mean():.1f}.")
    lines.extend(['', '## Interpretation limits', '',
                  'This is a development comparison, not a held-out test against the five baseline algorithms. '
                  'Development seeds can identify a direction for further work but cannot establish general superiority. '
                  'See paired_statistics.csv for two-sided Wilcoxon tests, rank-biserial effects and Holm-adjusted '
                  'p-values. Positive effects represent APPO minus NoRepair and favor APPO only for higher-is-better metrics. '
                  'Any modified optimizer still needs an independent full-budget benchmark with 20–30 seeds.', ''])
    stats = pd.read_csv(root/'metrics'/'paired_statistics.csv')
    means = metrics.groupby('Algorithm').mean(numeric_only=True)
    hv_gain = 100*(means.loc['APPO-NoRepair', 'HV']/means.loc['APPO', 'HV']-1)
    igd_reduction = 100*(1-means.loc['APPO-NoRepair', 'IGD']/means.loc['APPO', 'IGD'])
    hv_p = stats.loc[stats.Metric == 'HV', 'PValue'].iloc[0]
    hv_adjusted = stats.loc[stats.Metric == 'HV', 'HolmPValue'].iloc[0]
    direction = ('These indicators favor investigating disabled or selectively scheduled repair.'
                 if hv_gain > 0 and igd_reduction > 0 else
                 'These indicators do not uniformly favor disabling repair.')
    significance = ('The HV difference passes the 0.05 Holm-adjusted threshold in this experiment.'
                    if hv_adjusted < .05 else
                    'The HV result does not establish statistical significance at the 0.05 level.')
    lines.extend(['## Measured conclusion', '',
                  f'NoRepair changed mean HV by {hv_gain:+.1f}% and reduced mean IGD by {igd_reduction:.1f}% '
                  'relative to current APPO. These are within-experiment comparisons, not comparisons with '
                  f'the earlier five baselines. {direction}', '',
                  f'The HV paired Wilcoxon p-value is {hv_p:.4f}, Holm-adjusted {hv_adjusted:.4f}. '
                  + significance, ''])
    (root/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    print(metrics.to_string(index=False))
    print(diagnostics.to_string(index=False))
    print('Independent audit PASSED:', root/'REPORT.md')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    summarize(parser.parse_args().directory)
