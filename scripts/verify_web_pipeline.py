"""End-to-end verification against the running local API and PostgreSQL worker.

Creates a separate validation account and two distinct input days. Runs all six
algorithms at the full budget on day one and APPO on day two. Does not alter
existing users or research results. Writes IDs and evidence, never passwords.
"""
import copy
import json
from pathlib import Path
import sys
import time
import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.user_profile import USER_PROFILE

def main():
    client = httpx.Client(base_url='http://127.0.0.1:8000', headers={'X-DietLab-Request':'1'}, timeout=60)
    account = {'name':'Pipeline validation', 'email':'validation@dietlab.example.org', 'password':'DietLab-Local-Test-2026!'}
    response = client.post('/api/auth/register',json=account)
    if response.status_code == 409:
        response = client.post('/api/auth/login',json={k:account[k] for k in ('email','password')})
    response.raise_for_status()
    output=ROOT/'.local'/'flexible-web-verification.json'
    if '--resume' in sys.argv:
        evidence=json.loads(output.read_text())
        evidence['results']=[]
        ids=evidence['experiment_ids']
    else:
        profile={k:v for k,v in USER_PROFILE.items() if k not in ('existing_diet','meals_per_day')}
        client.put('/api/profile',json=profile).raise_for_status()
        diet={m:[{'food_code':i['food_code'],'servings':i['servings']} for i in items] for m,items in USER_PROFILE['existing_diet'].items()}
        second=copy.deepcopy(diet)
        second['breakfast'][0]['servings']=2
        second['Mid-morning']=[second['breakfast'].pop()]
        second['Skipped meal']=[]
        submission=client.post('/api/submissions',json={'title':'Full-budget application validation','days':[
            {'label':'Validation day 1','date':'2026-10-30','diet':diet},
            {'label':'Validation day 2','date':'2026-10-31','diet':second}]})
        submission.raise_for_status()
        ids=[]
        for day, algorithms in zip(submission.json()['days'],[['APPO','NSGA-II','NSGA-III','MOEA/D','SPEA2','MOPSO'],['APPO']]):
            r=client.post('/api/experiments',json={'day_ids':[day['id']],'algorithms':algorithms,'seeds':[42],'budget':15000})
            r.raise_for_status()
            ids.extend(r.json()['experiment_ids'])
        evidence={'experiment_ids':ids,'budget':15000,'results':[]}
        output.write_text(json.dumps(evidence,indent=2))
        print('Queued full-budget validation experiments:',ids,flush=True)
    for id in ids:
        last=None
        deadline=time.monotonic()+7200
        while time.monotonic()<deadline:
            try:
                response=client.get('/api/experiments/'+id); response.raise_for_status()
            except httpx.TransportError:
                time.sleep(2)
                continue
            exp=response.json()
            status=[(r['algorithm'],r['status'],r['progress']) for r in exp['runs']]
            if status!=last:
                print(status,flush=True); last=status
            if not any(r['status'] in ('queued','running') for r in exp['runs']) and exp['comparison'] is not None:
                break
            time.sleep(5)
        else:
            raise TimeoutError('Validation jobs did not finish')
        assert all(r['status'] in ('completed','no_feasible') for r in exp['runs']),status
        details=[]
        for run in exp['runs']:
            detail=client.get('/api/runs/'+run['id']).json()
            result=detail['result']
            assert result and result['summary']['evaluations']<=15000
            for solution in result['solutions']:
                assert len(solution['constraints'])==len(exp['snapshot'].get('constraint_labels',list(range(33)))) and max(solution['constraints'])<=1e-12
            assert client.get('/api/runs/'+run['id']+'/diets.csv').status_code==200
            details.append({'algorithm':run['algorithm'],'status':run['status'],**result['summary']})
        assert any(r['status']=='completed' for r in exp['runs']), 'No recommendation for this validation day'
        assert client.get('/api/experiments/'+id+'/export').status_code==200
        evidence['results'].append({'id':id,'day':exp['snapshot']['day'],'runs':details,'comparison_available':exp['comparison']['available']})
        output.write_text(json.dumps(evidence,indent=2))
    assert evidence['results'][0]['day']['diet']!=evidence['results'][1]['day']['diet']
    print('PASS: real PostgreSQL queue, seven full-budget jobs, distinct day outputs, versioned constraints and exports.',flush=True)

if __name__=='__main__':
    main()
