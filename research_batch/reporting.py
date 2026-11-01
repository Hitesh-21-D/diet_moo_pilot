"""Compare within respondents; aggregate respondents, not pooled Pareto fronts."""
from pathlib import Path
import numpy as np
import pandas as pd
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from src.metrics import get_normalization_bounds, normalize_front, calculate_hypervolume, calculate_igd, calculate_spacing, calculate_petq
from run_repeated_experiments import paired_statistics
from research_batch.common import read_json, write_json
from research_batch.runner import job_path

METRICS=['HV','IGD','Spacing','PETQ','Feasibility','Runtime','Evaluations','UniqueFeasibleDiets',
         'MeanNutritionDeviation','MeanHabitDeviation','MeanInterventions','Success']


def summarize(batch):
    batch=Path(batch);protocol=read_json(batch/'protocol.json');cohort=read_json(batch/'cohort.json')
    if not protocol or cohort is None:
        raise ValueError('No batch protocol/cohort; run the batch first')
    rows=[]; coverage=[]
    expected=len(protocol['algorithms'])*len(protocol['seeds'])
    for participant, entry in sorted(cohort.items()):
        case=dict(participant=participant,case_hash=entry['case_hash'])
        jobs=[read_json(job_path(batch,case,a,s)) for s in protocol['seeds'] for a in protocol['algorithms']]
        completed=sum(bool(j and j['status'] in ('completed','no_feasible')) for j in jobs)
        failed=sum(bool(j and j['status']=='failed') for j in jobs)
        complete=entry['status']=='ready' and completed==expected
        coverage.append(dict(Participant=participant,ImportStatus=entry['status'],ExpectedRuns=expected,
                             CompletedRuns=completed,FailedRuns=failed,MissingRuns=expected-completed-failed,
                             IncludedInComparison=complete))
        if not complete:
            continue
        fronts={str(i):np.array(j['F'],dtype=float).reshape(-1,4) for i,j in enumerate(jobs)}
        valid=[f for f in fronts.values() if len(f)]
        if valid:
            all_f=np.unique(np.vstack(valid),axis=0)
            reference=all_f[NonDominatedSorting().do(all_f,only_non_dominated_front=True)]
            ideal,nadir=get_normalization_bounds(fronts)
            norm_reference=normalize_front(reference,ideal,nadir)
        else:
            reference=np.empty((0,4));ideal=np.zeros(4);nadir=np.ones(4);norm_reference=reference
        write_json(batch/'reports'/'references'/f'{participant}.json',dict(case_hash=entry['case_hash'],
                    ideal=ideal,nadir=nadir,reference_front=reference,hv_reference=[1.1]*4))
        for i,job in enumerate(jobs):
            f=fronts[str(i)];normalized=normalize_front(f,ideal,nadir)
            hv=calculate_hypervolume(normalized) if len(f) else 0.
            igd=calculate_igd(normalized,norm_reference) if len(f) and len(reference) else np.nan
            rows.append(dict(Participant=participant,Algorithm=job['algorithm'],Seed=job['seed'],Status=job['status'],
                UniqueFeasibleDiets=len(f),Success=float(len(f)>0),HV=hv,IGD=igd,
                Spacing=calculate_spacing(normalized) if len(f) else np.nan,
                PETQ=calculate_petq(hv,igd,job['mean_interventions']) if len(f) else 0.,
                Feasibility=job['feasibility'],Runtime=job['runtime'],Evaluations=job['evaluations'],
                MeanNutritionDeviation=float(f[:,0].mean()) if len(f) else np.nan,
                MeanHabitDeviation=float(f[:,1].mean()) if len(f) else np.nan,MeanInterventions=job['mean_interventions']))
    report=batch/'reports';report.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(coverage).to_csv(report/'coverage.csv',index=False)
    frame=pd.DataFrame(rows,columns=['Participant','Algorithm','Seed','Status',*METRICS]).replace([np.inf,-np.inf],np.nan)
    frame.to_csv(report/'per_run_metrics.csv',index=False)
    complete_count=sum(c['IncludedInComparison'] for c in coverage)
    summary_info=dict(registered=len(cohort),ready=sum(c['ImportStatus']=='ready' for c in coverage),
                      complete_participants=complete_count,blocked=sum(c['ImportStatus']=='blocked' for c in coverage),
                      failed_runs=sum(c['FailedRuns'] for c in coverage),expected_runs_per_ready_participant=expected,
                      partial=complete_count!=sum(c['ImportStatus']=='ready' for c in coverage))
    write_json(report/'summary.json',summary_info)
    if len(frame):
        # Each participant contributes once regardless of the number of seeds.
        means=frame.groupby(['Participant','Algorithm'],sort=True)[METRICS].mean().reset_index()
        means['HV_rank']=means.groupby('Participant').HV.rank(ascending=False,method='average')
        means['Success_rank']=means.groupby('Participant').Success.rank(ascending=False,method='average')
        means.to_csv(report/'per_participant_metrics.csv',index=False)
        aggregate=means.groupby('Algorithm')[[*METRICS,'HV_rank','Success_rank']].agg(['mean','std','median','count'])
        aggregate.columns=['_'.join(c) for c in aggregate.columns]
        aggregate.reset_index().to_csv(report/'aggregate_metrics.csv',index=False)
        paired_statistics(means.rename(columns={'Participant':'Seed'})).to_csv(report/'paired_statistics.csv',index=False)
        print(aggregate[['Success_mean','HV_rank_mean','HV_mean','IGD_mean','Runtime_mean']].to_string(float_format=lambda n:f'{n:.4f}'),flush=True)
    else:
        for name in ['per_participant_metrics','aggregate_metrics','paired_statistics']:
            (report/f'{name}.csv').write_text('No complete participant cohorts\n',encoding='utf-8')
        print('No complete participant cohorts yet. Completed job checkpoints are retained.',flush=True)
    (report/'README.txt').write_text(
        'Research-only benchmark. Dietary preferences and food avoidances are not enforced when acknowledged at import.\n'
        'Coverage.csv accounts for every registered participant; blocked/incomplete/failed cohorts are not silently scored.\n'
        'Reference fronts and normalization are pooled across all six algorithms and selected seeds WITHIN each participant.\n'
        'Never pool fronts across different participants. Macro metrics average participant seed-means with equal participant weight.\n'
        'HV_rank (lower is better) and Success (higher is better) are the primary cohort summaries. Raw macro HV/IGD are descriptive\n'
        'averages of participant-relative scores, not a global-front performance measure. No-feasible runs have HV/PETQ=0, Success=0;\n'
        'IGD/spacing/deviation/interventions are missing. Their means are conditional on successful runs: inspect count and coverage.\n'
        'Paired Wilcoxon comparisons use participants (seed-averaged), not participant-seed pairs, as the sampling units.\n'
        'Holm correction covers the reported comparisons. These exploratory tests do not prove universal superiority.\n'
        'Changing cohort membership regenerates these reports; protocol and per-participant raw checkpoints are retained.\n',encoding='utf-8')
    print(f'Comparison coverage: {complete_count}/{len(cohort)} registered participants; reports: {report}',flush=True)
    return summary_info
