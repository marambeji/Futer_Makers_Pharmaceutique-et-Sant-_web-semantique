import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / '.deps'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

@pytest.fixture(autouse=True)
def isolated_accounts(tmp_path,monkeypatch):
    monkeypatch.setenv('PHARMAGRAPH_AUTH_DB',str(tmp_path/'accounts.sqlite3'))

@pytest.fixture
def authenticated():
    def authorize(client):
        import backend.app as module
        module.accounts.create_admin('Admin Test','admin@example.test','Test-Admin-2026!')
        response=client.post('/api/auth/login',json={'email':'admin@example.test','password':'Test-Admin-2026!'})
        assert response.status_code==200,response.text
        session=response.json()
        client.headers['Authorization']='Bearer '+session['token']
        client.auth_session=session
        return session
    return authorize
