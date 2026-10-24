"""Compositional, schema-grounded French/English NLP -> SPARQL (no LLM)."""
import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo
import os
import re
from rdflib import RDF, RDFS, OWL, Literal, XSD
from nltk.tokenize import RegexpTokenizer
from nltk.stem.snowball import FrenchStemmer, EnglishStemmer
from .schema import NS, classes, local, label
from .engine import PREFIX, validate

EXAMPLES = [
 'Cite tous les patients.',
 'Quels patients possèdent une voiture ?',
 'Affiche les patients suivis par le docteur Ahmed.',
 'Quels patients souffrent de diabète et prennent le Médicament Alpha ?',
 'Quels médecins travaillent dans les hôpitaux qui accueillent des patients âgés de plus de 60 ans ?',
 'Quels patients ont consulté plusieurs médecins pour une même maladie ?',
 'Quels patients possèdent une voiture et ont reçu une prescription dans les six derniers mois ?',
 'Quels patients sont suivis par le docteur Ahmed dans l’Hôpital Carthage ?',
 'List patients with a car.',
]

def normalize(value):
    from .nlp import normalize as norm
    return norm(value)

def months_before(today,n):
    month_index=today.year*12+today.month-1-n
    year,month=divmod(month_index,12)
    return date(year,month+1,min(today.day,calendar.monthrange(year,month+1)[1]))

def link_entities(graph,text):
    recognized=[]
    aliases={}
    named_classes=set(classes(graph))
    for subject in set(graph.subjects(RDFS.label,None)):
        types=set(graph.objects(subject,RDF.type)) & named_classes
        if not types: continue
        name=label(graph,subject)
        candidates={normalize(name), normalize(re.sub(r'\s*\([^)]*\)','',name)), normalize(local(subject))}
        if NS.Medecin in types:
            short=normalize(name).replace('docteur ','')
            candidates|={short,'doctor '+short,'dr '+short}
        if subject==NS.Diabete: candidates|={'diabetes','diabetique','diabetiques'}
        if NS.Medicament in types:
            candidates|={normalize(name).replace('medicament','medication')}
        for alias in candidates:
            if len(alias)>2: aliases.setdefault(alias,set()).add(subject)
    for alias,subjects in sorted(aliases.items(),key=lambda x:-len(x[0])):
        if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text):
            if len(subjects)>1: raise ValueError('Entité ambiguë : '+alias)
            subject=next(iter(subjects))
            if subject not in [s for s,_ in recognized]:
                recognized.append((subject,label(graph,subject)))
    return recognized

def translate_clinical(question,graph,today=None):
    text=normalize(question)
    tokens=RegexpTokenizer(r'\w+').tokenize(text)
    french=FrenchStemmer(); english=EnglishStemmer()
    stems=[french.stem(t) for t in tokens]
    english_stems=[english.stem(t) for t in tokens]
    def has(*words):
        return any(french.stem(normalize(word)) in stems or english.stem(normalize(word)) in english_stems for word in words)
    if any(re.search(r'\b'+w+r'\w*\b',text) for w in ['supprim','effac','ajout','modifi','delet','insert','updat']):
        raise ValueError('Les questions NLP sont en lecture seule. Utilisez le CRUD pour écrire.')
    entities=link_entities(graph,text)
    # Target class is the first explicitly requested class, not a noun in a nested clause.
    synonyms={'Personne':['personnes?','people','persons?'], 'Patient':['patients?'], 'Medecin':['medecins?','doctors?'], 'Consultation':['consultations?'],
              'Prescription':['prescriptions?'], 'Hopital':['hopitaux','hopital','hospitals?'],
              'Medicament':['medicaments?','medications?'], 'Maladie':['maladies?','diseases?'],
              'Vehicule':['vehicules?','vehicles?'], 'Service':['services?'],
              'Traitement':['traitements?','treatments?'], 'Assurance':['assurances?'], 'RendezVous':['rendez.vous','appointments?']}
    candidates=[]
    for cls in classes(graph):
        for pattern in synonyms.get(local(cls),[re.escape(normalize(label(graph,cls)))]):
            match=re.search(r'\b'+pattern+r'\b',text)
            if match: candidates.append((match.start(),cls))
    if not candidates: raise ValueError('Classe non reconnue. Exemple : « Cite tous les patients ».')
    target=min(candidates,key=lambda x:x[0])[1]
    target_id=local(target)
    by_type=lambda cls:[s for s,_ in entities if (s,RDF.type,NS[cls]) in graph]
    doctors,hospitals,diseases,meds=map(by_type,['Medecin','Hopital','Maladie','Medicament'])
    if re.search(r'\b(docteur|doctor|dr)\s+\w+',text) and not doctors:
        raise ValueError('Médecin non reconnu : utilisez le nom présent dans le catalogue.')
    body=[f'?resultat a/rdfs:subClassOf* ph:{target_id} ; rdfs:label ?nom .']
    select='DISTINCT ?nom ?resultat'
    suffix='ORDER BY ?nom LIMIT 100'
    explanation=[f'Sélection des individus de la classe {label(graph,target)}.']
    used=[]
    def edge(s,p,o):
        if not (NS[p],RDF.type,OWL.ObjectProperty) in graph and not (NS[p],RDF.type,OWL.DatatypeProperty) in graph:
            raise ValueError('Le schéma chargé ne contient pas la propriété '+p)
        used.append(p); body.append(f'{s} ph:{p} {o} .')
    def values(variable,uris):
        if uris: body.append('VALUES '+variable+' { '+' '.join(s.n3() for s in uris)+' }')
    wants_vehicle=bool(re.search(r'\b(voiture|voitures|car|cars|vehicule|vehicle)\b',text)) and target!=NS.Vehicule
    age=re.search(r'(plus de|moins de|au moins|au plus|over|under|older than|younger than|at least|at most)\s*(\d{1,3})\s*(?:ans|years)?',text)
    months=re.search(r'(?:(\d{1,2})|\b(six|trois|douze|three|twelve))\s+(?:derniers?\s+)?(?:mois|months)',text)
    since=re.search(r'(?:depuis|since)\s+(\d{4}-\d{2}-\d{2})',text)
    multi=bool(re.search(r'plusieurs medecins|multiple doctors|several doctors',text))
    if multi and target!=NS.Patient: raise ValueError('La recherche multi-médecins porte sur les patients.')
    patient='?resultat' if target==NS.Patient else '?patient'
    if target in (NS.Patient,NS.Medecin):
        if target==NS.Medecin:
            if hospitals or age or re.search(r'hopit|hospital',text):
                edge('?resultat','travailleDans','?hopital'); values('?hopital',hospitals)
                if age:
                    body.append('?patient a ph:Patient .'); edge('?patient','accueilliDans','?hopital')
            elif re.search(r'travaill|work',text):
                edge('?resultat','travailleDans','?hopital')
            if doctors: values('?resultat',doctors)
        else:
            if doctors or has('suivi','followed'):
                edge(patient,'suitPar','?medecin');values('?medecin',doctors)
            if hospitals:
                if doctors or re.search(r'suivi|followed',text):
                    edge('?medecin','travailleDans','?hopital')
                else: edge(patient,'accueilliDans','?hopital')
                values('?hopital',hospitals)
        if age:
            comparator={'plus de':'>','moins de':'<','au moins':'>=','au plus':'<=','over':'>','under':'<','older than':'>','younger than':'<','at least':'>=','at most':'<='}[age.group(1)]
            edge(patient,'age','?age');body.append(f'FILTER (?age {comparator} {int(age.group(2))})')
            explanation.append('Filtrage numérique de l’âge des patients.')
        if wants_vehicle:
            edge(patient,'possedeVehicule','?vehicule'); explanation.append('Présence d’un véhicule associé au patient.')
        for uri in diseases:
            edge(patient,'souffreDe',uri.n3())
        for uri in meds:
            edge(patient,'prendMedicament',uri.n3())
        if re.search(r'souffr|atteint|disease|diabet',text) and not diseases:
            raise ValueError('Maladie non reconnue : choisissez un libellé présent dans le graphe.')
        if re.search(r'prennent|prend |taking |takes ',text) and not meds:
            raise ValueError('Précisez le médicament par son nom complet dans le catalogue.')
        if months or since or re.search(r'prescription',text):
            edge('?prescription','prescritA',patient);edge('?prescription','datePrescription','?date')
            today=today or datetime.now(ZoneInfo(os.getenv('PHARMAGRAPH_TIMEZONE','Africa/Tunis'))).date()
            if months:
                count=int(months.group(1) or {'six':6,'trois':3,'douze':12,'three':3,'twelve':12}[months.group(2)])
                cutoff=months_before(today,count)
            elif since:
                try: cutoff=date.fromisoformat(since.group(1))
                except ValueError as exc: raise ValueError('Date invalide.') from exc
            else: cutoff=None
            if cutoff:
                body.append(f'FILTER (?date >= "{cutoff.isoformat()}"^^xsd:date && ?date <= "{today.isoformat()}"^^xsd:date)')
                explanation.append(f'Prescriptions du {cutoff.isoformat()} au {today.isoformat()}, bornes incluses.')
        if multi:
            edge('?consultation','concernePatient',patient);edge('?consultation','realiseePar','?medecinConsulte');edge('?consultation','diagnostique','?maladie')
            body.append('?maladie rdfs:label ?maladieNom .')
            select='?nom ?resultat ?maladieNom (COUNT(DISTINCT ?medecinConsulte) AS ?nombreMedecins)'
            suffix='GROUP BY ?nom ?resultat ?maladieNom HAVING (COUNT(DISTINCT ?medecinConsulte) > 1) ORDER BY ?nom LIMIT 100'
            explanation.append('Groupement par patient et maladie, avec au moins deux médecins distincts.')
    elif target==NS.Consultation:
        edge('?resultat','concernePatient','?patient');edge('?resultat','realiseePar','?medecin')
        values('?medecin',doctors)
        body.append('?patient rdfs:label ?patientNom . ?medecin rdfs:label ?medecinNom .')
        select='DISTINCT ?nom ?patientNom ?medecinNom'
    else:
        # Generic class listing is allowed only when there are no unsupported clauses.
        if re.search(r'\b(avec|with|qui|whose|where|suivi|taking|dans|depuis)\b',text):
            raise ValueError('Cette combinaison n’est pas encore couverte. Utilisez la console SPARQL ou les exemples.')
    if re.search(r'\b(sans|without|ou|or|entre|between)\b',text):
        raise ValueError('Négation, alternative ou intervalle non pris en charge par ce parseur ; utilisez la console SPARQL.')
    if not used and target in (NS.Patient,NS.Medecin) and re.search(r'\b(avec|with|qui|whose|where|souffr|dans|depuis)\b',text):
        raise ValueError('Critère non reconnu. La requête n’est pas exécutée pour éviter une réponse trompeuse.')
    query=PREFIX+'SELECT '+select+' WHERE {\n '+'\n '.join(body)+'\n} '+suffix
    validate(query)
    explanation += ['Entités reconnues : '+', '.join(name for _,name in entities)+'.'] if entities else []
    return {'intent':'clinical_'+target_id.lower(),'tokens':tokens,'stems':stems,
            'english_stems':english_stems, 'entities':[name for _,name in entities],
            'sparql':query,'explanation':' '.join(explanation),'schema_properties':sorted(set(used)),
            'method':'NLTK : tokenisation FR/EN, racinisation, liaison au lexique RDF, grammaire compositionnelle et validation SPARQL'}
