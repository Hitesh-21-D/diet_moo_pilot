"""Durable PostgreSQL job worker; separate, cancellable process for every run."""
import os
import subprocess
import sys
import time
from sqlalchemy import select
from backend.db import SessionLocal, Run, Experiment, ROOT
from backend.analysis import finalize

def recover():
    with SessionLocal() as db:
        stale=list(db.scalars(select(Run).where(Run.status=='running',Run.heartbeat<time.time()-120).with_for_update(skip_locked=True)))
        for row in stale:
            row.status='failed'
            row.error='Worker was interrupted. Create a new run to retry; no partial result was published.'
            row.finished=time.time()
        db.commit()

def claim():
    with SessionLocal() as db:
        row=db.scalar(select(Run).where(Run.status=='queued').order_by(Run.created).with_for_update(skip_locked=True).limit(1))
        if not row:
            return None
        row.status='running'
        row.started=row.heartbeat=time.time()
        db.commit()
        return row.id,row.experiment_id

def work_once():
    recover()
    job=claim()
    if not job:
        with SessionLocal() as db:
            ids=list(db.scalars(select(Experiment.id).where(Experiment.comparison.is_(None))))
        for id in ids:
            finalize(id)
        return False
    id,experiment_id=job
    logdir=ROOT/'.local'/'logs'
    logdir.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1')
    started=time.monotonic()
    with (logdir/f'{id}.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen([sys.executable,'-B','-m','backend.compute',id],cwd=ROOT,env=env,
            stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            while process.poll() is None:
                with SessionLocal() as db:
                    row=db.get(Run,id)
                    if row.cancel_requested or time.monotonic()-started>1800:
                        process.terminate()
                        process.wait(timeout=20)
                        row.status='cancelled' if row.cancel_requested else 'failed'
                        row.error=None if row.cancel_requested else 'Run exceeded the 30-minute execution limit.'
                        row.finished=time.time()
                        db.commit()
                        break
                    row.heartbeat=time.time()
                    db.commit()
                time.sleep(2)
        except BaseException:
            process.terminate()
            process.wait(timeout=20)
            with SessionLocal() as db:
                row=db.get(Run,id)
                if row.status=='running':
                    row.status='failed'
                    row.error='Worker stopped. Start a new run to retry.'
                    row.finished=time.time()
                    db.commit()
            raise
    with SessionLocal() as db:
        row=db.get(Run,id)
        if row.status=='running':
            row.status='cancelled' if row.cancel_requested else 'failed'
            row.error=None if row.cancel_requested else 'Computation process exited before publishing a result. Inspect the local worker log.'
            row.finished=time.time()
            db.commit()
    finalize(experiment_id)
    return True

if __name__=='__main__':
    print('DietLab worker ready. Jobs run sequentially; Ctrl+C stops the worker.',flush=True)
    while True:
        if not work_once():
            time.sleep(3)
