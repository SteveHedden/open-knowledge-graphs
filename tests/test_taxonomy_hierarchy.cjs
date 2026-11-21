const fs = require('fs'), assert = require('assert');
const source = fs.readFileSync('site/app.js','utf8');
class Element {
 constructor(){this.children=[];this.attrs={};this.dataset={};}
 appendChild(x){this.children.push(x)} replaceChildren(){this.children=[]}
 setAttribute(k,v){this.attrs[k]=v}
 querySelectorAll(){return this.children.flatMap(x=>[...(x.type==='button'?[x]:[]),...x.querySelectorAll()])}
}
global.document={createElement:()=>new Element()};
const functions=source.slice(source.indexOf('  function normalizeVocabularyOptions'),source.indexOf('  function configureControlledVocabularies'));
eval(functions + '\nglobal.normalize=normalizeVocabularyOptions;global.render=renderVocabularyButtons;');
const list=new Element(), container={querySelector:()=>list};
const options=normalize(JSON.parse(fs.readFileSync('data/controlled_vocabularies.json')).categories);
const buttons=render(container,options,'category');
assert.equal(buttons.length,options.length);
const health=buttons.find(b=>b.dataset.category==='healthcare');
assert.equal(health.textContent,'↳ Healthcare');
const parent=buttons.find(b=>b.dataset.category==='life-sciences-healthcare');
assert(parent.textContent.endsWith('— all'));
const group=list.children.find(g=>g.children.includes(parent));
assert(group.children[1].querySelectorAll().includes(health));
require(process.cwd()+'/site/shared-tags.js'); const tags=global.OKGTags;
const vocabulary=JSON.parse(fs.readFileSync('data/tag-vocabularies.json'));
const index=tags.termIndex(vocabulary);
const iri='https://openknowledgegraphs.com/ontology#';
assert(tags.matches({sharedTags:{domains:[{id:iri+'Healthcare'}]}},{domains:[iri+'LifeSciencesHealthcare']},index));
assert(!tags.matches({sharedTags:{domains:[{id:iri+'LifeSciences'}]}},{domains:[iri+'Healthcare']},index));
console.log('Hierarchy DOM grouping, stable filter IDs, parent matching and sibling exclusion pass.');
