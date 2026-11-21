import copy
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from job_provenance import adzuna_provenance, reviewed_requisition
from job_identity import reconcile_recurring, empty_history


def ad(ident='a', location='Austin'):
    return dict(id=ident, sourceRecordId=ident, sourceDataset='https://openknowledgegraphs.com/jobs/source/adzuna',
                sourceUrl='https://www.adzuna.com/'+ident, canonicalUrl='https://www.adzuna.com/'+ident,
                hiringOrganization='Eliassen Group', title='Knowledge Graph Architect',
                description='Reference ID: JN -102026-109252 Shortcut: http://careers.eliassen.com/PONgHs Remote',
                location=location, locationKeys=[location.lower()], workplaceMode='unknown',
                datePosted='2026-11-01', salary='USD 200000', baseSalary={'currency':'USD','minValue':200000},
                firstSeenAt='2026-11-02T00:00:00Z', firstParty=False)


def test_predictions_never_become_employer_salary_or_dates():
    row = adzuna_provenance(ad(), {'salary_is_predicted':'1'})
    assert 'salary' not in row and 'baseSalary' not in row and 'datePosted' not in row
    assert row['sourceSalaryAmount']['minValue'] == 200000
    assert row['sourceListedDate'] == '2026-11-01' and row['salaryProvenance']=='estimated'
    assert adzuna_provenance(row) == row
    actual = adzuna_provenance(ad(), {'salary_is_predicted':'0'})
    assert actual['baseSalary']['minValue'] == 200000 and actual['salaryProvenance']=='source-reported'
    assert 'baseSalary' not in adzuna_provenance(ad())


def test_reviewed_remote_reference_merges_locations_preserving_ads():
    rows=[reviewed_requisition(adzuna_provenance(ad('a','Austin'))), reviewed_requisition(adzuna_provenance(ad('b','Boston')))]
    history=empty_history()
    merged,audit=reconcile_recurring(rows,history)
    assert len(merged)==1 and audit['mergedRows']==1
    assert merged[0]['datePosted']=='2026-10-28'
    assert merged[0]['baseSalary']['unitText']=='hour'
    assert merged[0]['salaryProvenance']=='employer'
    assert {x['location'] for x in merged[0]['sourceOccurrences']}=={'Austin','Boston'}
    assert len(reconcile_recurring(rows,history)[0])==1
    assert reviewed_requisition(adzuna_provenance(merged[0]))==merged[0]


def test_title_similarity_cannot_authorize_a_merge():
    a=ad();b=ad('b','Boston');a['description']=b['description']='Ontology work, remote'
    rows=[reviewed_requisition(a),reviewed_requisition(b)]
    result,audit=reconcile_recurring(rows,empty_history())
    assert len(result)==2 and len(audit['unresolved'])==1
    assert all(r['requisitionStatus']=='unresolved-duplicate-candidate' for r in result)


def test_conflicting_identity_and_onsite_are_not_enriched():
    for field,value in [('requisitionId','DIFFERENT'),('organizationIri','https://other.example'),('workplaceMode','onsite')]:
        row=ad();row[field]=value
        assert 'requisitionReview' not in reviewed_requisition(row)
    row=ad();row['description']+=' Reference ID: JN -102026-999999'
    assert 'requisitionReview' not in reviewed_requisition(row)


def test_distinct_first_party_requisitions_stay_distinct():
    a=ad();b=ad('b','Austin')
    for r,req in [(a,'123'),(b,'124')]:
        r.update(firstParty=True,organizationIri='https://example.com',requisitionId=req)
    assert len(reconcile_recurring([a,b],empty_history())[0])==2


def test_estimate_and_listing_date_do_not_leak_into_employer_rdf():
    from types import SimpleNamespace
    from live_records import build_graph, SCHEMA, KGJOBS, KGJDLIVE
    from rdflib import Literal
    from rdflib.namespace import XSD
    row=adzuna_provenance(ad(), {'salary_is_predicted':'1'})
    row.update(classification='qualified', evidence=[], lastSeenAt=row['firstSeenAt'],
               retrievedAt=row['firstSeenAt'], active=True, canonicalFingerprint='fixture')
    graph=build_graph([row], {'runId':'fixture','retrievedAt':row['retrievedAt']},SimpleNamespace(dataset_uri=row['sourceDataset']))
    subject=KGJDLIVE['job/a']
    assert not list(graph.objects(subject,SCHEMA.baseSalary))
    assert not list(graph.objects(subject,SCHEMA.datePosted))
    assert (subject,KGJOBS.sourceListedDate,Literal('2026-11-01',datatype=XSD.date)) in graph
    assert (subject,KGJOBS.salaryProvenance,Literal('estimated')) in graph
