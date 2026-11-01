"""Standalone APPO pilot; every execution creates a fresh output directory."""
import argparse
from dataclasses import asdict
from src.appo_experiments import make_problem, new_output, manifest, execute, save_run
from src.algorithms.appo_config import APPOConfig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--budget', type=int, default=15000)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    problem = make_problem()
    config = APPOConfig(max_evaluations=args.budget, seed=args.seed)
    path = new_output('appo')
    manifest(path, args.budget, [args.seed], {'APPO': asdict(config)})
    run = execute(problem, 'APPO', args.budget, args.seed, config)
    save_run(path, run, problem, config, display=True)
    print(f"APPO: {len(run['F'])} feasible Pareto diets; feasibility={run['feasibility']:.1%}; "
          f"evaluations={run['evaluations']}; runtime={run['runtime']:.2f}s")
    if not len(run['F']):
        print('No feasible diets found. Final diagnostics:', run['result'].history[-1])
    print('Outputs:', path)


if __name__ == '__main__':
    main()
