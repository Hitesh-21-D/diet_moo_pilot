"""Freeze comparable metrics only after a complete per-day cohort finishes."""
import time
import numpy as np
import pandas as pd
from sqlalchemy import select
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from backend.db import SessionLocal, Experiment, Run
from backend.compute import clean
from src.metrics import get_normalization_bounds,normalize_front,calculate_hypervolume,calculate_igd,calculate_spacing,calculate_petq
from run_repeated_experiments import paired_statistics

def finalize(experiment_id):
    with SessionLocal() as db:
        exp=db.scalar(select(Experiment).where(Experiment.id==experiment_id).with_for_update())
        if not exp or exp.comparison is not None:
            return
        runs=list(db.scalars(select(Run).where(Run.experiment_id==experiment_id)))
        if not runs or any(r.status in ('running','queued') for r in runs):
            return
        if any(r.status not in ('completed','no_feasible') for r in runs):
            exp.comparison={'available':False,'reason':'This cohort is incomplete because a run failed or was cancelled. Create a new comparison to retry.'}
        elif len({r.algorithm for r in runs})<2:
            exp.comparison={'available':False,'reason':'Comparative HV, IGD and PETQ require at least two algorithms on this same day. Direct run diagnostics are available below.'}
        else:
            fronts={r.id:np.asarray(r.result['F']).reshape(-1,4) for r in runs}
            valid=[f for f in fronts.values() if len(f)]
            if not valid:
                exp.comparison={'available':False,'reason':'No run found a feasible diet. A reference front cannot be constructed.'}
            else:
                all_f=np.unique(np.vstack(valid),axis=0)
                reference=all_f[NonDominatedSorting().do(all_f,only_non_dominated_front=True)]
                ideal,nadir=get_normalization_bounds(fronts)
                norm_ref=normalize_front(reference,ideal,nadir)
                rows=[]
                for r in runs:
                    s=r.result['summary']
                    f=fronts[r.id]
                    normalized=normalize_front(f,ideal,nadir)
                    hv=calculate_hypervolume(normalized)
                    igd=calculate_igd(normalized,norm_ref)
                    rows.append(dict(Run=r.id,Algorithm=r.algorithm,Seed=r.seed,UniqueFeasibleDiets=len(f),
                        HV=hv,IGD=igd,Spacing=calculate_spacing(normalized) if len(f) else None,
                        Feasibility=s['feasibility'],Runtime=s['runtime'],Evaluations=s['evaluations'],
                        MeanNutritionDeviation=float(f[:,0].mean()) if len(f) else None,
                        MeanHabitDeviation=float(f[:,1].mean()) if len(f) else None,
                        MeanInterventions=s['mean_interventions'],
                        PETQ=calculate_petq(hv,igd,s['mean_interventions']) if len(f) else 0))
                frame=pd.DataFrame(rows)
                statistics=paired_statistics(frame).to_dict('records') if 'APPO' in frame.Algorithm.values else []
                summary=frame.drop(columns=['Run','Seed']).replace([np.inf,-np.inf],np.nan).groupby('Algorithm').agg(['mean','std','count'])
                summary.columns=['_'.join(c) for c in summary.columns]
                exp.comparison=clean(dict(available=True,version=1,created=time.time(),metrics=rows,
                    reference_front=reference,ideal=ideal,nadir=nadir,hv_reference=[1.1]*4,
                    statistics=statistics,summary=summary.reset_index().to_dict('records'),
                    note='Frozen common reference across every algorithm and seed in this day-specific experiment. Scores cannot be compared numerically to another experiment.'))
        db.commit()
