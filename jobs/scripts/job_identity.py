"""Conservative recurring identity and discovery ledger, independent of tagging.

The ledger retains identities, dates and source links, never absent public jobs.
Only reviewed employer/requisition identities with matching locations may merge.
"""
from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from pathlib import Path

from reconcile import (location_signature, merge_source_occurrences, _occurrences as source_occurrences,
                       _timestamp, normalize_title)

POLICY = Path(__file__).resolve().parents[1] / 'curation/job-identity-policy.json'


@lru_cache(maxsize=1)
def policy():
    return json.loads(POLICY.read_text())["employers"]

def strong_identity(record):
    organization = record.get('organizationIri')
    requisition = str(record.get('requisitionId') or '').strip().casefold()
    conflict = None
    for rule in policy():
        if normalize_title(record.get('hiringOrganization')) not in rule['names']:
            continue
        if organization and organization != rule['identity']:
            return None, None, 'conflicting reviewed employer identity'
        matches = sorted(set(re.findall(rule['requisitionPattern'], record.get('description', ''), re.I)))
        matches = [value.casefold() for value in matches]
        if len(matches) > 1 or (matches and requisition and requisition != matches[0]):
            return None, None, 'conflicting employer requisition evidence'
        if matches:
            organization = rule['identity']
            requisition = matches[0]
    if not organization or not requisition:
        return None, None, conflict
    base = json.dumps([organization, requisition], separators=(',', ':'))
    location = location_signature(record)
    if not location:
        return None, base, 'missing structured location evidence'
    return json.dumps([organization, requisition, location], separators=(',', ':')), base, None


def empty_history():
    return {'schemaVersion': 1, 'records': {}}


def load_history(path):
    if not Path(path).exists():
        return empty_history()
    value = json.loads(Path(path).read_text())
    if value.get('schemaVersion') != 1 or not isinstance(value.get('records'), dict):
        raise ValueError('Invalid job identity history')
    return value


def _occurrences(record):
    # Task 40's source-IRI migration also applies to restored historical links.
    rows=source_occurrences(record)
    for row in rows:
        value=str(row.get('sourceDataset') or '')
        prefix='https://openknowledgegraphs.com/prototypes/kg-jobs/source/'
        if value.startswith(prefix):
            row['sourceDataset']='https://openknowledgegraphs.com/jobs/source/'+value[len(prefix):]
    return rows


def occurrence_keys(record):
    return {(o.get('sourceDataset'), o.get('sourceRecordId')) for o in _occurrences(record)
            if o.get('sourceDataset') and o.get('sourceRecordId')}


def reconcile_recurring(records, history):
    """Return current rows and diagnostics; update the persistent ledger in place."""
    old = copy.deepcopy(history['records'])
    by_key, by_occurrence = {}, {}
    for ident, entry in old.items():
        if entry.get("identityKey"): by_key.setdefault(entry["identityKey"], set()).add(ident)
        for occurrence in occurrence_keys(entry): by_occurrence.setdefault(occurrence, set()).add(ident)
    groups, bases, unresolved = {}, {}, []
    for record in sorted(records, key=lambda r: r['id']):
        row = copy.deepcopy(record)
        key, base, reason = strong_identity(row)
        if reason:
            unresolved.append({'ids': [row['id']], 'reason': reason})
        row['_identity'] = key
        groups.setdefault(key or 'source:'+row['id'], []).append(row)
        if base:
            bases.setdefault(base, []).append((row['id'], key))
    for base, candidates in bases.items():
        if len({key for _, key in candidates}) > 1:
            unresolved.append({'ids': sorted(i for i, _ in candidates),
                               'reason': 'same employer/requisition has different or missing location/workplace evidence'})
    similar = {}
    for record in records:
        candidate = (record.get('organizationIri') or normalize_title(record.get('hiringOrganization')),
                     normalize_title(record.get('title')), location_signature(record))
        similar.setdefault(candidate, []).append(record)
    for candidates in similar.values():
        if len(candidates)>1 and len({strong_identity(r)[0] or r['id'] for r in candidates})>1:
            unresolved.append({'ids': sorted(r['id'] for r in candidates),
                               'reason': 'similar title/location but distinct or unproven employer requisitions; retained separately'})
    output, merges, discoveries, changes = [], [], [], []
    used = set()
    for _, group in sorted(groups.items()):
        # Explicit employment/expiration contradictions veto a group merge.
        conflicts = [field for field in ('employmentType', 'validThrough')
                     if len({str(r[field]).casefold() for r in group if r.get(field)}) > 1]
        batches = [[r] for r in group] if conflicts else [group]
        if conflicts:
            unresolved.append({'ids': sorted(r['id'] for r in group), 'reason': 'conflicting '+', '.join(conflicts)})
        for batch in batches:
            identities = set().union(*(occurrence_keys(r) for r in batch))
            key = batch[0]['_identity']
            prior_ids = {r['id'] for r in batch if r['id'] in old}
            for occurrence in identities: prior_ids.update(by_occurrence.get(occurrence, set()))
            if key and not conflicts: prior_ids.update(by_key.get(key, set()))
            prior = [(ident, old[ident]) for ident in prior_ids if ident not in used
                     and (not key or not old[ident].get('identityKey') or key == old[ident]['identityKey'])]
            prior.sort(key=lambda pair: (pair[1].get('firstSeenAt') or '~', pair[0]))
            batch.sort(key=lambda r: (not bool(r.get('firstParty')), r.get('firstSeenAt') or '~', r['id']))
            canonical = next((ident for ident, _ in prior if ident not in used), batch[0]['id'])
            winner = next((r for r in batch if r['id'] == canonical), batch[0])
            row = copy.deepcopy(winner); row.pop('_identity', None); row['id'] = canonical
            used.add(canonical)
            occurrences = merge_source_occurrences(*[_occurrences(r) for r in batch],
                                                     *[_occurrences(e) for _, e in prior])
            row['sourceOccurrences'] = occurrences
            row['firstSeenAt'] = _timestamp([r.get('firstSeenAt') for r in batch]+[e.get('firstSeenAt') for _,e in prior], latest=False)
            # Never extend expiry using another occurrence with a missing date.
            expirations = [r['validThrough'] for r in batch if r.get('validThrough')]
            if not expirations: expirations = [e['validThrough'] for _, e in prior if e.get('validThrough')]
            if expirations: row['validThrough'] = min(expirations)
            if len(batch) > 1 or row['id'] != winner['id']:
                row['reconciliationMethod'] = sorted(set(row.get('reconciliationMethod', [])) | {'reviewed-employer-requisition-location'})
                row['reconciliationReason'] = 'stable employer requisition with matching location and retained occurrences'
                merges.append({'canonicalId': canonical, 'sourceIds': sorted(r['id'] for r in batch)})
            if not prior: discoveries.append(canonical)
            for ident, entry in prior:
                if entry.get('datePosted') != row.get('datePosted'):
                    changes.append({'id': canonical, 'previous': entry.get('datePosted'), 'current': row.get('datePosted')})
                if ident != canonical: history['records'].pop(ident, None)
            history['records'][canonical] = {k: row[k] for k in ('id','firstSeenAt','datePosted','sourceUpdatedDate','validThrough','sourceOccurrences') if k in row}
            history['records'][canonical]['identityKey'] = key
            output.append(row)
    return sorted(output, key=lambda r: r['id']), {
        'mergedRows': len(records)-len(output), 'merges': merges, 'unresolved': unresolved,
        'newDiscoveries': sorted(discoveries), 'sourcePostingDateChanges': changes}
