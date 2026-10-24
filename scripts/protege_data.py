"""Exchange a complete local ontology between Protégé and PharmaGraph.

Stop the application before importing. Export defaults to the saved graph.
"""
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.deps'))
from rdflib import Graph, RDF, OWL, Namespace, Literal
from rdflib.compare import isomorphic

NS = Namespace('https://pharmagraph.example/ontology#')

def export_owl(destination):
    source = ROOT / 'data/live.ttl'
    if not source.exists():
        source = ROOT / 'data/ontology.ttl'
    graph = Graph().parse(source, format='turtle')
    extension = ROOT / 'data/clinical.ttl'
    if extension.exists() and (NS.ClinicalExtension,OWL.versionInfo,Literal('2.0')) not in graph:
        graph.parse(extension,format='turtle')
    graph.remove((NS.ClinicalExtension,RDF.type,OWL.Ontology))
    if (NS.ClinicalExtension,OWL.versionInfo,Literal('2.0')) in graph:
        graph.add((NS.ClinicalExtension,RDF.type,OWL.NamedIndividual))
    # Explicit OWL declarations make the individuals easy to identify in editors.
    for cls in list(graph.subjects(RDF.type,OWL.Class)):
        for subject in list(graph.subjects(RDF.type, cls)):
            graph.add((subject, RDF.type, OWL.NamedIndividual))
    destination.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination, format='xml')
    if not isomorphic(graph, Graph().parse(destination, format='xml')):
        raise ValueError('La vérification RDF/XML a échoué.')
    print(f'Export OWL vérifié : {destination} ({len(graph)} triplets)')

def import_owl(source):
    graph = Graph().parse(source, format='xml')
    if (NS.Molecule, RDF.type, OWL.Class) not in graph:
        raise ValueError('Le fichier doit contenir la classe PharmaGraph Molecule et conserver le namespace du projet.')
    destination = ROOT / 'data/live.ttl'
    if destination.exists():
        backups = ROOT / 'data/backups'
        backups.mkdir(exist_ok=True)
        shutil.copy2(destination, backups / ('live-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.ttl'))
    temporary = destination.with_suffix('.tmp')
    graph.serialize(temporary, format='turtle')
    temporary.replace(destination)
    print(f'Import terminé : {len(graph)} triplets. Relancez python run.py.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export', 'import'])
    parser.add_argument('file', nargs='?', type=Path, default=ROOT / 'data/pharmagraph.owl')
    args = parser.parse_args()
    if args.action == 'export':
        if args.file.exists():
            parser.error('Le fichier existe déjà. Choisissez un nouveau nom pour préserver les modifications de Protégé.')
        export_owl(args.file)
    else:
        import_owl(args.file)
