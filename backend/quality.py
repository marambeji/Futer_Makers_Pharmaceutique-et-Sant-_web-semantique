"""Explainable checks over explicit data; not a full OWL reasoner."""
from rdflib import RDF, RDFS, OWL
from .schema import classes, fields, NS, label, local, is_instance
from .entities import literal

def audit(graph):
    issues=[]
    def add(code,subject,message):
        issues.append({'code':code,'id':local(subject),'label':label(graph,subject),'message':message})
    named_classes=classes(graph)
    for subject in sorted(set(graph.subjects(RDF.type,None)),key=str):
        types=[t for t in graph.objects(subject,RDF.type) if t in named_classes]
        if not types: continue
        if not graph.value(subject,RDFS.label): add('label',subject,'Libellé manquant.')
        seen=set()
        for cls in types:
            for field in fields(graph,cls):
                if field['id'] in seen: continue
                seen.add(field['id'])
                values=list(graph.objects(subject,NS[field['id']]))
                if field['required'] and not values: add('required',subject,'Champ obligatoire manquant : '+field['id'])
                if not field['multiple'] and len(values)>1: add('cardinality',subject,'Propriété fonctionnelle avec plusieurs valeurs : '+field['id'])
                for value in values:
                    if field['kind']=='object' and not is_instance(graph,value,NS[field['range']]):
                        add('range',subject,'Cible incompatible avec '+field['id']+' : '+str(value))
                    if field['kind']=='data':
                        try:
                            literal(str(value),field)
                            if value.datatype and str(value.datatype)!=field['range_uri']:
                                add('datatype',subject,'Type RDF incompatible avec '+field['id'])
                        except ValueError as error: add('value',subject,str(error))
        for left,right in graph.subject_objects(OWL.disjointWith):
            if is_instance(graph,subject,left) and is_instance(graph,subject,right):
                add('disjoint',subject,'Types déclarés disjoints : '+local(left)+' / '+local(right))
    for prop in set(graph.subjects(RDF.type,OWL.ObjectProperty)):
        domain=graph.value(prop,RDFS.domain)
        for subject,target in graph.subject_objects(prop):
            if domain and not is_instance(graph,subject,domain):
                add('domain',subject,'Domaine incompatible avec '+local(prop))
    return {'issues':issues,'count':len(issues),'method':'Contrôles explicables du schéma : champs obligatoires, cardinalités, domaines, portées, types et valeurs. Ces vérifications ne remplacent pas HermiT dans Protégé.'}
