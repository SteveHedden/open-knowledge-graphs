#!/usr/bin/env python3
import sys,time,json,shutil,os,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import catalog_snapshot as cat
import dataset_snapshots as ds
import shared_tags as tags
from rdflib import Graph,URIRef,Literal
import argparse
parser=argparse.ArgumentParser(description='Network-free dataset-only publication rehearsal against stored production data')
parser.add_argument('--workdir',type=Path,required=True,help='New scratch directory outside the repository')
args=parser.parse_args()
base=args.workdir.resolve();base.mkdir(exist_ok=False)
report=[{'sourceCommit':ds.git(ROOT,'rev-parse','HEAD'),'releaseCodeDigest':ds.code_digest(ROOT)}]
def phase(label,fn):
 start=time.monotonic();value=fn();report.append({'phase':label,'seconds':round(time.monotonic()-start,3)});print(report[-1],flush=True);return value
baseline=base/'baseline';cat.prepare_staging(ROOT,baseline)
vocabulary=tags.read(baseline/'data/tag-vocabularies.json');ds.reproject(baseline,{k:vocabulary for k in ds.KINDS})
pinned=base/'pinned';pinned.mkdir()
selection={}
for kind in ds.KINDS:
 manifest=phase('seal-'+kind,lambda:ds.bundle(baseline,kind,pinned/kind,'rehearsal'))
 selection[kind]={'commit':'offline-'+kind,'snapshotId':manifest['snapshotId'],'createdAt':manifest['createdAt'],'sourceRetrievedAt':manifest['sourceRetrievedAt']}
tags.write_json(pinned/'selection.json',selection)
with patch('requests.sessions.Session.request',side_effect=AssertionError('Publication requested a source/API')):
 phase('initial-assembly',lambda:ds.assemble(ROOT,baseline,pinned))
 # Generate pages offline against existing verified membership; no new source input.
 phase('pages',lambda:subprocess.run([sys.executable,str(ROOT/'scripts/generate_pages.py'),'--membership-baseline',str(ROOT),'--refresh-shared-projections','--skip-link-check'],env={**os.environ,'OKG_CATALOG_ROOT':str(baseline)},check=True))
 phase('shared-validation',lambda:subprocess.run([sys.executable,str(ROOT/'scripts/validate_shared_tags.py'),'--root',str(baseline)],check=True))
 phase('catalog-validation',lambda:subprocess.run([sys.executable,str(ROOT/'scripts/validate_catalog.py'),'--root',str(baseline),'--repository-root',str(ROOT),'--baseline-ref','HEAD'],check=True))
 ds.record_inputs(ROOT,baseline)
 now=cat.utc_now();cat.write_jobs_manifest(baseline,now,'2026-09-19T00:00:00Z');cat.write_manifest(baseline,now,'2026-09-19T00:00:00Z');cat.verify_all_manifests(baseline)
 for kind in ds.KINDS:
  candidate=base/kind;shutil.copytree(baseline,candidate)
  changed=base/(kind+'-changed');shutil.copytree(baseline,changed)
  stem=ds.STEMS[kind];payload=tags.read(changed/f'data/{stem}.json');row=(payload if kind=='jobs' else payload['items'])[0]
  g=Graph().parse(changed/f'data/{stem}.ttl');owner=URIRef(tags.subject(row,kind))
  if kind=='resource':row['aliases']=sorted(set(row.get('aliases',[])+['Task 50 offline rehearsal']));g.add((owner,tags.OKG.alias,Literal('Task 50 offline rehearsal')))
  elif kind=='software':row['latestVersion']='task50-rehearsal';g.set((owner,tags.OKG.latestVersion,Literal(row['latestVersion'])))
  else:row['active']=False;g.set((owner,URIRef('https://openknowledgegraphs.com/jobs/ontology#active'),Literal(False)))
  tags.write_json(changed/f'data/{stem}.json',payload);tags.write_rdf(changed/f'data/{stem}.ttl',g)
  inputs=base/(kind+'-inputs');shutil.copytree(pinned,inputs);shutil.rmtree(inputs/kind)
  manifest=ds.bundle(changed,kind,inputs/kind,'rehearsal');selected={**selection,kind:{'commit':'offline-change-'+kind,'snapshotId':manifest['snapshotId'],'createdAt':manifest['createdAt'],'sourceRetrievedAt':manifest['sourceRetrievedAt']}};tags.write_json(inputs/'selection.json',selected)
  phase(kind+'-only-assembly',lambda:ds.assemble(ROOT,candidate,inputs))
  phase(kind+'-pages',lambda:subprocess.run([sys.executable,str(ROOT/'scripts/generate_pages.py'),'--membership-baseline',str(baseline),'--refresh-shared-projections','--skip-link-check'],env={**os.environ,'OKG_CATALOG_ROOT':str(candidate)},check=True))
  ds.record_inputs(ROOT,candidate)
  cat.write_jobs_manifest(candidate,now,'2026-09-19T00:00:00Z');cat.write_manifest(candidate,now,'2026-09-19T00:00:00Z');cat.verify_all_manifests(candidate)
  changes=phase(kind+'-change-detection',lambda:cat.substantive_changes(candidate,baseline));assert changes,kind
  again=base/(kind+'-repeat');shutil.copytree(candidate,again)
  phase(kind+'-repeat-assembly',lambda:ds.assemble(ROOT,again,inputs))
  # Final projection after page membership is unchanged; this mirrors publication.
  vocab=tags.read(again/'data/tag-vocabularies.json');ds.reproject(again,{k:vocab for k in ds.KINDS})
  ds.record_inputs(ROOT,again)
  assert ds.code_digest(ROOT)==report[0]['releaseCodeDigest'], 'Release code changed during rehearsal; rerun with fixed code'
  repeat_changes=phase(kind+'-dedup',lambda:cat.substantive_changes(again,candidate));assert not repeat_changes,(kind,repeat_changes)
  report.append({'scenario':kind,'changedFiles':changes,'repeatChanges':repeat_changes,'wikidataRequests':0,'classificationRequests':0})
 tags.write_json(ROOT/'audits/task50/local-rehearsal.json',report)
print('REHEARSAL PASSED',flush=True)
