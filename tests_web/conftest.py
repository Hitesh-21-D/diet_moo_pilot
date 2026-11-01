import os
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient

# An isolated temporary SQLite database is used only by fast API unit tests.
folder=Path(tempfile.mkdtemp(prefix='dietlab-tests-'))
os.environ['DIETLAB_DATABASE_URL']='sqlite:///'+str(folder/'tests.db')
from backend.db import Base, engine
from backend.api import app
from backend.security import attempts

@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    attempts.clear()
    yield

@pytest.fixture
def client():
    with TestClient(app,headers={'X-DietLab-Request':'1'}) as c:
        yield c

@pytest.fixture
def signed(client):
    r=client.post('/api/auth/register',json={'name':'Research User','email':'research@example.org','password':'test-password-12345'})
    assert r.status_code==201,r.text
    return client
