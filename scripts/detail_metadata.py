"""Statement-scoped Wikidata metadata for individual catalog pages.

The table's existing flattened fields are unchanged. Preserve statement identity,
rank and qualifiers so a license applying to one version is never presented as
an unqualified license for the entire resource.
"""
import json
from collections import defaultdict
from html import escape
from urllib.parse import urlsplit
from rdflib import Literal, URIRef
from rdflib.namespace import RDF
from semantic_config import OKG

FIELDS = {'P275': 'Licenses', 'P155': 'Predecessors', 'P156': 'Successors',
          'P6216': 'Copyright status', 'P7510': 'Namespace identifiers',
          'P856': 'Official websites', 'P1324': 'Source repositories'}
WB = 'http://wikiba.se/ontology#'


def query(qids):
    values = ' '.join('wd:' + q for q in qids)
    return f'''PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?item ?statement ?property ?propertyLabel ?value ?valueLabel ?rank
                ?qualifier ?qualifierLabel ?qualifierValue ?qualifierValueLabel
                ?precision ?calendar
WHERE {{
 VALUES ?item {{ {values} }}
 {{ VALUES ?property {{ wd:P275 wd:P155 wd:P156 wd:P6216 wd:P7510 wd:P856 wd:P1324 }} }}
 UNION {{ ?property wikibase:propertyType wikibase:ExternalId . }}
 ?property wikibase:claim ?claim ; wikibase:statementProperty ?statementProperty .
 ?item ?claim ?statement .
 ?statement ?statementProperty ?value ; wikibase:rank ?rank .
 FILTER(?rank != wikibase:DeprecatedRank)
 OPTIONAL {{ ?property rdfs:label ?propertyLabel . FILTER(LANG(?propertyLabel) = "en") }}
 OPTIONAL {{ ?value rdfs:label ?valueLabel . FILTER(LANG(?valueLabel) = "en") }}
 OPTIONAL {{
   ?qualifier wikibase:qualifier ?qualifierPredicate .
   ?statement ?qualifierPredicate ?qualifierValue .
   OPTIONAL {{ ?qualifier rdfs:label ?qualifierLabel . FILTER(LANG(?qualifierLabel) = "en") }}
   OPTIONAL {{ ?qualifierValue rdfs:label ?qualifierValueLabel . FILTER(LANG(?qualifierValueLabel) = "en") }}
   OPTIONAL {{
     ?qualifier wikibase:qualifierValue ?qualifierNodePredicate .
     ?statement ?qualifierNodePredicate ?timeNode .
     ?timeNode wikibase:timeValue ?qualifierValue ; wikibase:timePrecision ?precision ; wikibase:timeCalendarModel ?calendar .
   }}
 }}
}}'''


def parse(rows):
    grouped = {}
    for row in rows:
        v = lambda k: row.get(k, {}).get('value')
        if not all(v(k) for k in ('item', 'statement', 'property', 'value', 'rank')):
            raise ValueError('Incomplete detail metadata statement')
        if v('rank') == WB + 'DeprecatedRank':
            continue
        entry = grouped.setdefault((v('item'), v('statement')), {
            'statement': v('statement'), 'property': v('property'),
            'propertyLabel': v('propertyLabel') or v('property').rsplit('/', 1)[-1],
            'value': dict(row['value']), 'label': v('valueLabel') or v('value'),
            'rank': v('rank'), 'qualifiers': []})
        if v('qualifier') and v('qualifierValue'):
            q = {'property': v('qualifier'), 'propertyLabel': v('qualifierLabel') or v('qualifier').rsplit('/', 1)[-1],
                 'value': dict(row['qualifierValue']), 'label': v('qualifierValueLabel') or v('qualifierValue')}
            if v('precision'):
                q.update(precision=int(v('precision')), calendar=v('calendar'))
            if q not in entry['qualifiers']:
                entry['qualifiers'].append(q)
    result = defaultdict(list)
    for (item, _), entry in sorted(grouped.items()):
        entry['qualifiers'].sort(key=lambda q: json.dumps(q, sort_keys=True))
        result[item].append(entry)
    return dict(result)


def add_to_graph(graph, subject, entries):
    for entry in entries:
        node = URIRef(entry['statement'])
        graph.add((subject, OKG.detailStatement, node))
        graph.add((node, RDF.type, RDF.Statement))
        graph.add((node, RDF.subject, subject))
        graph.add((node, RDF.predicate, URIRef(entry['property'])))
        binding = entry['value']
        obj = URIRef(binding['value']) if binding['type'] == 'uri' else Literal(
            binding['value'], lang=binding.get('xml:lang'), datatype=binding.get('datatype'))
        graph.add((node, RDF.object, obj))
        graph.add((node, OKG.statementMetadata, Literal(json.dumps(entry, sort_keys=True), datatype=RDF.JSON)))


def projection(graph, subject):
    return sorted([json.loads(str(payload)) for node in graph.objects(subject, OKG.detailStatement)
                   for payload in graph.objects(node, OKG.statementMetadata)], key=lambda e: e['statement'])


def safe_url(value):
    try:
        u = urlsplit(value)
        return u.scheme in ('http', 'https') and bool(u.netloc)
    except ValueError:
        return False


def display_value(entry):
    text = entry['label']
    if entry.get('precision') is not None:
        from release_metadata import normalized_date
        date = normalized_date(entry['value']['value'], entry['precision'], entry.get('calendar'))
        text = date or text + ' (source date; calendar or precision not supported)'
    escaped = escape(text)
    value = entry['value']
    if value.get('type') == 'uri' and safe_url(value['value']):
        return f'<a href="{escape(value["value"], quote=True)}" target="_blank" rel="noopener noreferrer">{escaped}</a>'
    return escaped


def render(entries, primary_urls=()):
    groups = defaultdict(list)
    for entry in entries:
        prop = entry['property'].rsplit('/', 1)[-1]
        if prop in ('P856', 'P1324') and entry['value']['value'] in primary_urls and not entry['qualifiers']:
            continue
        heading = FIELDS.get(prop, 'Catalog identifiers')
        text = display_value(entry)
        if heading == 'Catalog identifiers':
            text = escape(entry['propertyLabel']) + ': ' + text
        if entry['qualifiers']:
            text += '<ul>' + ''.join('<li>' + escape(q['propertyLabel']) + ': ' + display_value(q) + '</li>' for q in entry['qualifiers']) + '</ul>'
        if entry['rank'] == WB + 'PreferredRank':
            text += ' <span class="detail-tag">Preferred statement</span>'
        if safe_url(entry['statement']):
            text += ' <a href="' + escape(entry['statement'], quote=True) + '">Wikidata statement</a>'
        groups[heading].append(text)
    return '\n'.join('<section class="detail-resource-links" style="margin:1.5rem 0;overflow-wrap:anywhere"><h2>' + escape(heading) + '</h2><ul>' +
                     ''.join('<li>' + text + '</li>' for text in groups[heading]) + '</ul></section>'
                     for heading in sorted(groups))
