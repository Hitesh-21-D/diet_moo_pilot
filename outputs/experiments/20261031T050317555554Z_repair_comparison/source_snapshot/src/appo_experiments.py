"""Shared execution, validation and export for APPO research experiments."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import hashlib
import json
import platform
from types import SimpleNamespace
from importlib.metadata import version
import numpy as np
import pandas as pd
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from config.user_profile import USER_PROFILE
from src.data_loader import load_indb, get_dataset_path
from src.food_pool import build_food_pools
from src.nutrient_targets import calculate_nutrient_targets
from src.problem import DietOptimizationProblem
from src.moead_problem import MOEADDietProblem
from src.algorithms.appo import run_appo
from src.algorithms.appo_config import APPOConfig
from src.algorithms.nsga2 import run_nsga2
from src.algorithms.nsga3 import run_nsga3
from src.algorithms.moead import run_moead
from src.algorithms.spea2 import run_spea2
from src.algorithms.mopso import run_mopso
from src.evaluation import extract_unique_feasible_solutions, calculate_feasibility_rate, mean_intervention_count
from src.metrics import (get_normalization_bounds, normalize_front, calculate_hypervolume,
                         calculate_igd, calculate_spacing, calculate_petq)
from src.diet_selector import select_final_diets
from src.report import create_diet_rows, print_selected_diets

ALGORITHMS = ['NSGA-II', 'NSGA-III', 'MOEA/D', 'SPEA2', 'MOPSO', 'APPO']


def make_problem():
    return DietOptimizationProblem(build_food_pools(load_indb()), calculate_nutrient_targets(USER_PROFILE),
                                   USER_PROFILE['existing_diet'])


def new_output(label):
    root = Path(__file__).resolve().parent.parent / 'outputs' / 'experiments'
    path = root / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_' + label)
    path.mkdir(parents=True, exist_ok=False)
    for folder in ('metrics', 'diets', 'appo', 'figures', 'raw'):
        (path/folder).mkdir()
    return path


def manifest(path, budget, seeds, configurations=None):
    data = dict(requested_budget=budget, seeds=list(seeds), profile=USER_PROFILE,
                dataset_sha256=hashlib.sha256(get_dataset_path().read_bytes()).hexdigest(),
                python=platform.python_version(), packages={p: version(p) for p in
                ('numpy', 'pandas', 'scipy', 'pymoo', 'matplotlib', 'openpyxl')},
                configurations=configurations or {},
                budget_policy='APPO exact; baselines use whole generations at or below requested budget. MOEA/D population 84.',
                timing_policy='External wall clock includes initialization and search; validation/export excluded.',
                validation_policy='Post-search recomputation excluded from search budget, never fed back into optimization.')
    (path/'manifest.json').write_text(json.dumps(data, indent=2), encoding='utf-8')


def execute(problem, name, budget, seed, config=None):
    if budget < 100:
        raise ValueError('Comparative experiment budget must be at least 100')
    start = perf_counter()
    if name.startswith('APPO'):
        result, _ = run_appo(problem, config or APPOConfig(max_evaluations=budget), seed, verbose=False)
    elif name == 'MOPSO':
        result, _ = run_mopso(problem, iterations=budget//100-1, seed=seed, verbose=False)
    elif name == 'MOEA/D':
        compatibility = MOEADDietProblem(problem.food_pools, problem.nutrient_targets, problem.existing_diet)
        result, _ = run_moead(compatibility, generations=max(1, budget//84), seed=seed, verbose=False)
    else:
        runner = {'NSGA-II': run_nsga2, 'NSGA-III': run_nsga3, 'SPEA2': run_spea2}[name]
        result, _ = runner(problem, population_size=100, generations=budget//100, seed=seed, verbose=False)
    runtime = perf_counter()-start
    count = result.evaluations if hasattr(result, 'evaluations') else result.algorithm.evaluator.n_eval
    positions = result.final_positions if hasattr(result, 'final_positions') else result.pop.get('X')
    X, F, diets = extract_unique_feasible_solutions(problem, result.X, problem.nutrient_targets, problem.existing_diet)
    # The shared extraction deduplicates and verifies feasibility but does not remove dominance.
    if len(F):
        keep = NonDominatedSorting().do(F, only_non_dominated_front=True)
        X, F, diets = X[keep], F[keep], [diets[i] for i in keep]
    assert count <= budget, (name, count, budget)
    return dict(name=name, seed=seed, result=result, X=X, F=F, diets=diets,
                runtime=runtime, evaluations=int(count),
                feasibility=calculate_feasibility_rate(problem, positions, problem.nutrient_targets))


def load_completed_run(source, problem, name, budget, seed):
    """Reuse an explicitly supplied run without repeating search or changing its timer."""
    source = Path(source)
    metadata = json.loads((source/'manifest.json').read_text())
    if metadata['requested_budget'] != budget or seed not in metadata['seeds']:
        raise ValueError('Reuse source has a different budget or seed')
    if metadata['profile'] != USER_PROFILE or metadata['dataset_sha256'] != hashlib.sha256(get_dataset_path().read_bytes()).hexdigest():
        raise ValueError('Reuse source has a different problem')
    safe = name.replace('/', '_') + '_' + str(seed)
    file = source/'raw'/f'{safe}.npz'
    if not file.exists():
        return None
    with np.load(file, allow_pickle=False) as data:
        result = SimpleNamespace(X=data['X'], F=data['F'], final_positions=data['final_positions'],
                                 evaluations=int(data['evaluations']))
        runtime = float(data['runtime'])
    folder = source/'appo'/safe
    if name.startswith('APPO') and (folder/'run_history.csv').exists():
        result.history = pd.read_csv(folder/'run_history.csv').to_dict('records')
        result.repair_statistics = pd.read_csv(folder/'repair_statistics.csv').to_dict('records')
    X, F, diets = extract_unique_feasible_solutions(problem, result.X, problem.nutrient_targets, problem.existing_diet)
    if len(F):
        keep = NonDominatedSorting().do(F, only_non_dominated_front=True)
        X, F, diets = X[keep], F[keep], [diets[i] for i in keep]
    return dict(name=name, seed=seed, result=result, X=X, F=F, diets=diets, runtime=runtime,
                evaluations=result.evaluations,
                feasibility=calculate_feasibility_rate(problem, result.final_positions, problem.nutrient_targets))


def save_run(path, run, problem, config=None, display=False):
    safe = run['name'].replace('/', '_') + '_' + str(run['seed'])
    result = run['result']
    positions = result.final_positions if hasattr(result, 'final_positions') else result.pop.get('X')
    np.savez_compressed(path/'raw'/f'{safe}.npz', X=run['X'], F=run['F'], final_positions=positions,
                        evaluations=run['evaluations'], runtime=run['runtime'], seed=run['seed'])
    selected = select_final_diets(run['X'], run['F'], run['diets'])
    rows = create_diet_rows(run['name'], selected, problem.existing_diet)
    pd.DataFrame(rows).to_csv(path/'diets'/f'{safe}_final_diets.csv', index=False)
    if display:
        print_selected_diets({run['name']: selected}, problem.existing_diet)
    if hasattr(result, 'history') and isinstance(result.history, list) and run['name'].startswith('APPO'):
        folder = path/'appo'/safe
        folder.mkdir()
        history = pd.DataFrame(result.history)
        history.to_csv(folder/'run_history.csv', index=False)
        history[['evaluations', 'feasibility']].to_csv(folder/'feasibility_history.csv', index=False)
        pd.DataFrame(result.repair_statistics).to_csv(folder/'repair_statistics.csv', index=False)
        pd.DataFrame(np.c_[run['X'], run['F']], columns=[f'x{i}' for i in range(24)]+[f'f{i+1}' for i in range(4)]).to_csv(folder/'pareto_archive.csv', index=False)
        (folder/'configuration.json').write_text(json.dumps(asdict(config or APPOConfig(max_evaluations=run['evaluations'], seed=run['seed'])), indent=2))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for col, label in [('feasibility', 'Feasible population fraction'), ('mutation', 'Mutation probability'),
                           ('crossover', 'Crossover probability'), ('archive_size', 'Feasible non-dominated archive size')]:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.plot(history.evaluations, history[col])
            ax.set(xlabel='Counted candidate evaluations (including repair)', ylabel=label)
            ax.grid(alpha=0.2)
            fig.tight_layout()
            fig.savefig(path/'figures'/f'{safe}_{col}.png', dpi=200)
            plt.close(fig)
    return rows


def score_runs(runs, problem, path, filename):
    fronts = {str(i): r['F'] for i, r in enumerate(runs)}
    valid = [f for f in fronts.values() if len(f)]
    if valid:
        combined = np.unique(np.vstack(valid), axis=0)
        ref = combined[NonDominatedSorting().do(combined, only_non_dominated_front=True)]
        ideal, nadir = get_normalization_bounds(fronts)
        normalized_ref = normalize_front(ref, ideal, nadir)
    else:
        ref = np.empty((0, 4))
        ideal, nadir = np.zeros(4), np.ones(4)
        normalized_ref = ref
    pd.DataFrame(ref, columns=['f1', 'f2', 'f3', 'f4']).to_csv(path/'metrics'/'reference_front.csv', index=False)
    (path/'metrics'/'normalization.json').write_text(json.dumps(dict(ideal=ideal.tolist(), nadir=nadir.tolist(), hv_reference=[1.1]*4), indent=2))
    rows = []
    for r in runs:
        F = r['F']
        normalized = normalize_front(F, ideal, nadir)
        hv = calculate_hypervolume(normalized)
        igd = calculate_igd(normalized, normalized_ref) if len(ref) else float('inf')
        interventions = mean_intervention_count(r['diets'], problem.existing_diet) if len(F) else float('nan')
        rows.append(dict(Algorithm=r['name'], Seed=r['seed'], UniqueFeasibleDiets=len(F),
                         HV=hv, IGD=igd, Spacing=calculate_spacing(normalized) if len(F) else float('nan'),
                         Feasibility=r['feasibility'], MeanNutritionDeviation=float(F[:, 0].mean()) if len(F) else float('nan'),
                         MeanHabitDeviation=float(F[:, 1].mean()) if len(F) else float('nan'),
                         MeanInterventions=interventions, Runtime=r['runtime'], Evaluations=r['evaluations'],
                         PETQ=calculate_petq(hv, igd, interventions) if len(F) else 0.0))
    df = pd.DataFrame(rows)
    df.to_csv(path/'metrics'/filename, index=False)
    return df


def comparison_figure(df, path, name='algorithm_comparison'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, metric in zip(axes, ['HV', 'IGD', 'PETQ']):
        grouped = df.groupby('Algorithm', sort=False)[metric]
        means, std = grouped.mean(), grouped.std().fillna(0)
        ax.bar(means.index, means.replace([np.inf, -np.inf], np.nan), yerr=std.replace([np.inf, -np.inf], 0))
        ax.set_ylabel(metric)
        ax.tick_params(axis='x', rotation=60)
    fig.tight_layout()
    fig.savefig(path/'figures'/f'{name}.png', dpi=200)
    plt.close(fig)
