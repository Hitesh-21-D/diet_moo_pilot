import csv
import json
from pathlib import Path
import pytest
from research_batch.importer import import_export, FILES
from research_batch.common import read_json, write_json
from research_batch.runner import run_batch, job_path
from research_batch.reporting import summarize
from src.appo_experiments import ALGORITHMS


def export(tmp_path, identities=('a',), custom=False, invalid=False):
    folder=tmp_path/'export';folder.mkdir(exist_ok=True)
    participants=[dict(response_id=i,age='2007' if invalid else '25',sex='male',height_cm='175',weight_kg='70',
                       goal='Weight maintenance',activity='Moderately active',diet='Vegetarian',foods_avoided='Peanuts',
                       other_avoided='',meal_order='breakfast',meal_labels='["Brunch"]',meal_count='1',skipped_meals='',
                       consent_version='v1',consent_timestamp='2026-10-31',schema_version='v1',catalog_version='test') for i in identities]
    logs=[dict(response_id=i,meal='breakfast',meal_index='0',meal_label='Brunch',entry_index='0',
               food_code='' if custom else 'ASC144',food_name='My food' if custom else 'Idli',
               quantity='1',serving_unit='idli',source='CUSTOM' if custom else 'INDB') for i in identities]
    for name,rows,fields in zip(FILES,[participants,logs,logs if custom else [],[]],
                                [list(participants[0]),list(logs[0]),list(logs[0]),['response_id','reason']]):
        with (folder/name).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    return folder


def test_import_append_and_no_duplicate_participants(tmp_path):
    workspace=tmp_path/'work'
    source=export(tmp_path)
    first=import_export(source,workspace)
    assert first['ready']==1
    before=read_json(workspace/'registry.json')
    import_export(source,workspace)
    assert read_json(workspace/'registry.json')==before
    source=export(tmp_path,('a','b'))
    assert import_export(source,workspace)['registered_total']==2


def test_custom_food_requires_explicit_mapping_and_not_counted_twice(tmp_path):
    source=export(tmp_path,custom=True);workspace=tmp_path/'work'
    assert import_export(source,workspace)['blocked']==1
    corrections=tmp_path/'corrections.json'
    write_json(corrections,{'a':{'reason':'Verified participant correction','entries':{
        'breakfast:0':{'reason':'Confirmed one idli in source unit','foods':[{'food_code':'ASC144','servings':1}]}}}})
    assert import_export(source,workspace,corrections)['ready']==1
    r=read_json(workspace/'registry.json')['participants']; key=next(iter(r))
    case=read_json(workspace/'cases'/f"{key}_{r[key]['case_hash']}.json")
    assert case['diet']=={'1. Brunch':[{'food_code':'ASC144','servings':1.0}]}
    assert case['restriction_policy']=='acknowledge-unmodelled'
    assert import_export(source,workspace,corrections,restriction_policy='exclude')['blocked']==1


def test_invalid_profile_is_not_imputed(tmp_path):
    source=export(tmp_path,invalid=True)
    result=import_export(source,tmp_path/'work')
    assert result['ready']==0
    assert any('profile age' in k for k in result['issue_counts'])


def test_aggregate_excludes_incomplete_cohorts_and_uses_participants(tmp_path):
    batch=tmp_path/'batch'
    write_json(batch/'protocol.json',dict(algorithms=ALGORITHMS,seeds=[42,43],budget=100))
    cohort={p:dict(status='ready',case_hash=p) for p in ['a','b']}
    write_json(batch/'cohort.json',cohort)
    for participant in cohort:
        for seed in [42,43]:
            for algorithm in ALGORITHMS:
                case=dict(participant=participant,case_hash=participant)
                value=.1 if algorithm=='APPO' else .3
                write_json(job_path(batch,case,algorithm,seed),dict(algorithm=algorithm,seed=seed,status='completed',
                    F=[[value,.4,.1,.2],[.4,value,.2,.1]],runtime=1.,evaluations=100,feasibility=1.,mean_interventions=2.))
    assert summarize(batch)['complete_participants']==2
    import pandas as pd
    stats=pd.read_csv(batch/'reports/paired_statistics.csv')
    assert (stats.PairedSeeds==2).all()  # two participants, not four participant-seed pairs
    bad=job_path(batch,dict(participant='b',case_hash='b'),'MOPSO',43)
    write_json(bad,dict(status='failed'))
    assert summarize(batch)['complete_participants']==1
    cov=pd.read_csv(batch/'reports/coverage.csv')
    assert cov.FailedRuns.sum()==1


def test_no_feasible_is_not_a_worker_failure(tmp_path):
    batch=tmp_path/'batch';case=dict(participant='a',case_hash='a')
    write_json(batch/'protocol.json',dict(algorithms=ALGORITHMS,seeds=[42],budget=100))
    write_json(batch/'cohort.json',{'a':dict(status='ready',case_hash='a')})
    for a in ALGORITHMS:
        write_json(job_path(batch,case,a,42),dict(algorithm=a,seed=42,status='no_feasible',F=[],runtime=1.,
                                               evaluations=100,feasibility=0.,mean_interventions=None))
    result=summarize(batch)
    assert result['complete_participants']==1 and result['failed_runs']==0
    import pandas as pd
    summary=pd.read_csv(batch/'reports/aggregate_metrics.csv')
    assert (summary.Success_mean==0).all() and (summary.HV_mean==0).all()
    assert (summary.IGD_count==0).all()


def test_resume_and_protocol_guard_without_reexecuting(tmp_path,monkeypatch):
    workspace=tmp_path/'work';import_export(export(tmp_path),workspace)
    # No selected jobs: create the protocol and then install valid checkpoints.
    batch=run_batch(workspace,'test',budget=100,seeds=[42],max_jobs=0)
    registry=read_json(workspace/'registry.json')['participants']; participant=next(iter(registry))
    case=dict(participant=participant,case_hash=registry[participant]['case_hash'])
    for a in ALGORITHMS:
        write_json(job_path(batch,case,a,42),dict(status='no_feasible'))
    def unexpected(*args,**kwargs):
        raise AssertionError('Completed jobs must not be executed again')
    monkeypatch.setattr('research_batch.runner.subprocess.run',unexpected)
    run_batch(workspace,'test',budget=100,seeds=[42])
    with pytest.raises(ValueError,match='protocol'):
        run_batch(workspace,'test',budget=200,seeds=[42])
