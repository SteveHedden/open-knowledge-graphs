"""Idempotent saved-snapshot repair, also applied before catalog publication."""
import json
from pathlib import Path
from urllib.parse import quote
from rdflib import Graph, URIRef
from job_identity import load_history, reconcile_recurring
from job_provenance import adzuna_provenance, reviewed_requisition
from live_records import build_graph, validate_graph, KGJDLIVE
from live_sources import load_source_registry
from rdf_utils import write_deterministic_turtle


def repair(root):
    root = Path(root)
    path = root/'data/jobs/jobs.json'
    if not path.exists(): return {}
    before = json.loads(path.read_text())
    if not any(str(row.get('sourceDataset', '')).endswith('/adzuna') for row in before):
        return {'changed': False, 'records': len(before)}
    raw_by_id = {}
    def collect(value):
        if isinstance(value, dict):
            if value.get('__CLASS__') == 'Adzuna::API::Response::Job': raw_by_id[str(value['id'])] = value
            else:
                for item in value.values(): collect(item)
        elif isinstance(value, list):
            for item in value: collect(item)
    raw_path = root/'data/jobs/raw/adzuna.json'
    if raw_path.exists(): collect(json.loads(raw_path.read_text()))
    prepared = [reviewed_requisition(adzuna_provenance(row, raw_by_id.get(str(row.get('sourceRecordId'))))) for row in before]
    history_path = root/'data/jobs/identity-history.json'
    history = load_history(history_path)
    rows, audit = reconcile_recurring(prepared, history)
    if rows == before: return {'changed': False, 'records': len(rows)}
    # Archive assessments before removing merged public subjects; subsequent
    # shared-tag projection checks input hashes before reusing any assignment.
    import classification_review as review
    review.archive(root, 'jobs', review.collect_prior(root, 'jobs'))
    old = Graph().parse(root/'data/jobs/jobs.ttl')
    run = json.loads((root/'data/jobs/run.json').read_text())
    source = load_source_registry(root/'sources.ttl')['adzuna']
    graph = build_graph(rows, run, source)
    # Preserve assessment subgraphs for surviving records until normal reprojection.
    okg = 'https://openknowledgegraphs.com/ontology#'
    surviving = {KGJDLIVE['job/'+quote(r['id'], safe='')] for r in rows}
    for subject in surviving:
        for p,o in old.predicate_objects(subject):
            if str(p).startswith(okg): graph.add((subject,p,o))
    for s,p,o in old:
        if str(s).startswith(('https://openknowledgegraphs.com/tag-assessments/', 'https://openknowledgegraphs.com/tag-assignments/')):
            graph.add((s,p,o))
    validate_graph(graph, root/'jobs')
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True)+'\n')
    write_deterministic_turtle(graph, root/'data/jobs/jobs.ttl')
    history_path.write_text(json.dumps(history, indent=2, sort_keys=True)+'\n')
    run.setdefault('reconciliation', {})['provenanceRepair'] = audit
    (root/'data/jobs/run.json').write_text(json.dumps(run, indent=2, sort_keys=True)+'\n')
    return {'changed': True, 'before':len(before), 'after':len(rows), 'merged':audit['mergedRows'], 'unresolved':len(audit['unresolved'])}


if __name__ == '__main__':
    import sys
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root/'scripts'))
    print(json.dumps(repair(root)))
