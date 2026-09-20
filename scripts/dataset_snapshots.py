#!/usr/bin/env python3
"""Immutable independent refresh outputs and coordinated, network-free assembly.

Dataset refs contain only a checked bundle; they never update main. Publication
pins their commit IDs once. Git's fast-forward push is the compare-and-swap guard.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import RDFS, DCTERMS

import catalog_snapshot as catalog
import shared_tags as tags

ROOT = Path(__file__).resolve().parents[1]
KINDS = ('resource', 'software', 'jobs')
STEMS = {'resource': 'ontologies', 'software': 'software', 'jobs': 'jobs/jobs'}
REF_PREFIX = 'dataset-snapshots/'


def report_output(key, value):
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream: stream.write(f'{key}={value}\n')


def git(root, *args, env=None, input=None):
    return subprocess.check_output(['git', *args], cwd=root, env=env, input=input).decode().strip()


@contextmanager
def phase(name):
    start = time.monotonic()
    print(json.dumps({'phase': name, 'status': 'started'}), flush=True)
    try:
        yield
    finally:
        print(json.dumps({'phase': name, 'elapsedSeconds': round(time.monotonic()-start, 3)}), flush=True)


def files_for(root, kind):
    if kind == 'jobs':
        paths = [p.relative_to(root).as_posix() for p in (root/'data/jobs').rglob('*')
                 if p.is_file() and p.name != 'manifest.json']
    else:
        stem = STEMS[kind]; paths = [f'data/{stem}.json', f'data/{stem}.ttl']
    history = root/f'data/classification-history/{kind}.ttl'
    if history.exists(): paths.append(history.relative_to(root).as_posix())
    evidence = root/f'data/classification-evidence/{kind}'
    paths.extend(p.relative_to(root).as_posix() for p in evidence.glob('*.json'))
    return sorted(paths)


def copy_dataset(source, root, kind):
    wanted = set(files_for(source, kind))
    for relative in set(files_for(root, kind)) - wanted:
        if not relative.startswith(('data/classification-history/','data/classification-evidence/')):
            (root/relative).unlink()
    for relative in sorted(wanted):
        target = root/relative; target.parent.mkdir(parents=True, exist_ok=True)
        if relative.startswith('data/classification-history/') and target.exists():
            tags.write_rdf(target,Graph().parse(target)+Graph().parse(source/relative))
        else:shutil.copy2(source/relative,target)


def bundle(root, kind, destination, code):
    """Seal complete data plus proposals for publisher-owned shared artifacts."""
    if destination.exists():
        raise ValueError('Snapshot destination already exists')
    destination.mkdir(parents=True)
    for relative in files_for(root, kind):
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root/relative, target)
    tags.write_json(destination/'vocabulary.json', tags.read(root/'data/tag-vocabularies.json'))
    if kind != 'jobs':
        tags.write_json(destination/'registry.json', {kind: tags.read(root/'data/uri_registry.json')[kind]})
        g = Graph().parse(root/'curation/classifications.ttl')
        predicate = tags.OKG.category if kind == 'resource' else tags.OKG.softwareType
        selected = Graph()
        for s, o in g.subject_objects(predicate):
            selected.add((s, predicate, o))
            for q in g.objects(s, tags.OKG.wikidataId):
                selected.add((s, tags.OKG.wikidataId, q))
        tags.write_rdf(destination/'classifications.ttl', selected)
    audit = root/'build/related-resources.json'
    if kind != 'jobs' and audit.exists(): shutil.copy2(audit, destination/'source-audit.json')
    hashes = {p.relative_to(destination).as_posix(): catalog.sha256_file(p)
              for p in sorted(destination.rglob('*')) if p.is_file()}
    # Ignore RDF serialization and retrieval timestamps when deciding whether
    # an unchanged catalog needs a new snapshot. Jobs include source freshness.
    effective = {p: catalog.normalized_artifact_fingerprint(destination, p)
                 if kind != 'jobs' else digest for p, digest in hashes.items()}
    manifest = {'schemaVersion': 1, 'dataset': kind, 'code': code,
                'createdAt': catalog.utc_now(), 'sourceRetrievedAt': (max(tags.read(root/'data/jobs/run.json').get('sourceRefreshes', {}).values(), default=catalog.utc_now()) if kind == 'jobs' else tags.read(root/f'data/{STEMS[kind]}.json')['generatedAt']), 'files': hashes,
                'effectiveDigest': tags.digest(effective)}
    payload = tags.read(root/f'data/{STEMS[kind]}.json')
    manifest['recordCount'] = len(payload if isinstance(payload,list) else payload['items'])
    refresh_selection = root/'build/refresh-selection.json'
    parent = tags.read(refresh_selection).get(kind, {}) if refresh_selection.exists() else {}
    manifest['parentCommit'] = None if parent.get('bootstrap') else parent.get('commit')
    manifest['snapshotId'] = tags.digest(manifest)
    tags.write_json(destination/'snapshot.json', manifest)
    verify(destination, kind)
    return manifest


def verify(root, kind):
    manifest = tags.read(root/'snapshot.json')
    if manifest.get('schemaVersion') != 1 or manifest.get('dataset') != kind:
        raise ValueError('Incompatible dataset snapshot')
    expected = dict(manifest); snapshot_id = expected.pop('snapshotId')
    if snapshot_id != tags.digest(expected):
        raise ValueError('Snapshot identity mismatch')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'snapshot.json'}:
        raise ValueError('Partial snapshot or unlisted files')
    allowed = set(files_for(root, kind)) | {'vocabulary.json'}
    if kind != 'jobs':
        allowed |= {'registry.json', 'classifications.ttl'}
        if 'source-audit.json' in manifest['files']: allowed.add('source-audit.json')
    if set(manifest['files']) != allowed:
        raise ValueError('Dataset snapshot crosses its ownership boundary')
    for relative, checksum in manifest['files'].items():
        catalog.normalize_relative_path(relative)
        path = root/relative
        if path.is_symlink() or catalog.sha256_file(path) != checksum:
            raise ValueError('Snapshot checksum mismatch: '+relative)
    stem = STEMS[kind]
    payload = tags.read(root/f'data/{stem}.json')
    rows = payload if isinstance(payload, list) else payload['items']
    if kind != 'jobs' and not rows: raise ValueError('Empty catalog snapshot')
    graph = Graph().parse(root/f'data/{stem}.ttl')
    if kind != 'jobs':
        from validate_catalog import ValidationReport, validate_json_contract_and_projection, DATASET_SPECS
        from semantic_config import load_source_mappings
        dataset = kind
        report = ValidationReport()
        graph_name = str(DATASET_SPECS[dataset]['graph'])
        validate_json_contract_and_projection({graph_name:graph}, {dataset:payload}, load_source_mappings(ROOT/'sources.ttl'), report)
        if report.errors:
            raise ValueError('Dataset RDF/JSON metadata mismatch: '+kind)
    terms = {t['id']: t for t in tags.read(root/'vocabulary.json')['terms']}
    seen = set()
    for row in rows:
        owner = tags.subject(row, kind)
        if owner in seen: raise ValueError('Duplicate snapshot identity')
        seen.add(owner)
        assessments = list(graph.objects(URIRef(owner), tags.OKG.tagAssessment))
        if len(assessments) != 1: raise ValueError('Incomplete classification: '+owner)
        if tags.public_projection(graph, assessments[0], terms) != row.get('sharedTags'):
            raise ValueError('Snapshot RDF/JSON classification mismatch: '+owner)
        if str(graph.value(assessments[0], tags.OKG.sourceContentHash)) != tags.digest(tags.fields(row, kind)):
            raise ValueError('Classification evidence no longer matches source: '+owner)
    return manifest


def store(repository, directory, kind):
    """Publish only a complete bundle, preserving prior snapshots in Git history."""
    manifest = verify(directory, kind)
    ref = 'refs/heads/'+REF_PREFIX+kind
    remote = git(repository, 'ls-remote', 'origin', ref)
    parent = remote.split()[0] if remote else None
    if parent != manifest.get('parentCommit'):
        # The acquisition must be based on the head it replaces. Fetching a
        # newer head at write time must never bless an older acquisition.
        if parent:
            git(repository, 'fetch', 'origin', ref)
            current = json.loads(git(repository, 'show', parent+':snapshot.json'))
            if current['effectiveDigest'] == manifest['effectiveDigest']:
                report_output('changed', 'false')
                return parent
        raise ValueError('Newer dataset snapshot exists; re-pin and retry refresh')
    if parent:
        git(repository, 'fetch', 'origin', ref)
        old = json.loads(git(repository, 'show', parent+':snapshot.json'))
        if old['effectiveDigest'] == manifest['effectiveDigest']:
            report_output('changed', 'false')
            print(json.dumps({'dataset': kind, 'snapshotReused': parent}), flush=True)
            return parent
    with tempfile.TemporaryDirectory() as temp:
        env = {**os.environ, 'GIT_INDEX_FILE': str(Path(temp)/'index'),
               'GIT_AUTHOR_NAME': 'github-actions[bot]', 'GIT_COMMITTER_NAME': 'github-actions[bot]',
               'GIT_AUTHOR_EMAIL': '41898282+github-actions[bot]@users.noreply.github.com',
               'GIT_COMMITTER_EMAIL': '41898282+github-actions[bot]@users.noreply.github.com'}
        git(repository, 'read-tree', '--empty', env=env)
        for path in sorted(directory.rglob('*')):
            if not path.is_file(): continue
            sha = git(repository, 'hash-object', '-w', str(path))
            git(repository, 'update-index', '--add', '--cacheinfo', '100644', sha,
                path.relative_to(directory).as_posix(), env=env)
        tree = git(repository, 'write-tree', env=env)
        commit = git(repository, 'commit-tree', tree, *(['-p', parent] if parent else []),
                     '-m', f'{kind} snapshot {manifest["snapshotId"]}', env=env)
        git(repository, 'push', 'origin', commit+':'+ref)
    report_output('changed', 'true')
    print(json.dumps({'dataset': kind, 'snapshotCommit': commit}), flush=True)
    return commit


def extract(repository, commit, destination):
    """Extract only regular Git blobs; no archives, symlinks or traversal paths."""
    destination.mkdir(parents=True, exist_ok=True)
    listing = subprocess.check_output(['git', 'ls-tree', '-rz', commit], cwd=repository)
    for entry in listing.split(b'\0'):
        if not entry: continue
        meta, raw_path = entry.split(b'\t', 1)
        mode, typ, sha = meta.decode().split()
        relative = catalog.normalize_relative_path(raw_path.decode())
        if mode != '100644' or typ != 'blob': raise ValueError('Unsupported snapshot object')
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(['git', 'cat-file', 'blob', sha], cwd=repository))


def pin(repository, destination):
    """Fetch all refs together, then record fixed commit IDs before assembly."""
    git(repository, 'fetch', 'origin', '+refs/heads/dataset-snapshots/*:refs/remotes/origin/dataset-snapshots/*')
    refs = git(repository, 'for-each-ref', '--format=%(refname:short) %(objectname)',
               'refs/remotes/origin/dataset-snapshots/')
    commits = dict(line.split() for line in refs.splitlines())
    selected = {}
    for kind in KINDS:
        commit = commits.get('origin/'+REF_PREFIX+kind)
        if commit:
            extract(repository, commit, destination/kind)
            manifest = verify(destination/kind, kind)
            selected[kind] = {'commit': commit, 'snapshotId': manifest['snapshotId'],
                              'createdAt': manifest['createdAt'], 'sourceRetrievedAt': manifest['sourceRetrievedAt']}
        else:
            # Bootstrap from committed validated production data on first cutover.
            prior = repository/'data/dataset-provenance.json'
            selected[kind] = tags.read(prior).get(kind) if prior.exists() else None
            selected[kind] = selected[kind] or {'commit': git(repository, 'rev-parse', 'HEAD'), 'bootstrap': True}
    tags.write_json(destination/'selection.json', selected)
    return selected


def merge_registry(current, proposed, kind):
    result = {k: dict(v) for k, v in current.items()}
    used = {v: k for k, v in result[kind].items()}
    for qid, slug in proposed[kind].items():
        if qid in result[kind] and result[kind][qid] != slug:
            raise ValueError('Snapshot would change established URL: '+qid)
        if slug in used and used[slug] != qid:
            raise ValueError('Concurrent slug collision requires reconciliation: '+slug)
        result[kind][qid] = slug; used[slug] = qid
    return result


def reproject(root, old_vocabularies):
    """Apply validated reviews, queue unsupported evidence, refresh projections."""
    previous = root/'build/previous-data'; previous.mkdir(parents=True,exist_ok=True)
    for kind, vocabulary in old_vocabularies.items():
        tags.write_json(previous/f'{kind}-vocabulary.json', vocabulary)
    # Review log from the publisher checkout wins over older snapshot results.
    rows=tags.read(root/'data/jobs/jobs.json'); graph=Graph().parse(root/'data/jobs/jobs.ttl')
    for row in rows:
        if row.get('validThrough') and datetime.fromisoformat(row['validThrough'].replace('Z','+00:00')).date() < datetime.now(timezone.utc).date():
            row['active']=False
            graph.set((URIRef(tags.subject(row,'jobs')),Namespace('https://openknowledgegraphs.com/jobs/ontology#').active,Literal(False)))
    tags.write_json(root/'data/jobs/jobs.json',rows);tags.write_rdf(root/'data/jobs/jobs.ttl',graph)
    tags.run(root)


def code_digest(repository):
    paths = git(repository, 'ls-files', 'scripts', 'api', 'mcp-server', 'site', 'validation',
                '.github/workflows', 'jobs/scripts', 'jobs/catalog-mention-policy.json').splitlines()
    return tags.digest({p: catalog.sha256_file(repository/p) for p in paths
                        if not p.startswith(('site/resource/', 'site/software/'))
                        and p not in ('site/sitemap.xml',) and (repository/p).is_file()})


def assemble(repository, root, pinned):
    selection = tags.read(pinned/'selection.json')
    old_vocab = tags.read(root/'data/tag-vocabularies.json')
    vocabularies = {kind: old_vocab for kind in KINDS}
    registry = tags.read(root/'data/uri_registry.json')
    curated = Graph().parse(root/'curation/classifications.ttl')
    prior_selection_path = root/'data/dataset-provenance.json'
    prior_selection = tags.read(prior_selection_path) if prior_selection_path.exists() else {}
    for kind in KINDS:
        retrieved = selection[kind].get('sourceRetrievedAt')
        if not retrieved:
            retrieved = max(tags.read(root/'data/jobs/run.json')['sourceRefreshes'].values()) if kind=='jobs' else tags.read(root/f'data/{STEMS[kind]}.json')['generatedAt']
        age = (datetime.now(timezone.utc)-datetime.fromisoformat(retrieved.replace('Z','+00:00'))).total_seconds()/3600
        print(json.dumps({'dataset':kind, 'selectedSnapshot':selection[kind], 'sourceAgeHours':round(age,2), 'retained':selection[kind] == prior_selection.get(kind)}))
        if selection[kind].get('bootstrap') or selection[kind].get('snapshotId') == prior_selection.get(kind, {}).get('snapshotId'): continue
        source = pinned/kind; manifest = verify(source, kind)
        vocabularies[kind] = tags.read(source/'vocabulary.json')
        copy_dataset(source, root, kind)
        if kind != 'jobs':
            registry = merge_registry(registry, tags.read(source/'registry.json'), kind)
            proposed = Graph().parse(source/'classifications.ttl')
            predicate = tags.OKG.category if kind == 'resource' else tags.OKG.softwareType
            # Preserve newer reviewed main-branch decisions; snapshots add values
            # only for subjects which do not already have a curated decision.
            for s, o in proposed.subject_objects(predicate):
                if curated.value(s, predicate) is None:
                    curated.add((s, predicate, o))
                    for q in proposed.objects(s, tags.OKG.wikidataId): curated.add((s, tags.OKG.wikidataId, q))
        age = (datetime.now(timezone.utc)-datetime.fromisoformat(manifest['createdAt'].replace('Z','+00:00'))).total_seconds()
        print(json.dumps({'dataset': kind, 'snapshot': selection[kind], 'ageHours': round(age/3600, 2)}))
    tags.write_json(root/'data/uri_registry.json', registry)
    tags.write_rdf(root/'curation/classifications.ttl', curated)
    with phase('stored-assessment-projections'): reproject(root, vocabularies)
    # Recompute cross-dataset recommendations once from the assembled graphs.
    from fetch_data import add_related_tools, build_json_payload
    from related_resources import build_similarity_context, diagnostics_document, write_diagnostics_atomic
    from semantic_config import load_source_mappings, ONTOLOGIES_DATASET, load_controlled_vocabulary, load_curated_assignments, classification_label_projection, controlled_vocabulary_projection, write_curated_assignments_atomic
    graphs = {kind: Graph().parse(root/f'data/{STEMS[kind]}.ttl') for kind in ('resource','software')}
    context = build_similarity_context(graphs.values())
    mappings = load_source_mappings(root/'sources.ttl')
    diagnostics = []
    for kind, graph in graphs.items():
        diagnostics.append(add_related_tools(graph, dataset=kind, context=context))
        if kind == 'resource':
            from semantic_config import ONTOLOGIES_DATASET
            # Eligibility of each exemplar is encoded by the admitted graph's
            # preserved source entities and declared uses/part-of predicates.
            by_qid = {str(q).rsplit('/',1)[-1]: subject for subject,q in graph.subject_objects(tags.OKG.wikidataId)}
            for exemplar in mappings.recommendation_exemplars:
                if exemplar.catalog != ONTOLOGIES_DATASET: continue
                subject = by_qid.get(exemplar.subject_qid); target = by_qid.get(exemplar.object_qid)
                if subject is None or target is None: continue
                if not graph.value(subject,tags.OKG.homepage) or not graph.value(target,tags.OKG.homepage): continue
                source_target = URIRef('http://www.wikidata.org/entity/'+exemplar.object_qid)
                claimed = any((subject,p,source_target) in graph for p in (tags.OKG.uses,DCTERMS.isPartOf))
                if claimed and (subject,tags.OKG.relatedTo,target) not in graph:
                    raise ValueError('Pinned recommendation missing: '+exemplar.label)
        payload = tags.read(root/f'data/{STEMS[kind]}.json')
        projection = build_json_payload(graph, mappings.target_classes_for(ONTOLOGIES_DATASET) if kind=='resource' else {tags.OKG.Software}, kind=='software', payload.get('generatedAt', catalog.utc_now()), mappings.projection_type_labels)
        # Keep shared tag projections, which the generic RDF projector omits.
        by_id = {r['canonicalUrl']: r for r in payload['items']}
        projection['items'] = [tags.apply_projection(r, by_id[r['canonicalUrl']]['sharedTags'], kind) for r in projection['items']]
        tags.write_json(root/f'data/{STEMS[kind]}.json', projection)
        tags.write_rdf(root/f'data/{STEMS[kind]}.ttl', graph)
    write_diagnostics_atomic(diagnostics_document(diagnostics), Path(os.environ.get('OKG_RELATED_DIAGNOSTICS_PATH',root/'build/related-resources.json')))
    categories = load_controlled_vocabulary(root/'vocabularies/categories.ttl')
    types = load_controlled_vocabulary(root/'vocabularies/software-types.ttl')
    assignments = load_curated_assignments(root/'curation/classifications.ttl', categories, types)
    for row in tags.read(root/'data/ontologies.json')['items']:
        qid = row['wikidataId'].rsplit('/',1)[-1]
        domains = row['sharedTags']['domains']
        if domains: assignments.categories[qid] = URIRef(domains[0]['id'])
        else: assignments.categories.pop(qid, None)
    write_curated_assignments_atomic(root/'curation/classifications.ttl', assignments, registry, categories, types)
    tags.write_json(root/'data/categories.json', classification_label_projection(assignments.categories, categories))
    tags.write_json(root/'data/software_types.json', classification_label_projection(assignments.software_types, types))
    tags.write_json(root/'data/controlled_vocabularies.json', controlled_vocabulary_projection(categories, types))
    from catalog_events import synchronize, validate
    synchronize(root)
    validate(root)
    record_inputs(repository, root)
    tags.write_json(root/'data/dataset-provenance.json', selection)
    tags.write_json(root/'build/dataset-selection.json', selection)


def record_inputs(repository, root):
    # Called again after final page-link projection so the recorded fingerprints
    # describe the actual deployed data, not an intermediate assembly.
    effective = {kind: catalog.normalized_artifact_fingerprint(root, f'data/{STEMS[kind]}.json') for kind in KINDS}
    tags.write_json(root/'data/publication-inputs.json', {'schemaVersion': 1, 'codeDigest': code_digest(repository), 'dataDigests': effective})


def hydrate(repository, root, pinned):
    selection = tags.read(pinned/'selection.json')
    tags.write_json(root/'build/refresh-selection.json', selection)
    registry = tags.read(root/'data/uri_registry.json')
    for kind in KINDS:
        source = pinned/kind
        if not source.exists(): continue
        verify(source, kind)
        copy_dataset(source, root, kind)
        if kind != 'jobs':
            registry = merge_registry(registry, tags.read(source/'registry.json'), kind)
            current = Graph().parse(root/'curation/classifications.ttl')
            proposed = Graph().parse(source/'classifications.ttl')
            for subject, predicate, value in proposed:
                if current.value(subject, predicate) is None: current.add((subject,predicate,value))
            tags.write_rdf(root/'curation/classifications.ttl', current)
    tags.write_json(root/'data/uri_registry.json', registry)
    previous = root/'build/previous-data'; previous.mkdir(parents=True, exist_ok=True)
    for kind in KINDS:
        shutil.copy2(root/f'data/{STEMS[kind]}.ttl', previous/f'{kind}.ttl')
    # Store the vocabulary used by each assessment, not a synthesized newer one.
    for kind in KINDS:
        source = pinned/kind/'vocabulary.json'
        shutil.copy2(source if source.exists() else root/'data/tag-vocabularies.json', previous/f'{kind}-vocabulary.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['bundle','store','pin','assemble','project','hydrate','finalize-jobs','finalize','record-inputs'])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--repository', type=Path, default=ROOT)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--dataset', choices=KINDS)
    parser.add_argument('--started-at')
    parser.add_argument('--output-file', type=Path)
    args = parser.parse_args()
    with phase(args.command):
        if args.command in ('finalize', 'finalize-jobs'):
            jobs_time = max(tags.read(args.root/'data/jobs/run.json').get('sourceRefreshes', {}).values(), default=tags.read(args.root/'data/jobs/manifest.json')['sourceRetrievedAt'])
            retrieved = max(jobs_time, *(tags.read(args.root/f'data/{STEMS[k]}.json')['generatedAt'] for k in ('resource','software')))
            if args.command == 'finalize-jobs':
                manifest = catalog.write_jobs_manifest(args.root, args.started_at, jobs_time)
            else:
                manifest = catalog.write_manifest(args.root, args.started_at, retrieved)
                if args.output_file:
                    with args.output_file.open('a') as stream: stream.write('generation_id='+manifest['generationId']+'\n')
        elif args.command == 'bundle': bundle(args.root, args.dataset, args.directory, git(args.repository,'rev-parse','HEAD'))
        elif args.command == 'store': store(args.repository, args.directory, args.dataset)
        elif args.command == 'pin': pin(args.repository, args.directory)
        elif args.command == 'record-inputs': record_inputs(args.repository, args.root)
        elif args.command == 'hydrate': hydrate(args.repository, args.root, args.directory)
        elif args.command == 'project':
            vocabulary = tags.read(args.root/'data/tag-vocabularies.json')
            reproject(args.root, {kind: vocabulary for kind in KINDS})
        else: assemble(args.repository, args.root, args.directory)

if __name__ == '__main__': main()
