const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('site/detail-analytics.js', 'utf8');
function harness(track) {
  const handlers = {}, events = [];
  const page = {dataset:{catalogTab:'software',resourceTitle:'Fluree'},contains:()=>true};
  const window = {location:{href:'https://openknowledgegraphs.com/software/fluree/',hostname:'openknowledgegraphs.com',pathname:'/software/fluree/'},umami:{track: track || ((...args)=>events.push(args))}};
  vm.runInNewContext(source,{URL,window,document:{querySelector:()=>page,addEventListener:(n,f)=>handlers[n]=f}});
  function click(href,type='click',button=0) { handlers[type]({type,button,target:{closest:()=>({getAttribute:()=>href,dataset:{linkType:'homepage'}})}}); }
  return {click,events,window};
}
test('external clicks preserve item and page context without sending URL query data',()=>{
 const h=harness();h.click('https://flur.ee/?private=value');
 assert.equal(h.events.length,1);assert.equal(h.events[0][0],'outbound_link_click');
 const p=h.events[0][1];assert.equal(p.resourceTitle,'Fluree');assert.equal(p.resourcePath,'/software/fluree/');assert.equal(p.destinationHost,'flur.ee');assert.equal(p.sourcePage,'detail');assert.ok(!JSON.stringify(p).includes('private'));
});
test('internal navigation, fragments and non-web links are not outbound',()=>{const h=harness();for(const url of ['#details','/software/other/','https://openknowledgegraphs.com/','mailto:a@example.com','javascript:void(0)'])h.click(url);assert.equal(h.events.length,0);});
test('middle click counts once; right click does not count',()=>{const h=harness();h.click('https://flur.ee','auxclick',1);h.click('https://flur.ee','auxclick',2);assert.equal(h.events.length,1);});
test('missing or failing tracker does not break navigation',()=>{const h=harness(()=>{throw Error('unavailable')});assert.doesNotThrow(()=>h.click('https://flur.ee'));delete h.window.umami;assert.doesNotThrow(()=>h.click('https://flur.ee'));});
