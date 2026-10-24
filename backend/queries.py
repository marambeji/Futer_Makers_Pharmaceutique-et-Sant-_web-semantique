"""Documented SPARQL examples used by the console and evaluation suite."""
from .engine import PREFIX

QUERIES = [
 {'id':'patients','title':'Patients, âge et assurance facultative','features':'OPTIONAL, DISTINCT, ORDER BY','query':'''SELECT DISTINCT ?nom ?age ?assurance WHERE {
 ?p a ph:Patient ; rdfs:label ?nom ; ph:age ?age .
 OPTIONAL { ?p ph:assurePar/rdfs:label ?assurance }
} ORDER BY DESC(?age)'''},
 {'id':'four_classes','title':'Patients suivis à Carthage et médicaments prescrits','features':'Jointures sur 5 classes, FILTER','query':'''SELECT DISTINCT ?patient ?medecin ?hopital ?medicament WHERE {
 ?p a ph:Patient ; rdfs:label ?patient ; ph:suitPar ?m .
 ?m a ph:Medecin ; rdfs:label ?medecin ; ph:travailleDans ?h .
 ?h a ph:Hopital ; rdfs:label ?hopital .
 ?ord a ph:Prescription ; ph:prescritA ?p ; ph:prescritMedicament/rdfs:label ?medicament .
 FILTER (?h = ph:HopitalCarthage)
} ORDER BY ?patient'''},
 {'id':'multi_doctors','title':'Plusieurs médecins pour la même maladie','features':'GROUP BY, HAVING, COUNT DISTINCT','query':'''SELECT ?patient ?maladie (COUNT(DISTINCT ?m) AS ?nombreMedecins) WHERE {
 ?c a ph:Consultation ; ph:concernePatient ?p ; ph:realiseePar ?m ; ph:diagnostique ?d .
 ?p rdfs:label ?patient . ?d rdfs:label ?maladie .
} GROUP BY ?patient ?maladie HAVING (COUNT(DISTINCT ?m) > 1)'''},
 {'id':'aggregates','title':'Coût des consultations par médecin','features':'COUNT, SUM, AVG, MIN, MAX','query':'''SELECT ?medecin (COUNT(?c) AS ?consultations) (SUM(?cout) AS ?total)
 (AVG(?cout) AS ?moyenne) (MIN(?cout) AS ?minimum) (MAX(?cout) AS ?maximum) WHERE {
 ?c a ph:Consultation ; ph:realiseePar/rdfs:label ?medecin ; ph:cout ?cout .
} GROUP BY ?medecin ORDER BY DESC(?total)'''},
 {'id':'union','title':'Patients diabétiques ou hypertendus','features':'UNION, DISTINCT','query':'''SELECT DISTINCT ?nom WHERE {
 ?p a ph:Patient ; rdfs:label ?nom .
 { ?p ph:souffreDe ph:Diabete } UNION { ?p ph:souffreDe ph:Hypertension }
} ORDER BY ?nom'''},
 {'id':'subquery','title':'Médecins avec plus de consultations que la moyenne','features':'Sous-requêtes, AVG, GROUP BY, FILTER','query':'''SELECT ?medecin ?nombre ?moyenne WHERE {
 { SELECT ?m (COUNT(?c) AS ?nombre) WHERE {
     ?m a ph:Medecin . OPTIONAL { ?c a ph:Consultation ; ph:realiseePar ?m }
   } GROUP BY ?m }
 { SELECT (AVG(?n) AS ?moyenne) WHERE {
     { SELECT ?doc (COUNT(?consult) AS ?n) WHERE {
         ?doc a ph:Medecin . OPTIONAL { ?consult a ph:Consultation ; ph:realiseePar ?doc }
       } GROUP BY ?doc }
   } }
 ?m rdfs:label ?medecin . FILTER (?nombre > ?moyenne)
}'''},
 {'id':'temporal','title':'Voiture et prescription depuis le 23 avril 2026','features':'Jointures, xsd:date, FILTER','query':'''SELECT DISTINCT ?patient ?date WHERE {
 ?p a ph:Patient ; rdfs:label ?patient ; ph:possedeVehicule ?v .
 ?ord a ph:Prescription ; ph:prescritA ?p ; ph:datePrescription ?date .
 FILTER (?date >= "2026-04-23"^^xsd:date && ?date <= "2026-10-23"^^xsd:date)
} ORDER BY DESC(?date)'''},
 {'id':'risk','title':'Molécules et contre-indications liées aux prescriptions','features':'Jointures sur 6 classes','query':'''SELECT DISTINCT ?patient ?medicament ?molecule ?contreIndication WHERE {
 ?ord a ph:Prescription ; ph:prescritA/rdfs:label ?patient ; ph:prescritMedicament ?med .
 ?med rdfs:label ?medicament ; ph:contientMolecule ?mol .
 ?mol rdfs:label ?molecule ; ph:aContreIndication/rdfs:label ?contreIndication .
} ORDER BY ?patient'''},
]
for item in QUERIES:
    item['query']=PREFIX+item['query']
