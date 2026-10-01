const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('jessica/web/static/app.js', 'utf8');
const context = vm.createContext({
  catalog:{pacts:[{id:'vida_lider',name:'Ofereça a vida de um líder'}]},
  publicUnitNames:new Map(), unitName:u=>u.name || 'Tropa pequena',
  cardName:id=>id === 'K_H' ? 'Rei de Copas' : id,
  HOUSE_NAMES:{city_2:'Cidade 2 (Leste)', center:'Centro'},
});
vm.runInContext(source.slice(source.indexOf('function publicUnitName('), source.indexOf('function actionDetails(')),context);
vm.runInContext(source.slice(source.indexOf('function eventText('),source.indexOf('function renderEvents(')),context);
const view = {board:{units:[{id:'defender',name:'Tuza'}]},self:{hand:['SEGREDO']}};
const events = [
  {type:'public_state_changed',data:{changes:[{kind:'unit',before:{id:'attacker',name:'Arken'},after:null}]}},
  {type:'player_view_updated',data:{view:{board:{units:[{id:'hidden',name:'OCULTO'}]}}}},
];
context.rememberPublicUnitNames(view,events);
const event = data=>({type:'night_action_resolved',data});
assert.equal(context.eventText(event({action_type:'night_attack',attacker_unit_id:'attacker',target_type:'unit',target_id:'defender'})), 'Arken atacou Tuza.');
assert.equal(context.eventText(event({action_type:'night_attack',attacker_unit_id:'attacker',target_type:'city',target_id:'2'})), 'Arken atacou Cidade 2 (Leste).');
assert.equal(context.eventText(event({action_type:'night_pass',unit_id:'attacker'})), 'Arken não declarou ataque.');
assert.equal(context.eventText(event({action_type:'night_luide_move',unit_id:'defender',destination:'center'})), 'Tuza moveu para Centro na janela de Luide.');
assert.equal(context.eventText({type:'artifact_sold',data:{player_id:1,card_id:'K_H'}}), 'J1 vendeu Rei de Copas.');
assert.equal(context.eventText({type:'interaction_resolved',data:{player_id:1,action_type:'demon_pact',pact_id:'vida_lider'}}), 'J1 firmou um pacto: Ofereça a vida de um líder.');
assert.equal(context.eventText({type:'interaction_resolved',data:{player_id:1,action_type:'play_artifact',card_id:'K_H'}}), 'J1 jogou Rei de Copas.');
assert.match(context.eventText({type:'public_state_changed',turn:2,phase:'day',data:{from_turn:1,from_phase:'night',changes:[]}}), /T1 Noite → T2 Dia/);
assert.equal(context.phaseName('unknown'), 'unknown');
assert.equal(context.publicUnitName('hidden'), 'Unidade hidden');
assert.ok(!JSON.stringify([...context.publicUnitNames]).includes('SEGREDO'));
context.publicUnitNames.clear();
assert.equal(context.publicUnitName('attacker'), 'Unidade attacker');
assert.match(source,/"end_turn", "finish_night"/);
assert.match(fs.readFileSync('jessica/web/static/style.css','utf8'),/@media\(max-width:820px\)\{#game>\.toolbar\{position:static\}\}/);
console.log('UI: nomes públicos de unidades mortas, Bases e cartas; nenhuma leitura de projeções privadas.');
const focus = {focus(){this.focused=true;},scrollIntoView(options){this.options=options;}};
const nodes = {revealPlayer:{},game:{inert:true},handoff:{hidden:false},actions:{querySelector:()=>focus}};
const handoff = vm.createContext({$:id=>nodes[id],pendingPlayerId:2,playerId:1,
  refresh:async allowed=>{assert.equal(allowed,true);assert.equal(handoff.playerId,2);}});
vm.runInContext(source.slice(source.indexOf('$("revealPlayer").onclick'),source.indexOf('createSaveControls();')),handoff);
(async()=>{
  await nodes.revealPlayer.onclick();
  assert.equal(nodes.game.inert,false);
  assert.equal(nodes.handoff.hidden,true);
  assert.equal(handoff.pendingPlayerId,null);
  assert.equal(focus.focused,true);
  assert.equal(focus.options.block,'nearest');
  console.log('UI: troca de jogador libera a interface e foca a próxima decisão.');
})().catch(error=>{console.error(error);process.exitCode=1;});
