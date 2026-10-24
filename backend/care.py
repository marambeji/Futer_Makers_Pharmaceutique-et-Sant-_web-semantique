"""Patient-centered read models and one atomic consultation/prescription journey."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import os
from rdflib import RDF, RDFS, Literal, URIRef
from rdflib.namespace import DCTERMS
from .schema import NS, label, local, is_instance
from .engine import PREFIX, execute
from .entities import identifier, serialize, upsert
from .store import clone, commit

def today_local():
    return datetime.now(ZoneInfo(os.getenv('PHARMAGRAPH_TIMEZONE','Africa/Tunis'))).date()

def named_links(graph,subject,prop):
    return [{'id':local(o),'label':label(graph,o)} for o in sorted(graph.objects(subject,NS[prop]),key=str)]

def patient_file(graph,patient_id):
    subject=identifier(patient_id)
    if not is_instance(graph,subject,NS.Patient):
        raise LookupError('Ce dossier patient est introuvable.')
    anchor=subject.n3()
    queries={
        'consultations':PREFIX+f'''SELECT ?id ?date ?medecin ?medecinId ?motif WHERE {{
 ?id a ph:Consultation ; ph:concernePatient {anchor} ; ph:realiseePar ?medecinId ; ph:dateConsultation ?date .
 ?medecinId rdfs:label ?medecin . OPTIONAL {{ ?id rdfs:comment ?motif }}
}} ORDER BY DESC(?date)''',
        'prescriptions':PREFIX+f'''SELECT ?id ?date ?medecin ?duree WHERE {{
 ?id a ph:Prescription ; ph:prescritA {anchor} ; ph:prescritPar/rdfs:label ?medecin ; ph:datePrescription ?date .
 OPTIONAL {{ ?id ph:dureeJours ?duree }}
}} ORDER BY DESC(?date)''',
        'appointments':PREFIX+f'''SELECT ?id ?date ?medecin ?statut WHERE {{
 ?id a ph:RendezVous ; ph:rdvPatient {anchor} ; ph:rdvMedecin/rdfs:label ?medecin ; ph:dateRdv ?date .
 OPTIONAL {{ ?id ph:statutRdv ?statut }}
}} ORDER BY ?date''',
    }
    datasets={key:execute(graph,q)['rows'] for key,q in queries.items()}
    for row in datasets['consultations']:
        uri=URIRef(row['id'])
        row['diagnoses']=named_links(graph,uri,'diagnostique')
        row['treatments']=named_links(graph,uri,'proposeTraitement')
    for row in datasets['prescriptions']:
        uri=URIRef(row['id'])
        row['medicines']=named_links(graph,uri,'prescritMedicament')
        row['consultation_ids']=[local(o) for o in graph.objects(uri,NS.issueConsultation)]
    doctors=[]
    for doctor in graph.objects(subject,NS.suitPar):
        doctors.append({'id':local(doctor),'label':label(graph,doctor),
                        'specialty':str(graph.value(doctor,NS.specialite) or 'Spécialité non renseignée'),
                        'hospitals':named_links(graph,doctor,'travailleDans')})
    medicine_ids=set(graph.objects(subject,NS.prendMedicament))
    medicine_ids|={o for row in datasets['prescriptions'] for o in graph.objects(URIRef(row['id']),NS.prescritMedicament)}
    medicines=[]
    for med in sorted(medicine_ids,key=str):
        molecules=[]
        for mol in graph.objects(med,NS.contientMolecule):
            molecules.append({'id':local(mol),'label':label(graph,mol),
                              'effects':named_links(graph,mol,'aEffetSecondaire'),
                              'contraindications':named_links(graph,mol,'aContreIndication')})
        medicines.append({'id':local(med),'label':label(graph,med),'molecules':molecules,
                          'declared_taken':(subject,NS.prendMedicament,med) in graph})
    timeline=[]
    for key,title in [('consultations','Consultation'),('prescriptions','Prescription'),('appointments','Rendez-vous')]:
        timeline += [{**row,'type':title} for row in datasets[key]]
    timeline.sort(key=lambda row:row['date'],reverse=True)
    return {'today':today_local().isoformat(),'patient':serialize(graph,subject),'doctors':doctors,
            'conditions':named_links(graph,subject,'souffreDe'),
            'hospitals':named_links(graph,subject,'accueilliDans'),
            'insurance':named_links(graph,subject,'assurePar'),
            'medicines':medicines,**datasets,'timeline':timeline,'queries':queries}

def overview(graph):
    today=today_local().isoformat()
    query=PREFIX+f'''SELECT ?id ?date ?patientId ?patient ?medecin WHERE {{
 ?id a ph:RendezVous ; ph:dateRdv ?date ; ph:rdvPatient ?patientId ; ph:rdvMedecin/rdfs:label ?medecin .
 ?patientId rdfs:label ?patient .
 FILTER (?date >= "{today}"^^xsd:date)
}} ORDER BY ?date LIMIT 5'''
    counts=execute(graph,PREFIX+'''SELECT
 (COUNT(DISTINCT ?patient) AS ?patients) (COUNT(DISTINCT ?medecin) AS ?medecins)
 (COUNT(DISTINCT ?consultation) AS ?consultations) WHERE {
 { ?patient a ph:Patient } UNION { ?medecin a ph:Medecin } UNION { ?consultation a ph:Consultation }
}''')['rows'][0]
    return {'today':today,'counts':{k:int(v) for k,v in counts.items()},
            'appointments':execute(graph,query)['rows'],'sparql':query}

def record_visit(graph,destination,body):
    operation=body['operation_id']
    consultation_id='Consultation_'+operation
    prescription_id='Prescription_'+operation
    appointment_id='Rdv_'+operation
    subject=identifier(consultation_id)
    fingerprint=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    result={'consultation_id':consultation_id,'prescription_id':prescription_id if body['medicines'] else None,
            'appointment_id':appointment_id if body.get('followup_date') else None,'patient_id':body['patient']}
    if (subject,None,None) in graph:
        if str(graph.value(subject,DCTERMS.identifier))==fingerprint:
            return {**result,'created':False,'message':'Cette consultation a déjà été enregistrée. Aucun doublon n’a été créé.'}
        raise FileExistsError('Cette opération existe déjà avec un contenu différent. Commencez une nouvelle consultation.')
    patient,doctor=identifier(body['patient']),identifier(body['doctor'])
    if not is_instance(graph,patient,NS.Patient) or not is_instance(graph,doctor,NS.Medecin):
        raise ValueError('Le patient ou le médecin sélectionné n’existe plus. Actualisez la page.')
    visit_date=date.fromisoformat(body['date'])
    if body.get('followup_date') and date.fromisoformat(body['followup_date'])<=visit_date:
        raise ValueError('Le rendez-vous de suivi doit être postérieur à la consultation.')
    if body['duration']<1 or body['duration']>365:
        raise ValueError('La durée doit être comprise entre 1 et 365 jours.')
    candidate=clone(graph)
    queries=[]
    def prepare(cls,entity):
        query=upsert(candidate,destination,cls,entity,prepare_only=True)['sparql']
        candidate.update(query)
        queries.append(query)
    relations={'concernePatient':[body['patient']],'realiseePar':[body['doctor']]}
    if body['conditions']:relations['diagnostique']=body['conditions']
    if body.get('treatment'):relations['proposeTraitement']=[body['treatment']]
    prepare('Consultation',{'id':consultation_id,'label':'Consultation de '+label(graph,patient),
            'data':{'dateConsultation':[body['date']]},'relations':relations})
    if body['medicines']:
        prepare('Prescription',{'id':prescription_id,'label':'Prescription de '+label(graph,patient),
                'data':{'datePrescription':[body['date']],'dureeJours':[str(body['duration'])]},
                'relations':{'prescritA':[body['patient']],'prescritPar':[body['doctor']],
                             'prescritMedicament':body['medicines'],'issueConsultation':[consultation_id]}})
    if body.get('followup_date'):
        prepare('RendezVous',{'id':appointment_id,'label':'Suivi de '+label(graph,patient),
                'data':{'dateRdv':[body['followup_date']],'statutRdv':['Planifié']},
                'relations':{'rdvPatient':[body['patient']],'rdvMedecin':[body['doctor']]}})
    triples=[(subject,DCTERMS.identifier,Literal(fingerprint)),(patient,NS.suitPar,doctor)]
    triples += [(patient,NS.souffreDe,identifier(value)) for value in body['conditions']]
    if body.get('reason','').strip():triples.append((subject,RDFS.comment,Literal(body['reason'].strip(),lang='fr')))
    queries.append('INSERT DATA { '+' '.join(f'{s.n3()} {p.n3()} {o.n3()} .' for s,p,o in triples)+' }')
    query=';\n'.join(queries)
    commit(graph,destination,query)
    return {**result,'created':True,'message':'La consultation et ses liens ont été enregistrés dans le dossier.','sparql':query}
