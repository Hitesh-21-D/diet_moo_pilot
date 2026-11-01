"""Common-reference multi-seed benchmarking and component ablations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from dataclasses import replace, asdict
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon, rankdata
from src.algorithms.appo_config import APPOConfig
from src.appo_experiments import (ALGORITHMS, make_problem, new_output, manifest, execute,
                                  save_run, score_runs, comparison_figure)


def ablations(budget):
    full = APPOConfig(max_evaluations=budget)
    return {'APPO': full, 'APPO-NoMemory': replace(full, memory_enabled=False),
            'APPO-NoRepair': replace(full, repair_enabled=False),
            'APPO-NoAdaptation': replace(full, adaptation_enabled=False),
            'APPO-NoDualDiversity': replace(full, dual_diversity_enabled=False)}


def paired_statistics(df):
    """APPO versus each competitor; Holm correction over all reported tests."""
    rows = []
    for metric in ['HV', 'IGD', 'Spacing', 'PETQ', 'Feasibility', 'Runtime',
                   'MeanHabitDeviation', 'MeanInterventions']:
        pivot = df.pivot(index='Seed', columns='Algorithm', values=metric)
        for name in pivot.columns:
            if name == 'APPO':
                continue
            pair = pivot[['APPO', name]].replace([np.inf, -np.inf], np.nan).dropna()
            diff = (pair.APPO - pair[name]).to_numpy()
            nonzero = diff[diff != 0]
            if len(diff) < 3:
                p = float('nan')
            elif not len(nonzero):
                p = 1.0
            else:
                p = float(wilcoxon(diff, alternative='two-sided', method='auto').pvalue)
            ranks = rankdata(abs(nonzero))
            effect = float(np.sum(np.sign(nonzero)*ranks)/ranks.sum()) if len(ranks) else 0.0
            rows.append(dict(Metric=metric, Comparator=name, PairedSeeds=len(diff),
                             ExcludedSeeds=len(pivot)-len(diff), PValue=p,
                             RankBiserial_APPO_minus_comparator=effect))
    result = pd.DataFrame(rows)
    result['HolmPValue'] = np.nan
    order = result.PValue.dropna().sort_values().index
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, result.loc[index, 'PValue']*(len(order)-rank)))
        result.loc[index, 'HolmPValue'] = running
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seeds', nargs='+', type=int)
    parser.add_argument('--budget', type=int)
    parser.add_argument('--smoke', action='store_true', help='Default to three seeds and 1000 evaluations')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--ablation', action='store_true')
    modes.add_argument('--repair-comparison', action='store_true',
                       help='Paired current APPO versus NoRepair only; all other settings identical')
    args = parser.parse_args()
    seeds = args.seeds if args.seeds is not None else ([42, 43, 44] if args.smoke else list(range(30)))
    if len(set(seeds)) != len(seeds):
        parser.error('Seeds must be distinct')
    budget = args.budget if args.budget is not None else (1000 if args.smoke else 15000)
    configs = ablations(budget) if args.ablation or args.repair_comparison else {'APPO': APPOConfig(max_evaluations=budget)}
    if args.repair_comparison:
        configs = {name: configs[name] for name in ('APPO', 'APPO-NoRepair')}
    names = list(configs) if args.ablation or args.repair_comparison else ALGORITHMS
    label = 'repair_comparison' if args.repair_comparison else ('ablation' if args.ablation else 'repeated')
    problem, path = make_problem(), new_output(label)
    manifest(path, budget, seeds, {n: asdict(c) for n, c in configs.items()})
    print('Outputs:', path, flush=True)
    source_files = [Path(__file__), *Path('src').rglob('*.py'), *Path('config').glob('*.py')]
    snapshot = path/'source_snapshot'
    snapshot.mkdir()
    hashes = {}
    for file in source_files:
        relative = file.resolve().relative_to(Path(__file__).resolve().parent)
        target = snapshot/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        content = file.read_bytes()
        target.write_bytes(content)
        hashes[str(relative)] = hashlib.sha256(content).hexdigest()
    (path/'protocol.json').write_text(json.dumps(dict(
        mode=label, python_hash_seed=os.environ.get('PYTHONHASHSEED', 'not pinned'),
        execution='Sequential runs; alternating algorithm order by seed for repair comparison',
        purpose='Development comparison; not a held-out superiority test',
        source_sha256=hashes), indent=2))
    runs, diet_rows = [], []
    for seed_index, seed in enumerate(seeds):
        order = list(reversed(names)) if args.repair_comparison and seed_index % 2 else names
        for name in order:
            print(f'Running {name} seed {seed} budget {budget}', flush=True)
            config = replace(configs[name], seed=seed) if name in configs else None
            run = execute(problem, name, budget, seed, config)
            if args.repair_comparison:
                assert run['evaluations'] == budget
            print(f"Completed {name}: {len(run['F'])} diets, {run['feasibility']:.1%} feasible, "
                  f"{run['evaluations']} evaluations, {run['runtime']:.2f}s", flush=True)
            runs.append(run)
            rows = save_run(path, run, problem, config)
            diet_rows.extend(dict(row, seed=seed) for row in rows)
            # Persist measurements immediately, so interrupted experiments retain completed runs.
            pd.DataFrame([{k: r[k] for k in ['name', 'seed', 'runtime', 'evaluations', 'feasibility']}
                          for r in runs]).to_csv(path/'raw'/'completed_runs.csv', index=False)
    filename = 'repair_comparison.csv' if args.repair_comparison else ('ablation_results.csv' if args.ablation else 'repeated_runs_raw.csv')
    df = score_runs(runs, problem, path, filename)
    pd.DataFrame(diet_rows).to_csv(path/'diets'/'representative_diets.csv', index=False)
    numeric = [c for c in df.select_dtypes('number').columns if c != 'Seed']
    # Undefined indicators remain missing; counts make their omission explicit.
    finite = df.replace([np.inf, -np.inf], np.nan)
    summary = finite.groupby('Algorithm')[numeric].agg(['mean', 'std', 'count'])
    summary.to_csv(path/'metrics'/'repeated_runs_summary.csv')
    paired_statistics(df).to_csv(path/'metrics'/'paired_statistics.csv', index=False)
    comparison_figure(df, path, 'ablation_comparison' if args.ablation else 'multi_seed_variability')
    print(df.to_string(index=False))
    print('Outputs:', path)


if __name__ == '__main__':
    main()
