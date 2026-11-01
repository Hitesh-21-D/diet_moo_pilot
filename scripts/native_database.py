"""Project-local PostgreSQL on Windows: no Docker, administrator or service installation."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import zipfile
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent.parent
LOCAL=ROOT/'.local'
BIN=LOCAL/'postgres'/'pgsql'/'bin'
DATA=LOCAL/'pgdata'
FLAGS=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0

def command(arguments, **kwargs):
    return subprocess.run([str(a) for a in arguments],cwd=ROOT,creationflags=FLAGS,check=True,**kwargs)

def start():
    LOCAL.mkdir(exist_ok=True)
    if not BIN.exists():
        archive=LOCAL/'downloads'/'postgresql.zip'
        if not archive.exists():
            raise SystemExit('Download the official EDB Windows PostgreSQL binaries to .local/downloads/postgresql.zip first.')
        destination=LOCAL/'postgres'
        with zipfile.ZipFile(archive) as zip:
            for member in zip.infolist():
                target=(destination/member.filename).resolve()
                if destination.resolve() not in target.parents:
                    raise ValueError('Invalid archive member')
            for member in zip.infolist():
                if member.filename.startswith(('pgsql/bin/','pgsql/lib/','pgsql/share/')):
                    zip.extract(member, destination)
    settings=LOCAL/'app-settings.json'
    if not DATA.exists():
        if settings.exists():
            password=urlparse(json.loads(settings.read_text())['database_url']).password
        else:
            password=secrets.token_urlsafe(32)
            settings.write_text(json.dumps({'database_url':f'postgresql+psycopg://dietlab:{password}@127.0.0.1:5433/dietlab'}))
        password_file=LOCAL/'init-password.tmp'
        password_file.write_text(password,encoding='utf-8')
        try:
            command([BIN/'initdb.exe','-D',DATA,'-U','dietlab','--pwfile',password_file,'--auth=scram-sha-256','--encoding=UTF8','--locale=C'])
        finally:
            password_file.unlink(missing_ok=True)
        with (DATA/'postgresql.conf').open('a') as file:
            file.write("\nlisten_addresses = '127.0.0.1'\nport = 5433\nmax_connections = 30\nshared_buffers = '64MB'\n")
    state=subprocess.run([str(BIN/'pg_ctl.exe'),'-D',str(DATA),'status'],capture_output=True,creationflags=FLAGS)
    if state.returncode!=0:
        command([BIN/'pg_ctl.exe','-D',DATA,'-l',LOCAL/'postgres.log','-w','start'])
    import psycopg
    connection_url=json.loads(settings.read_text())['database_url'].replace('postgresql+psycopg://','postgresql://')
    admin_url=connection_url.rsplit('/',1)[0]+'/postgres'
    with psycopg.connect(admin_url,autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname='dietlab'").fetchone():
            db.execute('CREATE DATABASE dietlab')
    command([sys.executable,'-B','-m','alembic','upgrade','head'])
    print('Native PostgreSQL ready at 127.0.0.1:5433. No Docker is used.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['start','stop'],default='start',nargs='?')
    args=parser.parse_args()
    if args.action=='start':
        start()
    elif DATA.exists():
        command([BIN/'pg_ctl.exe','-D',DATA,'-m','fast','-w','stop'])
