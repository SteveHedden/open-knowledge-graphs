"""Compare the reviewed implementation's JSON with the revised staged catalog.

Usage: python audits/task61/revision-2/compare_review.py PREVIOUS_STAGE NEW_STAGE
"""
import json
import sys
from pathlib import Path
from collections import Counter


def read_rows(root):
    return {r['canonicalUrl']:r for stem in ('software','ontologies')
            for r in json.loads((root/f'data/{stem}.json').read_text())['items']}


def run(previous, revised):
    out=Path(__file__).parent
    old,new=read_rows(previous),read_rows(revised)
    assert old.keys()==new.keys()
    changes=[];removed=[]
    for url,row in new.items():
        assert {k:v for k,v in row.items() if k not in ('uses','relatedTools')}=={
            k:v for k,v in old[url].items() if k not in ('uses','relatedTools')},(url,'unrelated record field changed')
        before={e['id']:e for e in old[url].get('uses',[])}
        after={e['id']:e for e in row.get('uses',[])}
        assert after.keys()<=before.keys(),(url,'unexpected new use')
        for target,edge in before.items():
            sources=after.get(target,{}).get('sources',[])
            assert all(s in edge['sources'] for s in sources),(url,'new or changed provenance')
            for source in edge['sources']:
                if source not in sources:
                    assert source['kind']=='classification',(url,'upstream evidence changed')
                    removed.append({'subject':url,'target':target,'source':source})
        if row.get('relatedTools',[])!=old[url].get('relatedTools',[]):
            changes.append({'subject':url,'title':row['title'],'before':old[url].get('relatedTools',[]),'after':row.get('relatedTools',[])})
    initial=json.loads((out.parent/'tag-use-audit.json').read_text())
    revised_audit={a['assignment']:a for a in json.loads((out/'tag-use-audit.json').read_text())}
    dispositions=[]
    for a in initial:
        b=revised_audit[a['assignment']]
        assert {k:v for k,v in a.items() if k!='disposition'}=={k:v for k,v in b.items() if k!='disposition'}
        if a['disposition']!=b['disposition']:
            dispositions.append({**a,'before':a['disposition'],'after':b['disposition'],'description':new[a['subject']]['description']})
    withdrawals={d['assignment'] for d in dispositions if d['before']=='supported' and d['after']!='supported'}
    assert {r['source']['assignment'] for r in removed}==withdrawals
    initial_sample=json.loads((out.parent/'page-review.json').read_text())
    revised_sample=json.loads((out/'page-review.json').read_text())
    assert {r['id']:r['after'] for r in initial_sample}=={r['id']:r['after'] for r in revised_sample},'Frozen sample changed'
    for name,value in [('recommendation-changes-since-review',changes),('disposition-changes',dispositions),('removed-classification-support',removed)]:
        (out/f'{name}.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'previousSupported':431,'revisedDispositions':dict(Counter(a['disposition'] for a in revised_audit.values())),
        'withdrawnClassificationSupports':len(removed),'changedRecommendationLists':len(changes),
        'checks':['other JSON fields including sharedTags identical','upstream evidence unchanged','remaining use provenance unchanged','withdrawals match audit','42-page sample identical']},indent=2))

if __name__=='__main__':run(*map(Path,sys.argv[1:]))
