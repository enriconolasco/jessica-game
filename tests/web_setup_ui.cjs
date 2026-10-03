const assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm');
const source=fs.readFileSync('jessica/web/static/app.js','utf8');
class Element {
  constructor(tag){this.tag=tag;this.children=[];this.events={};this.textContent='';this.value='';}
  appendChild(child){child.parent=this;this.children.push(child);if(this.tag==='select'&&this.children.length===1)this.value=child.value;return child;}
  append(...children){children.forEach(child=>this.appendChild(child));}
  replaceChildren(){this.children=[];}
  setAttribute(){}
  addEventListener(type,fn){this.events[type]=fn;}
  showModal(){this.open=true;}
  close(){this.open=false;this.events.close?.();}
  remove(){this.parent.children=this.parent.children.filter(child=>child!==this);}
  focus(){}
  descendants(){return this.children.flatMap(child=>[child,...(child.descendants?.()||[])]);}
}
const body=new Element('body'); let calls=[];
const context=vm.createContext({Promise,document:{body,createElement:tag=>new Element(tag)},
  Option:function(text,value){this.textContent=text;this.value=value;},
  catalog:{peoples:[{id:'humanos',heroes:[{id:'miyamoto',name:'Miyamoto',life:4},{id:'besouro',name:'Besouro',life:4}]},{id:'anoes',heroes:[{id:'ori',name:'Ori',life:3}]}]},
  peopleName:id=>id,showHelp(){},api:async(path,options)=>{calls.push({path,payload:JSON.parse(options.body)});return {match_id:'started'};}
});
vm.runInContext(source.slice(source.indexOf('function chooseSecretHeroes('),source.indexOf('function showHelp(')),context);
const payload=()=>({players:[{name:'Ana',people:'humanos',hero_id:'preset'},{name:'Beto',people:'anoes',hero_id:'preset'}],seed:42,config:{}});
const dialog=()=>body.children[0];
const button=text=>dialog().descendants().find(e=>e.tag==='button'&&e.textContent.includes(text));
const text=()=>dialog().descendants().map(e=>e.textContent).join(' ');
(async()=>{
  const data=payload(), pending=context.chooseSecretHeroes(data);
  assert.equal(calls.length,0);assert.match(text(),/Ana: humanos.*Beto: anoes/);
  assert.equal(dialog().descendants().filter(e=>e.tag==='select').length,0);
  button('Sou Ana').onclick();
  let select=dialog().descendants().find(e=>e.tag==='select');select.value='besouro';
  await button('Confirmar meu').onclick();
  assert.equal(calls.length,0);assert.match(text(),/Passe o aparelho a Beto/);
  assert.ok(!text().includes('Besouro'));assert.equal(dialog().descendants().filter(e=>e.tag==='select').length,0);
  button('Sou Beto').onclick();await button('Confirmar meu').onclick();
  assert.equal((await pending).match_id,'started');assert.equal(calls.length,1);
  assert.deepEqual(calls[0].payload.players.map(p=>p.hero_id),['besouro','ori']);assert.equal(body.children.length,0);
  const cancelled=context.chooseSecretHeroes(payload());
  button('Sou Ana').onclick();await button('Confirmar meu').onclick();button('Cancelar').onclick();
  assert.equal(await cancelled,null);assert.equal(calls.length,1);assert.equal(body.children.length,0);
  const dead=payload();dead.players[1].people='mortos_vivos';
  const undead=context.chooseSecretHeroes(dead);button('Sou Ana').onclick();await button('Confirmar meu').onclick();
  button('Sou Beto').onclick();await button('Confirmar meu').onclick();await undead;
  assert.equal(calls[1].payload.players[1].hero_id,'');
  console.log('UI pré-jogo: povos públicos, passagem do aparelho, heróis secretos, cancelamento e uma única criação após todas as confirmações.');
})().catch(error=>{console.error(error);process.exitCode=1;});
