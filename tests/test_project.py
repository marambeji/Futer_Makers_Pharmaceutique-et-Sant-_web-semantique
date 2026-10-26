import importlib
import pytest
from fastapi.testclient import TestClient
from rdflib import Graph, RDF, OWL
from backend.nlp import translate

@pytest.fixture
def api(tmp_path,monkeypatch,authenticated):
    monkeypatch.setenv('PHARMAGRAPH_DATA',str(tmp_path/'live.ttl'))
    import backend.app as module
    importlib.reload(module)
    with TestClient(module.app) as client:
        authenticated(client)
        yield client,module

@pytest.mark.parametrize('question,expected',[
    ('Quels sont les effets secondaires de la Molécule Alpha ?',{'Nausées','Vertiges'}),
    ('Quelles sont les contre-indications de la Molécule Bêta ?',{'Insuffisance rénale'}),
    ('Lister les molécules avec des nausées',{'Molécule Alpha','Molécule Gamma'}),
    ('Quels essais cliniques de phase 2 pour la Molécule Gamma ?',{'Étude Aurore (fictive)'}),
    ('Lister les molécules contre-indiquées pendant la grossesse',{'Molécule Alpha','Molécule Epsilon'}),
])
def test_translation(api,question,expected):
    client,module=api
    response=client.post('/api/ask',json={'question':question})
    assert response.status_code==200,response.text
    assert {r['nom'] for r in response.json()['rows']}==expected

def test_reject_unknown(api):
    client,_=api
    for question in ['Bonjour comment allez-vous ?', 'Effets de la Molécule Inconnue', 'Supprimer la Molécule Alpha']:
        assert client.post('/api/ask',json={'question':question}).status_code==422

def test_crud_persistence_and_safe_literals(api):
    client,module=api
    payload={'id':'Omega','nom':'Oméga "test" <script>','formule':'C1','effets':['Nausees'],'contre_indications':['Grossesse']}
    assert client.post('/api/molecules',json=payload).status_code==201
    assert client.post('/api/molecules',json=payload).status_code==409
    saved=Graph().parse(module.DATA,format='turtle')
    assert (module.NS.Omega,RDF.type,module.NS.Molecule) in saved
    payload['nom']='Molécule Oméga'
    assert client.put('/api/molecules/Omega',json=payload).status_code==200
    assert any(m['nom']=='Molécule Oméga' for m in client.get('/api/molecules').json())
    assert client.delete('/api/molecules/Omega').status_code==200
    assert client.delete('/api/molecules/Omega').status_code==404
    assert not list(Graph().parse(module.DATA).triples((module.NS.Omega,None,None)))

def test_invalid_relation_does_not_mutate(api):
    client,module=api
    before=len(module.graph)
    assert client.post('/api/molecules',json={'id':'X','nom':'Test','formule':'C','effets':['Unknown']}).status_code==422
    assert len(module.graph)==before

def test_edit_preserves_clinical_links(api):
    client,module=api
    payload={'id':'Alpha','nom':'Molécule Alpha','formule':'C10','effets':['Nausees'],'contre_indications':['Grossesse']}
    assert client.put('/api/molecules/Alpha',json=payload).status_code==200
    assert (module.NS.Alpha,module.NS.etudieDans,module.NS.EssaiA) in module.graph
    assert (module.NS.Alpha,module.NS.interagitAvec,module.NS.Beta) in module.graph

def test_console_and_assets(api):
    client,module=api
    for query in ['SELECT ?s WHERE {?s a <https://pharmagraph.example/ontology#Molecule>}','ASK {?s ?p ?o}']:
        assert client.post('/api/sparql',json={'query':query}).status_code==200
    for query in ['DELETE WHERE {?s ?p ?o}', 'SELECT * WHERE {SERVICE <https://example.org> {?s ?p ?o}}','SELECT * FROM <file:///etc/passwd> WHERE {?s ?p ?o}']:
        assert client.post('/api/sparql',json={'query':query}).status_code==422
    assert client.get('/').status_code==200
    assert client.get('/static/app.js').status_code==200
    assert client.get('/api/overview').json()['molecules']==6
    exported=Graph().parse(data=client.get('/api/ontology').text,format='turtle')
    assert (module.NS.interagitAvec,RDF.type,OWL.SymmetricProperty) in exported
