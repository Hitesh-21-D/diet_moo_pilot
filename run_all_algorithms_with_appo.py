"""Six algorithms using common post-search normalization and reference front."""
import argparse
import json
from src.appo_experiments import (ALGORITHMS, make_problem, new_output, manifest, execute,
                                  save_run, score_runs, comparison_figure, load_completed_run)
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--budget', type=int, default=15000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--reuse-from', nargs='+', default=[],
                        help='Reuse completed raw runs from matching experiments; write new outputs')
    args = parser.parse_args()
    problem, path = make_problem(), new_output('six_algorithms')
    manifest(path, args.budget, [args.seed])
    (path/'reuse_sources.json').write_text(json.dumps(args.reuse_from, indent=2))
    runs, diets = [], []
    for name in ALGORITHMS:
        print(f'Running {name}, seed={args.seed}, requested budget={args.budget}', flush=True)
        run = None
        for source in args.reuse_from:
            run = load_completed_run(source, problem, name, args.budget, args.seed)
            if run is not None:
                break
        if run is None:
            run = execute(problem, name, args.budget, args.seed)
        runs.append(run)
        diets.extend(save_run(path, run, problem))
        print(f"  {len(run['F'])} diets; {run['evaluations']} evaluations; {run['runtime']:.2f}s", flush=True)
    df = score_runs(runs, problem, path, 'six_algorithm_comparison.csv')
    pd.DataFrame(diets).to_csv(path/'diets'/'six_algorithm_final_diets.csv', index=False)
    comparison_figure(df, path)
    print(df.to_string(index=False))
    print('Outputs:', path)


if __name__ == '__main__':
    main()
