"""Run every Streamlit page against the real API logic on an isolated RDF file."""
import importlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

@pytest.mark.parametrize('page',['Accueil','Dossiers patients','Parcours de soins','Explorateur IA','Tableau de bord','Données & CRUD','Relations','Ontologie','Console SPARQL','Qualité des données'])
def test_streamlit_pages(tmp_path,monkeypatch,page):
    monkeypatch.setenv('PHARMAGRAPH_DATA',str(tmp_path/'live.ttl'))
    import backend.app as module
    importlib.reload(module)
    import ui.client
    import ui.care
    with TestClient(module.app) as client:
        def request(path,method='GET',body=None,params=None):
            response=client.request(method,'/api/'+path,json=body,params=params)
            if response.status_code>=400:raise ValueError(response.text)
            return response.content if path.startswith('ontology') else response.json()
        monkeypatch.setattr(ui.client,'request',request)
        monkeypatch.setattr(ui.care,'request',request)
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'ui/app.py'),default_timeout=25)
        app.run()
        assert not app.exception,[e.message for e in app.exception]
        assert not app.error,[e.value for e in app.error]
        if page in ['Données & CRUD','Relations','Ontologie','Console SPARQL','Qualité des données']:
            app.sidebar.radio[0].set_value('Atelier sémantique').run()
            app.sidebar.selectbox[0].set_value(page).run()
        else:app.sidebar.radio[0].set_value(page).run()
        assert not app.exception,[e.message for e in app.exception]
        assert not app.error,[e.value for e in app.error]

def test_streamlit_nlp_submission(tmp_path,monkeypatch):
    monkeypatch.setenv('PHARMAGRAPH_DATA',str(tmp_path/'live.ttl'))
    import backend.app as module
    importlib.reload(module)
    import ui.client
    import ui.care
    with TestClient(module.app) as client:
        def request(path,method='GET',body=None,params=None):
            response=client.request(method,'/api/'+path,json=body,params=params)
            if response.status_code>=400:raise ValueError(response.text)
            return response.json()
        monkeypatch.setattr(ui.client,'request',request)
        monkeypatch.setattr(ui.care,'request',request)
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'ui/app.py'),default_timeout=25).run()
        app.sidebar.radio[0].set_value('Explorateur IA').run()
        app.text_area[0].set_value('Quels patients ont consulté plusieurs médecins pour une même maladie ?')
        next(b for b in app.button if b.label=='Explorer le graphe ↗').click().run()
        assert not app.exception,[e.message for e in app.exception]
        assert len(app.session_state['answer']['rows'])==1
