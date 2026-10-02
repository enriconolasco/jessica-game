const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const source = fs.readFileSync('jessica/web/static/online.js', 'utf8');
const KEY = 'jessica-online-v1', REMEMBER = 'jessica-online-remembered-v1';
const access = {code:'ABCDEFG2', credential:'personal-token'};
const catalog = {peoples:[{id:'humanos',label:'Humanos',heroes:[{id:'miyamoto',name:'Miyamoto'}]}],heroes:[]};
const room = {version:1,code:access.code,revision:10,you:2,host_id:1,status:'playing',players:[{player_id:2,name:'Ana',people:'humanos',hero_id:'miyamoto',ready:true}]};
const action = {type:'end_turn',version:1,player_id:2,params:{}};
const storage = (map, blocked=false) => ({
  getItem:key=>map.get(key) ?? null,
  setItem:(key,value)=>{if(blocked)throw new Error('blocked');map.set(key,value);},
  removeItem:key=>{if(blocked)throw new Error('blocked');map.delete(key);}
});
function client({tab=new Map(), remembered=new Map(), href='http://localhost:8767/', blocked=false, backend}={}) {
  const nodes=new Map(), events={}, calls=[];
  let permission=true, reloaded=false;
  const node=id=>{
    if(!nodes.has(id))nodes.set(id,{hidden:false,checked:false,value:'',children:[],textContent:'',
      appendChild(child){this.children.push(child);if(this.children.length===1)this.value=child.value;},
      replaceChildren(){this.children=[];},get options(){return this.children;}});
    return nodes.get(id);
  };
  const context=vm.createContext({
    window:{addEventListener:(name,fn)=>{events[name]=fn;}},URL,Uint8Array,crypto:webcrypto,
    sessionStorage:storage(tab),localStorage:storage(remembered,blocked),
    document:{getElementById:node,createElement:()=>({}),querySelector:()=>null,hidden:false,addEventListener(){}},
    location:{href,reload:()=>{reloaded=true;}},Option:function(text,value){this.textContent=text;this.value=value;},
    setInterval:()=>1,clearInterval(){},setTimeout:()=>2,clearTimeout(){},confirm:()=>permission,
    matchId:null,showHelp(){},fetch:async(path,options)=>{
      calls.push({path,options});
      assert.ok(!path.includes(access.credential)&&!path.includes('credential')&&!path.includes('player_id'));
      if(backend)return backend(path,options);
      assert.equal(options.headers.Authorization,`Bearer ${access.credential}`);
      const result=path.endsWith('/snapshot')?{revision:10,player_id:2,view:{active_player_id:1},actions:[],events:[]}:room;
      return {ok:true,status:200,json:async()=>result};
    }
  });
  vm.runInContext(source,context);
  context.refresh=async()=>{context.lastView=await context.window.JessicaOnline.snapshot();};
  return {context,node,tab,remembered,calls,events,reloaded:()=>reloaded,setPermission:value=>{permission=value;},boot:()=>context.window.JessicaOnline.boot(catalog)};
}
const reply = result => ({ok:true,status:200,json:async()=>result});
(async()=>{
  const persistent=new Map(), tab=new Map([[KEY,JSON.stringify(access)]]);
  const initial=client({tab,remembered:persistent});await initial.boot();
  assert.equal(initial.node('onlineRemember').checked,false);assert.equal(persistent.size,0);
  const closedWithoutOptIn=client({remembered:persistent});await closedWithoutOptIn.boot();
  assert.equal(closedWithoutOptIn.calls.length,0);
  initial.node('onlineRemember').checked=true;initial.node('onlineRemember').onchange();
  assert.deepEqual(JSON.parse(persistent.get(REMEMBER)),access);
  const restored=client({remembered:persistent});await restored.boot();
  assert.equal(restored.context.lastView.player_id,2);
  assert.equal(restored.context.lastView.view.active_player_id,1);
  assert.equal(restored.node('onlineRemember').checked,true);
  assert.equal(JSON.parse(restored.tab.get(KEY)).credential,access.credential);
  assert.ok(!restored.node('onlineLink').value.includes(access.credential));
  restored.node('onlineRemember').checked=false;restored.node('onlineRemember').onchange();
  assert.equal(persistent.size,0);assert.ok(restored.tab.has(KEY));

  for(const raw of ('bad json', JSON.stringify({code:'<script>',credential:access.credential}), JSON.stringify({code:22222222,credential:access.credential}), JSON.stringify({...access,pending:{command_id:'x',revision:-1,action}}))) {
    const bad=new Map([[REMEMBER,raw]]), view=client({remembered:bad});await view.boot();
    assert.equal(view.calls.length,0);assert.equal(view.tab.size,0);assert.equal(bad.get(REMEMBER),raw);
  }
  let denial=true;
  const preserved=new Map([[REMEMBER,JSON.stringify(access)]]);
  const refused=client({remembered:preserved,backend:(path,options)=>{
    assert.equal(options.headers.Authorization,`Bearer ${access.credential}`);
    if(denial)return {ok:false,status:403,json:async()=>({error:'Sessão recusada'})};
    return reply(path.endsWith('/snapshot')?{revision:10,player_id:2,view:{},actions:[],events:[]}:room);
  }});
  await refused.boot();assert.equal(refused.tab.size,0);assert.equal(refused.node('onlineRemembered').hidden,false);
  assert.ok(refused.node('onlineMessage').textContent.includes('preservado'));assert.ok(preserved.has(REMEMBER));
  denial=false;await refused.node('onlineResume').onclick();assert.equal(refused.context.lastView.player_id,2);

  const invitation=client({remembered:new Map([[REMEMBER,JSON.stringify(access)]]),href:'http://localhost:8767/?room=OTHER222'});
  await invitation.boot();assert.equal(invitation.calls.length,0);assert.equal(invitation.node('onlineCode').value,'OTHER222');
  await invitation.node('onlineResume').onclick();assert.equal(invitation.context.lastView.player_id,2);

  let accepted=0, loseReply=true, revision=10;
  const results=new Map(), ids=[];
  const pendingStorage=new Map([[REMEMBER,JSON.stringify(access)]]);
  const backend=async(path,options)=>{
    if(path.endsWith('/actions')) {
      const command=JSON.parse(options.body);ids.push(command.command_id);
      if(!results.has(command.command_id)){accepted++;revision++;results.set(command.command_id,{success:true,revision,events:[]});}
      if(loseReply){loseReply=false;throw new Error('lost response');}
      return reply(results.get(command.command_id));
    }
    return reply(path.endsWith('/snapshot')?{revision,player_id:2,view:{},actions:[],events:[]}:{...room,revision});
  };
  const sending=client({remembered:pendingStorage,backend});await sending.boot();
  await assert.rejects(sending.context.window.JessicaOnline.requestMatch('/matches/ABCDEFG2/actions',{method:'POST',body:JSON.stringify(action)}),/lost response/);
  assert.ok(JSON.parse(pendingStorage.get(REMEMBER)).pending);
  const staleTab=client({tab:new Map([[KEY,JSON.stringify(access)]]),remembered:pendingStorage,backend});await staleTab.boot();
  assert.equal(JSON.parse(staleTab.tab.get(KEY)).pending.command_id,ids[0]);
  assert.equal(JSON.parse(pendingStorage.get(REMEMBER)).pending.command_id,ids[0]);
  const resumedPending=client({remembered:pendingStorage,backend});await resumedPending.boot();
  assert.equal(resumedPending.node('onlineRetry').hidden,false);
  await assert.rejects(resumedPending.context.window.JessicaOnline.requestMatch('/matches/ABCDEFG2/actions',{method:'POST',body:JSON.stringify(action)}),/pendente/);
  await resumedPending.node('onlineRetry').onclick();
  assert.equal(accepted,1);assert.equal(ids[0],ids[1]);assert.equal(JSON.parse(pendingStorage.get(REMEMBER)).pending,undefined);

  const other={code:'OTHER222',credential:'other-token'};
  const shared=new Map([[REMEMBER,JSON.stringify(other)]]);
  const replacement=client({tab:new Map([[KEY,JSON.stringify(access)]]),remembered:shared});await replacement.boot();
  replacement.setPermission(false);replacement.node('onlineRemember').checked=true;replacement.node('onlineRemember').onchange();
  assert.deepEqual(JSON.parse(shared.get(REMEMBER)),other);
  replacement.setPermission(true);replacement.node('onlineRemember').checked=true;replacement.node('onlineRemember').onchange();
  assert.deepEqual(JSON.parse(shared.get(REMEMBER)),access);
  shared.delete(REMEMBER);replacement.events.storage({key:REMEMBER});assert.equal(replacement.node('onlineRemember').checked,false);
  await replacement.context.window.JessicaOnline.snapshot();assert.ok(replacement.tab.has(KEY));
  const blocked=client({tab:new Map([[KEY,JSON.stringify(access)]]),blocked:true});await blocked.boot();
  blocked.node('onlineRemember').checked=true;blocked.node('onlineRemember').onchange();
  assert.equal(blocked.node('onlineRemember').checked,false);assert.ok(blocked.node('onlineMessage').textContent.includes('Mantenha esta aba'));
  assert.equal(blocked.context.lastView.player_id,2);
  const blockedRemoval=client({tab:new Map([[KEY,JSON.stringify(access)]]),remembered:new Map([[REMEMBER,JSON.stringify(access)]]),blocked:true});await blockedRemoval.boot();
  blockedRemoval.node('onlineRemember').checked=false;blockedRemoval.node('onlineRemember').onchange();
  assert.equal(blockedRemoval.node('onlineRemember').checked,true);assert.ok(blockedRemoval.remembered.has(REMEMBER));
  const blockedRead=client({tab:new Map([[KEY,JSON.stringify(access)]])});
  blockedRead.context.localStorage.getItem=()=>{throw new Error('blocked');};await blockedRead.boot();
  assert.equal(blockedRead.context.lastView.player_id,2);assert.equal(blockedRead.node('onlineRemember').checked,false);
  const reset=client({tab:new Map([[KEY,JSON.stringify(access)]]),remembered:new Map([[REMEMBER,JSON.stringify(access)]])});await reset.boot();
  reset.node('onlineReset').onclick();assert.equal(reset.tab.size,0);assert.equal(reset.remembered.size,0);assert.equal(reset.reloaded(),true);
  const resetOther=client({tab:new Map([[KEY,JSON.stringify(access)]]),remembered:new Map([[REMEMBER,JSON.stringify(other)]])});await resetOther.boot();
  resetOther.node('onlineReset').onclick();assert.deepEqual(JSON.parse(resetOther.remembered.get(REMEMBER)),other);
  console.log('Online acesso: opt-in, retorno após fechar aba, validação remota, convites sem credencial, pendência deduplicada, substituição/limpeza e armazenamento bloqueado verificados.');
})().catch(error=>{console.error(error);process.exitCode=1;});
