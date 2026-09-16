#!/usr/bin/env python3
"""Summarize the full local backfill without publishing historical JDs or suggestions."""
import json
from collections import Counter,defaultdict
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import shared_tags as tags

def main():
    audit=tags.read(ROOT/'build/tagging-audit.json');summary=tags.read(ROOT/'build/tagging-summary.json')
    vocab=tags.read(ROOT/'data/tag-vocabularies.json');terms={t['id']:t for t in vocab['terms']}
    current={}
    for kind,stem in [('resource','ontologies'),('software','software'),('jobs','jobs/jobs')]:
        payload=tags.read(ROOT/'data'/f'{stem}.json');current[kind]=payload if isinstance(payload,list) else payload['items']
    lines=['# Task 49 backfill audit','',f"Processed **{len(audit):,} source records/versions**, including **{summary['historicalRecords']:,} historical-only versions**. Historical descriptions and unpublished suggestions remain local.",'','## Coverage of current published records','','| Record type | Records | Tools/resources | Activities/use cases | Domains | Limited text |','|---|---:|---:|---:|---:|---:|']
    for kind,rows in current.items():
        counts=[len(rows),*[sum(bool(r['sharedTags'][d]) for r in rows) for d in tags.DIMS],sum(r['sharedTags']['assessment']['limitedText'] for r in rows)]
        lines.append('| '+kind+' | '+' | '.join(f'{n:,}' for n in counts)+' |')
    lines+=['','## Changes from previous descriptive tags','','Legacy resource categories, page-backed job catalog mentions and supplementary job tags are mapped to the shared identities for this comparison. Qualification evidence, roles and source-provided job categories remain separate. Counts below are assignment changes across current records, not distinct entities.','','| Dimension | Added | Retained | Removed | Records still unassigned |','|---|---:|---:|---:|---:|']
    for dim in tags.DIMS:
        rows=[r for r in audit if r['public']]
        counts=[sum(len(r[change][dim]) for r in rows) for change in ['new','retained','removed']]+[sum(dim in r['unassigned'] for r in rows)]
        lines.append('| '+dim+' | '+' | '.join(f'{n:,}' for n in counts)+' |')
    jobs=[r for r in current['jobs'] if r.get('active') is not False and r.get('classification') in ('qualified','review')]
    jobs=list({r.get('canonicalFingerprint') or r.get('canonicalUrl') or r['id']:r for r in jobs}.values())
    employers={str(r.get('organizationIri') or r.get('hiringOrganization','')).strip().casefold() for r in jobs};employers.discard('')
    historical_subjects={r['subject'] for r in audit if r['kind']=='jobs'}
    lines+=['','## Job evidence and duplicate limits','',f"The retained corpus contains **{len(historical_subjects):,} distinct job identities** across snapshots. Current observed demand is **{len(jobs):,} active eligible posting fingerprints** across **{len(employers):,} employer identities/normalized labels**. Known duplicate fingerprints are collapsed. Unresolved syndication and employer aliases can remain; these are not estimates of all market vacancies.",'',f"**{summary['unpublishedSuggestions']:,} candidate assignments/diagnostics** remain unpublished. Missing tags indicate insufficient accepted evidence. Truncated source descriptions are preserved and flagged.",'','## Representative accepted evidence','']
    for kind,rows in current.items():
        lines+=['### '+kind,'']
        shown=set()
        for dim in tags.DIMS:
            candidates=sorted((r for r in rows if r['sharedTags'][dim]),key=lambda r:(-len(r['sharedTags'][dim]),r.get('title','')))
            for r in candidates[:2]:
                for t in r['sharedTags'][dim][:2]:
                    key=(r.get('id') or r['canonicalUrl'],t['id'])
                    if key in shown:continue
                    shown.add(key);e=t['evidence'];phrase=e['phrase'].replace('\n',' ')
                    lines.append(f"- **{r['title']} → {t['label']}** ({e['reviewState']}, {e['field']}): “{phrase}”")
        lines.append('')
    pair_counts=Counter()
    for r in jobs:
        for tool in r['sharedTags']['tools']:
            for domain in r['sharedTags']['domains']:pair_counts[(tool['label'],domain['label'])]+=1
    lines+=['## Cross-dimension observations','','Tools and domains explicitly assigned to the same active posting (counts overlap):','']
    for (tool,domain),count in pair_counts.most_common(10):lines.append(f'- {tool} + {domain}: {count} postings.')
    if not pair_counts:lines.append('No accepted tool/domain intersections in the current source evidence.')
    lines+=['','## Interpretation','','The comparison measures catalog coverage against observed hiring demand. A catalog tool counts as its own available catalog entity without a self-use assertion. Resource/software overlap is deduplicated in the combined count. Parent filters include descendants; counts across tags overlap and must not be summed.','', 'The six-record GPT-5.4 pilot corrected Java omissions and unsupported job-domain inferences after prompt refinement. A subsequent spot audit found title-only activity inferences in earlier Anthropic output; those are retained as unpublished suggestions. These checks do not establish a corpus-wide accuracy score.','']
    (ROOT/'docs/task49/BACKFILL-AUDIT.md').write_text('\n'.join(lines))
    print('Wrote docs/task49/BACKFILL-AUDIT.md')
if __name__=='__main__':main()
