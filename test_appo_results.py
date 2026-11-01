"""Independent validation of a completed full-budget APPO artifact."""
import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from src.appo_experiments import make_problem
from src.evaluation import diet_signature


def validate(path):
    path = Path(path)
    problem = make_problem()
    metadata = json.loads((path/'manifest.json').read_text())
    files = list((path/'raw').glob('APPO_*.npz'))
    assert files, 'No APPO raw result found'
    for file in files:
        with np.load(file, allow_pickle=False) as saved:
            X, F, population = saved['X'], saved['F'], saved['final_positions']
            assert int(saved['evaluations']) == metadata['requested_budget']
        assert len(X) > 0, 'Full pilot must have a nonempty feasible archive'
        assert F.shape == (len(X), 4) and np.isfinite(F).all()
        assert len(NonDominatedSorting().do(F, only_non_dominated_front=True)) == len(F)
        seen = set()
        for x, f in zip(X, F):
            out = {}
            problem._evaluate(x, out)
            assert np.all(out['G'] <= 0), out['G']
            np.testing.assert_allclose(f, out['F'], rtol=1e-12, atol=1e-12)
            seen.add(diet_signature(problem.decode(x)))
        assert len(seen) == len(X)
        for x in population:
            assert np.isfinite(x).all()
            assert np.all((x >= problem.xl) & (x <= problem.xu))
        diets = pd.read_csv(path/'diets'/f'{file.stem}_final_diets.csv')
        assert set(diets.diet_type) == {'Best Nutritional Match', 'Minimum Dietary Change', 'Balanced Compromise'}
        assert not (diets.food_code == 'NONE').any()
        history_path = path/'appo'/file.stem/'run_history.csv'
        if history_path.exists():
            history = pd.read_csv(history_path)
            repair = pd.read_csv(path/'appo'/file.stem/'repair_statistics.csv')
            assert np.all(repair.final_cv <= repair.initial_cv + 1e-14)
            assert np.all(np.diff(history.evaluations) > 0)
            assert history.evaluations.iloc[-1] == metadata['requested_budget']
            assert len(repair) + repair.repair_evaluations.sum() == metadata['requested_budget']
        print(f'PASS {file.name}: {len(X)} unique, feasible, non-dominated diets; four original objectives; '
              'three representative categories; exact evaluation accounting')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output_directory')
    validate(parser.parse_args().output_directory)
