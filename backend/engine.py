"""Read-only local SPARQL validation and JSON serialization."""
from itertools import islice
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue
from pyparsing import ParseResults

PREFIX='PREFIX ph: <https://pharmagraph.example/ontology#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nPREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n'

def walk(node):
    if isinstance(node,CompValue):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node,(list,tuple,ParseResults)):
        for value in node:
            yield from walk(value)

def validate(query):
    try:
        parsed=parseQuery(query)
    except Exception as exc:
        raise ValueError('Syntaxe SPARQL invalide : '+str(exc)) from exc
    if parsed[1].name not in ('SelectQuery','AskQuery'):
        raise ValueError('Seuls SELECT et ASK sont autorisés dans la console.')
    nodes=list(walk(parsed))
    if any(n.name in ('ServiceGraphPattern','DatasetClause') for n in nodes):
        raise ValueError('SERVICE et FROM sont interdits : seules les données locales sont interrogées.')
    return query

def execute(graph, query, max_rows=1000):
    validate(query)
    result=graph.query(query)
    if result.type=='ASK':
        return {'columns':['boolean'],'rows':[{'boolean':bool(result.askAnswer)}],'truncated':False}
    rows=[{str(k):str(v) for k,v in row.asdict().items()} for row in islice(result,max_rows+1)]
    return {'columns':[str(v) for v in result.vars], 'rows':rows[:max_rows], 'truncated':len(rows)>max_rows}
