import csv
import hashlib
import io
import json
import time
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from argon2.exceptions import VerificationError
from backend.db import get_db, User, LoginSession, Profile, Submission, DietDay, Experiment, Run, ROOT
from backend.schemas import Register, Login, ProfileInput, SubmissionInput, DayInput, ExperimentInput
from backend.security import current_user, hasher, create_session, throttle, COOKIE, token_hash
from backend.catalog import catalog, validate_diet, decoded_input, dataset_hash
from src.nutrient_targets import calculate_nutrient_targets
from src.diet_representation import calculate_diet_totals

app = FastAPI(title='DietLab Research API', version='1.0.0')

@app.middleware('http')
async def protections(request: Request, call_next):
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        origin = request.headers.get('origin')
        allowed = {'http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000'}
        if request.headers.get('x-dietlab-request') != '1' or (origin and origin not in allowed):
            return JSONResponse({'detail':'Request origin could not be verified'}, status_code=403)
        try:
            length = int(request.headers.get('content-length','0'))
        except ValueError:
            return JSONResponse({'detail':'Invalid content length'}, status_code=400)
        if length > 2_000_000:
            return JSONResponse({'detail':'Request too large'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    return response

def own(db, cls, id, user):
    obj = db.get(cls, id)
    if not obj or obj.user_id != user.id:
        raise HTTPException(404, 'Record not found')
    return obj

def user_json(user):
    return dict(id=user.id, name=user.name, email=user.email)

@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {'status':'ok','application':'DietLab'}

@app.post('/api/auth/register', status_code=201)
def register(data: Register, request: Request, response: Response, db: Session = Depends(get_db)):
    throttle(request)
    if not data.name.strip():
        raise HTTPException(422, 'Name cannot be blank')
    user = User(name=data.name.strip(), email=str(data.email).lower(), password_hash=hasher.hash(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'An account with this email already exists')
    create_session(db,user,response)
    return user_json(user)

@app.post('/api/auth/login')
def login(data: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    throttle(request)
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    try:
        if not user or not hasher.verify(user.password_hash, data.password):
            raise HTTPException(401, 'Email or password is incorrect')
    except VerificationError:
        raise HTTPException(401, 'Email or password is incorrect')
    create_session(db,user,response)
    return user_json(user)

@app.post('/api/auth/logout')
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(request.cookies.get(COOKIE,''))))
    db.commit()
    response.delete_cookie(COOKIE, path='/')
    return {'ok':True}

@app.get('/api/auth/me')
def me(user: User = Depends(current_user)):
    return user_json(user)

@app.get('/api/profile')
def profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Profile,user.id)
    return {'profile':p.data if p else None, 'targets':calculate_nutrient_targets(p.data) if p else None}

@app.put('/api/profile')
def save_profile(data: ProfileInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    values = data.model_dump()
    targets = calculate_nutrient_targets(values)
    if targets['energy_kcal'] <= 0 or targets['carb_g'] <= 0:
        raise HTTPException(422, 'These inputs produce invalid targets; revise the goal or adjustment')
    p = db.get(Profile,user.id)
    if not p:
        p = Profile(user_id=user.id, data=values)
        db.add(p)
    p.data, p.updated = values, time.time()
    db.commit()
    return {'profile':values,'targets':targets}

@app.get('/api/foods')
def foods(user: User = Depends(current_user)):
    return catalog()

def day_json(d):
    return dict(id=d.id,label=d.label,date=d.date,diet=d.diet,updated=d.updated)

@app.get('/api/submissions')
def submissions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    result=[]
    for s in db.scalars(select(Submission).where(Submission.user_id==user.id).order_by(Submission.created.desc())):
        days=list(db.scalars(select(DietDay).where(DietDay.submission_id==s.id).order_by(DietDay.date,DietDay.label,DietDay.id)))
        result.append(dict(id=s.id,title=s.title,created=s.created,days=[day_json(d) for d in days]))
    return result

@app.post('/api/submissions',status_code=201)
def save_submission(data: SubmissionInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        for day in data.days:
            validate_diet(day.model_dump(mode='json')['diet'], allow_empty=True)
    except ValueError as e:
        raise HTTPException(422,str(e))
    submission=Submission(user_id=user.id,title=data.title)
    db.add(submission)
    db.flush()
    days=[]
    for day in data.days:
        values=day.model_dump(mode='json')
        d=DietDay(user_id=user.id,submission_id=submission.id,**values)
        db.add(d)
        db.flush()
        days.append(day_json(d))
    db.commit()
    return dict(id=submission.id,title=submission.title,days=days)

@app.put('/api/days/{id}')
def update_day(id: str, data: DayInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    day=own(db,DietDay,id,user)
    values=data.model_dump(mode='json')
    try:
        validate_diet(values['diet'], allow_empty=True)
    except ValueError as e:
        raise HTTPException(422,str(e))
    for key,value in values.items():
        setattr(day,key,value)
    day.updated=time.time()
    db.commit()
    return day_json(day)

@app.post('/api/experiments',status_code=201)
def create_experiments(data: ExperimentInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p=db.get(Profile,user.id)
    if not p:
        raise HTTPException(422,'Complete your profile first')
    days=[own(db,DietDay,id,user) for id in data.day_ids]
    try:
        for day in days:
            validate_diet(day.diet)
    except ValueError as error:
        raise HTTPException(422, f'{day.label}: {error}')
    active = list(db.scalars(select(Run).join(Experiment).where(Experiment.user_id==user.id,Run.status.in_(['queued','running']))))
    if len(active)+len(days)*len(data.algorithms)*len(data.seeds)>210:
        raise HTTPException(409,'Please finish or cancel existing jobs before adding more than 210 pending runs')
    source_hash=hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'src').rglob('*.py')))).hexdigest()
    ids=[]
    for day in days:
        # A separate immutable comparison cohort for EACH day.
        snap=dict(profile=p.data,targets=calculate_nutrient_targets(p.data),day=day_json(day),
                  input_diet=decoded_input(day.diet),input_totals=calculate_diet_totals(decoded_input(day.diet)),
                  dataset_sha256=dataset_hash(),source_sha256=source_hash,algorithms=data.algorithms,
                  seeds=data.seeds,budget=data.budget)
        from src.flexible_problem import FlexibleDietProblem
        snap.update(FlexibleDietProblem(snap['targets'], day.diet).metadata())
        exp=Experiment(user_id=user.id,day_id=day.id,label=day.label,snapshot=snap)
        db.add(exp)
        db.flush()
        ids.append(exp.id)
        for seed in data.seeds:
            for name in data.algorithms:
                db.add(Run(experiment_id=exp.id,algorithm=name,seed=seed,budget=data.budget))
    db.commit()
    return {'experiment_ids':ids}

def run_json(r, detail=False):
    value=dict(id=r.id,algorithm=r.algorithm,seed=r.seed,budget=r.budget,status=r.status,
               progress=r.progress,started=r.started,finished=r.finished,error=r.error,cancel_requested=r.cancel_requested)
    if r.result:
        value['summary']=r.result['summary']
    if detail:
        value['result']=r.result
    return value

def run_summaries(db, experiment_id):
    # Polling lists should not transfer every archived chromosome/diet from
    # PostgreSQL. Fetch the full archive only for an inspected run or export.
    fields=['id','algorithm','seed','budget','status','progress','started','finished','error','cancel_requested']
    query=select(*(getattr(Run,k) for k in fields),Run.result['summary'].label('summary')).where(
        Run.experiment_id==experiment_id).order_by(Run.created,Run.algorithm,Run.seed,Run.id)
    return [dict(row) for row in db.execute(query).mappings()]

@app.get('/api/experiments')
def experiments(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [dict(id=e.id,label=e.label,created=e.created,day_date=e.snapshot['day']['date'],
                 runs=run_summaries(db,e.id))
            for e in db.scalars(select(Experiment).where(Experiment.user_id==user.id).order_by(Experiment.created.desc()))]

@app.get('/api/experiments/{id}')
def experiment(id: str,user: User = Depends(current_user),db: Session = Depends(get_db)):
    e=own(db,Experiment,id,user)
    return dict(id=e.id,label=e.label,created=e.created,snapshot=e.snapshot,comparison=e.comparison,
                runs=run_summaries(db,e.id))

@app.get('/api/runs/{id}')
def run(id: str,user: User = Depends(current_user),db: Session = Depends(get_db)):
    r=db.get(Run,id)
    if not r:
        raise HTTPException(404,'Run not found')
    own(db,Experiment,r.experiment_id,user)
    return run_json(r,True)

@app.post('/api/runs/{id}/cancel')
def cancel(id: str,user: User = Depends(current_user),db: Session = Depends(get_db)):
    r=db.get(Run,id)
    if not r:
        raise HTTPException(404,'Run not found')
    own(db,Experiment,r.experiment_id,user)
    if r.status=='queued':
        r.status,r.finished='cancelled',time.time()
    elif r.status=='running':
        r.cancel_requested=True
    db.commit()
    return run_json(r)

@app.get('/api/experiments/{id}/export')
def export(id: str,user: User = Depends(current_user),db: Session = Depends(get_db)):
    e=own(db,Experiment,id,user)
    return Response(json.dumps(dict(snapshot=e.snapshot,comparison=e.comparison,runs=[run_json(r,True) for r in
                    db.scalars(select(Run).where(Run.experiment_id==id))]),indent=2,allow_nan=False),
                    media_type='application/json',headers={'Content-Disposition':f'attachment; filename="dietlab-{id}.json"'})

@app.get('/api/experiments/{id}/metrics.csv')
def metrics_csv(id: str,user: User = Depends(current_user),db: Session = Depends(get_db)):
    e=own(db,Experiment,id,user)
    if not e.comparison or not e.comparison.get('available'):
        raise HTTPException(409,'A completed comparative cohort is required')
    rows=e.comparison['metrics']
    buffer=io.StringIO()
    writer=csv.DictWriter(buffer,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return Response(buffer.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="metrics-{id}.csv"'})

@app.get('/api/runs/{id}/diets.csv')
def diets_csv(id: str,user: User = Depends(current_user),db: Session = Depends(get_db)):
    r=db.get(Run,id)
    if not r:
        raise HTTPException(404,'Run not found')
    e=own(db,Experiment,r.experiment_id,user)
    if not r.result:
        raise HTTPException(409,'Results are not ready')
    from src.report import create_diet_rows
    rows=create_diet_rows(r.algorithm,r.result['representatives'],e.snapshot['day']['diet'])
    buffer=io.StringIO()
    writer=csv.DictWriter(buffer,fieldnames=list(rows[0]) if rows else ['algorithm','diet_type','meal','food_name','servings'])
    writer.writeheader()
    writer.writerows(rows)
    return Response(buffer.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="diets-{id}.csv"'})

@app.get('/{path:path}',include_in_schema=False)
def frontend(path: str):
    dist=ROOT/'frontend'/'dist'
    target=(dist/path).resolve()
    if dist.resolve() not in target.parents:
        target=dist/'index.html'
    if target.is_file():
        return FileResponse(target)
    if (dist/'index.html').exists() and not path.startswith('api/'):
        return FileResponse(dist/'index.html')
    raise HTTPException(404,'Build the frontend with npm run build, or use the Vite development server')
