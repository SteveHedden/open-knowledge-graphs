#!/usr/bin/env python3
"""Offline migration from pinned Git history; no acquisition or classification calls.
Run in the release checkout; outputs require normal shared-tag/manifest validation.
"""
import json
import subprocess
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'jobs/scripts'))
from job_identity import empty_history, reconcile_recurring
from live_pipeline import _prepare_for_reconciliation, _organization_alias_index
from live_records import build_graph, validate_graph
from rdf_utils import write_deterministic_turtle


def migrate():
    path=ROOT/'data/jobs/jobs.json';current=json.loads(path.read_text())
    previous_data=ROOT/'build/previous-data';previous_data.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'data/jobs/jobs.ttl',previous_data/'jobs.ttl')
    shutil.copy2(ROOT/'data/tag-vocabularies.json',previous_data/'jobs-vocabulary.json')
    aliases=_organization_alias_index(ROOT/'data/organizations.json')
    history=empty_history()
    reconcile_recurring(_prepare_for_reconciliation(current,aliases),history)
    # Earliest available captured dates, not source posting dates, are evidence.
    commits=subprocess.check_output(['git','log','--format=%H','HEAD','--','data/jobs/jobs.json'],cwd=ROOT,text=True).splitlines()
    historical={}
    for commit in commits:
        result=subprocess.run(['git','show',commit+':data/jobs/jobs.json'],cwd=ROOT,capture_output=True,text=True)
        if result.returncode:continue
        for row in json.loads(result.stdout):
            ident=row['id'];prior=historical.get(ident)
            if not prior or (row.get('firstSeenAt') and row['firstSeenAt']<(prior.get('firstSeenAt') or '~')):
                historical[ident]=row
    reconcile_recurring(_prepare_for_reconciliation(list(historical.values()),aliases),history)
    out,audit=reconcile_recurring(_prepare_for_reconciliation(current,aliases),history)
    # Backfill is not a new discovery event; preserve the original ingestion clock.
    run=json.loads((ROOT/'data/jobs/run.json').read_text())
    run.setdefault('reconciliation',{})['recurringIdentity']=audit
    run['deduplicatedCount']=len(out);run['activeCount']=sum(bool(r.get('active')) for r in out)
    run['classificationCounts']={k:sum(r.get('classification')==k for r in out) for k in ('qualified','review','not_match')}
    graph=build_graph(out,run,SimpleNamespace(dataset_uri=run['sourceDataset']))
    validate_graph(graph,ROOT/'jobs')
    write_deterministic_turtle(graph,ROOT/'data/jobs/jobs.ttl')
    for destination,value in [(path,out),(ROOT/'data/jobs/run.json',run),(ROOT/'data/jobs/identity-history.json',history)]:
        destination.write_text(json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
    visible=lambda rs:[r for r in rs if r.get('active') is not False and (not r.get('validThrough') or r['validThrough'][:10]>='2026-09-21') and r.get('classification') in ('qualified','review')]
    report={'historyCommits':commits,'historyRecordIdentities':len(historical),'beforeRecords':len(current),'afterRecords':len(out),'beforeVisible':len(visible(current)),'afterVisible':len(visible(out)),'audit':audit,'discoveryBackfills':[{'id':r['id'],'before':next((x.get('firstSeenAt') for x in current if x['id']==r['id']),None),'after':r.get('firstSeenAt')} for r in out if any(x['id']==r['id'] and x.get('firstSeenAt')!=r.get('firstSeenAt') for x in current)]}
    (ROOT/'audits/task55/corpus-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('historyCommits','audit','discoveryBackfills')}))
    print('Backfilled discovery dates:',len(report['discoveryBackfills']))

if __name__=='__main__':migrate()
