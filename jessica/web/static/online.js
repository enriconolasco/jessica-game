window.JessicaOnline = (() => {
  const KEY = "jessica-online-v1";
  const REMEMBER_KEY = "jessica-online-remembered-v1";
  const node = id => document.getElementById(id);
  let session = null, catalog = null, room = null, revision = -1, busy = false, timer = null, disconnected = false;
  let cachedSnapshot = null, operationBusy = false;
  let socket = null, socketReady = false, reconnectTimer = null, reconnectDelay = 1000, stopped = false, needsSync = false;
  function readAccess(storage, key) {
    try {
      const raw = storage.getItem(key);
      if (!raw || raw.length > 131072) return null;
      const saved = JSON.parse(raw);
      if (!saved || typeof saved.code !== "string" || !/^[A-Z2-9]{8}$/.test(saved.code) || typeof saved.credential !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(saved.credential)) return null;
      if (saved.pending && (typeof saved.pending.command_id !== "string" || !/^[A-Za-z0-9_-]{1,64}$/.test(saved.pending.command_id) || !Number.isSafeInteger(saved.pending.revision) || saved.pending.revision < 0 || !saved.pending.action || typeof saved.pending.action !== "object" || Array.isArray(saved.pending.action))) return null;
      return {code:saved.code, credential:saved.credential, ...(saved.pending ? {pending:saved.pending} : {})};
    } catch (_) { return null; }
  }
  function remembered() {
    try { return readAccess(localStorage, REMEMBER_KEY); } catch (_) { return null; }
  }
  const sameAccess = (a, b) => !!a && !!b && a.code === b.code && a.credential === b.credential;
  function renderRemembered() {
    const saved = remembered();
    node("onlineRemember").checked = sameAccess(saved, session);
    node("onlineRemembered").hidden = !!session || !saved;
    node("onlineRememberedLabel").textContent = saved ? `Acesso lembrado neste navegador: sala ${saved.code}.` : "";
  }
  try { session = readAccess(sessionStorage, KEY); } catch (_) {}
  function store(settledCommandId = null) {
    const saved = remembered();
    if (sameAccess(saved, session) && saved.pending && !session.pending && saved.pending.command_id !== settledCommandId) session.pending = saved.pending;
    try {
      if (session) sessionStorage.setItem(KEY, JSON.stringify(session));
      else sessionStorage.removeItem(KEY);
    } catch (_) { node("onlineMessage").textContent = "Armazenamento indisponível: esta sessão não poderá voltar após recarregar."; }
    if (sameAccess(remembered(), session)) {
      try { localStorage.setItem(REMEMBER_KEY, JSON.stringify(session)); }
      catch (_) { node("onlineMessage").textContent = "Não foi possível atualizar o acesso lembrado. Não feche a aba enquanto houver comando pendente."; }
    }
    renderRemembered();
    node("onlineRetry").hidden = !session?.pending;
  }
  async function request(path, body, credential = session?.credential) {
    const response = await fetch(path, {method: body === undefined ? "GET" : "POST", cache:"no-store",
      headers:{"Content-Type":"application/json", ...(credential ? {Authorization:`Bearer ${credential}`} : {})},
      ...(body === undefined ? {} : {body:JSON.stringify(body)})});
    const result = await response.json();
    if (!response.ok) {
      const error = new Error(result.error?.message || result.error || "Requisição rejeitada.");
      error.status = response.status; throw error;
    }
    return result;
  }
  const path = resource => `/rooms/${session.code}${resource ? `/${resource}` : ""}`;
  function commandId() {
    return Array.from(crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2,"0")).join("");
  }
  async function sendPending() {
    if (!session?.pending) throw new Error("Não há comando pendente.");
    busy = true;
    const pendingId = session.pending.command_id;
    try {
      const result = await request(path("actions"), session.pending);
      delete session.pending; store(pendingId); return result;
    } catch (error) {
      if (error.status) { delete session.pending; store(pendingId); }
      else node("onlineMessage").textContent = "Resultado não confirmado. Reenvie o comando pendente; ele não será executado duas vezes.";
      throw error;
    } finally { busy = false; syncIfNeeded(); }
  }
  async function requestMatch(url, options) {
    if (!session) throw new Error("Entre em uma sala primeiro.");
    const match = /^\/matches\/([^/]+)\/(actions|dream-preview)$/.exec(url);
    if (!match || match[1] !== session.code || options.method !== "POST") throw new Error("Operação local indisponível no online.");
    const body = JSON.parse(options.body);
    if (match[2] === "dream-preview") return request(path("dream-preview"), body);
    store();
    if (session.pending) throw new Error("Verifique o comando pendente antes de enviar outra ação.");
    session.pending = {command_id:commandId(), revision, action:body};
    store(); return sendPending();
  }
  async function snapshot() {
    const result = await request(path("snapshot"));
    if (result.revision < revision && cachedSnapshot) return cachedSnapshot;
    revision = result.revision;
    cachedSnapshot = result;
    node("onlineConnection").textContent = `Conectado · ${socketReady ? "tempo real" : "HTTP"} · revisão ${revision} · você controla J${result.player_id}`;
    return result;
  }
  function heroOptions(selected = "") {
    const people = catalog.peoples.find(p => p.id === node("onlinePeople").value);
    node("onlineHero").replaceChildren();
    if (people?.id === "mortos_vivos") node("onlineHero").appendChild(new Option("Escolha durante a partida", ""));
    else (people?.heroes || []).forEach(h => node("onlineHero").appendChild(new Option(h.name, h.id)));
    if ([...node("onlineHero").options].some(o => o.value === selected)) node("onlineHero").value = selected;
    node("onlineHero").disabled = people?.id === "mortos_vivos";
    choiceHelp();
  }
  function choiceHelp() {
    const people = catalog.peoples.find(p => p.id === node("onlinePeople").value);
    const hero = people?.heroes.find(h => h.id === node("onlineHero").value);
    node("onlineChoiceHelp").textContent = `${people?.passive || ""}${hero ? ` · ${hero.name}: ${hero.description}` : ""}`;
  }
  function renderRoom(next) {
    if (room && next.revision < room.revision) return;
    const previousOwn = room?.players.find(p => p.player_id === room.you);
    room = next;
    node("onlineEntry").hidden = true; node("onlineRoom").hidden = false; node("onlineReset").hidden = false;
    node("onlineIdentity").textContent = `Sala ${room.code} · Você: J${room.you} ${room.players.find(p => p.player_id === room.you).name}`;
    const link = new URL(location.href); link.search = `?room=${room.code}`; link.hash = "";
    node("onlineLink").value = link.href;
    node("onlinePlayers").replaceChildren();
    room.players.forEach(p => {
      const line = document.createElement("li");
      const people = catalog.peoples.find(item => item.id === p.people);
      const hero = catalog.heroes.find(item => item.id === p.hero_id);
      line.textContent = `J${p.player_id} ${p.name}${p.player_id === room.you ? " (você)" : ""} · ${people?.label || "povo não escolhido"}${hero ? ` · ${hero.name}` : ""} · ${p.ready ? "pronto" : "aguardando"}`;
      node("onlinePlayers").appendChild(line);
    });
    const own = room.players.find(p => p.player_id === room.you);
    for (const option of node("onlinePeople").options) option.disabled = room.players.some(p => p.player_id !== room.you && p.people === option.value);
    if (own.people && (own.people !== previousOwn?.people || own.hero_id !== previousOwn?.hero_id)) {
      node("onlinePeople").value = own.people; heroOptions(own.hero_id);
    }
    node("onlinePeople").disabled = own.ready;
    node("onlineHero").disabled = own.ready || node("onlinePeople").value === "mortos_vivos";
    node("onlineSelect").disabled = own.ready || operationBusy;
    node("onlineReady").disabled = !own.people || operationBusy;
    node("onlineReady").textContent = own.ready ? "Ainda não estou pronto" : "Estou pronto";
    node("onlineStart").hidden = room.you !== room.host_id;
    node("onlineStart").disabled = operationBusy || room.players.length !== 4 || !room.players.every(p => p.ready);
    node("onlineChoice").hidden = room.status === "playing";
  }
  async function poll() {
    if (!session || busy) return;
    needsSync = false;
    busy = true;
    try {
      const next = await request(path());
      if (room?.revision !== next.revision || disconnected) renderRoom(next);
      if (next.status === "playing" && (revision !== next.revision || disconnected)) {
        matchId = session.code; node("game").hidden = false;
        await refresh();
      }
      disconnected = false;
      if (next.status === "lobby") node("onlineConnection").textContent = `Conectado · ${socketReady ? "tempo real" : "HTTP"} · ${next.players.length}/4 participantes`;
    } catch (error) {
      disconnected = true;
      node("onlineConnection").textContent = "Conexão interrompida — tentando retornar, sem trocar de jogador.";
      if (error.status === 401 || error.status === 403 || error.status === 404) {
        node("game").hidden = true;
        node("onlineMessage").textContent = "Sessão indisponível. Confira se este servidor usa o armazenamento correto e se a credencial foi preservada nesta aba.";
        clearInterval(timer);
        stopUpdates();
      }
    } finally { busy = false; syncIfNeeded(); }
  }
  function syncIfNeeded() {
    if (needsSync && !busy && !document.hidden && !document.querySelector("dialog[open]")) void poll();
  }
  function stopUpdates() {
    stopped = true; socketReady = false;
    clearTimeout(reconnectTimer);
    if (socket) socket.close();
    socket = null;
  }
  function connectUpdates() {
    if (!session || stopped || socket || typeof WebSocket === "undefined") return;
    const url = new URL(location.href); url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.port = String(Number(url.port || (url.protocol === "wss:" ? 443 : 80)) + 1); url.pathname = "/updates"; url.search = ""; url.hash = "";
    const connection = new WebSocket(url.href); socket = connection;
    connection.onopen = () => { if (session && !stopped) connection.send(JSON.stringify({version:1, code:session.code, credential:session.credential})); else connection.close(); };
    connection.onmessage = event => {
      if (socket !== connection || stopped) return;
      let message; try { message = JSON.parse(event.data); } catch (_) { connection.close(); return; }
      if (message.type !== "room_changed" || message.version !== 1 || !Number.isSafeInteger(message.revision) || message.revision < 0) {
        connection.close(); return;
      }
      const wasReady = socketReady; socketReady = true; reconnectDelay = 1000;
      if (!wasReady) disconnected = true;
      if (!wasReady || message.revision > (room?.revision ?? -1)) { needsSync = true; syncIfNeeded(); }
    };
    connection.onclose = event => {
      if (socket !== connection) return;
      socket = null; socketReady = false;
      node("onlineConnection").textContent = event.code === 1008 ? `Canal em tempo real recusado: ${event.reason || "protocolo inválido"}. HTTP continua ativo.` : "Tempo real interrompido — HTTP continua ativo; reconectando sem trocar de jogador.";
      if (!stopped && session && event.code !== 1008) {
        reconnectTimer = setTimeout(connectUpdates, reconnectDelay);
        reconnectDelay = Math.min(15000, reconnectDelay * 2);
      }
    };
  }
  async function operation(resource, body) {
    if (operationBusy) return;
    operationBusy = true;
    ["onlineCreate", "onlineJoin", "onlineSelect", "onlineReady", "onlineStart"].forEach(id => { node(id).disabled = true; });
    node("onlineMessage").textContent = "";
    try {
      if (resource === "create" || resource === "join") {
        const code = node("onlineCode").value.trim().toUpperCase();
        const result = await request(resource === "create" ? "/rooms" : `/rooms/${encodeURIComponent(code)}/join`, body);
        session = {code:result.room.code, credential:result.credential}; store(); renderRoom(result.room);
      } else renderRoom(await request(path(resource), body));
      await poll();
      connectUpdates();
    } catch (error) { node("onlineMessage").textContent = error.message; }
    finally {
      operationBusy = false;
      node("onlineCreate").disabled = node("onlineJoin").disabled = false;
      if (room) renderRoom(room);
    }
  }
  function forgetRemembered() {
    try { localStorage.removeItem(REMEMBER_KEY); renderRemembered(); return true; }
    catch (_) { node("onlineMessage").textContent = "Não foi possível esquecer o acesso. Confira as permissões de armazenamento do navegador."; renderRemembered(); return false; }
  }
  async function resumeRemembered() {
    const saved = remembered();
    if (session || !saved || operationBusy) return;
    operationBusy = true;
    node("onlineResume").disabled = true;
    node("onlineCreate").disabled = node("onlineJoin").disabled = true;
    try {
      const next = await request(`/rooms/${saved.code}`, undefined, saved.credential);
      session = saved; store(); renderRoom(next);
      await poll(); stopped = false; connectUpdates();
      node("onlineMessage").textContent = saved.pending ? "Acesso retomado. Verifique o comando pendente antes de enviar outra ação." : "Acesso retomado ao mesmo jogador.";
    } catch (error) { node("onlineMessage").textContent = `Não foi possível retomar: ${error.message} Confira o endereço e o banco do servidor; o acesso lembrado foi preservado.`; }
    finally {
      operationBusy = false;
      node("onlineResume").disabled = false;
      node("onlineCreate").disabled = node("onlineJoin").disabled = false;
      if (room) renderRoom(room);
    }
  }
  async function boot(data) {
    catalog = data;
    node("start").hidden = true;
    catalog.peoples.forEach(p => node("onlinePeople").appendChild(new Option(p.label, p.id)));
    heroOptions();
    node("onlinePeople").onchange = () => heroOptions();
    node("onlineHero").onchange = choiceHelp;
    node("onlineRules").onclick = () => showHelp();
    node("onlineCreate").onclick = () => operation("create", {name:node("onlineName").value});
    node("onlineJoin").onclick = () => operation("join", {name:node("onlineName").value});
    node("onlineSelect").onclick = () => operation("select", {people:node("onlinePeople").value, hero_id:node("onlineHero").value});
    node("onlineReady").onclick = () => operation("ready", {ready:!room.players.find(p => p.player_id === room.you).ready});
    node("onlineStart").onclick = () => operation("start", {});
    node("onlineResume").onclick = resumeRemembered;
    node("onlineForget").onclick = () => {
      if (confirm("Esquecer o acesso lembrado? Isso não libera sua vaga nem revoga outras abas.")) forgetRemembered();
    };
    node("onlineRemember").onchange = () => {
      if (!session) { renderRemembered(); return; }
      if (!node("onlineRemember").checked) { forgetRemembered(); return; }
      const saved = remembered();
      if (saved && !sameAccess(saved, session) && !confirm(`Substituir o acesso lembrado da sala ${saved.code}? Sem a aba antiga, você poderá perder acesso àquele jogador.`)) { renderRemembered(); return; }
      if (sameAccess(saved, session) && saved.pending && !session.pending) session.pending = saved.pending;
      try { localStorage.setItem(REMEMBER_KEY, JSON.stringify(session)); renderRemembered(); }
      catch (_) { node("onlineMessage").textContent = "Não foi possível lembrar o acesso. Mantenha esta aba aberta."; renderRemembered(); }
    };
    node("onlineRetry").onclick = async () => {
      try { await sendPending(); await refresh(); node("onlineMessage").textContent = "Comando confirmado."; }
      catch (error) { node("onlineMessage").textContent = error.message; }
    };
    node("onlineReset").onclick = () => {
      if (confirm("Limpar o acesso desta aba e sua cópia lembrada neste navegador? Você perderá o acesso ao jogador; isso não libera sua vaga nem revoga outras abas.")) {
        if (sameAccess(remembered(), session) && !forgetRemembered()) return;
        session = null; store(); location.reload();
      }
    };
    const invitation = new URL(location.href).searchParams.get("room");
    if (invitation && /^[A-Z2-9]{8}$/.test(invitation)) node("onlineCode").value = invitation;
    node("onlineConnection").textContent = "Crie uma sala ou entre pelo código de convite.";
    store();
    const saved = remembered();
    if (!session && saved && (!invitation || invitation === saved.code)) await resumeRemembered();
    await poll(); connectUpdates();
    const startTimer = () => { timer = setInterval(() => { if (!document.hidden && !document.querySelector("dialog[open]") && (!socketReady || needsSync || disconnected)) void poll(); }, 2000); };
    startTimer();
    document.addEventListener("visibilitychange", () => { if (!document.hidden) { needsSync = true; syncIfNeeded(); connectUpdates(); } });
    window.addEventListener("pagehide", () => { clearInterval(timer); stopUpdates(); });
    window.addEventListener("pageshow", event => { if (event.persisted) { stopped = false; needsSync = true; startTimer(); syncIfNeeded(); connectUpdates(); } });
    window.addEventListener("storage", event => { if (event.key === REMEMBER_KEY || event.key === null) renderRemembered(); });
  }
  return {boot, snapshot, requestMatch};
})();
