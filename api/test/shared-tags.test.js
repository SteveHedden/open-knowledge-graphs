import test from 'node:test';
import assert from 'node:assert/strict';
import '../../site/shared-tags.js';
const T=globalThis.OKGTags;
const index=T.termIndex({terms:[{id:'health',dimension:'domains',broader:[]},{id:'clinical',dimension:'domains',broader:['health']},{id:'finance',dimension:'domains',broader:[]},{id:'neo',dimension:'tools',broader:[],catalogPages:['https://example.com/neo']},{id:'star',dimension:'tools',broader:[]},{id:'search',dimension:'activities',broader:[]}].map(t=>({...t,label:t.id}))});
const job={sharedTags:{tools:[{id:'neo'}],activities:[{id:'search'}],domains:[{id:'clinical'}]}};
test('OR within dimensions and AND across dimensions, including descendants',()=>{
 assert.equal(T.matches(job,{tools:['neo','star'],activities:['search'],domains:['health']},index,false),true);
 assert.equal(T.matches(job,{tools:['neo'],domains:['finance']},index,false),false);
 assert.equal(T.matches(job,{domains:['finance','health']},index,false),true);
 assert.equal(T.matches(job,{domains:['unknown']},index,false),false);
});
test('catalog entity itself counts as supply without asserting self-use',()=>{
 const item={wikidataId:'Q1',canonicalUrl:'https://example.com/neo',sharedTags:{tools:[]}};
 assert.equal(T.matches(item,{tools:['neo']},index),true);
 assert.equal(T.matches(item,{tools:['neo']},index,false),false);
 assert.deepEqual(item.sharedTags.tools,[]);
});
test('distinct catalog counts merge dimensions without double counting',()=>{
 const rows=T.uniqueCatalog([{wikidataId:'Q1',sharedTags:{domains:[{id:'health'}]}},{wikidataId:'Q1',sharedTags:{domains:[{id:'clinical'}]}}]);
 assert.equal(rows.length,1);assert.equal(rows[0].sharedTags.domains.length,2);
});
test('demand preserves eligibility and active membership and deduplicates fingerprints',()=>{
 const active={active:true,classification:'qualified',canonicalFingerprint:'a'};
 assert.equal(T.eligibleJobs([active,{...active,id:'syndicated'},{...active,canonicalFingerprint:'b',classification:'not_match'},{...active,canonicalFingerprint:'c',active:false}]).length,1);
});
test('repeated query values retain OR selections',()=>assert.deepEqual(T.selections(new URLSearchParams('tools=neo&tools=star&domains=health')).tools,['neo','star']));
test('comparison counts parent descendants once and keeps supply/demand separate',()=>{
 const rows=T.coverageRows([{canonicalUrl:'r1',wikidataId:'Q1',sharedTags:{domains:[{id:'clinical'},{id:'health'}]}}],[{canonicalUrl:'s1',wikidataId:'Q1',sharedTags:{domains:[{id:'health'}]}}],[{...job,canonicalFingerprint:'j1',hiringOrganization:'Employer'}],index,'domains');
 const parent=rows.find(r=>r.id==='health');assert.deepEqual(parent,{id:'health',label:'health',resources:1,software:1,catalogEntities:1,jobs:1,employers:1});
});

test('unpublished catalog page still counts as an entity without creating a page link',()=>{
 const idx=T.termIndex({terms:[{id:'entity',label:'Entity',dimension:'tools',broader:[],catalogIdentities:['record'],catalogPages:[]}]});
 const row={canonicalUrl:'record',wikidataId:'Q1',sharedTags:{tools:[]}};
 assert.equal(T.matches(row,{tools:['entity']},idx),true);
 assert.equal(T.coverageRows([row],[],[],idx,'tools')[0].catalogEntities,1);
 assert.deepEqual(idx.get('entity').catalogPages,[]);
});
