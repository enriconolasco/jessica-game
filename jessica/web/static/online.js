window.JessicaOnline = (() => {
  const KEY = "jessica-online-v1";
  const node = id => document.getElementById(id);
  let session = null, catalog = null, room = null, revision = -1, busy = false, timer = null, disconnected = false;
  let cachedSnapshot = null, operationBusy = false;
  try { session = JSON.parse(sessionStorage.getItem(KEY)); } catch (_) {}
  if (!session || !/^[A-Z2-9]{8}$/.test(session.code) || typeof session.credential !== "string") session = null;
  function store() {
    try {
      if (session) sessionStorage.setItem(KEY, JSON.stringify(session));
      else sessionStorage.removeItem(KEY);
    } catch (_) { node("onlineMessage").textContent = "Armazenamento indisponível: esta sessão não poderá voltar após recarregar."; }
    node("onlineRetry").hidden = !session?.pending;
  }
  async function request(path, body) {
    const response = await fetch(path, {method: body === undefined ? "GET" : "POST", cache:"no-store",
      headers:{"Content-Type":"application/json", ...(session ? {Authorization:`Bearer ${session.credential}`} : {})},
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
    try {
      const result = await request(path("actions"), session.pending);
      delete session.pending; store(); return result;
    } catch (error) {
      if (error.status) { delete session.pending; store(); }
      else node("onlineMessage").textContent = "Resultado não confirmado. Reenvie o comando pendente; ele não será executado duas vezes.";
      throw error;
    } finally { busy = false; }
  }
  async function requestMatch(url, options) {
    if (!session) throw new Error("Entre em uma sala primeiro.");
    const match = /^\/matches\/([^/]+)\/(actions|dream-preview)$/.exec(url);
    if (!match || match[1] !== session.code || options.method !== "POST") throw new Error("Operação local indisponível no online.");
    const body = JSON.parse(options.body);
    if (match[2] === "dream-preview") return request(path("dream-preview"), body);
    if (session.pending) throw new Error("Verifique o comando pendente antes de enviar outra ação.");
    session.pending = {command_id:commandId(), revision, action:body};
    store(); return sendPending();
  }
  async function snapshot() {
    const result = await request(path("snapshot"));
    if (result.revision < revision && cachedSnapshot) return cachedSnapshot;
    revision = result.revision;
    cachedSnapshot = result;
    node("onlineConnection").textContent = `Conectado · revisão ${revision} · você controla J${result.player_id}`;
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
    busy = true;
    try {
      const next = await request(path());
      if (room?.revision !== next.revision || disconnected) renderRoom(next);
      if (next.status === "playing" && (revision !== next.revision || disconnected)) {
        matchId = session.code; node("game").hidden = false;
        await refresh();
      }
      disconnected = false;
      if (next.status === "lobby") node("onlineConnection").textContent = `Conectado · ${next.players.length}/4 participantes`;
    } catch (error) {
      disconnected = true;
      node("onlineConnection").textContent = "Conexão interrompida — tentando retornar, sem trocar de jogador.";
      if (error.status === 401 || error.status === 403 || error.status === 404) {
        node("game").hidden = true;
        node("onlineMessage").textContent = "Sessão indisponível. Este protótipo ainda perde salas ao reiniciar o servidor.";
        clearInterval(timer);
      }
    } finally { busy = false; }
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
    } catch (error) { node("onlineMessage").textContent = error.message; }
    finally {
      operationBusy = false;
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
    node("onlineRetry").onclick = async () => {
      try { await sendPending(); await refresh(); node("onlineMessage").textContent = "Comando confirmado."; }
      catch (error) { node("onlineMessage").textContent = error.message; }
    };
    node("onlineReset").onclick = () => {
      if (confirm("Limpar a credencial deste aparelho? Você perderá o acesso ao jogador; isso não libera sua vaga na sala.")) {
        session = null; store(); location.reload();
      }
    };
    const invitation = new URL(location.href).searchParams.get("room");
    if (invitation && /^[A-Z2-9]{8}$/.test(invitation)) node("onlineCode").value = invitation;
    node("onlineConnection").textContent = "Crie uma sala ou entre pelo código de convite.";
    store(); await poll();
    timer = setInterval(() => { if (!document.hidden && !document.querySelector("dialog[open]")) void poll(); }, 2000);
    window.addEventListener("pagehide", () => clearInterval(timer));
  }
  return {boot, snapshot, requestMatch};
})();
