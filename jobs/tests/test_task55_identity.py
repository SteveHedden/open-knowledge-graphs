"""Recurring identity, provenance and discovery regressions; no network calls."""
import copy
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from job_identity import empty_history, reconcile_recurring, strong_identity

FIXTURE = Path(__file__).parent/'fixtures/task55/confirmed-pairs.json'

def rows():
    return json.loads(FIXTURE.read_text())

def test_five_confirmed_pairs_and_repeat_are_stable():
    source = rows(); history = empty_history()
    result, audit = reconcile_recurring(source, history)
    assert len(result) == 5 and audit['mergedRows'] == 5
    assert sum(len(r['sourceOccurrences']) for r in result) == 10
    repeated, second = reconcile_recurring(list(reversed(source)), history)
    assert repeated == result and second['newDiscoveries'] == []
    assert all(r['firstSeenAt'] == min(x['firstSeenAt'] for x in source if strong_identity(x)[0]==strong_identity(r)[0]) for r in result)

def test_new_id_and_absence_restore_original_identity_and_discovery():
    original = rows()[0]; history=empty_history()
    first,_=reconcile_recurring([original],history)
    reconcile_recurring([],history)
    new=copy.deepcopy(original)
    new.update(id='adzuna-new',sourceRecordId='new',sourceUrl='https://www.adzuna.com/new',canonicalUrl='https://www.adzuna.com/new',firstSeenAt='2026-10-01T00:00:00Z',datePosted='2026-10-01')
    new.pop('sourceOccurrences')
    restored,audit=reconcile_recurring([new],history)
    assert restored[0]['id']==first[0]['id']
    assert restored[0]['firstSeenAt']==first[0]['firstSeenAt']
    assert len(restored[0]['sourceOccurrences'])==2
    assert audit['newDiscoveries']==[] and len(audit['sourcePostingDateChanges'])==1

def test_distinct_requisitions_and_employers_are_not_merged():
    a=rows()[0]; b=copy.deepcopy(a);b['id']='second';b['sourceRecordId']='second';b.pop('sourceOccurrences')
    b['description']=b['description'].replace('R0242874','R9999999')
    assert len(reconcile_recurring([a,b],empty_history())[0])==2
    b=copy.deepcopy(a);b['id']='other-employer';b['hiringOrganization']='Booz Allen Hamilton Consulting';b.pop('sourceOccurrences');b['sourceRecordId']='other'
    assert len(reconcile_recurring([a,b],empty_history())[0])==2

def test_location_mode_and_conflicting_requisition_veto_merge():
    a=rows()[0]
    for field,value in [('locationKeys',['other city']),('workplaceMode','remote'),('requisitionId','R9999999'),('organizationIri','https://other.example/')]:
        b=copy.deepcopy(a);b['id']='other';b['sourceRecordId']='other';b.pop('sourceOccurrences');b[field]=value
        result,audit=reconcile_recurring([a,b],empty_history())
        assert len(result)==2 and audit['unresolved']

def test_conflicting_expiry_and_employment_remain_separate():
    a=rows()[0];b=copy.deepcopy(a);b['id']='other';b['sourceRecordId']='other';b.pop('sourceOccurrences')
    a['validThrough']='2026-09-01';b['validThrough']='2026-10-01'
    assert len(reconcile_recurring([a,b],empty_history())[0])==2

def test_reappearance_does_not_erase_known_expiration():
    a=rows()[0];a['validThrough']='2026-09-01';history=empty_history()
    reconcile_recurring([a],history)
    a.pop('validThrough');a['datePosted']='2026-10-01'
    out,_=reconcile_recurring([a],history)
    assert out[0]['validThrough']=='2026-09-01'

def test_posting_date_change_does_not_reset_discovery_or_reclassify():
    a=rows()[0];history=empty_history();reconcile_recurring([a],history)
    a['datePosted']='2026-10-01';a['firstSeenAt']='2026-10-01T00:00:00Z'
    out,audit=reconcile_recurring([a],history)
    assert out[0]['firstSeenAt']==rows()[0]['firstSeenAt']
    assert out[0]['evidence']==a['evidence'] and out[0]['classification']==a['classification']
    assert audit['newDiscoveries']==[]

def test_existing_identity_without_requisition_restores_discovery():
    a=rows()[0];a['description']='No employer requisition provided';history=empty_history()
    reconcile_recurring([a],history);reconcile_recurring([],history)
    a['firstSeenAt']='2026-10-01T00:00:00Z'
    out,audit=reconcile_recurring([a],history)
    assert out[0]['firstSeenAt']==rows()[0]['firstSeenAt'] and not audit['newDiscoveries']

def test_jooble_updated_is_not_a_posting_date_and_missing_dates_stay_unknown():
    from live_sources import load_source_registry
    from jooble_adapter import normalize_jooble_job
    source=load_source_registry(Path(__file__).resolve().parents[2]/'sources.ttl')['jooble']
    raw={'id':123,'title':'Ontology Engineer','snippet':'Build ontologies.','company':'Example','link':'https://jooble.org/desc/123','updated':'2026-09-20T10:00:00.0000000'}
    for clock in ('2026-09-21T00:00:00Z','2026-09-22T00:00:00Z'):
        out=normalize_jooble_job(raw,source,clock,'ontology')
        assert out['sourceUpdatedDate']=='2026-09-20' and 'datePosted' not in out
    raw['updated']='Yesterday'
    out=normalize_jooble_job(raw,source,'2026-09-21T00:00:00Z','ontology')
    assert 'sourceUpdatedDate' not in out and 'datePosted' not in out

def test_identity_ledger_survives_atomic_runtime_and_public_promotion(tmp_path):
    from live_records import publish_snapshot
    from promote_jobs_snapshot import promote
    history=empty_history();current,_=reconcile_recurring(rows(),history)
    runtime=tmp_path/'runtime'
    publish_snapshot(current,{},None,tmp_path,runtime,{},'adzuna',{'adzuna':current},identity_history=history)
    publish_snapshot(current,{},None,tmp_path,runtime,{},'adzuna',{'adzuna':current})
    (runtime/'jobs.ttl').write_text('@prefix schema: <https://schema.org/> .\n')
    destination=tmp_path/'data/jobs';promote(runtime,destination)
    assert json.loads((destination/'identity-history.json').read_text())==history
