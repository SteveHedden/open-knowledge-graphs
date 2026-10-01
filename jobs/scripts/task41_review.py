#!/usr/bin/env python3
"""Refresh access evidence and build Task 41's nonpublishing approval packet.

Run the existing first_party_pilot first; this tool never activates sources.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import zipfile
from pathlib import Path

import requests

from first_party_sources import load_first_party_sources, load_production_first_party_sources, request_count_from_payload
from live_sources import load_production_source_registry
from source_schedule import production_source_weights, bounded_weight_batches

ROOT = Path(__file__).resolve().parents[2]
AUDITS = ROOT / 'jobs/audits'
KEYS = tuple('first-party-' + name for name in ('artsy', 'databricks', 'sage-publishing', 'triply'))


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def collect_access(runtime):
    """At most eight requests, no redirects/retries, 20s and 5MB per response."""
    rows = []
    for key in KEYS:
        source = load_first_party_sources()[key]
        for kind, url in [('robots', source.robots_url), ('terms', source.terms_url)]:
            row = dict(sourceKey=key, kind=kind, url=url, retrievedAt=now())
            try:
                with requests.get(url, timeout=20, stream=True, allow_redirects=False) as response:
                    row.update(status=response.status_code, location=response.headers.get('Location'))
                    body = bytearray()
                    for chunk in response.iter_content(65536):
                        body.extend(chunk)
                        if len(body) > 5_000_000:
                            raise ValueError('access evidence exceeds 5MB cap')
                    target = runtime / 'access' / f'{key}-{kind}.txt'
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(body)
                    row.update(sha256=digest(target), bytes=len(body), file=str(target.relative_to(ROOT)))
            except (requests.RequestException, ValueError) as exc:
                row['error'] = str(exc)
            rows.append(row)
    write(runtime / 'access-evidence.json', rows)
    return rows


def verify_baseline(baseline):
    current = {**load_production_source_registry(ROOT / 'sources.ttl'), **load_production_first_party_sources()}
    contracts = json.loads(json.dumps({k: asdict(v) for k, v in sorted(current.items())}, default=str))
    if contracts != baseline['sources'] or production_source_weights() != baseline['weights']:
        raise ValueError('approved production contracts changed since baseline capture')
    expected_snapshot = {name for name in baseline['protectedFiles'] if name.startswith('data/jobs/')}
    actual_snapshot = {str(p.relative_to(ROOT)) for p in (ROOT / 'data/jobs').rglob('*') if p.is_file()}
    if actual_snapshot != expected_snapshot:
        raise ValueError('protected snapshot file set changed')
    for name, expected in baseline['protectedFiles'].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f'protected file changed: {name}')
    if set(KEYS) & set(current):
        raise ValueError('candidate activated before review')
    return sorted(current)


def verify_approved_baseline(baseline):
    """Permit only the explicitly approved additions; retain prior contracts."""
    approval = json.loads((AUDITS / 'task41-production-approval.json').read_text())
    additions = set(approval['approvedSourceKeys'])
    current = {**load_production_source_registry(ROOT / 'sources.ttl'), **load_production_first_party_sources()}
    contracts = json.loads(json.dumps({k: asdict(v) for k, v in sorted(current.items())}, default=str))
    if set(current) != set(baseline['sources']) | additions:
        raise ValueError('approved source set changed beyond the recorded additions')
    if any(contracts[k] != v for k, v in baseline['sources'].items()):
        raise ValueError('existing approved production contract changed')
    return sorted(current)


def build(runtime, baseline_path=None):
    baseline_path = baseline_path or AUDITS / 'task41-production-baseline.json'
    baseline = json.loads(baseline_path.read_text())
    approved = verify_baseline(baseline)
    audit = json.loads((AUDITS / 'task41-commercial-source-audit.json').read_text())
    run = json.loads((runtime / 'run.json').read_text())
    if run['mode'] != 'live-local-review' or run['publicationPerformed']:
        raise ValueError('expected nonpublishing live review')
    results = {r['sourceKey']: r for r in run['sourceResults']}
    if set(results) != set(KEYS):
        raise ValueError('live review must include exactly the four candidates')
    evidence = json.loads((runtime / 'access-evidence.json').read_text())
    recommendations = json.loads((AUDITS / 'task41-activation-recommendations.json').read_text())['sources']
    sources = load_first_party_sources()
    for row in audit['organizations']:
        key = 'first-party-' + row['id']
        row['historicalAsOf'] = audit['asOf']
        if key not in KEYS:
            row['proposedProductionAction'] = 'remain-registry-only'
            continue
        result = results[key]
        for stale in ('productionBlockers', 'productionReadiness', 'robotsEvidence'):
            row.pop(stale, None)
        row['activationRecommendation'] = recommendations[key]
        row['productionBlockers'] = recommendations[key]['blockers']
        row['productionReadiness'] = 'awaiting-explicit-review-decision'
        # Failed retrieval is unknown, never a legitimate zero-opening result.
        success = result['status'] == 'refreshed'
        row['freshReview'] = {
            'retrievedAt': run['retrievedAt'], 'outcome': result,
            'contract': asdict(sources[key]),
            'accessEvidence': [r for r in evidence if r['sourceKey'] == key],
        }
        for field, result_field in [('currentOpenings', 'records'), ('qualified', 'qualified'), ('review', 'review'), ('notMatch', 'notMatch')]:
            row[field] = result.get(result_field, 0) if success else None
        row['decisionRecords'] = []
        if success:
            records = json.loads((runtime / 'sources' / f'{key}.json').read_text())
            row['decisionRecords'] = [{k: r.get(k) for k in ('sourceRecordId', 'title', 'canonicalUrl', 'classification', 'evidence', 'qualificationAudit')} for r in records if r['classification'] != 'not_match']
            raw = runtime / 'raw' / f'{key}.json'
            row['freshReview']['rawSha256'] = digest(raw)
            requests_used = request_count_from_payload(json.loads(raw.read_text()), sources[key])
            if requests_used > sources[key].max_requests_per_run:
                raise ValueError(f'{key} exceeded its source request limit')
            row['freshReview']['requestCount'] = requests_used
        row['proposedProductionAction'] = 'manager-review' if success else 'remain-registry-only'
    weights = {**baseline['weights'], **{k: sources[k].max_requests_per_batch for k in KEYS}}
    batches = bounded_weight_batches(weights)
    audit.update(asOf=run['retrievedAt'], status='refreshed-awaiting-explicit-source-decisions',
                 productionCandidates=[k for k in KEYS if recommendations[k]['action'] == 'propose-enable' and results[k]['status'] == 'refreshed'], reviewOnlySources=list(KEYS),
                 productionBaseline={'sourceCount': len(approved), 'sources': approved, 'unchanged': True, 'baselineFile': baseline_path.name, 'repositoryCommit': baseline.get('repositoryCommit')},
                 policyAssessment='task41-policy-assessment.json',
                 scheduler={'maxParallelSources': 4, 'declaredBatchRequestCap': 128, 'hypotheticalBatches': batches,
                            'batchWeights': [sum(weights[k] for k in b) for b in batches]},
                 historicalAudit='task41-commercial-source-audit.json')
    # Preserve compact replay evidence, including failed access responses, without
    # copying any review output into the public snapshot.
    files = [runtime / 'run.json', runtime / 'access-evidence.json']
    files += sorted((runtime / 'access').glob('*.txt'))
    files += [runtime / 'raw' / f'{k}.json' for k in KEYS if results[k]['status'] == 'refreshed']
    manifest = []
    archive = AUDITS / 'task41-review-evidence.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            name = str(path.relative_to(runtime))
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(entry, path.read_bytes())
            manifest.append(dict(path=name, sha256=digest(path), bytes=path.stat().st_size))
    audit['replayEvidence'] = dict(archive=archive.name, sha256=digest(archive), files=manifest)
    write(AUDITS / 'task41-refreshed-review.json', audit)
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-dir', type=Path, default=ROOT / 'jobs/runtime/task41-review')
    parser.add_argument('--fetch-access', action='store_true')
    parser.add_argument('--baseline', type=Path, help='captured production baseline for this checkout')
    args = parser.parse_args()
    runtime = args.runtime_dir.resolve()
    if args.fetch_access:
        collect_access(runtime)
    result = build(runtime, args.baseline)
    print(f"Reviewed {len(result['organizations'])} organizations; production unchanged")
