"""One isolated process per optimization run; no changes to the scientific algorithms."""
import hashlib
import json
import math
import os
import sys
import time
import traceback
from dataclasses import asdict
import numpy as np
from sqlalchemy import select
from backend.db import SessionLocal, Run, Experiment, ROOT
from backend.catalog import pools, dataset_hash
from src.problem import DietOptimizationProblem
from src.moead_problem import MOEADDietProblem
from src.appo_experiments import execute
from src.algorithms.appo_config import APPOConfig
from src.diet_selector import select_final_diets
from src.diet_representation import calculate_diet_totals
from src.constraints import evaluate_constraints
from src.evaluation import intervention_count, mean_intervention_count

def clean(value):
    if isinstance(value,np.ndarray):
        return clean(value.tolist())
    if isinstance(value,np.generic):
        return clean(value.item())
    if isinstance(value,float) and not math.isfinite(value):
        return None
    if isinstance(value,dict):
        return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [clean(v) for v in value]
    return value

def process_run(id):
    with SessionLocal() as db:
        row=db.get(Run,id)
        if not row or row.status!='running':
            return
        experiment=db.get(Experiment,row.experiment_id)
        snap=experiment.snapshot
        name,seed,budget=row.algorithm,row.seed,row.budget
    actual=hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'src').rglob('*.py')))).hexdigest()
    if actual != snap['source_sha256'] or dataset_hash()!=snap['dataset_sha256']:
        raise ValueError('Scientific source or dataset changed after submission. Create a new experiment.')
    from src.flexible_problem import FlexibleDietProblem
    problem=(FlexibleDietProblem(snap['targets'],snap['day']['diet']) if snap.get('formulation_version') == 'flexible-v2'
             else DietOptimizationProblem(pools(),snap['targets'],snap['day']['diet']))
    config=APPOConfig(max_evaluations=budget,seed=seed,repair_enabled=name!='APPO-NoRepair')
    checkpoints=[]
    counter=0
    window=[]
    def observe(f,cv):
        nonlocal counter,window
        counter+=1
        window.append(float(cv))
        if counter%100==0:
            checkpoints.append(dict(evaluations=counter,candidate_feasibility=float(np.mean(np.asarray(window)<=0)),
                                    min_candidate_cv=min(window)))
            window=[]
            with SessionLocal() as db:
                r=db.get(Run,id)
                r.progress=counter
                db.commit()
    original=problem._evaluate
    def evaluate(x,out,*args,**kwargs):
        original(x,out,*args,**kwargs)
        observe(out['F'],np.maximum(out['G'],0).sum())
    problem._evaluate=evaluate
    original_moead=MOEADDietProblem._evaluate
    def evaluate_moead(self,x,out,*args,**kwargs):
        original_moead(self,x,out,*args,**kwargs)
        observe(out['raw_objectives'],out['constraint_violation'])
    MOEADDietProblem._evaluate=evaluate_moead
    import src.algorithms.mopso as mopso
    original_swarm=mopso.evaluate_population
    def evaluate_swarm(problem,positions):
        output=original_swarm(problem,positions)
        for f,cv in zip(output[0],output[1]):
            observe(f,cv)
        return output
    mopso.evaluate_population=evaluate_swarm
    try:
        run=execute(problem,name,budget,seed,config if name.startswith('APPO') else None)
    finally:
        problem._evaluate=original
        MOEADDietProblem._evaluate=original_moead
        mopso.evaluate_population=original_swarm
    if counter!=run['evaluations']:
        raise ValueError(f'Observed evaluation count {counter} disagrees with optimizer count {run["evaluations"]}')
    representatives=select_final_diets(run['X'],run['F'],run['diets'])
    solutions=[]
    for i,(x,f,diet) in enumerate(zip(run['X'],run['F'],run['diets'])):
        constraints=problem.constraints(diet) if hasattr(problem, 'constraints') else evaluate_constraints(diet,snap['targets'])
        if not np.all(constraints<=1e-12):
            raise ValueError('Returned diet failed independent constraint validation')
        solutions.append(dict(index=i,chromosome=x,objectives=f,constraints=constraints,diet=diet,
                              totals=calculate_diet_totals(diet),interventions=intervention_count(diet,problem.existing_diet)))
    for selection in representatives:
        selection['totals']=calculate_diet_totals(selection['diet'])
        selection['interventions']=intervention_count(selection['diet'],problem.existing_diet)
    result=run['result']
    history=result.history if name.startswith('APPO') else []
    repairs=result.repair_statistics if name.startswith('APPO') else []
    payload=dict(summary=dict(feasible_diets=len(solutions),feasibility=run['feasibility'],runtime=run['runtime'],
                              evaluations=run['evaluations'],mean_objectives=np.mean(run['F'],axis=0) if len(solutions) else None,
                              mean_interventions=mean_intervention_count(run['diets'],problem.existing_diet) if solutions else None),
                 solutions=solutions,representatives=representatives,history=history,checkpoints=checkpoints,
                 repair_statistics=repairs,configuration=asdict(config) if name.startswith('APPO') else {'budget':budget,'seed':seed},
                 history_note='Candidate feasibility is measured in successive windows of 100 evaluated candidates; it is not population feasibility.',
                 hash_seed=os.environ.get('PYTHONHASHSEED'), F=run['F'], final_positions=result.final_positions if hasattr(result,'final_positions') else result.pop.get('X'))
    with SessionLocal() as db:
        row=db.get(Run,id)
        if row.status=='running' and not row.cancel_requested:
            row.result=clean(payload)
            row.status='completed' if solutions else 'no_feasible'
            row.progress=run['evaluations']
            row.finished=time.time()
            db.commit()

if __name__=='__main__':
    try:
        process_run(sys.argv[1])
    except Exception:
        traceback.print_exc()
        with SessionLocal() as db:
            row=db.get(Run,sys.argv[1])
            if row and row.status=='running':
                row.status='failed'
                row.error='Computation failed. Review the local worker log, then create a new run.'
                row.finished=time.time()
                db.commit()
        raise
