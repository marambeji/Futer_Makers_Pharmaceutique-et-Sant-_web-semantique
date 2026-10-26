import importlib
from datetime import date,timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from rdflib import RDF, URIRef
from backend.schema import NS
from backend.store import load_graph
from streamlit.testing.v1 import AppTest

@pytest.fixture
def api(tmp_path,monkeypatch,authenticated):
    monkeypatch.setenv('PHARMAGRAPH_DATA',str(tmp_path/'live.ttl'))
    import backend.app as module
    importlib.reload(module)
    with TestClient(module.app) as client:
        authenticated(client)
        yield client,module

def visit(**changes):
    return {'operation_id':'abc123'*4,'patient':'Nour','doctor':'Ahmed','date':'2026-10-23',
            'reason':'Suivi fictif du dossier','conditions':['Diabete'],'treatment':'TraitementA',
            'medicines':['MedAlpha'],'duration':30,'followup_date':'2026-11-23',**changes}

def test_read_patient_file(api):
    client,_=api
    response=client.get('/api/care/patients/Nour')
    assert response.status_code==200,response.text
    dossier=response.json()
    assert len(dossier['doctors'])==2
    assert len(dossier['consultations'])==2
    assert len(dossier['prescriptions'])==1
    assert len(dossier['appointments'])==1
    assert {m['id'] for m in dossier['medicines']}=={'MedAlpha','MedBeta'}
    alpha=next(m for m in dossier['medicines'] if m['id']=='MedAlpha')
    assert alpha['molecules'][0]['id']=='Alpha'
    assert client.get('/api/care/patients/Unknown').status_code==404
    assert client.get('/api/care/patients/Alpha').status_code==404

def test_overview_uses_actual_data(api):
    client,_=api
    overview=client.get('/api/care/overview').json()
    assert overview['counts']=={'patients':8,'medecins':3,'consultations':8}
    assert all(row['date']>=overview['today'] for row in overview['appointments'])

def test_atomic_journey_and_idempotency(api):
    client,module=api
    body=visit()
    response=client.post('/api/care/visits',json=body)
    assert response.status_code==201,response.text
    result=response.json()
    assert result['created']
    consultation=NS[result['consultation_id']]
    prescription=NS[result['prescription_id']]
    appointment=NS[result['appointment_id']]
    assert (consultation,NS.concernePatient,NS.Nour) in module.graph
    assert (prescription,NS.issueConsultation,consultation) in module.graph
    assert (prescription,NS.prescritMedicament,NS.MedAlpha) in module.graph
    assert (appointment,NS.rdvMedecin,NS.Ahmed) in module.graph
    assert (consultation,NS.diagnostique,NS.Diabete) in module.graph
    size=len(module.graph)
    again=client.post('/api/care/visits',json=body)
    assert again.status_code==201
    assert not again.json()['created']
    assert len(module.graph)==size
    assert client.post('/api/care/visits',json=visit(reason='Différent')).status_code==409
    reloaded=load_graph(module.ROOT,module.DATA)
    assert (prescription,NS.issueConsultation,consultation) in reloaded
    dossier=client.get('/api/care/patients/Nour').json()
    assert len(dossier['consultations'])==3
    assert len(dossier['prescriptions'])==2
    assert len(dossier['appointments'])==2
    assert client.get('/api/quality').json()['count']==0

@pytest.mark.parametrize('changes',[{'medicines':['Unknown']},{'conditions':['Ahmed']},{'doctor':'Unknown'},{'treatment':'Nour'},{'followup_date':'2026-10-22'},{'date':'not-a-date'}])
def test_journey_rejects_invalid_without_partial_write(api,changes):
    client,module=api
    before=set(module.graph)
    result=client.post('/api/care/visits',json=visit(**changes))
    assert result.status_code==422,result.text
    assert set(module.graph)==before
    assert not module.DATA.exists()

def test_visit_without_prescription_or_followup(api):
    client,module=api
    result=client.post('/api/care/visits',json=visit(medicines=[],followup_date=None,treatment=None)).json()
    assert result['prescription_id'] is None
    assert result['appointment_id'] is None
    assert (NS[result['consultation_id']],RDF.type,NS.Consultation) in module.graph

def test_streamlit_complete_journey(api,monkeypatch):
    client,module=api
    import ui.client
    # ui.care imports the same request function, so patch both boundaries.
    import ui.care
    import ui.auth
    def request(path,method='GET',body=None,params=None):
        response=client.request(method,'/api/'+path,json=body,params=params)
        if response.status_code>=400:raise ValueError(response.text)
        return response.content if path.startswith('ontology') else response.json()
    monkeypatch.setattr(ui.client,'request',request)
    monkeypatch.setattr(ui.care,'request',request)
    monkeypatch.setattr(ui.auth,'request',request)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'ui/app.py'),default_timeout=25)
    app.session_state['auth_token']=client.auth_session['token']
    app.session_state['auth_user']=client.auth_session['user']
    app.run()
    app.sidebar.radio[0].set_value('Parcours de soins').run()
    assert not app.exception,[e.message for e in app.exception]
    assert app.session_state['care_step']==0
    assert not module.DATA.exists(), 'Reading a draft must not write data.'
    next(b for b in app.button if b.label=='Continuer vers la prescription →').click().run()
    assert app.session_state['care_step']==1
    app.multiselect[0].set_value(['MedAlpha'])
    next(b for b in app.button if b.label=='Continuer vers le suivi →').click().run()
    assert app.session_state['care_step']==2
    app.checkbox[0].check()
    next(b for b in app.button if b.label=='Relire le parcours →').click().run()
    assert app.session_state['care_step']==3
    assert not module.DATA.exists()
    next(b for b in app.button if b.label=='Enregistrer ce parcours dans le dossier').click().run()
    assert not app.exception,[e.message for e in app.exception]
    result=app.session_state['care_saved']
    assert result['created'] and result['prescription_id'] and result['appointment_id']
    next(b for b in app.button if b.label=='Retrouver le dossier et son historique →').click().run()
    assert not app.exception,[e.message for e in app.exception]
    assert app.sidebar.radio[0].value=='Dossiers patients'
