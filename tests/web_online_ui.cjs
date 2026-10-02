const assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm');
const {webcrypto}=require('node:crypto');
const source=fs.readFileSync('jessica/web/static/online.js','utf8');
const app=fs.readFileSync('jessica/web/static/app.js','utf8');
class Element {
  constructor(){this.children=[];this.hidden=false;this.value='';this.textContent='';}
  appendChild(child){this.children.push(child);if(this.children.length===1&&child.value!==undefined)this.value=child.value;}
  replaceChildren(){this.children=[];}
  get options(){return this.children;}
}
const stored=new Map([['jessica-online-v1',JSON.stringify({code:'ABCDEFG2',credential:'own-token'})]]);
let accepted=0, loseReply=true, commandIds=[];
const responses=new Map();
let gameRevision=10;
let releaseLobby, lobbyPosts=0;
const room={code:'ABCDEFG2',you:1,host_id:1,revision:10,status:'playing',players:[{player_id:1,name:'Ana',people:'humanos',hero_id:'miyamoto',ready:true},{player_id:2,name:'Beto',people:'orcs',hero_id:'arken',ready:true}]};
const catalog={peoples:[{id:'humanos',label:'Humanos',heroes:[{id:'miyamoto',name:'Miyamoto',description:'habilidade'}],passive:'passiva'},{id:'orcs',label:'Orcs',heroes:[{id:'arken',name:'Arken'}]}],heroes:[{id:'miyamoto',name:'Miyamoto'},{id:'arken',name:'Arken'}]};
const action={type:'end_turn',version:1,player_id:1,params:{}};
function client(withSocket=false, href='http://localhost:8767/?room=ABCDEFG2', sameOrigin=false){
  const nodes=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
  if(sameOrigin)node('onlineTransport').content='same-origin';
  let timer, cleared=false, reconnect, dialog=false, httpCalls=0;
  const sockets=[], listeners={};
  class FakeSocket {
    constructor(url){this.url=url;sockets.push(this);}
    send(text){this.sent=JSON.parse(text);}
    close(){this.onclose?.({code:1000});}
  }
  const context=vm.createContext({window:{addEventListener(){}}, URL, Uint8Array, crypto:webcrypto,
    sessionStorage:{getItem:k=>stored.get(k),setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},
    document:{getElementById:node,createElement:()=>new Element(),querySelector:()=>dialog?{}:null,hidden:false,addEventListener:(name,fn)=>{listeners[name]=fn;}},
    location:{href},Option:function(text,value){this.textContent=text;this.value=value;},
    setInterval:fn=>{timer=fn;return 1;},clearInterval:()=>{cleared=true;},setTimeout:fn=>{reconnect=fn;return 2;},clearTimeout(){},confirm:()=>false,
    matchId:null,playerId:9,currentView:null,pendingPlayerId:null,$:node,
    api:async()=>{throw new Error('Local endpoint must not be used');},showHelp(){},
    fetch:async(path,options)=>{
      httpCalls++;
      assert.equal(options.headers.Authorization,'Bearer own-token');
      assert.ok(!path.includes('player_id')&&!path.includes('own-token'));
      let result;
      if(path.endsWith('/ready')){
        lobbyPosts++;await new Promise(resolve=>{releaseLobby=resolve;});result={...room,revision:gameRevision};
      }else if(path.endsWith('/actions')){
        const command=JSON.parse(options.body); commandIds.push(command.command_id);
        if(!responses.has(command.command_id)){accepted++;gameRevision++;responses.set(command.command_id,{success:true,events:[],revision:gameRevision});}
        if(loseReply){loseReply=false;throw new Error('network lost after commit');}
        result=responses.get(command.command_id);
      }else if(path.endsWith('/snapshot')) result={revision:gameRevision,player_id:1,view:{active_player_id:2,self:{hand:['OWN_CARD']}},actions:[],events:[]};
      else result={...room,revision:gameRevision};
      return {ok:true,status:200,json:async()=>JSON.parse(JSON.stringify(result))};
    }
  });
  if(withSocket)context.WebSocket=FakeSocket;
  vm.runInContext(source,context);
  context.ONLINE=context.window.JessicaOnline;
  const begin=app.indexOf('async function refresh('),end=app.indexOf('  rememberPublicUnitNames(view, events);',begin);
  vm.runInContext(app.slice(begin,end)+'return {view,actions,events,playerId};\n}',context);
  return {context,node,poll:()=>timer(),cleared:()=>cleared,sockets, reconnect:()=>reconnect(), calls:()=>httpCalls,
    setDialog:value=>{dialog=value;},visible:()=>listeners.visibilitychange()};
}
(async()=>{
  const first=client();await first.context.ONLINE.boot(catalog);
  assert.equal(first.context.playerId,1);assert.equal(first.context.currentView.active_player_id,2);
  assert.equal(first.node('handoff').hidden,true);assert.equal(first.node('game').inert,false);
  assert.equal(first.node('start').hidden,true);
  assert.equal(first.node('onlineLink').value,'http://localhost:8767/?room=ABCDEFG2');
  assert.ok(!first.node('onlineLink').value.includes('own-token'));
  await assert.rejects(first.context.ONLINE.requestMatch('/matches/ABCDEFG2/actions',{method:'POST',body:JSON.stringify(action)}),/network lost/);
  assert.equal(first.node('onlineRetry').hidden,false);
  assert.ok(JSON.parse(stored.get('jessica-online-v1')).pending);
  await assert.rejects(first.context.ONLINE.requestMatch('/matches/ABCDEFG2/actions',{method:'POST',body:JSON.stringify(action)}),/pendente/);
  await first.node('onlineRetry').onclick();
  assert.equal(accepted,1);assert.equal(commandIds[0],commandIds[1]);
  assert.equal(first.node('onlineRetry').hidden,true);
  const reloaded=client();await reloaded.context.ONLINE.boot(catalog);
  assert.equal(reloaded.context.playerId,1);assert.equal(reloaded.context.matchId,'ABCDEFG2');
  await assert.rejects(reloaded.context.ONLINE.requestMatch('/matches/OTHER123/actions',{method:'POST',body:JSON.stringify(action)}),/indisponível/);
  await assert.rejects(reloaded.context.ONLINE.requestMatch('/matches/ABCDEFG2/export',{}),/indisponível/);
  const updating=reloaded.node('onlineReady').onclick();
  assert.equal(reloaded.node('onlineReady').disabled,true);
  assert.equal(reloaded.node('onlineSelect').disabled,true);
  await reloaded.node('onlineReady').onclick();assert.equal(lobbyPosts,1);
  releaseLobby();await updating;assert.equal(reloaded.node('onlineReady').disabled,false);
  const live=client(true);await live.context.ONLINE.boot(catalog);
  const ws=live.sockets[0];assert.equal(ws.url,'ws://localhost:8768/updates');ws.onopen();
  assert.deepEqual(ws.sent,{version:1,code:'ABCDEFG2',credential:'own-token'});
  ws.onmessage({data:JSON.stringify({type:'room_changed',version:1,revision:gameRevision})});
  await new Promise(setImmediate);
  const calls=live.calls();live.poll();assert.equal(live.calls(),calls);
  live.setDialog(true);gameRevision++;
  ws.onmessage({data:JSON.stringify({type:'room_changed',version:1,revision:gameRevision})});
  assert.equal(live.calls(),calls);live.setDialog(false);live.poll();await new Promise(setImmediate);
  assert.ok(live.calls()>calls);
  ws.onclose({code:1006});live.reconnect();
  assert.equal(live.sockets.length,2);live.sockets[1].onopen();assert.deepEqual(live.sockets[1].sent,ws.sent);
  const lan=client(true,'http://192.168.1.10:8767/?room=ABCDEFG2');await lan.context.ONLINE.boot(catalog);
  assert.equal(lan.sockets[0].url,'ws://192.168.1.10:8768/updates');
  assert.equal(lan.node('onlineLink').value,'http://192.168.1.10:8767/?room=ABCDEFG2');
  for(const origin of ['https://jessica.example','https://jessica.example:8443']){
    const secure=client(true,origin+'/?room=ABCDEFG2',true);await secure.context.ONLINE.boot(catalog);
    assert.equal(secure.sockets[0].url,origin.replace('https:','wss:')+'/updates');
    assert.equal(secure.node('onlineLink').value,origin+'/?room=ABCDEFG2');
    assert.ok(!secure.sockets[0].url.includes('own-token'));
    secure.sockets[0].onopen();assert.deepEqual(secure.sockets[0].sent,ws.sent);
  }
  console.log('Online UI: identidade fixa, sem handoff, convite sem credencial, retorno após reload, reenvio do mesmo comando e isolamento de rotas locais verificados.');
})().catch(error=>{console.error(error);process.exitCode=1;});
