import importlib.util
from pathlib import Path
from rdflib import Graph, RDF, OWL
from rdflib.compare import isomorphic

def test_protege_roundtrip(tmp_path):
    spec = importlib.util.spec_from_file_location('protege_data',Path(__file__).resolve().parents[1] / 'scripts/protege_data.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    initial = module.ROOT / 'data/ontology.ttl'
    module.ROOT = tmp_path
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/ontology.ttl').write_bytes(initial.read_bytes())
    output = tmp_path / 'test.owl'
    module.export_owl(output)
    exported = Graph().parse(output,format='xml')
    assert (module.NS.Alpha,RDF.type,OWL.NamedIndividual) in exported
    module.import_owl(output)
    assert isomorphic(exported, Graph().parse(tmp_path / 'data/live.ttl'))
    module.import_owl(output)
    assert len(list((tmp_path / 'data/backups').glob('*.ttl')))==1
