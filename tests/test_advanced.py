from datetime import date
import importlib
import pytest
from fastapi.testclient import TestClient
from rdflib import RDF, RDFS, OWL, Literal
from backend.schema import NS, classes, fields
from backend.clinical_nlp import translate_clinical
from backend.engine import execute
from backend.queries import QUERIES

@pytest.fixture
def api(tmp_path,monkeypatch,authenticated):
    monkeypatch.setenv('PHARMAGRAPH_DATA',str(tmp_path/'live.ttl'))
    import backend.app as module
    importlib.reload(module)
    with TestClient(module.app) as client:
        authenticated(client)
        yield client,module

@pytest.mark.parametrize('question,names',[
 ('Cite tous les patients.',{'Nour','Youssef','Ines','Omar','Salma','Aziz','Meriem','Adam'}),
 ('Quels patients possèdent une voiture ?',{'Nour','Ines','Salma'}),
 ('Affiche les patients suivis par le docteur Ahmed.',{'Nour','Youssef','Aziz'}),
 ('Quels patients souffrent de diabète et prennent le Médicament Alpha ?',{'Nour','Youssef','Aziz'}),
 ('Quels médecins travaillent dans les hôpitaux qui accueillent des patients âgés de plus de 60 ans ?',{'Ahmed','Leila'}),
 ('Quels patients ont consulté plusieurs médecins pour une même maladie ?',{'Nour'}),
 ('Quels patients sont suivis par le docteur Ahmed dans l’Hôpital Carthage ?',{'Nour','Youssef','Aziz'}),
 ('List patients with a car.',{'Nour','Ines','Salma'}),
 ('List patients followed by doctor Ahmed.',{'Nour','Youssef','Aziz'}),
])
def test_nlp_composition(api,question,names):
    client,module=api
    response=client.post('/api/ask',json={'question':question})
    assert response.status_code==200,response.text
    assert {r['resultat'].split('#')[-1] for r in response.json()['rows']}==names
    assert response.json()['explanation']
    assert response.json()['answer']

def test_nlp_temporal_calendar_months(api):
    _,module=api
    parsed=translate_clinical('Quels patients possèdent une voiture et ont reçu une prescription dans les six derniers mois ?',module.graph,date(2026,10,23))
    assert '2026-04-23' in parsed['sparql']
    result=execute(module.graph,parsed['sparql'])
    assert {r['resultat'].split('#')[-1] for r in result['rows']}=={'Nour','Ines'}

@pytest.mark.parametrize('query_id,rows', [('patients',8),('multi_doctors',1),('aggregates',3),('union',5),('subquery',2),('temporal',2)])
def test_advanced_results(api,query_id,rows):
    client,_=api
    query=next(q['query'] for q in QUERIES if q['id']==query_id)
    response=client.post('/api/sparql',json={'query':query})
    assert response.status_code==200,response.text
    assert len(response.json()['rows'])==rows

def test_all_query_examples(api):
    client,_=api
    for query in QUERIES:
        response=client.post('/api/sparql',json={'query':query['query']})
        assert response.status_code==200,(query['id'],response.text)
        assert response.json()['rows'],query['id']

def test_ontology_has_one_identity(api):
    _,module=api
    assert list(module.graph.subjects(RDF.type,OWL.Ontology))==[NS['']]

@pytest.mark.parametrize('cls',['Molecule','EffetSecondaire','ContreIndication','EssaiClinique','Personne','Patient','Medecin','Consultation','RendezVous','Maladie','Traitement','Medicament','Hopital','Service','Assurance','Vehicule'])
def test_crud_every_main_class(api,cls):
    client,module=api
    records=client.get('/api/entities/'+cls).json()
    prototype=records[0] if records else {'data':{},'relations':{}}
    body={'id':'Test'+cls,'label':'Exemple '+cls,'data':prototype['data'],'relations':prototype['relations']}
    # Personne is an abstract parent; inherited patient fields do not belong to it.
    metadata={f['id'] for f in fields(module.graph,NS[cls])}
    body['data']={k:v for k,v in body['data'].items() if k in metadata}
    body['relations']={k:v for k,v in body['relations'].items() if k in metadata}
    response=client.post('/api/entities/'+cls,json=body)
    assert response.status_code==201,response.text
    assert client.get('/api/entities/'+cls+'/'+body['id']).status_code==200
    body['label']='Modifié '+cls
    assert client.put('/api/entities/'+cls+'/'+body['id'],json=body).status_code==200
    assert client.delete('/api/entities/'+cls+'/'+body['id']).status_code==200
    assert client.get('/api/entities/'+cls+'/'+body['id']).status_code==404

def test_relations_without_deleting_individuals(api):
    client,module=api
    body={'source':'Adam','predicate':'suitPar','target':'Ahmed'}
    assert client.post('/api/relations',json=body).status_code==200
    assert (NS.Adam,NS.suitPar,NS.Ahmed) in module.graph
    assert client.request('DELETE','/api/relations',json=body).status_code==200
    assert (NS.Adam,RDF.type,NS.Patient) in module.graph
    assert (NS.Ahmed,RDF.type,NS.Medecin) in module.graph
    bad={'source':'Adam','predicate':'suitPar','target':'Diabete'}
    assert client.post('/api/relations',json=bad).status_code==422

def test_constraints_and_transaction(api):
    client,module=api
    before=set(module.graph)
    payload={'id':'Wrong','label':'Patient erroné','data':{'age':['-3'],'sexe':['F']}}
    assert client.post('/api/entities/Patient',json=payload).status_code==422
    assert set(module.graph)==before
    payload={'id':'Broken','label':'Consultation sans patient','data':{'dateConsultation':['2026-10-01']}}
    assert client.post('/api/entities/Consultation',json=payload).status_code==422
    assert client.delete('/api/entities/Patient/Nour').status_code==422
    assert client.request('DELETE','/api/relations',json={'source':'Consultation1','predicate':'concernePatient','target':'Nour'}).status_code==422

def test_dashboard_sparql_filters(api):
    client,_=api
    stats=client.get('/api/dashboard').json()
    assert stats['metrics']=={'patients':8,'medecins':3,'consultations':8,'prescriptions':5}
    assert float(stats['datasets']['couts']['rows'][0]['total'])==565
    stats=client.get('/api/dashboard',params={'min_age':60,'sex':'F','start':'2026-09-01','end':'2026-10-23'}).json()
    assert stats['metrics']=={'patients':1,'medecins':2,'consultations':2,'prescriptions':1}
    assert client.get('/api/dashboard',params={'min_age':80,'max_age':20}).status_code==422

def test_quality_explains_injected_issues(api):
    client,module=api
    result=client.get('/api/quality').json()
    assert result['count']==0,result
    module.graph.add((NS.Nour,NS.age,Literal(-1)))
    result=client.get('/api/quality').json()
    assert any(i['code']=='cardinality' for i in result['issues'])
    assert any(i['code']=='value' for i in result['issues'])

def test_lexicon_is_dynamic(api):
    client,_=api
    body={'id':'NouveauDocteur','label':'Docteur Rania'}
    assert client.post('/api/entities/Medecin',json=body).status_code==201
    assert client.post('/api/relations',json={'source':'Adam','predicate':'suitPar','target':'NouveauDocteur'}).status_code==200
    response=client.post('/api/ask',json={'question':'Quels patients sont suivis par le docteur Rania ?'})
    assert response.status_code==200,response.text
    assert len(response.json()['rows'])==1

def test_readonly_validator_checks_algebra_not_literals(api):
    client,_=api
    assert client.post('/api/sparql',json={'query':'SELECT ("SERVICE FROM" AS ?text) WHERE {}'}).status_code==200
    assert client.post('/api/sparql',json={'query':'SELECT * WHERE { { SELECT * WHERE { SERVICE <https://example.com> {?s ?p ?o} } } }'}).status_code==422

def test_migration_once_preserves_deletions(api):
    client,module=api
    # An optional/unused vehicle can be deleted; migration marker prevents reseeding.
    client.request('DELETE','/api/relations',json={'source':'Salma','predicate':'possedeVehicule','target':'Voiture3'})
    assert client.delete('/api/entities/Vehicule/Voiture3').status_code==200
    reloaded=module.load_graph(module.ROOT,module.DATA)
    assert (NS.Voiture3,RDF.type,NS.Vehicule) not in reloaded
