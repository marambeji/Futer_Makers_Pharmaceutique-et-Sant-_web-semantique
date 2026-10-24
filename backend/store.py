"""Load/migrate RDF data and commit changes atomically within one process."""
from pathlib import Path
from rdflib import Graph, RDF, OWL, Literal
from .schema import NS

def load_graph(root, destination):
    graph=Graph().parse(destination if destination.exists() else root/'data/ontology.ttl',format='turtle')
    # Merge the new extension once, preserving pre-existing data and deletions.
    changed=False
    if (NS.ClinicalExtension,OWL.versionInfo,Literal('2.0')) not in graph:
        graph.parse(root/'data/clinical.ttl',format='turtle')
        changed=True
    if (NS.ClinicalExtension,RDF.type,OWL.Ontology) in graph:
        graph.remove((NS.ClinicalExtension,RDF.type,OWL.Ontology))
        graph.add((NS.ClinicalExtension,RDF.type,OWL.NamedIndividual))
        changed=True
    if destination.exists() and changed:
        persist(graph,destination)
    return graph

def clone(graph):
    copy=Graph()
    for prefix,namespace in graph.namespaces():
        copy.bind(prefix,namespace)
    for triple in graph:
        copy.add(triple)
    return copy

def persist(graph, destination):
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_suffix('.tmp')
    graph.serialize(temporary,format='turtle')
    temporary.replace(destination)

def commit(graph, destination, query):
    candidate=clone(graph)
    candidate.update(query)
    persist(candidate,destination)
    graph.remove((None,None,None))
    for triple in candidate:
        graph.add(triple)
