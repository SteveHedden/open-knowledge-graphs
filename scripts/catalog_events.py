#!/usr/bin/env python3
"""Publisher-owned resource/software history; RDF is authoritative, JSON derived.

Git backfill establishes catalog inclusion evidence, never deployment evidence.
Refresh snapshots must not replace this append-only identity/history ledger.
"""
from __future__ import annotations
import argparse
import calendar
from datetime import date, datetime, timezone
import json
from pathlib import Path
import subprocess
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD
from semantic_config import OKG
from release_metadata import digest, BASE

KINDS={'resource':'ontologies','software':'software'}
LEDGER='data/catalog-events.ttl'
FEED='data/catalog-events.json'
REPO='https://github.com/SteveHedden/open-knowledge-graphs'

def now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def identity(kind,qid):return URIRef(BASE+'catalog-identities/'+kind+'/'+qid)
def event_id(kind,qid,event_type,version=None):return URIRef(BASE+'catalog-events/'+digest([kind,qid,event_type,version]))
def text(g,s,p):
    v=g.value(s,p)
    return str(v).replace('+00:00','Z') if v is not None and isinstance(v,Literal) and v.datatype==XSD.dateTime else str(v or '')
def write_graph(path,g):
    data='\n'.join(sorted(g.serialize(format='nt').splitlines()))+'\n'
    if path.exists() and path.read_text()==data:return
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp');temp.write_text(data);temp.replace(path)
def load(root):
    path=root/LEDGER
    return Graph().parse(path,format='turtle') if path.exists() else Graph()
def rows(root,kind):
    p=root/f'data/{KINDS[kind]}.json'
    return json.loads(p.read_text())['items'] if p.exists() else []
def qid(row):
    v=row.get('wikidataId','').rstrip('/').rsplit('/',1)[-1]
    return v if v.startswith('Q') and v[1:].isdigit() else None

def record_identity(g,kind,key,recorded=None,commit=None,uncertain=False):
    subject=identity(kind,key)
    if (subject,RDF.type,OKG.CatalogIdentity) in g:return subject
    g.add((subject,RDF.type,OKG.CatalogIdentity))
    g.add((subject,OKG.eventKind,Literal(kind)));g.add((subject,OKG.sourceEntity,URIRef('http://www.wikidata.org/entity/'+key)))
    g.add((subject,OKG.firstSeenBasis,Literal('unknown-baseline' if uncertain else 'catalog-commit' if commit else 'catalog-observation')))
    if recorded:g.add((subject,OKG.firstRecordedAt,Literal(recorded,datatype=XSD.dateTime)))
    if recorded and not uncertain:g.add((subject,OKG.firstSeenAt,Literal(recorded,datatype=XSD.dateTime)))
    if commit:g.add((subject,OKG.historySource,URIRef(REPO+'/commit/'+commit)))
    return subject

def git(repo,*args):return subprocess.check_output(['git',*args],cwd=repo,stderr=subprocess.DEVNULL).decode()
def historical_rows(repo,commit,kind):
    # JSON first; before projections existed inspect only resource subjects,
    # excluding linked creators and reference entities.
    stem=KINDS[kind]
    try:
        doc=json.loads(git(repo,'show',f'{commit}:data/{stem}.json'))
        return doc.get('items',[]) if isinstance(doc,dict) else doc
    except (subprocess.CalledProcessError,json.JSONDecodeError):pass
    try:g=Graph().parse(data=git(repo,'show',f'{commit}:data/{stem}.ttl'),format='turtle')
    except subprocess.CalledProcessError:return None
    return [{'wikidataId':str(q)} for s,q in g.subject_objects(OKG.wikidataId)
            if g.value(s,OKG.title) is not None]

def backfill(repo,root,ref='HEAD'):
    if git(repo,'rev-parse','--is-shallow-repository').strip()=='true':
        raise ValueError('Reliable backfill requires complete Git history')
    g=load(root)
    for kind,stem in KINDS.items():
        commits=git(repo,'log','--first-parent','--reverse','--format=%H %cI',ref,'--',f'data/{stem}.json',f'data/{stem}.ttl').splitlines()
        baseline=True
        for line in commits:
            commit,stamp=line.split(' ',1);items=historical_rows(repo,commit,kind)
            if items is None:continue
            for item in items:
                key=qid(item)
                if key:record_identity(g,kind,key,stamp,commit,uncertain=baseline)
            baseline=False
    # Registry retains previously listed IDs even if old files cannot be read.
    registry=root/'data/uri_registry.json'
    if registry.exists():
        for kind,entries in json.loads(registry.read_text()).items():
            if kind in KINDS:
                for key in entries:record_identity(g,kind,key,uncertain=True)
    for kind in KINDS:
        for row in rows(root,kind):
            if key:=qid(row):record_identity(g,kind,key,uncertain=True)
    write_graph(root/LEDGER,g)
    return g

def date_ended(value, today):
    try:
        bits=list(map(int,value.split('-')))
        y=bits[0];m=bits[1] if len(bits)>1 else 12
        d=bits[2] if len(bits)>2 else calendar.monthrange(y,m)[1]
        return date(y,m,d)<=today
    except (ValueError,IndexError):return False

def set_value(g,s,p,value):g.set((s,p,Literal(value)))
def event(g,owner,kind,key,typ,stamp,version=None):
    e=event_id(kind,key,typ,version)
    if (e,RDF.type,OKG.CatalogEvent) not in g:
        g.add((e,RDF.type,OKG.CatalogEvent));g.add((e,OKG.eventIdentity,owner))
        set_value(g,e,OKG.eventType,typ)
        g.add((e,OKG.discoveredAt,Literal(stamp,datatype=XSD.dateTime)))
    return e

def synchronize(root,observed_at=None):
    stamp=observed_at or now();today=datetime.fromisoformat(stamp.replace('Z','+00:00')).date()
    g=load(root)
    initialized=bool(list(g.subjects(RDF.type,OKG.CatalogIdentity)))
    # A missing seed never makes the pre-existing catalog look newly added.
    for e in list(g.subjects(RDF.type,OKG.CatalogEvent)):set_value(g,e,OKG.eventEligible,False)
    for owner in list(g.subjects(RDF.type,OKG.CatalogIdentity)):set_value(g,owner,OKG.catalogPresent,False)
    for kind in KINDS:
        for row in rows(root,kind):
            key=qid(row)
            if not key:continue
            owner=record_identity(g,kind,key,stamp,uncertain=not initialized)
            set_value(g,owner,OKG.catalogPresent,True)
            set_value(g,owner,OKG.title,row['title'])
            g.set((owner,OKG.catalogUrl,URIRef(row['canonicalUrl'])))
            first=text(g,owner,OKG.firstSeenAt)
            if first:
                e=event(g,owner,kind,key,'new-to-okg',first)
                set_value(g,e,OKG.eventDate,first[:10]);set_value(g,e,OKG.eventDatePrecision,'day')
                set_value(g,e,OKG.eventEligible,True)
            release=row.get('latestRelease')
            if not release or not release.get('statement') or not release.get('date'):continue
            e=event(g,owner,kind,key,'release',stamp,release['version'])
            snapshot=URIRef(BASE+'release-observations/'+digest(release))
            g.add((snapshot,RDF.type,OKG.ReleaseObservation))
            set_value(g,snapshot,OKG.releaseMetadata,json.dumps(release,sort_keys=True,ensure_ascii=False))
            g.add((e,OKG.releaseObservation,snapshot));g.set((e,OKG.currentReleaseObservation,snapshot))
            set_value(g,e,OKG.eventDate,release['date']);set_value(g,e,OKG.eventDatePrecision,release['datePrecision'])
            eligible=not release.get('selectionIssue') and not release.get('dateIssue') and date_ended(release['date'],today)
            set_value(g,e,OKG.eventEligible,eligible)
    write_graph(root/LEDGER,g)
    payload=project(g)
    dest=root/FEED;encoded=json.dumps(payload,indent=2,ensure_ascii=False)+'\n'
    if not dest.exists() or dest.read_text()!=encoded:
        temp=dest.with_suffix('.tmp');temp.write_text(encoded);temp.replace(dest)
    return payload

def project(g):
    entries=[]
    for e in g.subjects(RDF.type,OKG.CatalogEvent):
        owner=g.value(e,OKG.eventIdentity);kind=text(g,owner,OKG.eventKind)
        row={'id':str(e),'type':text(g,e,OKG.eventType),'kind':kind,'identity':str(owner),
             'wikidataId':text(g,owner,OKG.sourceEntity),'title':text(g,owner,OKG.title),
             'url':text(g,owner,OKG.catalogUrl),'date':text(g,e,OKG.eventDate),
             'datePrecision':text(g,e,OKG.eventDatePrecision),'discoveredAt':text(g,e,OKG.discoveredAt),
             'eligible':g.value(e,OKG.eventEligible)==Literal(True),
             'dateBasis':'release' if text(g,e,OKG.eventType)=='release' else text(g,owner,OKG.firstSeenBasis)}
        source=text(g,owner,OKG.historySource)
        if source and row['type']=='new-to-okg':row['historySource']=source
        current=g.value(e,OKG.currentReleaseObservation)
        if current:
            row['release']=json.loads(text(g,current,OKG.releaseMetadata))
            row['history']=[str(n) for n in sorted(g.objects(e,OKG.releaseObservation),key=str)]
        entries.append(row)
    entries.sort(key=lambda r:(r['date'],r['id']),reverse=True)
    return {'schemaVersion':1,'dateSemantics':'Catalog inclusion is not proof of deployment. Release dates are never discovery dates.','events':entries}

def validate(root):
    g=load(root);payload=json.loads((root/FEED).read_text())
    if payload!=project(g):raise ValueError('Event RDF/JSON mismatch')
    from jsonschema import Draft202012Validator, FormatChecker
    schema=json.loads((Path(__file__).resolve().parents[1]/"validation/catalog-events-v1/events.schema.json").read_text())
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(payload)
    seen=set()
    for e in payload['events']:
        if e['id'] in seen:raise ValueError('Duplicate event')
        seen.add(e['id'])
        if e['type'] not in ('new-to-okg','release'):raise ValueError('Unknown event type')
        if e['type']=='release' and (e['date']!=e['release']['date'] or not e['release']['statement']):raise ValueError('Release lacks paired evidence')
    return len(seen)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['backfill','sync','validate']);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--repository',type=Path);p.add_argument('--ref',default='HEAD');a=p.parse_args()
    if a.command=='backfill':backfill(a.repository or a.root,a.root,a.ref);synchronize(a.root)
    elif a.command=='sync':synchronize(a.root)
    else:print(f'Validated {validate(a.root)} events')
if __name__=='__main__':main()
