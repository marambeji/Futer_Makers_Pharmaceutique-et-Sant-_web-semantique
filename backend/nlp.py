"""French, deterministic semantic parser: NLTK tokens/stems + RDF entity linking."""
import re
import unicodedata
from nltk.tokenize import RegexpTokenizer
from nltk.stem.snowball import FrenchStemmer
from rdflib import RDFS, RDF

PREFIX = 'PREFIX ph: <https://pharmagraph.example/ontology#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n'
tokenizer = RegexpTokenizer(r'\w+')
stemmer = FrenchStemmer()

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')

def translate_pharma(question, graph, ns):
    text = normalize(question)
    tokens = tokenizer.tokenize(text)
    stems = [stemmer.stem(t) for t in tokens]
    def has(*words):
        return any(stemmer.stem(normalize(word)) in stems for word in words)
    if any(t in tokens for t in ['supprimer', 'effacer', 'ajouter', 'modifier']):
        raise ValueError('Le traducteur est réservé à la consultation. Utilisez l’administration pour modifier les données.')
    entities = []
    for subject, label in graph.subject_objects(RDFS.label):
        if any((subject, RDF.type, cls) in graph for cls in [ns.Molecule, ns.EffetSecondaire, ns.ContreIndication, ns.EssaiClinique]):
            name = normalize(str(label))
            if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text):
                entities.append((subject, str(label)))
    molecules = [(s, l) for s, l in entities if (s, RDF.type, ns.Molecule) in graph]
    if len(molecules) > 1:
        raise ValueError('Posez une question sur une seule molécule à la fois.')
    if re.search(r'\bmolecule\s+(?!avec\b|qui\b|ayant\b|et\b)\w+', text) and not molecules:
        raise ValueError('Molécule non reconnue. Utilisez son nom complet tel qu’il apparaît dans le catalogue.')
    intent, prop, cls = 'molecules', None, ns.Molecule
    if has('effet', 'secondaire'):
        intent, prop, cls = 'effets', ns.aEffetSecondaire, ns.EffetSecondaire
    elif has('contre', 'déconseillé', 'contreindication'):
        intent, prop, cls = 'contre_indications', ns.aContreIndication, ns.ContreIndication
    elif has('essai', 'clinique', 'étude'):
        intent, prop, cls = 'essais', ns.etudieDans, ns.EssaiClinique
    elif not has('molécule', 'lister', 'liste', 'afficher', 'médicament'):
        raise ValueError('Question non reconnue. Essayez « Quels sont les effets secondaires de la Molécule Alpha ? »')
    # A linked condition in a request for molecules reverses the relation.
    conditions = [(s,l) for s,l in entities if (s,RDF.type,ns.EffetSecondaire) in graph or (s,RDF.type,ns.ContreIndication) in graph]
    if not molecules and conditions and has('molécule', 'médicament'):
        intent, prop, cls = 'molecules', None, ns.Molecule
    if prop:
        anchor = molecules[0][0].n3() if molecules else '?molecule'
        body = f'{anchor} a ph:Molecule ; <{prop}> ?resultat . ?resultat rdfs:label ?nom .'
        if not molecules:
            body += ' ?molecule rdfs:label ?moleculeNom .'
        if intent == 'essais':
            body += ' ?resultat ph:phase ?phase ; ph:participants ?participants ; ph:statut ?statut .'
            phase = re.search(r'phase\s+([1234])\b', text)
            if phase:
                body += f' FILTER (?phase = {int(phase.group(1))})'
    else:
        body = '?resultat a ph:Molecule ; rdfs:label ?nom .'
        if molecules:
            body += f' VALUES ?resultat {{ {molecules[0][0].n3()} }}'
        else:
            linked = [(s,l) for s,l in entities if (s, RDF.type, ns.EffetSecondaire) in graph or (s, RDF.type, ns.ContreIndication) in graph]
            for s, _ in linked:
                relation = ns.aEffetSecondaire if (s, RDF.type, ns.EffetSecondaire) in graph else ns.aContreIndication
                body += f' ?resultat <{relation}> {s.n3()} .'
    query = PREFIX + 'SELECT DISTINCT * WHERE { ' + body + ' } ORDER BY ?nom LIMIT 100'
    return {'intent': intent, 'tokens': tokens, 'stems': stems, 'entities': [l for _,l in entities], 'sparql': query, 'method': 'NLTK RegexpTokenizer + FrenchStemmer, lexique RDF et règles sémantiques'}

def translate(question, graph, ns):
    from .clinical_nlp import translate_clinical
    text=normalize(question)
    if re.search(r'\b(personne|personnes|people|person|persons|patient|patients|medecin|medecins|doctor|doctors|consultation|consultations|prescription|prescriptions|hopital|hopitaux|hospital|hospitals|maladie|maladies|disease|diseases|vehicule|vehicules|vehicle|vehicles|service|services|traitement|traitements|treatment|treatments|assurance|assurances|medicament|medicaments|medication|medications|rendez.vous|appointment|appointments)\b',text) and not re.search(r'\b(molecule|molecules|effet|effets|essai|essais|contre.indication)',text):
        return translate_clinical(question,graph)
    result=translate_pharma(question,graph,ns)
    result['explanation']='Recherche des relations pharmaceutiques explicites dans le graphe, à partir des entités reconnues.'
    return result
