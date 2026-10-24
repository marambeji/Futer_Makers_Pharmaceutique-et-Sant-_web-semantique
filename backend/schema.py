"""Schema inspection and editable field metadata read from the OWL graph."""
from rdflib import RDF, RDFS, OWL, URIRef, Namespace

NS = Namespace('https://pharmagraph.example/ontology#')
REQUIRED = {
    'Molecule': ['formule'], 'Patient': ['age','sexe'],
    'Consultation': ['concernePatient','realiseePar','dateConsultation'],
    'Prescription': ['prescritA','prescritPar','prescritMedicament','datePrescription'],
    'RendezVous': ['rdvPatient','rdvMedecin','dateRdv'],
    'Service': ['serviceDe'],
}

def local(uri):
    return str(uri).rsplit('#',1)[-1]

def label(graph, uri):
    return str(graph.value(uri,RDFS.label) or local(uri))

def classes(graph):
    return sorted({s for s in graph.subjects(RDF.type,OWL.Class) if isinstance(s,URIRef) and str(s).startswith(str(NS))},key=str)

def is_instance(graph, subject, cls):
    return any(cls in set(graph.transitive_objects(t,RDFS.subClassOf)) for t in graph.objects(subject,RDF.type))

def fields(graph, cls):
    ancestors = set(graph.transitive_objects(cls,RDFS.subClassOf))
    output=[]
    for typ,kind in [(OWL.DatatypeProperty,'data'),(OWL.ObjectProperty,'object')]:
        for prop in sorted(set(graph.subjects(RDF.type,typ)),key=str):
            if not any(domain in ancestors for domain in graph.objects(prop,RDFS.domain)):
                continue
            output.append({'id':local(prop),'uri':str(prop),'label':label(graph,prop),'kind':kind,
                           'range':local(graph.value(prop,RDFS.range) or ''),
                           'range_uri':str(graph.value(prop,RDFS.range) or ''),
                           'multiple':(prop,RDF.type,OWL.FunctionalProperty) not in graph,
                           'required':local(prop) in REQUIRED.get(local(cls),[])})
    return output

def describe(graph):
    return {'namespace':str(NS),'classes':[
        {'id':local(cls),'uri':str(cls),'label':label(graph,cls),
         'parents':[local(p) for p in graph.objects(cls,RDFS.subClassOf) if isinstance(p,URIRef)],
         'count':sum(is_instance(graph,s,cls) for s in set(graph.subjects(RDFS.label,None)) if (s,RDF.type,OWL.Class) not in graph and (s,RDF.type,OWL.Ontology) not in graph),
         'fields':fields(graph,cls)} for cls in classes(graph)]}
