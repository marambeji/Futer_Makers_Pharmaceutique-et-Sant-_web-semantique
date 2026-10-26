import importlib
import time
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from streamlit.testing.v1 import AppTest

@pytest.fixture
def public_client(tmp_path,monkeypatch):
    monkeypatch.setenv('PHARMAGRAPH_DATA',str(tmp_path/'live.ttl'))
    import backend.app as module
    importlib.reload(module)
    with TestClient(module.app) as client:yield client,module

def register(client,email='admin@example.test',role='admin'):
    if role=='admin':
        import backend.app as module
        module.accounts.create_admin('Compte de test',email,'Motdepasse-Test-2026')
        return client.get('/api/auth/status')
    return client.post('/api/auth/register',json={'name':'Compte de test','email':email,'password':'Motdepasse-Test-2026','role':role})

def login(client,email='admin@example.test',password='Motdepasse-Test-2026'):
    return client.post('/api/auth/login',json={'email':email,'password':password})

def header(session):return {'Authorization':'Bearer '+session['token']}

def test_bootstrap_and_password_storage(public_client):
    client,module=public_client
    assert not client.get('/api/auth/status').json()['initialized']
    assert client.post('/api/auth/register',json={'name':'Admin interdit','email':'public@example.test','password':'Motdepasse-Test-2026','role':'admin'}).status_code==403
    # Professional registration is available even before local admin setup.
    response=register(client,'first-doctor@example.test','medecin')
    assert response.status_code==201 and response.json()['requires_approval']
    assert not client.get('/api/auth/status').json()['initialized']
    register(client)
    assert client.get('/api/auth/status').json()['initialized']
    with pytest.raises(Exception,match='déjà configuré'):
        module.accounts.create_admin('Autre admin','second@example.test','Motdepasse-Test-2026')
    session=login(client).json()
    assert session['user']['role']=='admin'
    assert 'password_hash' not in session['user']
    with module.accounts.connection() as db:
        encoded=db.execute('SELECT password_hash FROM users').fetchone()[0]
        assert encoded.startswith('scrypt$')
        assert 'Motdepasse' not in encoded
        assert db.execute('SELECT token_hash FROM sessions').fetchone()[0]!=session['token']
    assert client.get('/api/auth/me',headers=header(session)).status_code==200

@pytest.mark.parametrize('method,path',[
 ('GET','/api/schema'),('GET','/api/entities/Patient'),('GET','/api/care/patients/Nour'),
 ('GET','/api/ontology'),('GET','/api/dashboard'),('GET','/api/molecules'),
 ('POST','/api/ask'),('POST','/api/sparql'),('POST','/api/care/visits'),('GET','/api/auth/users')])
def test_api_requires_authentication(public_client,method,path):
    client,_=public_client
    assert client.request(method,path).status_code==401

@pytest.mark.parametrize('role',['medecin','chercheur'])
def test_pending_approval_and_permissions(public_client,role):
    client,module=public_client
    register(client)
    admin=login(client).json()
    new=register(client,role+'@example.test',role)
    assert new.status_code==201 and new.json()['requires_approval']
    assert login(client,role+'@example.test').status_code==403
    user_id=new.json()['user']['id']
    activation=client.patch('/api/auth/users/'+user_id,json={'role':role,'active':True},headers=header(admin))
    assert activation.status_code==200
    session=login(client,role+'@example.test').json()
    assert client.get('/api/schema',headers=header(session)).status_code==200
    assert client.post('/api/sparql',json={'query':'ASK {?s ?p ?o}'},headers=header(session)).status_code==200
    assert client.get('/api/auth/users',headers=header(session)).status_code==403
    assert client.patch('/api/auth/users/'+user_id,json={'role':'admin','active':True},headers=header(session)).status_code==403
    assert client.post('/api/molecules',json={'id':'Forbidden','nom':'Interdit','formule':'C'},headers=header(session)).status_code==403
    payload={'id':'PatientRole','label':'Patient test','data':{'age':['42'],'sexe':['F']}}
    expected=201 if role=='medecin' else 403
    assert client.post('/api/entities/Patient',json=payload,headers=header(session)).status_code==expected
    if role=='medecin':
        assert client.post('/api/entities/Medecin',json={'id':'Forbidden','label':'Interdit'},headers=header(session)).status_code==403
    # Removing access revokes any existing session immediately.
    client.patch('/api/auth/users/'+user_id,json={'role':role,'active':False},headers=header(admin))
    assert client.get('/api/schema',headers=header(session)).status_code==401

def test_logout_and_expiration(public_client):
    client,module=public_client
    register(client);session=login(client).json()
    assert client.post('/api/auth/logout',headers=header(session)).status_code==200
    assert client.get('/api/auth/me',headers=header(session)).status_code==401
    session=login(client).json()
    with module.accounts.connection() as db:db.execute('UPDATE sessions SET expires_at=?',(int(time.time())-1,))
    assert client.get('/api/auth/me',headers=header(session)).status_code==401

def test_no_self_demote_or_duplicate_email(public_client):
    client,_=public_client
    register(client);session=login(client).json()
    assert register(client,'ADMIN@example.test','chercheur').status_code==409
    assert client.patch('/api/auth/users/'+session['user']['id'],json={'role':'chercheur','active':True},headers=header(session)).status_code==422

def test_login_throttle(public_client):
    client,_=public_client
    register(client)
    for _ in range(5):assert login(client,password='incorrect').status_code==401
    assert login(client,password='incorrect').status_code==429

@pytest.fixture
def make_ui(public_client,monkeypatch):
    client,_=public_client
    import streamlit as st
    import ui.client
    import ui.auth
    import ui.care
    def request(path,method='GET',body=None,params=None):
        token=st.session_state.get('auth_token')
        response=client.request(method,'/api/'+path,json=body,params=params,headers={'Authorization':'Bearer '+token} if token else {})
        if response.status_code>=400:raise ValueError(response.json().get('detail',response.text))
        return response.content if path.startswith('ontology') else response.json()
    for module in (ui.client,ui.auth,ui.care):monkeypatch.setattr(module,'request',request)
    def make(session=None):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'ui/app.py'),default_timeout=30)
        if session:
            app.session_state['auth_token']=session['token'];app.session_state['auth_user']=session['user']
        return app.run()
    return make

def test_registration_and_login_screens(public_client,make_ui):
    client,_=public_client
    app=make_ui()
    assert not app.exception
    assert not app.sidebar.radio
    assert any(input.label=='Votre nom complet' for input in app.text_input)
    role=next(widget for widget in app.selectbox if widget.label=='Votre rôle')
    assert role.options==['Médecin','Chercheur']
    values={'Votre nom complet':'Médecin Interface','Votre adresse e-mail':'interface@example.test',
            'Choisir un mot de passe':'Interface-Test-2026','Confirmer le mot de passe':'Interface-Test-2026'}
    for widget in app.text_input:
        if widget.label in values:widget.set_value(values[widget.label])
    app.checkbox[0].check()
    next(b for b in app.button if b.label=='Créer mon compte →').click().run()
    assert not app.exception,[e.message for e in app.exception]
    assert not client.get('/api/auth/status').json()['initialized']
    register(client)
    admin=login(client).json()
    user=next(u for u in client.get('/api/auth/users',headers=header(admin)).json() if u['email']=='interface@example.test')
    assert user['role']=='medecin' and not user['active']
    client.patch('/api/auth/users/'+user['id'],headers=header(admin),json={'role':'medecin','active':True})
    next(w for w in app.text_input if w.label=='Adresse e-mail').set_value('interface@example.test')
    next(w for w in app.text_input if w.label=='Mot de passe').set_value('Interface-Test-2026')
    next(b for b in app.button if b.label=='Se connecter à mon espace →').click().run()
    assert not app.exception,[e.message for e in app.exception]
    assert app.session_state['auth_user']['role']=='medecin'
    assert 'Mon équipe' not in app.sidebar.radio[0].options

def test_researcher_ui_is_read_only(public_client,make_ui):
    client,_=public_client
    register(client);admin=login(client).json()
    researcher=register(client,'research@example.test','chercheur').json()['user']
    client.patch('/api/auth/users/'+researcher['id'],headers=header(admin),json={'role':'chercheur','active':True})
    session=login(client,'research@example.test').json()
    app=make_ui(session)
    assert not app.exception,[e.message for e in app.exception]
    options=app.sidebar.radio[0].options
    assert 'Nouvelle consultation' not in options and 'Mon équipe' not in options
    button=next(b for b in app.button if b.label=='Préparer une consultation')
    assert button.disabled


def test_team_directory_filters_and_activation(public_client,make_ui):
    client,_=public_client
    register(client)
    admin=login(client).json()
    member=register(client,'doctor-directory@example.test','medecin').json()['user']
    app=make_ui(admin)
    app.sidebar.radio[0].set_value('Mon équipe').run()
    assert not app.exception
    next(w for w in app.selectbox if w.label=='État du compte').set_value('En attente').run()
    selected=next(w for w in app.selectbox if w.label=='Membre à gérer')
    assert selected.value==member['id']
    next(w for w in app.checkbox if w.label=='Autoriser l’accès').check()
    next(w for w in app.button if w.label=='Enregistrer les accès').click().run()
    assert not app.exception
    assert login(client,'doctor-directory@example.test').status_code==200
    assert any('Aucun membre' in msg.value for msg in app.info)
