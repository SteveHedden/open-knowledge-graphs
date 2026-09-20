"""Wikidata P348 releases with dates bound to the same statement.

No repository discovery. All qualifiers/references returned by the source are
preserved; unsupported calendars/precision and conflicting dates stay unknown.
"""
from __future__ import annotations
import calendar
import hashlib
import json
import re
from datetime import date
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD, PROV

BASE = 'https://openknowledgegraphs.com/'
from semantic_config import OKG
WB = 'http://wikiba.se/ontology#'
GREGORIAN = 'http://www.wikidata.org/entity/Q1985727'

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def value(row,key):
    return row.get(key,{}).get('value')

def query(scope, version='P348', publication='P577'):
    return f'''PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX pqv: <http://www.wikidata.org/prop/qualifier/value/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT DISTINCT ?item ?verStmt ?version ?versionRank ?pubDate ?precision ?calendar ?dateValue
                ?qualifierProperty ?qualifierValue ?reference ?referenceProperty ?referenceValue
WHERE {{
  {{ {scope} }}
  ?item p:{version} ?verStmt .
  ?verStmt ps:{version} ?version ; wikibase:rank ?versionRank .
  FILTER(?versionRank != wikibase:DeprecatedRank)
  OPTIONAL {{
    ?verStmt pq:{publication} ?pubDate ; pqv:{publication} ?dateValue .
    ?dateValue wikibase:timeValue ?pubDate ; wikibase:timePrecision ?precision ; wikibase:timeCalendarModel ?calendar .
  }}
  OPTIONAL {{ ?verStmt ?qualifierProperty ?qualifierValue .
    FILTER(STRSTARTS(STR(?qualifierProperty), "http://www.wikidata.org/prop/qualifier/"))
    FILTER(!STRSTARTS(STR(?qualifierProperty), "http://www.wikidata.org/prop/qualifier/value")) }}
  OPTIONAL {{ ?verStmt prov:wasDerivedFrom ?reference .
    OPTIONAL {{ ?reference ?referenceProperty ?referenceValue .
      FILTER(STRSTARTS(STR(?referenceProperty), "http://www.wikidata.org/prop/reference/"))
      FILTER(!STRSTARTS(STR(?referenceProperty), "http://www.wikidata.org/prop/reference/value")) }} }}
}}'''

def normalized_date(raw, precision, calendar):
    if calendar != GREGORIAN or precision not in (9,10,11): return None
    m=re.fullmatch(r'\+?(\d{4})-(\d{2})-(\d{2})T.*',raw or '')
    if not m:return None
    y,mo,d=map(int,m.groups())
    try:date(y,mo if precision>=10 else 1,d if precision==11 else 1)
    except ValueError:return None
    return f'{y:04}' + (f'-{mo:02}' if precision>=10 else '') + (f'-{d:02}' if precision==11 else '')

def candidates(rows):
    grouped={}
    for row in rows:
        item,version,statement=(value(row,k) for k in ('item','version','verStmt'))
        rank=value(row,'versionRank') or WB+'NormalRank'
        if not item or not version or rank==WB+'DeprecatedRank':continue
        item=item.replace('https://www.wikidata.org/entity/','http://www.wikidata.org/entity/')
        # Statement identity is mandatory for production provenance; synthetic
        # legacy callers may omit it but cannot create a verifiable event.
        key=(item,statement or digest([version,rank,value(row,'pubDate')]))
        c=grouped.setdefault(key,{'version':version,'statement':statement,'rank':rank,'dates':[], 'qualifiers':{},'references':{}})
        if value(row,'pubDate'):
            try:precision=int(value(row,'precision'))
            except (ValueError,TypeError):precision=None
            dt={'value':value(row,'pubDate'),'precision':precision,'calendar':value(row,'calendar')}
            if value(row,'dateValue'):dt['node']=value(row,'dateValue')
            if dt not in c['dates']:c['dates'].append(dt)
        for pk,vk,target in [('qualifierProperty','qualifierValue',c['qualifiers']),('referenceProperty','referenceValue',c['references'].setdefault(value(row,'reference'),{}))]:
            if value(row,pk) and value(row,vk):
                values=target.setdefault(value(row,pk),[])
                binding=row[vk]
                if binding not in values:values.append(binding)
    result={}
    for (item,_),c in grouped.items():
        c['references']={k:v for k,v in c['references'].items() if k}
        c['dates'].sort(key=lambda d:json.dumps(d,sort_keys=True))
        for properties in [c['qualifiers'],*c['references'].values()]:
            for vals in properties.values():vals.sort(key=lambda v:json.dumps(v,sort_keys=True))
        dates={normalized_date(d['value'],d['precision'],d['calendar']) for d in c['dates']}
        if len(dates)==1 and None not in dates:
            c['date']=next(iter(dates));c['datePrecision']={4:'year',7:'month',10:'day'}[len(c['date'])]
        elif c['dates']:c['dateIssue']='conflicting-or-unsupported-date'
        result.setdefault(item,[]).append(c)
    for vals in result.values():vals.sort(key=lambda c:(c['version'],c['statement'] or ''))
    return result

def date_interval(value):
    parts=list(map(int,value.split('-')))
    y=parts[0];m=parts[1] if len(parts)>1 else 1;d=parts[2] if len(parts)>2 else 1
    end_month=parts[1] if len(parts)>1 else 12
    end_day=parts[2] if len(parts)>2 else calendar.monthrange(y,end_month)[1]
    return date(y,m,d),date(y,end_month,end_day)

def select(rows):
    out={}
    for item,vals in candidates(rows).items():
        eligible=[c for c in vals if c['rank']==WB+'PreferredRank'] or vals
        dated=[c for c in eligible if c.get('date')]
        chosen=max(dated or eligible,key=lambda c:(c.get('date',''),c['version'],c['statement'] or ''))
        # Deterministic legacy tie breaking remains; expose uncertainty and do
        # not advertise an ambiguous tied release as a verified event.
        tied=[c for c in eligible if c.get('date')==chosen.get('date')]
        chosen=dict(chosen)
        if len({c['version'] for c in tied})>1:chosen['selectionIssue']='tied-release-candidates'
        if chosen.get('date'):
            start,end=date_interval(chosen['date'])
            for other in dated:
                other_start,other_end=date_interval(other['date'])
                if other['version']!=chosen['version'] and start<=other_end and other_start<=end:
                    chosen['selectionIssue']='overlapping-release-dates'
        out[item]=chosen
    return out

def binding_term(binding):
    if binding.get('type')=='uri':return URIRef(binding['value'])
    return Literal(binding['value'],lang=binding.get('xml:lang'),datatype=URIRef(binding['datatype']) if binding.get('datatype') else None)

def add_to_graph(graph,subject,release):
    node=URIRef(BASE+'releases/'+digest(release))
    graph.add((subject,OKG.latestRelease,node));graph.add((node,RDF.type,OKG.Release))
    graph.add((node,OKG.releaseMetadata,Literal(json.dumps(release,sort_keys=True,ensure_ascii=False))))
    graph.add((subject,OKG.latestVersion,Literal(release['version'])))
    graph.add((node,OKG.releaseVersion,Literal(release['version'])))
    if release.get('statement'):
        statement=URIRef(release['statement'])
        graph.add((node,OKG.sourceStatement,statement))
        graph.add((statement,URIRef('http://www.wikidata.org/prop/statement/P348'),Literal(release['version'])))
        graph.add((statement,URIRef(WB+'rank'),URIRef(release['rank'])))
        for predicate,values in release['qualifiers'].items():
            for binding in values:graph.add((statement,URIRef(predicate),binding_term(binding)))
        for ref,properties in release['references'].items():
            graph.add((statement,PROV.wasDerivedFrom,URIRef(ref)))
            for predicate,values in properties.items():
                for binding in values:graph.add((URIRef(ref),URIRef(predicate),binding_term(binding)))
        for raw in release['dates']:
            value_node=URIRef(raw.get('node') or BASE+'release-date-values/'+digest(raw))
            graph.add((statement,URIRef('http://www.wikidata.org/prop/qualifier/value/P577'),value_node))
            graph.add((value_node,URIRef(WB+'timeValue'),Literal(raw['value'],datatype=XSD.dateTime)))
            if raw.get('precision') is not None:graph.add((value_node,URIRef(WB+'timePrecision'),Literal(raw['precision'])))
            if raw.get('calendar'):graph.add((value_node,URIRef(WB+'timeCalendarModel'),URIRef(raw['calendar'])))
    graph.add((node,OKG.statementRank,URIRef(release['rank'])))
    if release.get('date'):
        typ={'day':XSD.date,'month':XSD.gYearMonth,'year':XSD.gYear}[release['datePrecision']]
        graph.add((subject,OKG.releaseDate,Literal(release['date'],datatype=typ)))
        graph.add((subject,OKG.releaseDatePrecision,Literal(release['datePrecision'])))
    return node

def projection(graph,subject):
    node=graph.value(subject,OKG.latestRelease)
    raw=graph.value(node,OKG.releaseMetadata) if node else None
    return json.loads(str(raw)) if raw else None

def validate_graph(graph):
    """Reject divergence between evidence, queryable RDF and display scalars."""
    for subject,node in graph.subject_objects(OKG.latestRelease):
        release=projection(graph,subject)
        if not release:raise ValueError('Release node has no source evidence')
        if release['rank'] not in (WB+'PreferredRank',WB+'NormalRank'):raise ValueError('Unsupported release rank')
        supported={normalized_date(d['value'],d['precision'],d['calendar']) for d in release['dates']}
        if release.get('date') and (supported!={release['date']} or release.get('dateIssue')):
            raise ValueError('Release date does not match its paired source evidence')
        expected=Graph();expected_node=add_to_graph(expected,subject,release)
        if node!=expected_node or any(t not in graph for t in expected):
            raise ValueError('Release RDF differs from its evidence projection')
        for predicate in (OKG.latestVersion,OKG.releaseDate,OKG.releaseDatePrecision,OKG.latestRelease):
            if set(graph.objects(subject,predicate))!=set(expected.objects(subject,predicate)):
                raise ValueError('Release scalar differs from its statement evidence')
