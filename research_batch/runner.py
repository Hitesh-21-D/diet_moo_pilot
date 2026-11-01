"""Atomic checkpoints and isolated sequential workers for laptop-sized cohorts."""
import contextlib
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from importlib.metadata import version
import numpy as np
from src.appo_experiments import ALGORITHMS, execute
from src.data_loader import get_dataset_path
from src.flexible_problem import FlexibleDietProblem
from src.diet_selector import select_final_diets
from src.evaluation import mean_intervention_count
from research_batch.common import ROOT, digest, read_json, write_json, scientific_hashes


@contextlib.contextmanager
def exclusive(workspace):
    workspace=Path(workspace);workspace.mkdir(parents=True,exist_ok=True)
    with (workspace/'batch.lock').open('a+b') as f:
        f.seek(0);f.write(b'0');f.flush();f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            raise ValueError('Another import/run/summary process holds this workspace lock') from None
        try:
            yield
        finally:
            f.seek(0)
            if os.name=='nt':
                msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(f,fcntl.LOCK_UN)


def job_path(batch, case, algorithm, seed):
    # Flat, compact paths also work on Windows without long-path support.
    identity=digest([case['participant'],case['case_hash'],algorithm,seed])[:32]
    return Path(batch)/'runs'/f'{identity}.json'


def worker(request):
    r=read_json(request)
    if scientific_hashes()!=r['source_hashes'] or hashlib.sha256(get_dataset_path().read_bytes()).hexdigest()!=r['dataset_sha256']:
        raise ValueError('Scientific source/workbook changed; start a new batch')
    case=read_json(r['case_file'])
    problem=FlexibleDietProblem(case['targets'],case['diet'])
    run=execute(problem,r['algorithm'],r['budget'],r['seed'])
    for x,f,diet in zip(run['X'],run['F'],run['diets']):
        if not np.all(problem.constraints(diet)<=0):
            raise ValueError('Returned diet failed independent validation')
        np.testing.assert_allclose(f,problem.objectives(diet),rtol=1e-10,atol=1e-10)
        if list(diet)!=list(case['diet']):
            raise ValueError('Meal identity changed')
    result=dict(participant=case['participant'],case_hash=case['case_hash'],algorithm=r['algorithm'],seed=r['seed'],
                status='completed' if len(run['F']) else 'no_feasible',evaluations=run['evaluations'],runtime=run['runtime'],
                feasibility=run['feasibility'],F=run['F'],X=run['X'],
                mean_interventions=mean_intervention_count(run['diets'],case['diet']) if run['diets'] else None,
                representatives=select_final_diets(run['X'],run['F'],run['diets']),
                formulation=problem.metadata(),validated=True)
    write_json(r['output'],result)


def run_batch(workspace, name, budget=15000, seeds=(42,), limit_participants=None, max_jobs=None, retry_failed=False, timeout=1800):
    workspace=Path(workspace).resolve(); batch=workspace/'batches'/name
    registry=read_json(workspace/'registry.json')
    if not registry:
        raise ValueError('Import questionnaire exports first')
    cohort=registry['participants']
    all_cases=[read_json(workspace/'cases'/f"{p}_{v['case_hash']}.json") for p,v in sorted(cohort.items())]
    policies=sorted({(c['restriction_policy'],c['calorie_adjustment_policy']) for c in all_cases})
    protocol=dict(version=1,algorithms=ALGORITHMS,budget=budget,seeds=list(seeds),
                  source_hashes=scientific_hashes(),dataset_sha256=hashlib.sha256(get_dataset_path().read_bytes()).hexdigest(),
                  python=platform.python_version(),packages={p:version(p) for p in ['numpy','pandas','scipy','pymoo','openpyxl']},
                  import_policies=[list(p) for p in policies],
                  hash_seed='0',threads=1,metric_policy='within-participant pooled-algorithm/seed reference; participant-equal macro summary and paired ranks')
    old=read_json(batch/'protocol.json')
    if old is not None and old!=protocol:
        raise ValueError('Batch protocol/source/environment changed. Use a NEW --batch name; existing results are preserved.')
    if old is None:
        write_json(batch/'protocol.json',protocol)
        for name_ in protocol['source_hashes']:
            dest=batch/'source_snapshot'/name_;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((ROOT/name_).read_bytes())
    write_json(batch/'cohort.json',cohort)
    ready=[case for case in all_cases if case['status']=='ready']
    if limit_participants is not None:
        ready=ready[:limit_participants]
    tasks=[]
    for case in ready:
        for seed in seeds:
            for algorithm in ALGORITHMS:
                output=job_path(batch,case,algorithm,seed)
                prior=read_json(output)
                if prior and (prior['status'] in ('completed','no_feasible') or not retry_failed):
                    continue
                tasks.append((case,algorithm,seed,output))
    pending=len(tasks)
    if max_jobs is not None:
        tasks=tasks[:max_jobs]
    print(f'{len(cohort)} registered participants; {sum(v["status"]=="ready" for v in cohort.values())} ready. {pending} pending jobs in selected scope; running {len(tasks)}.',flush=True)
    print('Restrictions are unmodelled where acknowledged. No participant records are uploaded.',flush=True)
    elapsed=[]
    for i,(case,algorithm,seed,output) in enumerate(tasks,1):
        request=dict(case_file=str(workspace/'cases'/f"{case['participant']}_{case['case_hash']}.json"),
                     algorithm=algorithm,seed=seed,budget=budget,output=str(output),
                     source_hashes=protocol['source_hashes'],dataset_sha256=protocol['dataset_sha256'])
        request_file=batch/'requests'/f'{digest(request)}.json';write_json(request_file,request)
        output.parent.mkdir(parents=True,exist_ok=True)
        started=time.perf_counter()
        print(f'[{i}/{len(tasks)}] {case["participant"]} {algorithm}, seed {seed}',flush=True)
        env=dict(os.environ,PYTHONHASHSEED='0',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        try:
            with output.with_suffix('.log').open('w',encoding='utf-8') as log:
                proc=subprocess.run([sys.executable,'-B',str(ROOT/'run_survey_benchmark.py'),'_worker',str(request_file)],
                                    cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            if proc.returncode!=0:
                raise RuntimeError(f'Worker exited {proc.returncode}; inspect adjacent .log')
        except (subprocess.TimeoutExpired, RuntimeError) as e:
            write_json(output,dict(participant=case['participant'],case_hash=case['case_hash'],algorithm=algorithm,
                                   seed=seed,status='failed',error=str(e),runtime=time.perf_counter()-started))
        elapsed.append(time.perf_counter()-started)
        result=read_json(output)
        eta=np.mean(elapsed)*(len(tasks)-i)/60
        print(f'  {result["status"]}; {len(result.get("F",[]))} feasible diets; ~{eta:.1f} min remaining in this invocation',flush=True)
    return batch
