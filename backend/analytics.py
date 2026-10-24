"""Dashboard aggregates computed only with SPARQL, never duplicated counters."""
from datetime import date
from .engine import PREFIX, execute

def dashboard(graph,min_age=0,max_age=120,sex='',start=None,end=None):
    if not 0<=min_age<=max_age<=120:
        raise ValueError('Intervalle d’âge invalide.')
    if sex not in ('','F','M','Autre','Non précisé'):
        raise ValueError('Sexe invalide.')
    for value in (start,end):
        if value: date.fromisoformat(value)
    if start and end and start>end: raise ValueError('La date de début dépasse la date de fin.')
    patient=f'?p a ph:Patient ; ph:age ?age ; ph:sexe ?sexe . FILTER (?age >= {min_age} && ?age <= {max_age}) '
    if sex: patient+=f'FILTER (?sexe = "{sex}") '
    def period(variable):
        parts=[]
        if start: parts.append(f'{variable} >= "{start}"^^xsd:date')
        if end: parts.append(f'{variable} <= "{end}"^^xsd:date')
        return ' FILTER ('+' && '.join(parts)+') ' if parts else ''
    consultation=patient+' ?c a ph:Consultation ; ph:concernePatient ?p ; ph:realiseePar ?m ; ph:dateConsultation ?date . '+period('?date')
    prescription=patient+' ?ord a ph:Prescription ; ph:prescritA ?p ; ph:datePrescription ?date . '+period('?date')
    queries={
        'patients':'SELECT (COUNT(DISTINCT ?p) AS ?total) WHERE { '+patient+' }',
        'medecins':'SELECT (COUNT(DISTINCT ?m) AS ?total) WHERE { '+patient+' ?p ph:suitPar ?m . }',
        'consultations':'SELECT (COUNT(DISTINCT ?c) AS ?total) WHERE { '+consultation+' }',
        'prescriptions':'SELECT (COUNT(DISTINCT ?ord) AS ?total) WHERE { '+prescription+' }',
        'maladies':'SELECT ?nom (COUNT(DISTINCT ?p) AS ?nombre) WHERE { '+patient+' ?p ph:souffreDe/rdfs:label ?nom . } GROUP BY ?nom ORDER BY DESC(?nombre)',
        'par_medecin':'SELECT ?nom (COUNT(DISTINCT ?c) AS ?nombre) WHERE { '+consultation+' ?m rdfs:label ?nom . } GROUP BY ?nom ORDER BY DESC(?nombre)',
        'medicaments':'SELECT ?nom (COUNT(DISTINCT ?ord) AS ?nombre) WHERE { '+prescription+' ?ord ph:prescritMedicament/rdfs:label ?nom . } GROUP BY ?nom ORDER BY DESC(?nombre)',
        'ages':'SELECT ?age (COUNT(DISTINCT ?p) AS ?nombre) WHERE { '+patient+' } GROUP BY ?age ORDER BY ?age',
        'sexes':'SELECT ?sexe (COUNT(DISTINCT ?p) AS ?nombre) WHERE { '+patient+' } GROUP BY ?sexe',
        'periode':'SELECT ?date (COUNT(DISTINCT ?c) AS ?nombre) WHERE { '+consultation+' } GROUP BY ?date ORDER BY ?date',
        'couts':'SELECT (COALESCE(SUM(?cout),0) AS ?total) (AVG(?cout) AS ?moyenne) (MIN(?cout) AS ?minimum) (MAX(?cout) AS ?maximum) WHERE { '+consultation+' ?c ph:cout ?cout . }',
    }
    output={key:{**execute(graph,PREFIX+query),'sparql':PREFIX+query} for key,query in queries.items()}
    return {'metrics':{key:int(output[key]['rows'][0]['total']) for key in ['patients','medecins','consultations','prescriptions']},
            'datasets':output,'scope':'Âge et sexe filtrent la cohorte de patients. La période filtre les consultations et prescriptions ; le nombre de patients et leurs médecins reste celui de la cohorte.'}
