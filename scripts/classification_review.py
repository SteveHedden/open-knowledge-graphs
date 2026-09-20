#!/usr/bin/env python3
"""Versioned, network-free review contracts shared by Codex and optional adapters.

The RDF result log is authoritative. The JSON backlog is a reproducible index;
GitHub is a notification surface, never a source of assignments.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import tempfile
import os
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, DCTERMS
import shared_tags as tags

O = tags.OKG
VERSION = '1'
SCHEMA_ROOT = Path(__file__).resolve().parents[1]/'validation/classification-review-v1'
STEMS = {'resource':'ontologies','software':'software','jobs':'jobs/jobs'}
RESULTS = 'curation/classification-reviews.ttl'
BACKLOG = 'data/classification-backlog.json'
STATUS = ('pending', 'deferred', 'complete', 'reviewed-empty', 'excluded-not-match')


def atom_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.')
    try:
        with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False,indent=2,sort_keys=True);f.write('\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


@contextmanager
def lock(root):
    p=Path(root)/'build/classification-review.lock';p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        yield


def semantics(term):return tags.digest(tags.term_semantics(term))


def vocabulary(root, terms):
    terms=dict(terms)
    p=Path(root)/'vocabularies/software-types.ttl'
    if p.exists():
        g=Graph().parse(p)
        for s in g.subjects(RDF.type,tags.SKOS.Concept):
            terms[str(s)]={'id':str(s),'dimension':'softwareType','label':str(g.value(s,tags.SKOS.prefLabel)),
                'definition':str(g.value(s,tags.SKOS.definition) or ''),'boundary':str(g.value(s,tags.SKOS.scopeNote) or ''),
                'broader':sorted(map(str,g.objects(s,tags.SKOS.broader)))}
    return terms


def context(record, terms):
    # Scope to potentially relevant tools and all decision concepts. Additions
    # are compatible, but removal/meaning changes within this context are not.
    return {k:semantics(t) for k,t in sorted(terms.items())
            if t['dimension']!='tools' or k in record.get('candidates',[])}


def context_valid(previous, terms):
    return all(k in terms and semantics(terms[k])==v for k,v in previous.items())


def scalar(g,s,p,required=True):
    values=list(g.objects(s,p))
    if len(values)>1 or (required and len(values)!=1):raise ValueError(f'Expected one {p} on {s}')
    return str(values[0]) if values else ''


def parse_results(g):
    results=[]
    for s in sorted(g.subjects(RDF.type,O.ClassificationReview),key=str):
        r={k:scalar(g,s,O[p]) for k,p in [('version','reviewSchemaVersion'),('subject','tagSubject'),('kind','recordKind'),
            ('inputHash','sourceContentHash'),('outcome','reviewOutcome'),('reviewer','reviewedBy'),('method','classificationMethod'),
            ('reviewedAt','reviewedAt'),('scope','reviewScope'),('vocabularyContext','vocabularyContext'),('correctionsHash','correctionsHash')]}
        r['id']=str(s);r['scope']=json.loads(r['scope']);r['vocabularyContext']=json.loads(r['vocabularyContext'])
        r['findings']=sorted(map(str,g.objects(s,O.unresolvedFinding)))
        r['assignments']=[]
        for a in g.objects(s,O.tagAssignment):
            row={key:scalar(g,a,O[prop],required=key not in ('requirementStatus','requirementGroup')) for key,prop in [
                ('target','tagTarget'),('field','sourceField'),('quote','supportingText'),('relation','relationContext'),
                ('requirementStatus','requirementStatus'),('requirementGroup','requirementGroup')]}
            row['requirementStatus']=row['requirementStatus'] or 'unspecified';row['state']='reviewed'
            r['assignments'].append(row)
        r['assignments'].sort(key=lambda a:a['target'])
        r['digest']=tags.digest({k:v for k,v in r.items() if k!='id'})
        results.append(r)
    return results


def load_results(root):
    path=Path(root)/RESULTS
    return parse_results(Graph().parse(path)) if path.exists() else []


def corrections_hash(root, owner):
    rows=[dict(v,target=k[1]) for k,v in tags.load_overrides(Path(root)).items() if k[0]==owner]
    return tags.digest(sorted(rows,key=lambda v:v['target']))


def validate_result(r, record, terms, root):
    if r['version']!=VERSION or r['kind']!=record['kind']:raise ValueError('Unsupported result version or kind')
    if r['subject']!=record['subject'] or r['inputHash']!=tags.digest(record['fields']):raise ValueError('Stale input evidence')
    if r['correctionsHash']!=corrections_hash(root,r['subject']):raise ValueError('Human corrections changed')
    expected=set(tags.DIMS)|({'softwareType'} if r['kind']=='software' else set())
    if not isinstance(r['scope'],list) or set(r['scope'])!=expected:raise ValueError('Review must cover all applicable dimensions')
    if not isinstance(r['vocabularyContext'],dict) or not context_valid(r['vocabularyContext'],terms):raise ValueError('Stale vocabulary context')
    # The context supplied to the worker may omit newly added terms, never old
    # terms from the exact evidence snapshot being reviewed.
    snapshot=Path(root)/'data/classification-evidence'/record["kind"]/f"{tags.digest([record['subject'],r['inputHash'],r['vocabularyContext']])}.json"
    if not snapshot.exists():raise ValueError('Missing exact evidence snapshot; rebuild backlog first')
    saved=tags.read(snapshot)
    if saved['fields']!=record['fields'] or saved['subject']!=record['subject']:raise ValueError('Evidence snapshot mismatch')
    if not all(r['vocabularyContext'].get(k)==v for k,v in saved['vocabularyContext'].items()):raise ValueError('Incomplete review vocabulary context')
    if r['outcome'] not in ('accepted','reviewed-empty','deferred'):raise ValueError('Invalid review outcome')
    if not r['reviewer'].strip() or r['reviewer']=='REPLACE_WITH_REVIEWER' or not r['method'].strip():raise ValueError('Reviewer and method required')
    datetime.fromisoformat(r['reviewedAt'].replace('Z','+00:00'))
    if r['outcome']=='reviewed-empty' and (r['assignments'] or r['findings']):raise ValueError('Empty review cannot hide assignments or unresolved findings')
    if r['outcome']=='accepted' and not r['assignments']:raise ValueError('Use explicit reviewed-empty outcome')
    if r['outcome']=='deferred' and not r['findings']:raise ValueError('Deferred reviews require an unresolved finding')
    if r['findings'] and r['outcome']!='deferred':raise ValueError('Unresolved findings require deferred outcome')
    seen=set();overrides=tags.load_overrides(Path(root))
    for a in r['assignments']:
        target=a['target'];t=terms.get(target)
        if not t or target not in r['vocabularyContext']:raise ValueError('Unapproved or out-of-context target')
        if target in seen:raise ValueError('Duplicate target')
        seen.add(target)
        if record['subject']==target or record['subject'] in t.get('catalogIdentities',[]):raise ValueError('Self assignment')
        if overrides.get((record['subject'],target),{}).get('reviewState')=='rejected':raise ValueError('Assignment conflicts with human correction')
        if not a['quote'].strip() or a['quote'] not in record['fields'].get(a['field'],''):raise ValueError('Unsupported evidence quote')
        if a['requirementStatus'] not in ('required','preferred','contextual','unspecified'):raise ValueError('Invalid requirement status')
        if a['requirementGroup'] and a['requirementGroup'] not in record['fields'].get(a['field'],''):raise ValueError('Unsupported requirement group')
        if t['dimension']=='softwareType':
            if r['kind']!='software' or a['relation']!='software-type':raise ValueError('Invalid software type assignment')
        else:
            tags.validate_response([{**a,'state':'accepted'}],record,terms)
    if sum(terms[a['target']]['dimension']=='softwareType' for a in r['assignments'])>1:raise ValueError('Only one primary software type is supported')


def collect_prior(root, kind):
    """Prefer the pinned predecessor; never let older Git baselines win."""
    root=Path(root);stem=STEMS[kind];sources=[]
    p=root/f'data/{stem}.ttl';v=root/'data/tag-vocabularies.json'
    current=Graph().parse(p) if p.exists() else Graph()
    if not any(current.triples((None,O.tagAssessment,None))) and root.resolve()!=tags.ROOT.resolve():
        base=tags.ROOT;p=base/f'data/{stem}.ttl';v=base/'data/tag-vocabularies.json'
        if p.exists():sources.append((Graph().parse(p),tags.read(v)['terms'] if v.exists() else []))
    p=root/f'build/previous-data/{kind}.ttl';v=root/f'build/previous-data/{kind}-vocabulary.json'
    if p.exists():sources.append((Graph().parse(p),tags.read(v)['terms'] if v.exists() else []))
    # A current assessment (e.g. second publisher pass) supersedes predecessor.
    p=root/f'data/{stem}.ttl';v=root/'data/tag-vocabularies.json'
    if p.exists():sources.append((current,tags.read(v)['terms'] if v.exists() else []))
    prior={}
    for g,vs in sources:
        old={t['id']:t for t in vs}
        for owner,ass in g.subject_objects(O.tagAssessment):
            prior[str(owner)]=(g,ass,old)
    return prior


def node_row(g,n):
    return {'target':str(g.value(n,O.tagTarget)),'field':str(g.value(n,O.sourceField)),
        'quote':str(g.value(n,O.supportingText)), 'relation':str(g.value(n,O.relationContext)),
        'requirementStatus':str(g.value(n,O.requirementStatus) or 'unspecified'),
        'requirementGroup':str(g.value(n,O.requirementGroup) or ''),
        'method':str(g.value(n,O.classificationMethod) or ''),
        'state':'reviewed' if str(g.value(n,O.reviewState))=='reviewed' else 'accepted'}


def prepare_record(root, r, terms, prior, results, overrides, bindings=None):
    """Retain assignment-scoped evidence; missing/changed evidence is publishable."""
    bindings={} if bindings is None else bindings
    r['model']='none';r['method']='codex-review-v1';r['candidates']=r.get('candidates',[])
    r['key']=tags.digest([r['subject'],r['fields']]);r['assessment_status']='pending'
    r['review_reason']='new';r['overrides']={};rows=[];old_fields={};same=False;old_type='';old_type_hash='';old_type_field='';old_type_quote=''
    previous=prior.get(r['subject'])
    if previous:
        g,a,old_terms=previous
        if not old_terms:old_terms=terms
        same=str(g.value(a,O.sourceContentHash))==tags.digest(r['fields'])
        encoded=g.value(a,O.evidenceSnapshot)
        old_fields=json.loads(str(encoded)) if encoded else {}
        r['review_reason']='missing' if same else 'changed'
        invalid=False
        for n in g.objects(a,O.tagAssignment):
            row=node_row(g,n);target=row['target'];field=row['field']
            sem=str(g.value(n,O.termSemanticsHash) or '')
            compatible=target in terms and (sem==semantics(terms[target]) if sem else target in old_terms and tags.term_semantics(old_terms[target])==tags.term_semantics(terms[target]))
            relevant=same or (field in old_fields and old_fields[field]==r['fields'].get(field))
            if compatible and relevant:rows.append(row)
            else:invalid=True
        previous_context=g.value(a,O.vocabularyContext)
        if previous_context:
            relevant_targets={row['target'] for row in rows}|set(r['candidates'])
            scoped={k:v for k,v in json.loads(str(previous_context)).items() if k in relevant_targets}
            if not context_valid(scoped,terms):invalid=True
        status=str(g.value(a,O.assessmentStatus))
        if same and status in ('pending','deferred'):
            r['review_reason']=str(g.value(a,O.reviewReason) or 'missing')
        if same and not invalid and status in ('complete','reviewed-empty','insufficient-evidence'):
            r['assessment_status']='complete' if rows else 'reviewed-empty'
            r['provenance_method']=str(g.value(a,O.classificationMethod) or 'legacy-migration')
            r['method']=r['provenance_method'].split(':')[0]
            r['key']=str(g.value(a,O.cacheKey))
        elif invalid:r['review_reason']='changed'
        old_type=str(g.value(a,O.reviewedSoftwareType) or '')
        old_type_hash=str(g.value(a,O.softwareTypeSemanticsHash) or '')
        old_type_field=str(g.value(a,O.softwareTypeSourceField) or '')
        old_type_quote=str(g.value(a,O.softwareTypeSupportingText) or '')
        old_result=g.value(a,O.appliedReview)
        if old_result and r['assessment_status'] in ('complete','reviewed-empty'):r['applied_review']=str(old_result)
    for key,decision in overrides.items():
        if key[0]!=r['subject']:continue
        # Bind a correction to its original evidence, not the latest pending
        # assessment. Otherwise an invalidated decision revives on refresh two.
        field=decision.get('sourceField','review');target=key[1]
        ident=tags.digest([key,decision])
        if ident not in bindings:
            baseline=old_fields or (r['fields'] if same or previous is None else {})
            old_term=previous[2].get(target) if previous else terms.get(target)
            bindings[ident]={'owner':r['subject'],'target':target,'fields':baseline,
                             'semantics':semantics(old_term) if old_term else ''}
        baseline=bindings[ident]
        relevant=bool(baseline['fields']) and (baseline['fields']==r['fields'] if field=='review' else baseline['fields'].get(field)==r['fields'].get(field))
        compatible=target in terms and baseline['semantics']==semantics(terms[target])
        if relevant and compatible:r['overrides'][key]=decision
        else:r['assessment_status']='pending';r['review_reason']='changed'
    type_labels={t['label']:k for k,t in terms.items() if t['dimension']=='softwareType'}
    r['software_type']=None
    if r['kind']=='software':
        candidate=old_type or type_labels.get(r['raw'].get('softwareType'))
        # Bootstrap existing curated software types without re-tagging. Once an
        # evidence snapshot exists, its field hash and term meaning are checked.
        if candidate in terms and (same or not old_fields or (old_type_field in old_fields and old_fields[old_type_field]==r['fields'].get(old_type_field))) and (not old_type_hash or old_type_hash==semantics(terms[candidate])):
            r['software_type']=candidate
            if old_type_field:r['software_type_evidence']={'field':old_type_field,'quote':old_type_quote}
        elif candidate:r['assessment_status']='pending';r['review_reason']='changed'
        if not candidate and r['assessment_status']=='complete':r['assessment_status']='pending';r['review_reason']='missing'
    if r['kind']=='jobs' and (r['raw'].get('classification')=='not_match' or r['raw'].get('active') is False):
        r['assessment_status']='excluded-not-match' if r['raw'].get('classification')=='not_match' else 'excluded-inactive'
        r.pop('provenance_method',None)
        r['review_reason']='missing';r['method']='admission-exclusion-v1';r['key']=tags.digest([r['subject'],r['fields'],r['assessment_status']]);r['overrides']={};return []
    for review in sorted((x for x in results if x['subject']==r['subject']),key=lambda x:(x['reviewedAt'],x['id']),reverse=True):
        try:validate_result(review,r,terms,root)
        except (ValueError,KeyError,TypeError):continue
        # Unchanged protected corrections take precedence over routine review.
        rows=[a for a in review['assignments'] if terms[a['target']]['dimension']!='softwareType']
        type_assignment=next((a for a in review['assignments'] if terms[a['target']]['dimension']=='softwareType'),None)
        r['software_type']=type_assignment['target'] if type_assignment else None
        if type_assignment:r['software_type_evidence']=type_assignment
        r.pop('provenance_method',None)
        r['applied_review']=review['id'];r['key']=tags.digest([r['subject'],review['digest']])
        r['assessment_status']={'accepted':'complete','reviewed-empty':'reviewed-empty','deferred':'deferred'}[review['outcome']]
        r['findings']=review['findings'];r['method']=review['method'];r['reviewer']=review['reviewer']
        break
    rows.sort(key=lambda a:a['target'])
    r['vocabulary_context']={k:semantics(terms[k]) for k in ({a['target'] for a in rows}|set(r['candidates'])) if k in terms}
    r['key']=tags.digest([r['subject'],r['fields'],r['assessment_status'],rows,r.get('software_type'),r.get('applied_review'),r['vocabulary_context'],r['overrides'] if not r['overrides'] else sorted((list(k),v) for k,v in r['overrides'].items())])
    return rows


def annotate(g,r,terms):
    ass=g.value(URIRef(r['subject']),O.tagAssessment)
    g.set((ass,O.evidenceSnapshot,Literal(json.dumps(r['fields'],sort_keys=True))))
    g.set((ass,O.vocabularyContext,Literal(json.dumps(r.get('vocabulary_context',{}),sort_keys=True))))
    g.set((ass,O.reviewReason,Literal(r.get('review_reason','missing'))))
    if r.get('applied_review'):g.set((ass,O.appliedReview,URIRef(r['applied_review'])))
    if r.get('reviewer'):g.set((ass,O.reviewedBy,Literal(r['reviewer'])))
    for finding in r.get('findings',[]):g.add((ass,O.unresolvedFinding,Literal(finding)))
    if r.get('software_type'):
        g.set((ass,O.reviewedSoftwareType,URIRef(r['software_type'])))
        g.set((ass,O.softwareTypeSemanticsHash,Literal(semantics(terms[r['software_type']]))))
        if r.get('software_type_evidence'):
            g.set((ass,O.softwareTypeSourceField,Literal(r['software_type_evidence']['field'])))
            g.set((ass,O.softwareTypeSupportingText,Literal(r['software_type_evidence']['quote'])))
    for n in g.objects(ass,O.tagAssignment):
        t=str(g.value(n,O.tagTarget));g.set((n,O.termSemanticsHash,Literal(semantics(terms[t]))))


def archive(root,kind,graphs):
    p=Path(root)/f'data/classification-history/{kind}.ttl'
    history=Graph().parse(p) if p.exists() else Graph()
    for g,a,_ in graphs.values():
        for triple in g.triples((a,None,None)):history.add(triple)
        for n in g.objects(a,O.tagAssignment):
            for triple in g.triples((n,None,None)):history.add(triple)
    tags.write_rdf(p,history)


def correction_bindings(root,kind):
    p=Path(root)/f'data/classification-history/{kind}.ttl';out={}
    if not p.exists():return out
    g=Graph().parse(p)
    for s in g.subjects(RDF.type,O.CorrectionEvidence):
        out[str(g.value(s,O.decisionHash))]={'owner':str(g.value(s,O.tagSubject)),
            'target':str(g.value(s,O.tagTarget)),'fields':json.loads(str(g.value(s,O.evidenceSnapshot))),
            'semantics':str(g.value(s,O.termSemanticsHash))}
    return out


def save_bindings(root,kind,bindings):
    p=Path(root)/f'data/classification-history/{kind}.ttl';g=Graph().parse(p) if p.exists() else Graph()
    for key,row in bindings.items():
        s=URIRef(tags.BASE+'classification-correction-evidence/'+key)
        for pred,val in [(RDF.type,O.CorrectionEvidence),(O.decisionHash,Literal(key)),
                         (O.tagSubject,URIRef(row['owner'])),(O.tagTarget,URIRef(row['target'])),
                         (O.evidenceSnapshot,Literal(json.dumps(row['fields'],sort_keys=True))),
                         (O.termSemanticsHash,Literal(row['semantics']))]:g.add((s,pred,val))
    tags.write_rdf(p,g)


def build_backlog(root):
    root=Path(root);terms,_=tags.load_vocabulary(root);terms=vocabulary(root,terms)
    records,_=tags.gather(root,None);index=tags.entity_index(terms,tags.read(tags.ROOT/'jobs/catalog-mention-policy.json'))
    graphs={k:Graph().parse(root/f'data/{v}.ttl') for k,v in STEMS.items() if (root/f'data/{v}.ttl').exists()}
    entries=[];reviews=load_results(root)
    for r in records:
        if r['kind']=='jobs' and (r['raw'].get('classification')=='not_match' or r['raw'].get('active') is False):continue
        r['candidates']=tags.candidates(r['fields'],index,terms,r['subject'])
        g=graphs[r['kind']];ass=g.value(URIRef(r['subject']),O.tagAssessment)
        status=str(g.value(ass,O.assessmentStatus)) if ass else 'pending'
        review=str(g.value(ass,O.appliedReview) or '') if ass else ''
        # Include applied results until the issue reconciler proves publication.
        if status not in ('pending','deferred') and not review:continue
        h=tags.digest(r['fields']);sid=tags.digest([r['subject'],h,context(r,terms)]);path=f'data/classification-evidence/{r["kind"]}/{sid}.json'
        evidence={'schemaVersion':VERSION,'subject':r['subject'],'kind':r['kind'],'inputHash':h,
                  'fields':r['fields'],'source':r['source'],'vocabularyContext':context(r,terms)}
        if not (root/path).exists():atom_json(root/path,evidence)
        awaiting_review=None
        for candidate in sorted(reviews,key=lambda x:(x['reviewedAt'],x['id']),reverse=True):
            if candidate['subject']!=r['subject'] or candidate['id']==review:continue
            try:validate_result(candidate,r,terms,root)
            except (ValueError,KeyError,TypeError):continue
            awaiting_review=candidate;break
        entries.append({'id':r['subject'],'kind':r['kind'],'title':r['raw'].get('title',r['subject']),
            'source':r['source'],'reason':str(g.value(ass,O.reviewReason) or 'missing') if ass else 'missing',
            'inputHash':h,'evidence':path,'vocabularyContext':context(r,terms),
            'correctionsHash':corrections_hash(root,r['subject']),
            'reviewScope':list(tags.DIMS)+(['softwareType'] if r['kind']=='software' else []),
            'status':'reviewed' if awaiting_review else ('applied' if review and status not in ('pending','deferred') else status),
            'review':awaiting_review['id'] if awaiting_review else review,'unresolved':list(map(str,g.objects(ass,O.unresolvedFinding))) if ass else [],
            'assignmentsRdf':f'data/{STEMS[r["kind"]]}.ttl','correctionsRdf':'curation/tag-decisions.ttl'})
    payload={'schemaVersion':VERSION,'records':sorted(entries,key=lambda r:(r['kind'],r['id']))}
    import jsonschema
    jsonschema.validate(payload,tags.read(SCHEMA_ROOT/'backlog.schema.json'))
    atom_json(root/BACKLOG,payload)
    return payload


def import_results(root,path):
    root=Path(root)
    with lock(root):
        g=Graph().parse(path,format='turtle')
        from pyshacl import validate
        conforms,_,report=validate(g,shacl_graph=Graph().parse(SCHEMA_ROOT/'result.shacl.ttl'))
        if not conforms:raise ValueError('Review result schema violation: '+str(report))
        reviews=parse_results(g)
        if not reviews:raise ValueError('No review results')
        terms,_=tags.load_vocabulary(root);terms=vocabulary(root,terms)
        records,_=tags.gather(root,None);index=tags.entity_index(terms,tags.read(tags.ROOT/'jobs/catalog-mention-policy.json'))
        byid={r['subject']:r for r in records}
        for r in records:r['candidates']=tags.candidates(r['fields'],index,terms,r['subject'])
        for result in reviews:
            if result['subject'] not in byid:raise ValueError('Record no longer exists')
            validate_result(result,byid[result['subject']],terms,root)
        p=root/RESULTS;stored=Graph().parse(p) if p.exists() else Graph()
        for result in reviews:
            s=URIRef(result['id'])
            if (s,RDF.type,O.ClassificationReview) in stored:
                existing=next(x for x in parse_results(stored) if x['id']==result['id'])
                if existing['digest']!=result['digest']:raise ValueError('Immutable review ID reused')
        # Reject arbitrary triples: only result subjects and linked assignments
        # are publishable, with a constrained predicate set and no blank nodes.
        nodes=set(g.subjects(RDF.type,O.ClassificationReview))|set(g.objects(None,O.tagAssignment))
        allowed={RDF.type,*[O[x] for x in ('reviewSchemaVersion','tagSubject','recordKind','sourceContentHash','reviewOutcome','reviewedBy','classificationMethod','reviewedAt','reviewScope','vocabularyContext','correctionsHash','unresolvedFinding','tagAssignment','tagTarget','sourceField','supportingText','relationContext','requirementStatus','requirementGroup')]}
        for s,pred,o in g:
            if s not in nodes or not isinstance(s,URIRef) or pred not in allowed:raise ValueError('Unexpected result content')
            if isinstance(o,Literal) and any(x in str(o) for x in ('/Users/','/private/tmp/','Bearer ','sk-ant-')):raise ValueError('Private implementation content in result')
        for node in nodes:
            if any(stored.triples((node,None,None))) and set(stored.triples((node,None,None)))!=set(g.triples((node,None,None))):
                raise ValueError('Immutable result or assignment node reused')
        stored+=g;tags.write_rdf(root/RESULTS,stored)
    return len(reviews)


def template(root, ident, output):
    """Prepare a draft; workers must deliberately resolve it before import."""
    backlog=build_backlog(root)
    row=next((x for x in backlog['records'] if x['id']==ident),None)
    if row is None:raise ValueError('Record not in current review backlog')
    now=datetime.now(timezone.utc).isoformat()
    s=URIRef(tags.BASE+'classification-reviews/'+tags.digest([ident,row['inputHash'],now]))
    g=Graph();g.bind('okg',O);g.add((s,RDF.type,O.ClassificationReview))
    fields={'reviewSchemaVersion':VERSION,'tagSubject':URIRef(ident),'recordKind':row['kind'],
            'sourceContentHash':row['inputHash'],'reviewOutcome':'deferred','reviewedBy':'REPLACE_WITH_REVIEWER',
            'classificationMethod':'codex-direct-review','reviewedAt':now,
            'reviewScope':json.dumps(row['reviewScope']),'vocabularyContext':json.dumps(row['vocabularyContext'],sort_keys=True),
            'correctionsHash':row['correctionsHash'],'unresolvedFinding':'Draft: review has not been completed.'}
    for key,value in fields.items():g.add((s,O[key],value if isinstance(value,URIRef) else Literal(value)))
    output=Path(output)
    if output.exists():raise ValueError('Draft output already exists')
    output.write_text(g.serialize(format='turtle'))
    return str(s)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=tags.ROOT)
    sub=p.add_subparsers(dest='command',required=True);sub.add_parser('backlog')
    imp=sub.add_parser('import');imp.add_argument('results',type=Path)
    draft=sub.add_parser('template');draft.add_argument('--id',required=True);draft.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    if args.command=='backlog':print(json.dumps({'records':len(build_backlog(args.root)['records'])}))
    elif args.command=='template':print(template(args.root,args.id,args.output))
    else:print(json.dumps({'reviewed':import_results(args.root,args.results),'next':'Run shared_tags.py, validate, commit, and publish through the coordinated publisher.'}))
if __name__=='__main__':main()
