#!/usr/bin/env python3
"""Validate published tag targets, evidence, RDF/JSON parity and protected fields."""
import argparse
import json
from pathlib import Path
import subprocess
from rdflib import Graph,URIRef
from rdflib.namespace import RDF
from shared_tags import ROOT,OKG,DIMS,PREDICATES,load_vocabulary,fields,subject,public_projection

def validate(root=ROOT,baseline=None):
    root=Path(root);terms,_=load_vocabulary(root);checked=0;assignments=0
    for kind,stem in [('resource','ontologies'),('software','software'),('jobs','jobs/jobs')]:
        payload=json.loads((root/'data'/f'{stem}.json').read_text());rows=payload if isinstance(payload,list) else payload['items'];g=Graph().parse(root/'data'/f'{stem}.ttl')
        old={}
        if baseline:
            data=json.loads(subprocess.check_output(['git','show',f'{baseline}:data/{stem}.json'],cwd=root))
            old={(r.get('id') or r['canonicalUrl']):r for r in data if isinstance(data,list)} if isinstance(data,list) else {r['canonicalUrl']:r for r in data['items']}
        for r in rows:
            ident=subject(r,kind);s=URIRef(ident);assessments=list(g.objects(s,OKG.tagAssessment));assert len(assessments)==1,(ident,'assessment cardinality')
            p=public_projection(g,assessments[0],terms);assert r.get('sharedTags')==p,(ident,'RDF/JSON parity')
            assert r.get('categories')==[t['label'] for t in p['domains']]
            text=json.dumps(p);assert 'requirementStatus' not in text and 'requirementGroup' not in text,(ident,'internal metadata exposed')
            fs=fields(r,kind)
            if kind=='jobs':
                for node in g.objects(assessments[0],OKG.tagAssignment):
                    assert str(g.value(node,OKG.requirementStatus)) in ('required','preferred','contextual','unspecified')
                    group=g.value(node,OKG.requirementGroup)
                    if group:assert any(str(group) in value for value in fs.values()),(ident,'unsupported requirement group')
            for dim in DIMS:
                ids={t['id'] for t in p[dim]};assert ids==set(map(str,g.objects(s,PREDICATES[dim]))),(ident,dim,'direct triple parity')
                for tag in p[dim]:
                    assert terms[tag['id']]['dimension']==dim
                    assert tag['id']!=ident and ident not in terms[tag['id']].get('catalogIdentities',terms[tag['id']].get('catalogPages',[]))
                    evidence=tag['evidence'];assert evidence['reviewState'] in ('automated','reviewed')
                    if evidence['reviewState']=='automated':assert evidence['phrase'] in fs.get(evidence['field'],''),(ident,'unsupported evidence')
                    assignments+=1
            previous=old.get(r.get('id') or r['canonicalUrl'])
            if previous:
                protected=['id','canonicalUrl','wikidataId','title','description']
                if kind=='jobs':protected+=['classification','evidence','active','sourceOccurrences','canonicalFingerprint','firstSeenAt','lastSeenAt']
                for key in protected:assert previous.get(key)==r.get(key),(ident,'protected field changed',key)
            checked+=1
        if baseline:assert {r.get('id') or r['canonicalUrl'] for r in rows}==set(old),(kind,'membership changed')
    print(json.dumps({'result':'passed','records':checked,'acceptedAssignments':assignments,'checks':['RDF/JSON and direct triple parity','allowed targets','exact source excerpts','no internal metadata in public JSON','no self-use','original descriptions and job eligibility/membership preserved']},indent=2))
    return checked,assignments
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--baseline');a=p.parse_args();validate(a.root,a.baseline)
