window.JessicaOnline = (() => {
  const KEY = "jessica-online-v1";
  const REMEMBER_KEY = "jessica-online-remembered-v1";
  const node = id => document.getElementById(id);
  let session = null, catalog = null, room = null, revision = -1, busy = false, timer = null, disconnected = false;
  let cachedSnapshot = null, operationBusy = false;
  let initialFingerprint = null, initialRows = [];
  let socket = null, socketReady = false, reconnectTimer = null, reconnectDelay = 1000, stopped = false, needsSync = false;
  function readAccess(storage, key) {
    try {
      const raw = storage.getItem(key);
      if (!raw || raw.length > 131072) return null;
      const saved = JSON.parse(raw);
      if (!saved || typeof saved.code !== "string" || !/^[A-Z2-9]{8}$/.test(saved.code) || typeof saved.credential !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(saved.credential)) return null;
      if (saved.pending && (typeof saved.pending.command_id !== "string" || !/^[A-Za-z0-9_-]{1,64}$/.test(saved.pending.command_id) || !Number.isSafeInteger(saved.pending.revision) || saved.pending.revision < 0 || !saved.pending.action || typeof saved.pending.action !== "object" || Array.isArray(saved.pending.action))) return null;
      if (saved.rotation && (typeof saved.rotation.credential !== "string" || !/^[a-f0-9]{64}$/.test(saved.rotation.credential))) return null;
      return {code:saved.code, credential:saved.credential, ...(saved.pending ? {pending:saved.pending} : {}), ...(saved.rotation ? {rotation:saved.rotation} : {})};
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
    node("onlineRotate").textContent = session?.rotation ? "Confirmar troca de acesso pendente" : "Revogar outros acessos ao meu jogador";
  }
  try { session = readAccess(sessionStorage, KEY); } catch (_) {}
  function store(settledCommandId = null, settledRotation = null) {
    const saved = remembered();
    if (sameAccess(saved, session) && saved.pending && !session.pending && saved.pending.command_id !== settledCommandId) session.pending = saved.pending;
    if (sameAccess(saved, session) && saved.rotation && !session.rotation && saved.rotation.credential !== settledRotation) session.rotation = saved.rotation;
    let tabSaved = false, copySaved = !sameAccess(saved, session);
    try {
      if (session) sessionStorage.setItem(KEY, JSON.stringify(session));
      else sessionStorage.removeItem(KEY);
      tabSaved = true;
    } catch (_) { node("onlineMessage").textContent = "Armazenamento indisponível: esta sessão não poderá voltar após recarregar."; }
    if (sameAccess(remembered(), session)) {
      try { localStorage.setItem(REMEMBER_KEY, JSON.stringify(session)); copySaved = true; }
      catch (_) { node("onlineMessage").textContent = "Não foi possível atualizar o acesso lembrado. Não feche a aba enquanto houver comando pendente."; }
    }
    renderRemembered();
    node("onlineRetry").hidden = !session?.pending;
    return tabSaved && copySaved;
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
    if (session?.rotation) throw new Error("Confirme a troca de acesso pendente antes de reenviar ações.");
    if (!session?.pending) throw new Error("Não há comando pendente.");
    busy = true;
    const pendingId = session.pending.command_id;
    try {
      const result = await request(path("actions"), session.pending);
      delete session.pending; store(pendingId); return result;
    } catch (error) {
      if (error.status && error.status !== 429 && error.status !== 503) { delete session.pending; store(pendingId); }
      else node("onlineMessage").textContent = error.status ? "Servidor ocupado ou armazenamento indisponível. Aguarde e reenvie o mesmo comando pendente." : "Resultado não confirmado. Reenvie o comando pendente; ele não será executado duas vezes.";
      throw error;
    } finally { busy = false; syncIfNeeded(); }
  }
  async function requestMatch(url, options) {
    if (!session) throw new Error("Entre em uma sala primeiro.");
    if (session.rotation) throw new Error("Confirme a troca de acesso pendente antes de enviar ações.");
    const match = /^\/matches\/([^/]+)\/(actions|dream-preview)$/.exec(url);
    if (!match || match[1] !== session.code || options.method !== "POST") throw new Error("Operação local indisponível no online.");
    const body = JSON.parse(options.body);
    if (match[2] === "dream-preview") return request(path("dream-preview"), body);
    store();
    if (session.rotation) throw new Error("Confirme a troca de acesso pendente antes de enviar ações.");
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
      const confirmed = room.setup_phase === "peoples" ? p.people_confirmed : p.ready;
      line.textContent = `J${p.player_id} ${p.name}${p.player_id === room.you ? " (você)" : ""} · ${people?.label || "povo não escolhido"}${hero ? ` · ${hero.name}${room.status !== "playing" ? " (secreto)" : ""}` : room.setup_phase === "heroes" && room.status !== "playing" ? " · herói secreto" : ""} · ${confirmed ? "confirmado" : "aguardando"}`;
      node("onlinePlayers").appendChild(line);
    });
    const own = room.players.find(p => p.player_id === room.you);
    for (const option of node("onlinePeople").options) option.disabled = room.players.some(p => p.player_id !== room.you && p.people === option.value);
    if (own.people && (own.people !== previousOwn?.people || own.hero_id !== previousOwn?.hero_id)) {
      node("onlinePeople").value = own.people; heroOptions(own.hero_id);
    }
    const peoplesStage = room.setup_phase === "peoples";
    const confirmed = peoplesStage ? own.people_confirmed : own.ready;
    node("onlineSetupStage").textContent = peoplesStage ? "1/2 — Povos públicos. Todos precisam confirmar antes de escolher heróis." : "2/2 — Heróis secretos. A última confirmação revela todos e inicia a partida.";
    node("onlineHeroLabel").hidden = peoplesStage;
    node("onlinePeople").disabled = !peoplesStage || confirmed;
    node("onlineHero").disabled = peoplesStage || own.ready || node("onlinePeople").value === "mortos_vivos";
    node("onlineSelect").disabled = confirmed || operationBusy;
    node("onlineSelect").textContent = peoplesStage ? "Selecionar povo público" : "Salvar escolha secreta de herói";
    node("onlineRotate").disabled = operationBusy;
    node("onlineReady").disabled = !own.people || !peoplesStage && own.people !== "mortos_vivos" && !own.hero_id || operationBusy;
    node("onlineReady").textContent = confirmed ? "Desmarcar minha confirmação" : peoplesStage ? "Confirmar povo" : "Confirmar herói e aguardar revelação";
    node("onlineStart").hidden = Boolean(room.setup_phase) || room.you !== room.host_id;
    node("onlineStart").disabled = operationBusy || room.players.length !== (room.capacity || 4) || !room.players.every(p => p.ready);
    const fingerprint = JSON.stringify([room.code, room.capacity || 4, room.initial_conditions || {}]);
    if (room.status === "lobby" && fingerprint !== initialFingerprint) {
      initialFingerprint = fingerprint; initialRows = []; node("onlineInitial").replaceChildren();
      for (let pid = 1; pid <= (room.capacity || 4); pid++) {
        const section = document.createElement("section"); section.className = "setup-player";
        const title = document.createElement("h3"); title.textContent = `Jogador ${pid}`; section.appendChild(title);
        const inputs = {};
        [["city_life","Vida da Base",1,100],["gold","Ouro",0,999],["magic","Magia",0,999],["artifacts","Artefatos",0,24]].forEach(([key,text,min,max]) => {
          const label = document.createElement("label"); label.textContent = text;
          const input = document.createElement("input"); input.type = "number"; input.min = min; input.max = max;
          input.placeholder = "Padrão"; input.value = room.initial_conditions?.[pid]?.[key] ?? "";
          input.disabled = room.you !== room.host_id; inputs[key] = input; label.appendChild(input); section.appendChild(label);
        });
        initialRows.push({pid, inputs}); node("onlineInitial").appendChild(section);
      }
    }
    node("onlineConfigure").hidden = room.you !== room.host_id;
    node("onlineConfigure").disabled = operationBusy;
    node("onlineChoice").hidden = room.status === "playing";
  }
  async function poll() {
    if (!session || busy || session.rotation) return;
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
      if (next.status === "lobby") node("onlineConnection").textContent = `Conectado · ${socketReady ? "tempo real" : "HTTP"} · ${next.players.length}/${next.capacity || 4} participantes`;
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
    if (!session || session.rotation || stopped || socket || typeof WebSocket === "undefined") return;
    const url = new URL(location.href); url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    if (document.getElementById("onlineTransport")?.content !== "same-origin") {
      url.port = String(Number(url.port || (url.protocol === "wss:" ? 443 : 80)) + 1);
    }
    url.pathname = "/updates"; url.search = ""; url.hash = "";
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
    if (session?.rotation) { node("onlineMessage").textContent = "Confirme a troca de acesso pendente primeiro."; return; }
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
  async function verifyAccess(saved) {
    if (!saved.rotation) return {access:saved, room:await request(`/rooms/${saved.code}`, undefined, saved.credential)};
    let next;
    try { next = await request(`/rooms/${saved.code}/credential`, {credential:saved.rotation.credential}, saved.credential); }
    catch (_) { next = await request(`/rooms/${saved.code}`, undefined, saved.rotation.credential); }
    const access = {...saved, credential:saved.rotation.credential}; delete access.rotation;
    return {access, room:next};
  }
  function adoptAccess(previous, access) {
    const keepCopy = sameAccess(remembered(), previous);
    session = access;
    if (keepCopy) {
      try { localStorage.setItem(REMEMBER_KEY, JSON.stringify(session)); }
      catch (_) { node("onlineMessage").textContent = "Acesso trocado; a cópia antiga contém a troca pendente. Preserve esta aba e confira o armazenamento."; }
    }
    store();
  }
  async function rotateAccess() {
    if (!session || operationBusy || busy) return;
    if (!store()) { node("onlineMessage").textContent = "Acesso não trocado: não foi possível guardar a nova credencial com segurança."; return; }
    if (session.pending && !session.rotation) { node("onlineMessage").textContent = "Verifique o comando pendente antes de trocar o acesso."; return; }
    if (!session.rotation && !confirm("Trocar sua credencial e revogar os outros acessos ao seu jogador? Esta aba mantém seu lugar na partida.")) return;
    const saved = session;
    const candidate = saved.rotation?.credential || Array.from(crypto.getRandomValues(new Uint8Array(32)), n => n.toString(16).padStart(2,"0")).join("");
    saved.rotation = {credential:candidate};
    if (!store()) {
      delete saved.rotation; store(null, candidate);
      node("onlineMessage").textContent = "Acesso não trocado: não foi possível guardar a nova credencial com segurança.";
      return;
    }
    operationBusy = busy = true; node("onlineRotate").disabled = true; stopUpdates();
    try {
      const result = await verifyAccess(saved);
      adoptAccess(saved, result.access); renderRoom(result.room);
      node("onlineMessage").textContent = "Acesso atualizado. Credenciais antigas foram revogadas; você mantém o mesmo jogador.";
    } catch (_) { node("onlineMessage").textContent = "Troca não confirmada. Não limpe seu acesso; use Confirmar troca de acesso pendente. A nova credencial foi preservada."; }
    finally {
      operationBusy = busy = false; stopped = false;
      if (!session.rotation) { disconnected = true; await poll(); connectUpdates(); }
      if (room) renderRoom(room); renderRemembered();
    }
  }
  async function resumeRemembered() {
    const saved = remembered();
    if (session || !saved || operationBusy) return;
    operationBusy = true;
    node("onlineResume").disabled = true;
    node("onlineCreate").disabled = node("onlineJoin").disabled = true;
    try {
      const result = await verifyAccess(saved);
      adoptAccess(saved, result.access); renderRoom(result.room);
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
    node("onlineCreate").onclick = () => operation("create", {name:node("onlineName").value, num_players:+node("onlineCapacity").value || 4});
    node("onlineJoin").onclick = () => operation("join", {name:node("onlineName").value});
    node("onlineSelect").onclick = () => operation("select", room.setup_phase === "peoples" ? {people:node("onlinePeople").value} : {hero_id:node("onlineHero").value});
    node("onlineReady").onclick = () => {
      const own = room.players.find(p => p.player_id === room.you);
      return operation("ready", {ready:!(room.setup_phase === "peoples" ? own.people_confirmed : own.ready)});
    };
    node("onlineStart").onclick = () => operation("start", {});
    node("onlineConfigure").onclick = () => operation("configure", {revision:room.revision,
      initial_conditions:Object.fromEntries(initialRows.map(({pid,inputs}) => [String(pid),
        Object.fromEntries(Object.entries(inputs).flatMap(([key,input]) => input.value === "" ? [] : [[key, Number(input.value)]]))]))});
    node("onlineRotate").onclick = rotateAccess;
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
    if (session?.rotation) await rotateAccess();
    if (!session?.rotation) { await poll(); connectUpdates(); }
    const startTimer = () => { timer = setInterval(() => { if (!document.hidden && !document.querySelector("dialog[open]") && (!socketReady || needsSync || disconnected)) void poll(); }, 2000); };
    startTimer();
    document.addEventListener("visibilitychange", () => { if (!document.hidden) { needsSync = true; syncIfNeeded(); connectUpdates(); } });
    window.addEventListener("pagehide", () => { clearInterval(timer); stopUpdates(); });
    window.addEventListener("pageshow", event => { if (event.persisted) { stopped = false; needsSync = true; startTimer(); syncIfNeeded(); connectUpdates(); } });
    window.addEventListener("storage", event => { if (event.key === REMEMBER_KEY || event.key === null) renderRemembered(); });
  }
  return {boot, snapshot, requestMatch};
})();
