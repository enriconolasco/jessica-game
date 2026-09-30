const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tagName=tag.toUpperCase(); this.children=[]; this.dataset={}; this.attrs={}; this.listeners={}; this.textContent=''; this.className=''; this.classList={add: c => this.className+=' '+c}; }
  appendChild(child) { child.parentElement=this; this.children.push(child); return child; }
  append(...children) { children.forEach(c => this.appendChild(c)); }
  replaceChildren(...children) { this.children.forEach(c => c.parentElement=null); this.children=[]; this.append(...children); }
  after(child) { const p=this.parentElement; child.parentElement=p; p.children.splice(p.children.indexOf(this)+1,0,child); }
  setAttribute(k,v) { this.attrs[k]=v; if(k.startsWith('data-')) this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v; }
  getAttribute(k) { return this.attrs[k] ?? null; }
  addEventListener(k,fn) { this.listeners[k]=fn; }
  matches(selector) { return selector.split(',').some(s => { s=s.trim(); return s.startsWith('.') ? this.className.split(' ').includes(s.slice(1)) : s==='[hidden]' ? Boolean(this.hidden) : s==='[inert]' ? Boolean(this.inert) : s==='[contenteditable]' ? Boolean(this.contenteditable) : s==='dialog[open]' ? this.tagName==='DIALOG'&&this.open : this.tagName===s.toUpperCase(); }); }
  closest(s) { for(let n=this;n;n=n.parentElement) if(n.matches(s)) return n; return null; }
  querySelectorAll(s) { return this.children.flatMap(c => [...(c.matches(s)?[c]:[]), ...c.querySelectorAll(s)]); }
  querySelector(s) { return this.querySelectorAll(s)[0] || null; }
  contains(el) { return el===this || this.children.some(c=>c.contains(el)); }
  getClientRects() { return this.closest('[hidden], [inert]') ? [] : [{}]; }
  click() { this.onclick?.(); this.listeners.click?.(); }
  focus() { document.activeElement=this; this.listeners.focus?.(); }
}
const body=new Element('body');
const document={body, createElement:t=>new Element(t), createElementNS:(_,t)=>new Element(t),
  querySelectorAll:s=>body.querySelectorAll(s), querySelector:s=>body.querySelector(s),
  getElementById:id=> { const find=n=>n.id===id?n:n.children.map(find).find(Boolean); return find(body); }};
const context=vm.createContext({document});
const root=path.join(__dirname,'../jessica/web/static');
const presentation=fs.readFileSync(path.join(root,'presentation.js'),'utf8');
vm.runInContext(presentation,context);
const view={curuna_id:2,players:[{id:1,name:'Ana',people:'dragoes',stats:{kills:3},city:{life:3,life_max:3}},
  {id:2,name:'Beto',people:'gnomos_duendes',stats:{},city:{life:2,life_max:6}},
  {id:3,name:'Cris',people:'demonios',stats:{damage_dealt:8},city:{life:2,life_max:6}}],
  board:{units:[]},timeline:[{turn:1,resources:{1:{gold:2,magic:3,life:3}}},{turn:2,resources:{1:{gold:4,magic:5,life:3},2:{gold:1,magic:2,life:2}}}],self:{hand:['PRIVATE_CARD']}};
context.view=view;
for(let mask=0;mask<8;mask++) {
  const peoples=['gnomos_duendes','dragoes','demonios'].filter((_,i)=>mask&(1<<i));
  context.sample={players:peoples.map(people=>({people}))};
  assert.equal(JSON.stringify(vm.runInContext('hudPresence(sample)',context)),JSON.stringify({bets:Boolean(mask&1),canastra:Boolean(mask&2),pacts:Boolean(mask&4)}));
}
assert.match(context.curunaLabel(view,p=>p),/Beto.*gnomos_duendes/);
const data=context.reportData(view,'combat','kills');
assert.equal(data.bars[0].value,3); assert.equal(data.bars[1].value,0);
assert.equal(data.rows[2][1],8); assert.ok(!JSON.stringify(data).includes('PRIVATE_CARD'));
const economy=context.reportData(view,'economy','magic');
assert.equal(economy.series[0].points[1].value,5);
assert.equal(economy.series[1].points[0].value,null);
assert.equal(context.reportData({...view, timeline:[]},'economy','life').rows.length,0);
const report=new Element('div'); context.drawReport(report,view,'combat','kills');
assert.equal(report.querySelectorAll('table').length,1); assert.equal(report.querySelectorAll('svg').length,1);
context.drawReport(new Element('div'),view,'economy','gold');
const el=(tag,id,cls='')=>{const n=new Element(tag); n.id=id; n.className=cls; body.appendChild(n); return n;};
const viewport=el('div','viewport'); const map=new Element('div'); map.id='minimap'; viewport.appendChild(map);
for(const house of ['center','city_1','city_2','city_3','city_4']) { const n=new Element('section'); n.className='house'; n.dataset.house=house; n.append(new Element('h3'),Object.assign(new Element('div'),{className:'house-units'})); map.appendChild(n); }
el('p','mapCuruna'); el('nav','mapNavigation'); el('aside','unitDetails');
view.board.units=Array.from({length:25},(_,i)=>({id:`u${i}`,owner_id:i%3+1,kind:i===0?'hero':'troop',hero_id:i===0?'barba_negra':undefined,archetype:'light',house:'center',life:2,life_max:4,statuses:{}}));
view.board.units.push({id:'dead',owner_id:1,kind:'troop',house:'center',life:0,life_max:4});
const app=fs.readFileSync(path.join(root,'app.js'),'utf8');
vm.runInContext(app.slice(0,app.indexOf('function actionDetails(')),context);
vm.runInContext('currentView=view; renderMap(view)',context);
assert.equal(map.querySelectorAll('.unit-marker').length,25);
assert.equal(map.querySelectorAll('.unit-life').length,25);
assert.equal(map.querySelectorAll('img').length,25);
assert.ok(map.children.find(h=>h.dataset.house==='city_2').className.includes('curuna-house'));
assert.match(map.children.find(h=>h.dataset.house==='city_1').querySelector('.house-caption').textContent,/Ana.*dragoes.*3\/3/);
const marker=map.querySelector('.unit-marker'); marker.click();
assert.equal(document.getElementById('unitDetails').children[3].textContent,'Vida 2/4');
const group=el('details','group','action-group'); group.dataset.actionType='collect_resources'; group.open=true;
const summary=new Element('summary'), send=new Element('button'), input=new Element('input'); group.append(summary, input, send);
let sent=0; send.onclick=()=>sent++;
const game=el('section','game'); const save=new Element('button'); save.id='save'; game.appendChild(save);
let saved=0; save.onclick=()=>saved++;
const handoff=el('section','handoff'); handoff.hidden=true;
const reveal=new Element('button'); reveal.id='revealPlayer'; handoff.appendChild(reveal);
let revealed=0; reveal.onclick=()=>revealed++;
const press=(key, target=send, options={})=> { document.activeElement=target; const e={key,target,preventDefault(){this.prevented=true;},...options}; context.handleShortcut(e,document); return e; };
assert.ok(press('1',send,{altKey:true}).prevented); assert.equal(sent,1);
press('1',input); assert.equal(sent,1);
send.disabled=true; press('1',send,{altKey:true}); assert.equal(sent,1); send.disabled=false;
press('1',send,{altKey:true,repeat:true}); assert.equal(sent,1);
press('s',save,{altKey:true}); assert.equal(saved,1);
game.inert=true; press('s',save,{altKey:true}); assert.equal(saved,1); game.inert=false;
const dialog=el('dialog','dialog'); dialog.open=true;
press('s',save,{altKey:true}); assert.equal(saved,1); dialog.open=false;
handoff.hidden=false; press('s',save,{altKey:true}); assert.equal(saved,1);
press('p',reveal,{altKey:true}); assert.equal(revealed,1); handoff.hidden=true;
assert.ok(press('1',save).prevented); assert.equal(document.activeElement,input); assert.equal(sent,1);
assert.ok(press('@',save,{altKey:true,shiftKey:true,code:'Digit2'}).prevented);
assert.match(document.getElementById('rosterTitle').textContent,/Cidade 1/);
context.annotateShortcuts(); assert.match(send.title,/Alt\+1.*dentro desta ação/); assert.match(marker.title,/Enter\/Espaço/);
const css=fs.readFileSync(path.join(root,'map.css'),'utf8');
assert.ok(!/house-units\s*\{[^}]*display\s*:\s*none/.test(css));
assert.match(css,/hero img\{width:64px;height:64px/); assert.match(css,/unit-marker img\{[^}]*width:32px;height:32px/);
console.log('UI: presença de povos (8 combinações), Curruna, 25 unidades vivas, inspeção, relatórios públicos, SVGs e atalhos/contextos verificados.');
