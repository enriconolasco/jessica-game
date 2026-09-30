const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const roots = new Map();
class Element {
  constructor(tag) { this.tag=tag; this.children=[]; this.files=[]; }
  appendChild(child) { child.parentElement=this; this.children.push(child); if(child.id) roots.set(child.id,child); if(this.tag==='select' && this.children.length===1) this.value=child.value; return child; }
  append(...children) { children.forEach(c=>this.appendChild(c)); }
  replaceChildren(...children) { this.children=[]; this.append(...children); }
  get options() { return this.children; }
}
for(const id of ['start','save','setupMessage','saveId','message']) roots.set(id,new Element('div'));
roots.get('save').parentElement = new Element('div');
const entries = [{save_id:'aaaaaaaaaaaa',name:'Cópia',kind:'manual',turn:2,phase:'day',updated_at:'2026-09-30T12:00:00Z'},
  {save_id:'bbbbbbbbbbbb',name:'Atual',kind:'autosave',turn:3,phase:'night',updated_at:'2026-09-30T13:00:00Z'},
  {save_id:'cccccccccccc',name:'Anterior',kind:'recovery',turn:2,phase:'night',updated_at:'2026-09-30T12:30:00Z'},
  {save_id:'dddddddddddd',name:'Save inválido',invalid:true}];
let entered=null, imported=null;
const context = vm.createContext({$:id=>roots.get(id), Date, JSON,
  Option:function(text,value){this.textContent=text;this.value=value;},
  document:{createElement:tag=>new Element(tag)},
  api:async(route,options)=> { if(route==='/saves') return entries; imported=JSON.parse(options.body); return {match_id:'imported',warnings:['Estado preservado.','Histórico começa aqui.']}; },
  enter:async id=>{entered=id;},
});
const source=fs.readFileSync(path.join(__dirname,'../jessica/web/static/app.js'),'utf8');
vm.runInContext(source.slice(source.indexOf('async function refreshSaves('),source.indexOf('$("revealPlayer").onclick')),context);
(async()=>{
  context.createSaveControls(); await context.refreshSaves();
  const saved=roots.get('savedGames'), filter=roots.get('saveFilter');
  assert.equal(filter.value,'main'); assert.equal(saved.options.length,4);
  assert.ok(saved.options.find(o=>o.value==='dddddddddddd').disabled);
  assert.ok(!saved.options.some(o=>o.value==='cccccccccccc'));
  saved.value='aaaaaaaaaaaa'; await context.refreshSaves(); assert.equal(saved.value,'aaaaaaaaaaaa');
  filter.value='recovery'; await filter.onchange(); assert.equal(saved.options.length,2);
  assert.match(saved.options[1].textContent,/Noite.*recuperação anterior/);
  saved.value='cccccccccccc'; saved.onchange(); assert.equal(roots.get('saveId').value,'cccccccccccc');
  filter.value='all'; await filter.onchange(); assert.equal(saved.options.length,5);
  const controls=roots.get('start').children[0];
  const file=controls.children[3].children[0];
  file.files=[{size:30,text:async()=>JSON.stringify({turn:2,players:[]})}];
  await file.onchange(); assert.equal(entered,'imported'); assert.equal(imported.turn,2);
  assert.equal(roots.get('message').textContent,'Estado preservado. Histórico começa aqui.'); assert.equal(file.value,'');
  console.log('UI: filtros de saves/recuperações, seleção preservada, entrada para carregar, importação e avisos verificados.');
})().catch(e=>{console.error(e);process.exitCode=1;});
