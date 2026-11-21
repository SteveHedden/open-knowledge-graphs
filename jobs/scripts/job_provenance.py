"""Source provenance and narrowly reviewed remote requisition enrichment."""
import copy
import hashlib
import json
import re
from pathlib import Path

REVIEW_PATH = Path(__file__).resolve().parents[1] / 'curation/reviewed-job-requisitions.json'


def adzuna_provenance(record, raw=None):
    row = copy.deepcopy(record)
    if not str(row.get('sourceDataset', '')).endswith('/adzuna'):
        return row
    # An aggregator creation date is not an employer's publication date.
    if row.get('datePosted') and row.get('datePostedSource') != 'employer':
        row.setdefault('sourceListedDate', row.pop('datePosted'))
    if row.get('salaryProvenance') == 'employer':
        return row
    flag = str((raw or {}).get('salary_is_predicted', ''))
    basis = {'1': 'estimated', '0': 'source-reported'}.get(flag, row.get('salaryProvenance', 'unverified'))
    row['salaryProvenance'] = basis
    if basis != 'source-reported':
        if row.get('salary'): row['sourceSalary'] = row.pop('salary')
        if row.get('baseSalary'): row['sourceSalaryAmount'] = row.pop('baseSalary')
    return row


def reviewed_requisition(record):
    """Only explicit employer/reference/source evidence authorizes enrichment.

    No title, snippet similarity, inferred location or guessed requisition match.
    Reviewed content is scoped to exact source evidence; unrelated ads stay intact.
    """
    row = copy.deepcopy(record)
    reviews = json.loads(REVIEW_PATH.read_text())['requisitions']
    for rule in reviews:
        if row.get('hiringOrganization', '').strip().casefold() != rule['employerName'].casefold(): continue
        if row.get('provider') not in (None, 'adzuna') or not str(row.get('sourceDataset','')).endswith('/adzuna'): continue
        text = row.get('description', '')
        references = set(re.findall(rule['referencePattern'], text, re.I))
        already_reviewed = row.get('requisitionReview') == rule['reviewId']
        if not already_reviewed and (references != {rule['requisitionId']} or rule['sourceToken'] not in text): continue
        if row.get('requisitionId') and row['requisitionId'] != rule['requisitionId']: continue
        if row.get('workplaceMode') in ('onsite','hybrid'): continue
        if row.get('organizationIri') and row['organizationIri'] != rule['organizationIri']: continue
        for occurrence in row.get('sourceOccurrences', []):
            if occurrence.get('sourceRecordId') == row.get('sourceRecordId'):
                occurrence.setdefault('location', row.get('sourceAdvertisedLocation', row.get('location', '')))
                if row.get('sourceListedDate'): occurrence.setdefault('sourceListedDate', row['sourceListedDate'])
        row.setdefault('sourceDescription', text)
        row.setdefault('sourceAdvertisedLocation', row.get('location', ''))
        row.update({k: rule[k] for k in ['requisitionId', 'description', 'datePosted', 'location', 'locationKeys', 'workplaceMode', 'salary', 'baseSalary', 'validThrough']})
        row['requisitionReview'] = rule['reviewId']
        row['requisitionScope'] = 'reviewed-remote'
        row['requisitionOrganization'] = rule['organizationIri']
        row['employerPostingUrl'] = rule['url']
        row['canonicalUrl'] = rule['url']
        row['canonicalFingerprint'] = hashlib.sha256(rule['url'].encode()).hexdigest()
        row['datePostedSource'] = 'employer'
        row['salaryProvenance'] = 'employer'
        row['remote'] = True
    return row
