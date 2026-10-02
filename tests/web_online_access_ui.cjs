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
function client({tab=new Map(), remembered=new Map(), href='http://localhost:8767/', blocked=false, tabBlocked=false, backend}={}) {
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
    sessionStorage:storage(tab,tabBlocked),localStorage:storage(remembered,blocked),
    document:{getElementById:node,createElement:()=>({}),querySelector:()=>null,hidden:false,addEventListener(){}},
    location:{href,reload:()=>{reloaded=true;}},Option:function(text,value){this.textContent=text;this.value=value;},
    setInterval:()=>1,clearInterval(){},setTimeout:()=>2,clearTimeout(){},confirm:()=>permission,
    matchId:null,showHelp(){},fetch:async(path,options)=>{
      calls.push({path,options});
      assert.ok(!path.includes(access.credential)&&!path.includes('credential=')&&!path.includes('player_id'));
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

  for(const raw of ('bad json', JSON.stringify({code:'<script>',credential:access.credential}), JSON.stringify({code:22222222,credential:access.credential}), JSON.stringify({...access,pending:{command_id:'x',revision:-1,action}}), JSON.stringify({...access,rotation:{credential:'invalid'}}))) {
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
  const overload=[];
  const results=new Map(), ids=[];
  const pendingStorage=new Map([[REMEMBER,JSON.stringify(access)]]);
  const backend=async(path,options)=>{
    if(path.endsWith('/actions')) {
      const command=JSON.parse(options.body);ids.push(command.command_id);
      if(overload.length){const status=overload.shift();return {ok:false,status,json:async()=>({error:'Servidor ocupado'})};}
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
  overload.push(429,503);
  for(let index=0;index<2;index++) {
    await resumedPending.node('onlineRetry').onclick();
    assert.equal(JSON.parse(pendingStorage.get(REMEMBER)).pending.command_id,ids[0]);
    assert.equal(resumedPending.node('onlineRetry').hidden,false);
  }
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
  function rotatingBackend(tab, lose=false, offlineAfterCommit=false) {
    let token=access.credential, mutations=0, revision=10, offline=false;
    return {get token(){return token;},get mutations(){return mutations;},restore(){offline=false;},request:async(path,options)=>{
      if(offline)throw new Error('offline');
      if(options.headers.Authorization!==`Bearer ${token}`)return {ok:false,status:403,json:async()=>({error:'Revogado'})};
      if(path.endsWith('/credential')) {
        const candidate=JSON.parse(options.body).credential;
        assert.match(candidate,/^[a-f0-9]{64}$/);
        assert.equal(JSON.parse(tab.get(KEY)).rotation.credential,candidate,'candidate must be saved before POST');
        if(candidate!==token){token=candidate;mutations++;revision++;}
        if(lose){lose=false;offline=offlineAfterCommit;throw new Error('lost rotation reply');}
      }
      return reply(path.endsWith('/snapshot')?{revision,player_id:2,view:{},actions:[],events:[]}:{...room,revision});
    }};
  }
  const rotationTab=new Map([[KEY,JSON.stringify(access)]]), rotationCopy=new Map([[REMEMBER,JSON.stringify(access)]]);
  const rotationServer=rotatingBackend(rotationTab,true);
  const rotating=client({tab:rotationTab,remembered:rotationCopy,backend:rotationServer.request});
  const sockets=[];
  rotating.context.WebSocket=class {
    constructor(url){this.url=url;sockets.push(this);}
    send(packet){this.packet=JSON.parse(packet);}
    close(){this.onclose?.({code:1000});}
  };
  await rotating.boot();sockets[0].onopen();
  rotating.setPermission(false);await rotating.node('onlineRotate').onclick();assert.equal(rotationServer.mutations,0);
  rotating.setPermission(true);await rotating.node('onlineRotate').onclick();
  assert.equal(rotationServer.mutations,1,rotating.node('onlineMessage').textContent + JSON.stringify(rotating.calls.map(call=>call.path)));assert.equal(rotating.context.lastView.player_id,2);
  assert.equal(JSON.parse(rotationTab.get(KEY)).credential,rotationServer.token);
  assert.equal(JSON.parse(rotationCopy.get(REMEMBER)).credential,rotationServer.token);
  assert.equal(JSON.parse(rotationTab.get(KEY)).rotation,undefined);
  assert.equal(sockets.length,2);sockets[1].onopen();assert.equal(sockets[1].packet.credential,rotationServer.token);
  assert.ok(!rotating.node('onlineLink').value.includes(rotationServer.token));

  const stagedTab=new Map([[KEY,JSON.stringify(access)]]), stagedCopy=new Map([[REMEMBER,JSON.stringify(access)]]);
  const stagedServer=rotatingBackend(stagedTab,true,true);
  const staged=client({tab:stagedTab,remembered:stagedCopy,backend:stagedServer.request});await staged.boot();
  await staged.node('onlineRotate').onclick();
  assert.equal(stagedServer.mutations,1);assert.ok(JSON.parse(stagedCopy.get(REMEMBER)).rotation);
  assert.equal(staged.node('onlineRotate').textContent,'Confirmar troca de acesso pendente');
  await assert.rejects(staged.context.window.JessicaOnline.requestMatch('/matches/ABCDEFG2/actions',{method:'POST',body:JSON.stringify(action)}),/troca de acesso/);
  stagedServer.restore();
  const stageRecovered=client({remembered:stagedCopy,backend:stagedServer.request});await stageRecovered.boot();
  assert.equal(stageRecovered.context.lastView.player_id,2);assert.equal(stagedServer.mutations,1);
  assert.equal(JSON.parse(stagedCopy.get(REMEMBER)).credential,stagedServer.token);

  const retryTab=new Map([[KEY,JSON.stringify(access)]]), retryServer=rotatingBackend(retryTab);
  let failWrite=true;
  const retryRotation=client({tab:retryTab,backend:(path,options)=>{
    if(path.endsWith('/credential')&&failWrite){failWrite=false;return {ok:false,status:503,json:async()=>({error:'Falha de disco'})};}
    return retryServer.request(path,options);
  }});
  await retryRotation.boot();await retryRotation.node('onlineRotate').onclick();
  assert.equal(retryServer.mutations,0);const preservedCandidate=JSON.parse(retryTab.get(KEY)).rotation.credential;
  await retryRotation.node('onlineRotate').onclick();
  assert.equal(retryServer.mutations,1);assert.equal(retryServer.token,preservedCandidate);

  const refusedRotation=client({tab:new Map([[KEY,JSON.stringify(access)]]),tabBlocked:true});await refusedRotation.boot();
  await refusedRotation.node('onlineRotate').onclick();assert.equal(refusedRotation.calls.filter(call=>call.path.endsWith('/credential')).length,0);
  assert.ok(refusedRotation.node('onlineMessage').textContent.includes('Acesso não trocado'));
  const refusedCopyRotation=client({tab:new Map([[KEY,JSON.stringify(access)]]),remembered:new Map([[REMEMBER,JSON.stringify(access)]]),blocked:true});await refusedCopyRotation.boot();
  await refusedCopyRotation.node('onlineRotate').onclick();assert.equal(refusedCopyRotation.calls.filter(call=>call.path.endsWith('/credential')).length,0);
  const pendingRotation=client({tab:new Map([[KEY,JSON.stringify({...access,pending:{command_id:'existing',revision:10,action}})]])});await pendingRotation.boot();
  await pendingRotation.node('onlineRotate').onclick();assert.equal(pendingRotation.calls.filter(call=>call.path.endsWith('/credential')).length,0);
  assert.ok(pendingRotation.node('onlineMessage').textContent.includes('comando pendente'));
  console.log('Online revogação: cancelamento, gravação prévia, identidade fixa, resposta perdida, recuperação após fechar, bloqueio de ações/armazenamento e reconexão WS verificados.');
  console.log('Online acesso: opt-in, retorno após fechar aba, validação remota, convites sem credencial, pendência deduplicada, substituição/limpeza e armazenamento bloqueado verificados.');
})().catch(error=>{console.error(error);process.exitCode=1;});
