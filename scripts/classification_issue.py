#!/usr/bin/env python3
"""Idempotent GitHub inbox for the classification backlog (no comments)."""
from __future__ import annotations
import argparse
from collections import Counter
import html
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import quote
import requests
from rdflib import Graph, URIRef
import classification_review as review
import shared_tags as tags

MARKER='<!-- okg-classification-queue-v1 -->'


def published_state(repository, ref='catalog-current'):
    result={}
    for kind,stem in review.STEMS.items():
        p=subprocess.run(['git','show',f'{ref}:data/{stem}.ttl'],cwd=repository,capture_output=True,text=True)
        if p.returncode:continue
        g=Graph().parse(data=p.stdout,format='turtle')
        for owner,ass in g.subject_objects(tags.OKG.tagAssessment):
            result[str(owner)]={'inputHash':str(g.value(ass,tags.OKG.sourceContentHash)),
                'review':str(g.value(ass,tags.OKG.appliedReview) or ''),
                'status':str(g.value(ass,tags.OKG.assessmentStatus))}
    return result


def reconcile(backlog, published):
    outstanding=[]
    for row in backlog['records']:
        live=published.get(row['id'],{})
        if row['status']=='applied' and row['review'] and live.get('review')==row['review'] and live.get('inputHash')==row['inputHash'] and live.get('status') in ('complete','reviewed-empty'):continue
        outstanding.append({**row,'publication':'published' if live.get('inputHash')==row['inputHash'] else 'awaiting publication'})
    return outstanding


def safe_text(s):
    return html.escape(re.sub(r'[\r\n|`\[\]]',' ',str(s))).replace('@','＠')


def render(rows, repo, ref='main'):
    base=f'https://github.com/{repo}/blob/{quote(ref,safe="")}/'
    counts=Counter((r['kind'],r['reason']) for r in rows)
    lines=[MARKER,'New and changed records await classification review or publication. Publication state is shown per record; an applied review is not proof of a successful release.','',
           '| Kind | New | Changed | Missing |','| --- | ---: | ---: | ---: |']
    for k in review.STEMS:lines.append(f'| {k} | {counts[k,"new"]} | {counts[k,"changed"]} | {counts[k,"missing"]} |')
    lines+=['','Assign approved tools/resources, activities and domains; fill missing software types. Cite source evidence or explicitly record reviewed-no-applicable-tags. Keep ambiguity and proposed new terms unresolved.','',
            '| Record | Reason | State | Publication |','| --- | --- | --- | --- |']
    for r in rows[:25]:
        link=base+r['evidence']
        lines.append(f'| [{safe_text(r["title"])[:180]}]({link}) | {safe_text(r["reason"])} | {safe_text(r["status"])} | {r["publication"]} |')
    if len(rows)>25:lines.append(f'\nShowing 25 of {len(rows)} records; use the full backlog.')
    lines+=['',f'[Current backlog]({base}{review.BACKLOG}) · [Classification instructions]({base}docs/classification-review.md) · [Approved vocabularies]({base}data/tag-vocabularies.json) · [Software types]({base}vocabularies/software-types.ttl)',
            '', 'Load the current machine-readable backlog before working. This issue is a summary, not frozen review input. Each backlog entry links its exact evidence snapshot, applicable vocabulary context, source and existing RDF assignments/corrections.', '',
            '- [ ] Review pending records and identify unresolved cases.',
            '- [ ] Validate results against current evidence and vocabulary.',
            '- [ ] Apply, validate, and publish supported assignments through the normal release process.',
            '- [ ] Reconcile with the live-verified generation; close only when no review or accepted-result publication work remains.', '',
            'No paid classification APIs, automatic new terms or Wikidata edits. Keep private worker paths, prompts, credentials, logs and reasoning out of public results.']
    return f'Review pending OKG classifications — {len(rows)} records','\n'.join(lines)+'\n'


class GitHub:
    def __init__(self, repo, token):self.base='https://api.github.com/repos/'+repo;self.headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    def call(self, method, path, payload=None):
        for attempt in range(3):
            try:
                r=requests.request(method,self.base+path,headers=self.headers,json=payload,timeout=30)
                if r.status_code==429 or r.status_code>=500:
                    if method=='GET' and attempt<2:time.sleep(2**attempt);continue
                r.raise_for_status();return r.json()
            except requests.RequestException:
                # Mutations may already have succeeded. Reconcile on the next
                # serialized workflow run instead of blindly creating duplicates.
                if method!='GET' or attempt==2:raise
                time.sleep(2**attempt)
    def find(self):
        found=[]
        for page in range(1,101):
            rows=self.call('GET',f'/issues?state=all&per_page=100&page={page}')
            found.extend(r for r in rows if 'pull_request' not in r and MARKER in (r.get('body') or ''))
            if len(rows)<100:break
        else:raise ValueError('Issue inventory limit reached; refusing duplicate creation')
        if len(found)>1:raise ValueError('Multiple queue issues require explicit reconciliation')
        return found[0] if found else None


def sync(client, rows, repo, ref='main'):
    issue=client.find();title,body=render(rows,repo,ref)
    if issue is None:
        if not rows:return 'empty'
        client.call('POST','/issues',{'title':title,'body':body});return 'created'
    state='open' if rows else 'closed'
    payload={k:v for k,v in {'title':title,'body':body,'state':state}.items() if issue.get(k)!=v}
    if not payload:return 'unchanged'
    client.call('PATCH',f'/issues/{issue["number"]}',payload);return 'updated'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=tags.ROOT);p.add_argument('--repository',default=os.getenv('GITHUB_REPOSITORY'));p.add_argument('--ref',default='main');p.add_argument('--sync',action='store_true');a=p.parse_args()
    if not a.repository or not re.fullmatch(r'[\w.-]+/[\w.-]+',a.repository):p.error('A GitHub owner/repository is required')
    with review.lock(a.root):
        backlog=tags.read(a.root/review.BACKLOG)
        rows=reconcile(backlog,published_state(a.root));title,body=render(rows,a.repository,a.ref)
        if not a.sync:print(title+'\n\n'+body);return
        token=os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
        if not token:raise ValueError('GitHub token missing; retry issue synchronization later')
        try:print(sync(GitHub(a.repository,token),rows,a.repository,a.ref))
        except Exception:
            if os.getenv('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('\nClassification inbox synchronization failed. Data remains retained; rerun Classification Review Inbox.\n')
            raise
if __name__=='__main__':main()
