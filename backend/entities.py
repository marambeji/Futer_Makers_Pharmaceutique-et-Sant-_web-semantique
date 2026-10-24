"""CRUD for each named OWL class; literals and relations validated against schema."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from rdflib import RDF, RDFS, OWL, XSD, Literal
from .schema import NS, local, label, classes, fields, is_instance
from .store import commit

def identifier(value):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,59}',value):
        raise ValueError('Identifiant invalide : lettres ASCII, chiffres et underscore, sans espace.')
    return NS[value]

def class_uri(graph,value):
    uri=identifier(value)
    if uri not in classes(graph):
        raise ValueError('Classe inconnue : '+value)
    return uri

def serialize(graph,subject):
    return {'id':local(subject),'uri':str(subject),'label':label(graph,subject),
            'types':[local(t) for t in graph.objects(subject,RDF.type) if t in classes(graph)],
            'data':{local(p):[str(v) for v in graph.objects(subject,p)] for p in set(graph.predicates(subject,None)) if (p,RDF.type,OWL.DatatypeProperty) in graph},
            'relations':{local(p):[local(v) for v in graph.objects(subject,p)] for p in set(graph.predicates(subject,None)) if (p,RDF.type,OWL.ObjectProperty) in graph}}

def list_entities(graph,cls):
    cls=class_uri(graph,cls)
    subjects={s for s in graph.subjects(RDF.type,None) if str(s).startswith(str(NS)) and is_instance(graph,s,cls)}
    return [serialize(graph,s) for s in sorted(subjects,key=lambda s:label(graph,s))]

def literal(value, field):
    typ=field['range']
    value=str(value).strip()
    if len(value)>500 or not value:
        raise ValueError('Valeur vide ou trop longue pour '+field['id'])
    try:
        if typ=='integer':
            if not re.fullmatch(r'-?\d+',value): raise ValueError()
            number=int(value)
            if field['id']=='age' and not 0<=number<=120: raise ValueError()
            if field['id'] in ('participants','dureeJours') and number<0: raise ValueError()
            if field['id']=='phase' and not 1<=number<=4: raise ValueError()
            return Literal(number,datatype=XSD.integer)
        if typ=='decimal':
            number=Decimal(value)
            if not number.is_finite() or number<0: raise ValueError()
            if field['id']=='couverture' and number>100: raise ValueError()
            return Literal(number,datatype=XSD.decimal)
        if typ=='date':
            return Literal(date.fromisoformat(value),datatype=XSD.date)
        if field['id']=='sexe' and value not in ('F','M','Autre','Non précisé'):
            raise ValueError()
        return Literal(value,datatype=XSD.string)
    except (ValueError,InvalidOperation) as exc:
        raise ValueError('Valeur invalide pour '+field['id']+' ('+typ+')') from exc

def validate_fields(graph,cls,data,relations):
    metadata={f['id']:f for f in fields(graph,cls)}
    triples=[]
    for key,values in {**data,**relations}.items():
        field=metadata.get(key)
        if not field or (field['kind']=='data') != (key in data):
            raise ValueError('Propriété hors schéma : '+key)
        if len(values)>50 or (not field['multiple'] and len(values)>1):
            raise ValueError('Cardinalité invalide pour '+key)
        for value in values:
            if field['kind']=='data':
                target=literal(value,field)
            else:
                target=identifier(value)
                if not is_instance(graph,target,NS[field['range']]):
                    raise ValueError('Cible invalide pour '+key+' : '+value+' doit être de type '+field['range'])
            triples.append((NS[key],target))
    for field in metadata.values():
        values=(data if field['kind']=='data' else relations).get(field['id'],[])
        if field['required'] and not values:
            raise ValueError('Champ obligatoire : '+field['id'])
    return triples

def upsert(graph,destination,cls,body,update=False,prepare_only=False):
    cls=class_uri(graph,cls)
    subject=identifier(body['id'])
    if update and (subject,RDF.type,cls) not in graph:
        raise LookupError('Individu introuvable dans cette classe.')
    if not update and (subject,None,None) in graph:
        raise FileExistsError('Cet identifiant est déjà utilisé.')
    name=body['label'].strip()
    if not 2<=len(name)<=150:
        raise ValueError('Le libellé doit contenir entre 2 et 150 caractères.')
    predicates=validate_fields(graph,cls,body.get('data',{}),body.get('relations',{}))
    triples=[(subject,RDF.type,cls),(subject,RDF.type,OWL.NamedIndividual),(subject,RDFS.label,Literal(name,lang='fr'))]
    triples += [(subject,p,o) for p,o in predicates]
    query='INSERT DATA { '+' '.join(f'{s.n3()} {p.n3()} {o.n3()} .' for s,p,o in triples)+' }'
    if update:
        # Replace exactly the editable schema fields; preserve other types/annotations.
        editable=[RDFS.label]+[NS[f['id']] for f in fields(graph,cls)]
        query=';\n'.join(f'DELETE WHERE {{ {subject.n3()} {p.n3()} ?o }}' for p in editable)+';\n'+query
    if prepare_only:
        return {'sparql':query}
    commit(graph,destination,query)
    return {'ok':True,'sparql':query,'entity':serialize(graph,subject)}

def remove(graph,destination,cls,value):
    cls=class_uri(graph,cls)
    subject=identifier(value)
    if not is_instance(graph,subject,cls):
        raise LookupError('Individu introuvable.')
    # Avoid silently breaking required relations in a consultation/prescription.
    for source,prop in graph.subject_predicates(subject):
        for source_type in graph.objects(source,RDF.type):
            if source_type in classes(graph):
                field=next((f for f in fields(graph,source_type) if NS[f['id']]==prop),None)
                if field and field['required'] and len(list(graph.objects(source,prop)))<=1:
                    raise ValueError('Suppression impossible : '+label(graph,source)+' nécessite la relation '+local(prop)+'. Modifier ou supprimer cet individu auparavant.')
    query=f'DELETE WHERE {{ {subject.n3()} ?p ?o }}; DELETE WHERE {{ ?s ?p {subject.n3()} }}'
    commit(graph,destination,query)
    return {'ok':True,'sparql':query}

def change_relation(graph,destination,source,predicate,target,delete=False):
    source,target=identifier(source),identifier(target)
    predicate=identifier(predicate)
    field=None
    for typ in graph.objects(source,RDF.type):
        if typ in classes(graph):
            field=next((f for f in fields(graph,typ) if f['kind']=='object' and NS[f['id']]==predicate),field)
    if not field or not is_instance(graph,target,NS[field['range']]):
        raise ValueError('Relation ou types des individus incompatibles avec le schéma.')
    values=list(graph.objects(source,predicate))
    if delete:
        if target not in values: raise LookupError('Relation absente.')
        if field['required'] and len(values)<=1: raise ValueError('Cette relation est obligatoire.')
    elif not field['multiple'] and values and target not in values:
        raise ValueError('Propriété fonctionnelle : retirer ou modifier la relation existante.')
    query=('DELETE' if delete else 'INSERT')+f' DATA {{ {source.n3()} {predicate.n3()} {target.n3()} . }}'
    commit(graph,destination,query)
    return {'ok':True,'sparql':query}
