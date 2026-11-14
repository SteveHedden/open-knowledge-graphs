#!/usr/bin/env python3
"""Offline evaluation of task 60 against a frozen, manifest-verified catalog.

The input directory contains public ontologies/software TTL and JSON, page_qids,
manifest and frozen-sample JSON. Never fetch sources or modify input artifacts.
Human relevance judgments are recorded separately from executable validation.
"""
import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path
from rdflib import Graph, URIRef
from rdflib.namespace import RDF
import related_resources as related
import generate_pages
import fetch_data
import validate_catalog


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def source_triples(graph):
    nodes=set(graph.objects(None,related.OKG.recommendation))
    return {t for t in graph if t[0] not in nodes and t[1] not in (related.OKG.relatedTo,related.OKG.recommendation)}


def evaluate(input_dir, output_dir):
    manifest=read(input_dir/'manifest.json');sample=read(input_dir/'frozen-sample.json')
    manifest_hashes={a['path']:a['sha256'] for a in manifest['artifacts']}
    for name in ('ontologies.ttl','software.ttl','ontologies.json','software.json','page_qids.json'):
        digest=hashlib.sha256((input_dir/name).read_bytes()).hexdigest()
        assert digest==manifest_hashes['data/'+name], (name,'not from pinned generation')
        if name in sample['inputs']:
            assert digest==sample['inputs'][name], (name,'sample snapshot changed')
    stems={'resource':'ontologies','software':'software'}
    graphs={kind:Graph().parse(input_dir/(stem+'.ttl')) for kind,stem in stems.items()}
    payloads={kind:read(input_dir/(stem+'.json')) for kind,stem in stems.items()}
    membership=read(input_dir/'page_qids.json')
    eligible={kind:{r['canonicalUrl'] for r in payloads[kind]['items']
                    if r['wikidataId'].rsplit('/',1)[-1] in membership[kind]} for kind in stems}
    all_eligible=set.union(*eligible.values())
    corpus=graphs['resource']+graphs['software'];context=related.build_similarity_context(graphs.values())
    before={kind:source_triples(g) for kind,g in graphs.items()};diagnostics={};coverage={};all_changes=[]
    for kind,graph in graphs.items():
        diagnostics[kind]=related.add_related_resources(graph,kind,context=context,candidate_graph=corpus,eligible_urls=all_eligible)
        assert before[kind]==source_triples(graph), (kind,'source data changed')
        related.validate_recommendations(graph,corpus)
        original=set(graph)
        repeat=related.add_related_resources(graph,kind,context=context,candidate_graph=corpus,eligible_urls=all_eligible)
        assert repeat==diagnostics[kind] and set(graph)==original, (kind,'nondeterminism')
        old_payload=copy.deepcopy(payloads[kind]);old_rows={r['canonicalUrl']:r for r in old_payload['items']}
        for row in payloads[kind]['items']:
            suggestions=related.project_recommendations(graph,URIRef(row['canonicalUrl']))
            if suggestions:row['relatedTools']=suggestions
            else:row.pop('relatedTools',None)
            old=old_rows[row['canonicalUrl']]
            assert {k:v for k,v in row.items() if k!='relatedTools'}=={k:v for k,v in old.items() if k!='relatedTools'}
            if row['canonicalUrl'] not in eligible[kind]:continue
            old_targets={e['canonicalUrl'] for e in old.get('relatedTools',[]) if e['canonicalUrl'] in all_eligible}
            new_targets={e['canonicalUrl'] for e in suggestions}
            for target in sorted(old_targets ^ new_targets):
                pair=related.score_pair(related.features_for_resource(corpus,URIRef(row['canonicalUrl'])),related.features_for_resource(corpus,URIRef(target)),context=context)
                disposition='gained' if target in new_targets else 'lost'
                all_changes.append({'subject':row['canonicalUrl'],'target':target,'change':disposition,
                    'reason': ('Supported candidate selected' if disposition=='gained' else 'Still qualified; outside stronger top five' if pair.qualifies else 'No approved qualifying path in frozen source graph'),
                    'scoreEvidence':pair.as_dict()})
        def covered(rows):
            return sum(any(e['canonicalUrl'] in all_eligible for e in row.get('relatedTools',[])) for row in rows if row['canonicalUrl'] in eligible[kind])
        coverage[kind]={'eligiblePages':len(eligible[kind]),'beforePagesWithRecommendations':covered(old_payload['items']),
            'afterPagesWithRecommendations':covered(payloads[kind]['items'])}
        write(output_dir/'data'/f'{stems[kind]}.json',payloads[kind])
        graph.serialize(output_dir/'data'/f'{stems[kind]}.ttl',format='turtle')
    combined=graphs['resource']+graphs['software']
    rows={r['canonicalUrl']:r for payload in payloads.values() for r in payload['items']}
    (output_dir/'preview').mkdir(parents=True,exist_ok=True)
    for css in (Path(__file__).resolve().parents[1]/'site').glob('*.css'):
        shutil.copy2(css,output_dir/'preview'/css.name)
    review=[]
    for page in sample['pages']:
        row=rows[page['id']];kind=page['catalog'];suggestions=row.get('relatedTools',[])
        assert len(suggestions)<=5
        page_html=generate_pages.make_page(row,kind,page['id'].rstrip('/').rsplit('/',1)[-1],page_urls=all_eligible)
        page_path=output_dir/'preview'/kind/page['id'].rstrip('/').rsplit('/',1)[-1]/'index.html'
        page_path.parent.mkdir(parents=True,exist_ok=True);page_path.write_text(page_html)
        ld=json.loads(generate_pages.make_json_ld(row,kind))
        evidence_ld=ld.get(str(related.OKG.recommendation),[])
        parsed=Graph().parse(data=json.dumps({'@id':page['id'],str(related.OKG.recommendation):evidence_ld}),format='json-ld')
        for entry in suggestions:
            node=URIRef(entry['recommendationId'])
            assert set(parsed.predicate_objects(node))==set(combined.predicate_objects(node))
            assert generate_pages.esc(entry['reason']['text']) in page_html
        review.append({**page,'suggestions':suggestions,'changes':[c for c in all_changes if c['subject']==page['id']]})
    # Validate actual public RDF/JSON projection using the shared validator.
    report=validate_catalog.ValidationReport()
    mappings=fetch_data.load_source_mappings(fetch_data.SOURCES_PATH)
    validate_catalog.validate_json_contract_and_projection(
        {f'data/{stems[k]}.ttl':g for k,g in graphs.items()},payloads,mappings,report)
    ontology=Graph().parse(Path(__file__).resolve().parents[1]/'ontology.ttl')
    validate_catalog.validate_declared_schema_terms(ontology,graphs.values(),report)
    assert not report.errors, validate_catalog.render_report(report)
    summary={'generationId':manifest['generationId'],'sampleSize':len(review),'suggestionCount':sum(len(r['suggestions']) for r in review),
             'coverage':coverage,'changes':{direction:sum(c['change']==direction for c in all_changes) for direction in ('gained','lost')},
             'checks':['manifest hashes','source triples and record fields unchanged','repeat-run determinism','all-catalog evidence validation','RDF/JSON projection','40-page RDF/JSON-LD/HTML reasons','schema declarations']}
    write(output_dir/'summary.json',summary);write(output_dir/'review.json',review)
    write(output_dir/'changes.json',all_changes);write(output_dir/'diagnostics.json',diagnostics)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.input_dir.resolve()==args.output_dir.resolve():parser.error('Input and output directories must differ')
    evaluate(args.input_dir,args.output_dir)
