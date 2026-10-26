from pathlib import Path
from threading import RLock
import os
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef
from .nlp import translate
from .store import load_graph, commit
from .engine import execute
from . import entities, schema
from .analytics import dashboard
from .quality import audit
from .queries import QUERIES
from .clinical_nlp import EXAMPLES
from .care import patient_file, record_visit, overview as care_overview
from .auth import Accounts, AuthError, authorize
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
NS = Namespace('https://pharmagraph.example/ontology#')
DATA = Path(os.environ.get('PHARMAGRAPH_DATA', str(ROOT / 'data/live.ttl')))
lock = RLock()
graph = load_graph(ROOT, DATA)
app = FastAPI(title='PharmaGraph', description='Démonstration pédagogique sur données fictives', version='1.0')
accounts=Accounts(os.environ.get('PHARMAGRAPH_AUTH_DB',str(ROOT/'data/accounts.sqlite3')))

@app.middleware('http')
async def authentication(request: Request, call_next):
    path=request.url.path
    public=path in ('/api/auth/status','/api/auth/register','/api/auth/login')
    if path.startswith('/api/') and not public:
        try:
            user=accounts.authenticate(request.headers.get('authorization'))
            authorize(user,request.method,path)
            request.state.user=user
        except AuthError as error:
            return JSONResponse({'detail':str(error)},status_code=error.status,headers={'Cache-Control':'no-store'})
    response=await call_next(request)
    if path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response

app.mount('/static', StaticFiles(directory=ROOT / 'frontend'), name='static')
app.mount('/design', StaticFiles(directory=ROOT / 'ui/assets'), name='design')

class Registration(BaseModel):
    name: str = Field(min_length=2,max_length=100)
    email: str = Field(min_length=3,max_length=200)
    password: str = Field(min_length=10,max_length=128)
    role: str

class Login(BaseModel):
    email: str = Field(min_length=3,max_length=200)
    password: str = Field(min_length=1,max_length=128)

class AccountUpdate(BaseModel):
    role: str
    active: bool

def auth_operation(operation):
    try:return operation()
    except AuthError as error:raise HTTPException(error.status,str(error))

@app.get('/api/auth/status')
def auth_status():
    return {'initialized':accounts.initialized()}

@app.post('/api/auth/register',status_code=201)
def register(body: Registration):
    return auth_operation(lambda:accounts.register(**body.model_dump()))

@app.post('/api/auth/login')
def login(body: Login):
    return auth_operation(lambda:accounts.login(body.email,body.password))

@app.get('/api/auth/me')
def me(request: Request):return request.state.user

@app.post('/api/auth/logout')
def logout(request: Request):
    accounts.logout(request.headers.get('authorization'))
    return {'ok':True}

@app.get('/api/auth/users')
def users():return accounts.users()

@app.patch('/api/auth/users/{user_id}')
def update_account(user_id: str,body: AccountUpdate,request: Request):
    return auth_operation(lambda:accounts.update(request.state.user,user_id,body.role,body.active))

class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)

class Query(BaseModel):
    query: str = Field(min_length=5, max_length=8000)

class Molecule(BaseModel):
    id: str = Field(pattern=r'^[A-Za-z][A-Za-z0-9_]{0,49}$')
    nom: str = Field(min_length=2, max_length=100)
    formule: str = Field(min_length=1, max_length=80)
    effets: list[str] = Field(default_factory=list, max_length=20)
    contre_indications: list[str] = Field(default_factory=list, max_length=20)

def save():
    DATA.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA.with_suffix('.tmp')
    graph.serialize(temporary, format='turtle')
    temporary.replace(DATA)

def results(query):
    return execute(graph,query)

@app.get('/')
def home():
    return FileResponse(ROOT / 'frontend/index.html')

@app.get('/api/overview')
def overview():
    with lock:
        return {'triples': len(graph), 'molecules': len(set(graph.subjects(RDF.type, NS.Molecule))), 'effets': len(set(graph.subjects(RDF.type, NS.EffetSecondaire))), 'essais': len(set(graph.subjects(RDF.type, NS.EssaiClinique)))}

@app.get('/api/molecules')
def molecules():
    with lock:
        return [{'id': str(s).split('#')[-1], 'nom': str(graph.value(s,RDFS.label)), 'formule': str(graph.value(s,NS.formule) or ''), 'effets': [str(graph.value(o,RDFS.label)) for o in graph.objects(s,NS.aEffetSecondaire)], 'contre_indications': [str(graph.value(o,RDFS.label)) for o in graph.objects(s,NS.aContreIndication)]} for s in sorted(graph.subjects(RDF.type,NS.Molecule), key=str)]

@app.get('/api/catalogue')
def catalogue():
    with lock:
        return {key: [{'id': str(s).split('#')[-1], 'nom': str(graph.value(s,RDFS.label))} for s in graph.subjects(RDF.type,cls)] for key,cls in [('effets',NS.EffetSecondaire),('contre_indications',NS.ContreIndication)]}

@app.post('/api/ask')
def ask(body: Question):
    with lock:
        try:
            parsed = translate(body.question, graph, NS)
            answer=results(parsed['sparql'])
            count=len(answer['rows'])
            summary=f'{count} résultat(s) trouvé(s) dans les données explicites du graphe.'
            if not count: summary='Aucun résultat dans le graphe pour ces critères. Cela ne prouve pas une absence dans le monde réel.'
            return {**parsed, **answer, 'answer':summary}
        except ValueError as error:
            raise HTTPException(422, str(error))

@app.post('/api/sparql')
def sparql(body: Query):
    # Deliberately limited console: no updates, federated services or file/network access.
    try:
        with lock:
            return results(body.query)
    except Exception as error:
        raise HTTPException(422, str(error))

def write_molecule(body, update=False):
    subject = NS[body.id]
    exists = (subject,RDF.type,NS.Molecule) in graph
    if update and not exists:
        raise HTTPException(404,'Molécule introuvable')
    if not update and (subject,None,None) in graph:
        raise HTTPException(409,'Identifiant déjà utilisé')
    for values,cls in [(body.effets,NS.EffetSecondaire),(body.contre_indications,NS.ContreIndication)]:
        for item in values:
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,49}',item) or (NS[item],RDF.type,cls) not in graph:
                raise HTTPException(422,'Relation inconnue : '+item)
    triples = [(subject,RDF.type,NS.Molecule),(subject,RDFS.label,Literal(body.nom,lang='fr')),(subject,NS.formule,Literal(body.formule))]
    triples += [(subject,p,NS[item]) for values,p in [(body.effets,NS.aEffetSecondaire),(body.contre_indications,NS.aContreIndication)] for item in values]
    query = 'INSERT DATA { '+ ' '.join(f'{s.n3()} {p.n3()} {o.n3()} .' for s,p,o in triples)+' }'
    if update:
        editable = [RDFS.label,NS.formule,NS.aEffetSecondaire,NS.aContreIndication]
        query = ';\n'.join(f'DELETE WHERE {{ {subject.n3()} {prop.n3()} ?o }}' for prop in editable) + ';\n' + query
    commit(graph,DATA,query)
    return {'ok': True, 'sparql': query}

@app.post('/api/molecules',status_code=201)
def create(body: Molecule):
    with lock:
        return write_molecule(body)

@app.put('/api/molecules/{identifier}')
def update(identifier: str,body: Molecule):
    if identifier != body.id:
        raise HTTPException(422,'Identifiant non modifiable')
    with lock:
        return write_molecule(body,True)

@app.delete('/api/molecules/{identifier}')
def delete(identifier: str):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,49}',identifier):
        raise HTTPException(422,'Identifiant invalide')
    with lock:
        subject = NS[identifier]
        if (subject,RDF.type,NS.Molecule) not in graph:
            raise HTTPException(404,'Molécule introuvable')
        query = f'DELETE WHERE {{ {subject.n3()} ?p ?o }}; DELETE WHERE {{ ?s ?p {subject.n3()} }}'
        commit(graph,DATA,query)
        return {'ok':True,'sparql':query}

@app.get('/api/ontology')
def ontology(format: str = 'turtle'):
    with lock:
        from fastapi.responses import Response
        if format not in ('turtle','xml'):
            raise HTTPException(422,'Format attendu : turtle ou xml')
        return Response(graph.serialize(format=format),media_type='text/turtle' if format=='turtle' else 'application/rdf+xml',headers={'Content-Disposition':'attachment; filename="pharmagraph.'+('ttl' if format=='turtle' else 'owl')+'"'})

class EntityBody(BaseModel):
    id: str = Field(min_length=1,max_length=60)
    label: str = Field(min_length=2,max_length=150)
    data: dict[str,list[str]] = Field(default_factory=dict,max_length=50)
    relations: dict[str,list[str]] = Field(default_factory=dict,max_length=50)

class RelationBody(BaseModel):
    source: str = Field(max_length=60)
    predicate: str = Field(max_length=60)
    target: str = Field(max_length=60)

def business(operation):
    with lock:
        try: return operation()
        except FileExistsError as error: raise HTTPException(409,str(error))
        except LookupError as error: raise HTTPException(404,str(error))
        except ValueError as error: raise HTTPException(422,str(error))

@app.get('/api/schema')
def get_schema():
    return business(lambda:schema.describe(graph))

@app.get('/api/entities/{class_id}')
def get_entities(class_id: str):
    return business(lambda:entities.list_entities(graph,class_id))

@app.get('/api/entities/{class_id}/{identifier}')
def get_entity(class_id: str,identifier: str):
    def operation():
        cls=entities.class_uri(graph,class_id)
        subject=entities.identifier(identifier)
        if not schema.is_instance(graph,subject,cls): raise LookupError('Individu introuvable.')
        return entities.serialize(graph,subject)
    return business(operation)

@app.post('/api/entities/{class_id}',status_code=201)
def create_entity(class_id: str,body: EntityBody):
    return business(lambda:entities.upsert(graph,DATA,class_id,body.model_dump()))

@app.put('/api/entities/{class_id}/{identifier}')
def edit_entity(class_id: str,identifier: str,body: EntityBody):
    if identifier!=body.id: raise HTTPException(422,'Identifiant non modifiable.')
    return business(lambda:entities.upsert(graph,DATA,class_id,body.model_dump(),True))

@app.delete('/api/entities/{class_id}/{identifier}')
def remove_entity(class_id: str,identifier: str):
    return business(lambda:entities.remove(graph,DATA,class_id,identifier))

@app.post('/api/relations')
def add_relation(body: RelationBody):
    return business(lambda:entities.change_relation(graph,DATA,body.source,body.predicate,body.target))

@app.delete('/api/relations')
def remove_relation(body: RelationBody):
    return business(lambda:entities.change_relation(graph,DATA,body.source,body.predicate,body.target,True))

@app.get('/api/dashboard')
def get_dashboard(min_age: int = 0,max_age: int = 120,sex: str = '',start: str | None = None,end: str | None = None):
    return business(lambda:dashboard(graph,min_age,max_age,sex,start,end))

@app.get('/api/quality')
def get_quality():
    return business(lambda:audit(graph))

@app.get('/api/examples')
def examples():
    return {'questions':EXAMPLES,'queries':QUERIES}

class VisitBody(BaseModel):
    operation_id: str = Field(pattern=r'^[a-f0-9]{24,32}$')
    patient: str = Field(max_length=60)
    doctor: str = Field(max_length=60)
    date: str = Field(max_length=10)
    reason: str = Field(default='',max_length=500)
    conditions: list[str] = Field(default_factory=list,max_length=20)
    treatment: str | None = Field(default=None,max_length=60)
    medicines: list[str] = Field(default_factory=list,max_length=20)
    duration: int = Field(default=30,ge=1,le=365)
    followup_date: str | None = Field(default=None,max_length=10)

@app.get('/api/care/overview')
def get_care_overview():
    return business(lambda:care_overview(graph))

@app.get('/api/care/patients/{identifier}')
def get_patient_file(identifier: str):
    return business(lambda:patient_file(graph,identifier))

@app.post('/api/care/visits',status_code=201)
def create_visit(body: VisitBody):
    return business(lambda:record_visit(graph,DATA,body.model_dump()))

def openapi_with_authentication():
    if app.openapi_schema:return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    description=get_openapi(title=app.title,version=app.version,routes=app.routes)
    description.setdefault('components',{}).setdefault('securitySchemes',{})['BearerAuth']={'type':'http','scheme':'bearer','description':'Jeton retourné par /api/auth/login'}
    public={'/api/auth/status','/api/auth/register','/api/auth/login'}
    for path,operations in description['paths'].items():
        if path.startswith('/api/') and path not in public:
            for operation in operations.values():
                if isinstance(operation,dict):operation['security']=[{'BearerAuth':[]}]
    app.openapi_schema=description
    return description

app.openapi=openapi_with_authentication
