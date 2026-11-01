import copy
import time
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.api import app
from backend.db import SessionLocal, Run, Experiment, User
from backend.analysis import finalize
from backend.worker import claim, recover
from config.user_profile import USER_PROFILE

def setup(signed, days=2):
    profile={k:v for k,v in USER_PROFILE.items() if k not in ('existing_diet','meals_per_day')}
    assert signed.put('/api/profile',json=profile).status_code==200
    diet={m:[{'food_code':i['food_code'],'servings':i['servings']} for i in items] for m,items in USER_PROFILE['existing_diet'].items()}
    payload={'title':'Two-day research input','days':[{'label':f'Day {i+1}','date':f'2026-10-{i+1:02d}','diet':copy.deepcopy(diet)} for i in range(days)]}
    if days>1:
        payload['days'][1]['diet']['breakfast'][0]['servings']=2
    response=signed.post('/api/submissions',json=payload)
    assert response.status_code==201,response.text
    return response.json(), profile

def test_auth_and_csrf(client):
    assert client.get('/api/profile').status_code==401
    data={'name':'A','email':'a@example.org','password':'twelve-character-password'}
    with TestClient(app) as untrusted:
        assert untrusted.post('/api/auth/register',json=data).status_code==403
    response=client.post('/api/auth/register',json=data)
    assert response.status_code==201
    cookie=response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie
    with SessionLocal() as db:
        user=db.scalar(select(User))
        assert user.password_hash.startswith('$argon2') and data['password'] not in user.password_hash
    client.post('/api/auth/logout')
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/login',json={'email':data['email'],'password':'wrong'}).status_code==401
    assert client.post('/api/auth/login',json={'email':data['email'],'password':data['password']}).status_code==200

def test_multi_day_snapshots_and_ownership(signed):
    submission,profile=setup(signed)
    ids=[d['id'] for d in submission['days']]
    response=signed.post('/api/experiments',json={'day_ids':ids,'algorithms':['APPO','SPEA2'],'seeds':[42,43],'budget':1000})
    assert response.status_code==201,response.text
    experiments=response.json()['experiment_ids']
    assert len(experiments)==2
    a=signed.get('/api/experiments/'+experiments[0]).json()
    b=signed.get('/api/experiments/'+experiments[1]).json()
    assert a['snapshot']['day']['diet']!=b['snapshot']['day']['diet']
    assert len(a['runs'])==4
    profile['weight_kg']=70
    signed.put('/api/profile',json=profile)
    assert signed.get('/api/experiments/'+experiments[0]).json()['snapshot']['profile']['weight_kg']==57.5
    with TestClient(app,headers={'X-DietLab-Request':'1'}) as other:
        assert other.post('/api/auth/register',json={'name':'Other','email':'other@example.org','password':'another-long-password'}).status_code==201
        for endpoint in ['/api/experiments/'+experiments[0],'/api/runs/'+a['runs'][0]['id'],'/api/experiments/'+experiments[0]+'/export','/api/experiments/'+experiments[0]+'/metrics.csv','/api/runs/'+a['runs'][0]['id']+'/diets.csv']:
            assert other.get(endpoint).status_code==404
        assert other.post('/api/runs/'+a['runs'][0]['id']+'/cancel').status_code==404

def test_validation_and_drafts(signed):
    assert signed.put('/api/profile',json={'age':12}).status_code==422
    submission,_=setup(signed,1)
    day=submission['days'][0]
    del day['id'];day.pop('updated',None)
    day['diet']['breakfast'][0]['food_code']='NOT-IN-DATABASE'
    assert signed.post('/api/submissions',json={'title':'Invalid','days':[day]}).status_code==422
    day['diet']={m:[] for m in USER_PROFILE['existing_diet']}
    saved=signed.post('/api/submissions',json={'title':'Draft','days':[day]})
    assert saved.status_code==201
    id=saved.json()['days'][0]['id']
    assert signed.post('/api/experiments',json={'day_ids':[id],'algorithms':['APPO']}).status_code==422

def test_cancel_and_recovery(signed):
    submission,_=setup(signed,1)
    response=signed.post('/api/experiments',json={'day_ids':[submission['days'][0]['id']],'algorithms':['APPO'],'budget':100})
    id=response.json()['experiment_ids'][0]
    run=signed.get('/api/experiments/'+id).json()['runs'][0]
    assert signed.post('/api/runs/'+run['id']+'/cancel').json()['status']=='cancelled'
    finalize(id)
    assert signed.get('/api/experiments/'+id).json()['comparison']['available'] is False
    assert claim() is None
    with SessionLocal() as db:
        r=db.get(Run,run['id']);r.status='running';r.heartbeat=time.time()-300;db.commit()
    recover()
    assert signed.get('/api/runs/'+run['id']).json()['status']=='failed'

def test_single_algorithm_no_self_reference(signed):
    submission,_=setup(signed,1)
    id=signed.post('/api/experiments',json={'day_ids':[submission['days'][0]['id']],'algorithms':['APPO']}).json()['experiment_ids'][0]
    with SessionLocal() as db:
        r=db.scalar(select(Run).where(Run.experiment_id==id));r.status='no_feasible';db.commit()
    finalize(id)
    comparison=signed.get('/api/experiments/'+id).json()['comparison']
    assert comparison['available'] is False
    assert 'two algorithms' in comparison['reason']
    assert signed.get('/api/experiments/'+id+'/metrics.csv').status_code==409

def test_common_reference_statistics_and_csv(signed):
    submission,_=setup(signed,1)
    id=signed.post('/api/experiments',json={'day_ids':[submission['days'][0]['id']],
        'algorithms':['APPO','NSGA-II'],'seeds':[42,43,44],'budget':100}).json()['experiment_ids'][0]
    with SessionLocal() as db:
        runs=list(db.scalars(select(Run).where(Run.experiment_id==id)))
        for r in runs:
            shift=(r.seed-42)/100
            front=[[.1+shift,.4,.2,.1],[.4,.1+shift,.1,.2]] if r.algorithm=='APPO' else [[.3+shift,.5,.2,.1],[.5,.3+shift,.1,.2]]
            r.status='completed'
            r.result={'F':front,'summary':{'feasibility':1.,'runtime':2.,'evaluations':100,'mean_interventions':4}}
        db.commit()
    finalize(id)
    value=signed.get('/api/experiments/'+id).json()['comparison']
    assert value['available'] and value['version']==1
    assert len(value['metrics'])==6 and len(value['statistics'])==8
    assert all(s['PairedSeeds']==3 for s in value['statistics'])
    assert all(0<=r['HV']<=1.1**4 for r in value['metrics'])
    assert all(r['IGD']>=0 for r in value['metrics'])
    exported=signed.get('/api/experiments/'+id+'/metrics.csv')
    assert exported.status_code==200 and exported.text.count('\n')==7
    finalize(id)
    assert signed.get('/api/experiments/'+id).json()['comparison']==value
