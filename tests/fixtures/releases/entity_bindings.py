"""Test-only adapter from captured Wikidata JSON to equivalent query bindings."""
import itertools

def binding(snak):
    d=snak.get('datavalue',{});v=d.get('value')
    if d.get('type')=='wikibase-entityid':return {'type':'uri','value':'http://www.wikidata.org/entity/'+v['id']}
    if d.get('type')=='time':return {'type':'literal','datatype':'http://www.w3.org/2001/XMLSchema#dateTime','value':v['time'].lstrip('+')}
    if isinstance(v,str):return {'type':'uri' if snak.get('datatype')=='url' else 'literal','value':v}
    return None

def bindings(qid,entity):
    rows=[]
    for claim in entity['claims'].get('P348',[]):
        if claim['mainsnak'].get('snaktype')!='value':continue
        base={'item':{'type':'uri','value':'http://www.wikidata.org/entity/'+qid},
              'verStmt':{'type':'uri','value':'http://www.wikidata.org/entity/statement/'+claim['id'].replace('$','-')},
              'version':binding(claim['mainsnak']),
              'versionRank':{'type':'uri','value':'http://wikiba.se/ontology#'+claim['rank'].capitalize()+'Rank'}}
        dates=claim.get('qualifiers',{}).get('P577',[]) or [None]
        qualifiers=[(p,s) for p,snaks in claim.get('qualifiers',{}).items() for s in snaks if binding(s)] or [(None,None)]
        references=[(r['hash'],p,s) for r in claim.get('references',[]) for p,snaks in r['snaks'].items() for s in snaks if binding(s)] or [(None,None,None)]
        for dt,(qp,qs),(rh,rp,rs) in itertools.product(dates,qualifiers,references):
            row=dict(base)
            if dt and dt.get('datavalue'):
                v=dt['datavalue']['value']
                row.update({'pubDate':binding(dt),'precision':{'value':str(v['precision'])},'calendar':{'type':'uri','value':v['calendarmodel']}})
            if qp:row.update({'qualifierProperty':{'type':'uri','value':'http://www.wikidata.org/prop/qualifier/'+qp},'qualifierValue':binding(qs)})
            if rp:row.update({'reference':{'type':'uri','value':'http://www.wikidata.org/reference/'+rh},'referenceProperty':{'type':'uri','value':'http://www.wikidata.org/prop/reference/'+rp},'referenceValue':binding(rs)})
            rows.append(row)
    return rows
