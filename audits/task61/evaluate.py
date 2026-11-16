"""Compare an untouched local catalog checkout with a staged Task 61 replay.

Usage: python audits/task61/evaluate.py BASE_ROOT STAGED_ROOT [OUTPUT_DIR]
Catalog inputs are not modified; rendered previews are written in STAGED_ROOT.
Review output defaults to the directory alongside this script.
"""
import hashlib
import json
import sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from rdflib import Graph, URIRef
import catalog_uses as uses
import related_resources as related
import generate_pages as pages
import validate_catalog as validation
import fetch_data


def run(base,stage,out=None):
    out=out or Path(__file__).parent
    out.mkdir(parents=True,exist_ok=True)
    read=lambda p:json.loads(p.read_text())
    graphs={k:Graph().parse(stage/f'data/{s}.ttl') for k,s in [('resource','ontologies'),('software','software')]}
    corpus=graphs['resource']+graphs['software']
    before={};after={};hashes={};payloads={}
    for kind,stem in [('resource','ontologies'),('software','software')]:
        b=read(base/f'data/{stem}.json');a=read(stage/f'data/{stem}.json');payloads[kind]=a
        before.update({r['canonicalUrl']:r for r in b['items']});after.update({r['canonicalUrl']:r for r in a['items']})
        for ext in ('ttl','json'):hashes[f'data/{stem}.{ext}']=hashlib.sha256((base/f'data/{stem}.{ext}').read_bytes()).hexdigest()
        related.validate_recommendations(graphs[kind],corpus)
    expected=read(Path(__file__).parent/'summary.json')['inputHashes']
    assert hashes==expected,'Frozen baseline input hashes changed'
    assert before.keys()==after.keys()
    for url,row in after.items():
        for key in ('canonicalUrl','wikidataId','title','description','types','category','categories','softwareType','softwareTypes'):
            assert row.get(key)==before[url].get(key),(url,key,'protected field changed')
    # Immutable review records/corrections and Jobs artifacts must be byte-identical.
    protected=[]
    for folder in ('curation','data/jobs'):
        for p in (base/folder).rglob('*'):
            if p.is_file() and p.name!='tag-assignments.ttl':
                q=stage/p.relative_to(base)
                assert q.exists() and p.read_bytes()==q.read_bytes(),p
                protected.append(str(p.relative_to(base)))
    terms={t['id']:t for t in read(stage/'data/tag-vocabularies.json')['terms']}
    from shared_tags import registry_graph
    ids=uses.Identities(corpus+registry_graph(terms));audit=[]
    for graph in graphs.values():
        uses.validate(graph,ids,terms)
        original=set(graph);audit+=uses.normalize(graph,ids,terms);assert set(graph)==original
    oldaudit=read(Path(__file__).parent/'tag-use-audit.json');statuses={a['assignment']:a['status'] for a in audit}
    for row in oldaudit:row['disposition']=statuses.get(row['assignment'],'not-in-current-assessment')
    (out/'tag-use-audit.json').write_text(json.dumps(oldaudit,indent=2)+'\n')
    sample=read(ROOT/'audits/task60/2026-11-14/frozen-sample.json')['pages']
    selected=[p['id'] for p in sample]
    selected+=sorted(url for url in after if (url.endswith('/shacl-play/') or url.endswith('/context-ontology-accelerator/')) and url not in selected)
    membership=read(stage/'data/page_qids.json')
    eligible={u for u,r in after.items() if r['wikidataId'].rsplit('/',1)[-1] in membership['software' if '/software/' in u else 'resource']}
    context=related.build_similarity_context(graphs.values());reviews=[];changes=[]
    for url in sorted(eligible):
        old=before[url].get('relatedTools',[]);new=after[url].get('relatedTools',[])
        oldtargets={e['canonicalUrl'] for e in old};newtargets={e['canonicalUrl'] for e in new}
        assert len(newtargets)==len(new)<=5 and newtargets<=eligible
        delta=[]
        for target in sorted(oldtargets^newtargets):
            pair=related.score_pair(related.features_for_resource(corpus,URIRef(url)),related.features_for_resource(corpus,URIRef(target)),context=context)
            entry={'subject':url,'target':target,'change':'gained' if target in newtargets else 'lost','explanation':('Selected by existing ranking after canonical use normalization' if target in newtargets else 'Still qualifies; displaced from the top five' if pair.qualifies else 'No longer has an eligible qualifying path'),'scoreEvidence':pair.as_dict()}
            delta.append(entry);changes.append(entry)
        if url not in selected:continue
        row=after[url];kind='software' if '/software/' in url else 'resource'
        html=pages.make_page(row,kind,url.rstrip('/').rsplit('/',1)[-1],page_urls=eligible)
        links,reasons=validation.extract_related_display(html)
        assert links==[{'canonicalUrl':e['canonicalUrl'],'title':e['title']} for e in new]
        assert reasons==[e['reason']['text'] for e in new]
        assert 'aria-label="Related tools and resources"' not in html
        ld=json.loads(pages.make_json_ld(row,kind))
        parsed=Graph().parse(data=json.dumps({'@id':url,str(uses.OKG.recommendation):ld.get(str(uses.OKG.recommendation),[]),str(uses.OKG.uses):ld.get(str(uses.OKG.uses),[])}),format='json-ld')
        assert set(parsed.objects(URIRef(url),uses.OKG.uses))==set(corpus.objects(URIRef(url),uses.OKG.uses))
        for entry in new:
            node=URIRef(entry['recommendationId'])
            assert set(parsed.predicate_objects(node))==set(corpus.predicate_objects(node))
        preview=stage/'site'/url.split('openknowledgegraphs.com/')[1]/'index.html';preview.write_text(html)
        reviews.append({'id':url,'title':row['title'],'before':old,'after':new,'changes':delta})
    assert len(reviews)==len(selected),(len(reviews),len(selected))
    shacl=next(r for r in reviews if r['id'].endswith('/shacl-play/'))
    aws=next(r for r in reviews if r['id'].endswith('/context-ontology-accelerator/'))
    assert {'Resource Description Framework','SHACL'}<={r['title'] for r in shacl['after'] if r['reason']['text']=='Uses'}
    assert {'elk','hermit','ontop'}<={r['canonicalUrl'].rstrip('/').rsplit('/',1)[-1] for r in aws['after'] if r['reason']['text']=='Uses'}
    report=validation.ValidationReport()
    validation.validate_json_contract_and_projection({f'data/{s}.ttl':graphs[k] for k,s in [('resource','ontologies'),('software','software')]},payloads,fetch_data.load_source_mappings(ROOT/'sources.ttl'),report)
    validation.validate_declared_schema_terms(Graph().parse(ROOT/'ontology.ttl'),graphs.values(),report)
    assert not report.errors,validation.render_report(report)
    summary={'baselineCommit':'640e5f1f2','inputHashes':hashes,'sampleSize':len(reviews),'sampleSuggestions':sum(len(r['after']) for r in reviews),'eligiblePages':len(eligible),'beforeCovered':sum(bool(before[u].get('relatedTools')) for u in eligible),'afterCovered':sum(bool(after[u].get('relatedTools')) for u in eligible),'changes':dict(Counter(c['change'] for c in changes)),'tagDisposition':dict(Counter(a['status'] for a in audit)),'protectedFiles':len(protected),'checks':['all recommendation paths and wording','identity resolution and use-evidence parity','repeat normalization idempotence','protected catalog fields','immutable review/correction and Jobs bytes','five-result cap and eligible targets','sample HTML/RDF/JSON-LD parity','RDF/JSON projection and declared schema']}
    for name,value in [('summary',summary),('page-review',reviews),('changes',changes)]:
        (out/f'{name}.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':run(*map(Path,sys.argv[1:]))
