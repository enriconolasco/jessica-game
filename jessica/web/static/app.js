let matchId = null;
let playerId = 1;
const $ = id => document.getElementById(id);
const ICON_ROOT = "/assets/visual-direction-v0.2/icons/";
const PEOPLE_ICON = {humanos:"humanos", anoes:"anoes", orcs:"orcs", fadas:"fadas", vampiros:"vampiros", lobisomens:"lobisomens", gigantes:"gigantes", mortos_vivos:"mortos-vivos", filhos_floresta:"filhos-floresta", gnomos_duendes:"gnomos-duendes", dragoes:"dragoes", demonios:"demonios"};
const HOUSE_NAMES = {center:"Centro", city_1:"Cidade 1 (Norte)", city_2:"Cidade 2 (Leste)", city_3:"Cidade 3 (Sul)", city_4:"Cidade 4 (Oeste)"};

async function api(path, options = {}) {
  const response = await fetch(path, {headers:{"Content-Type":"application/json"}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || data.error || "Falha");
  return data;
}

const unitName = unit => unit.hero_id || unit.archetype || unit.id;
function publicStates(unit) {
  const states = Object.entries(unit.statuses || {}).map(([key, value]) => `${key}: ${value}`);
  if (unit.resistance_stacks) states.push(`resistência: ${unit.resistance_stacks}`);
  if (unit.double_damage) states.push("dano dobrado");
  return states;
}
function describeUnit(unit, player, people) {
  const states = publicStates(unit);
  return `${unitName(unit)}; ${player?.name || `Jogador ${unit.owner_id}`}; ${people}; ${unit.kind === "hero" ? "herói" : "tropa"}; ${HOUSE_NAMES[unit.house] || unit.house}; vida ${unit.life} de ${unit.life_max}${states.length ? `; ${states.join(", ")}` : ""}`;
}
function showUnit(unit, player, people) {
  const states = publicStates(unit);
  $("unitDetails").replaceChildren();
  [unitName(unit), `${player?.name || `Jogador ${unit.owner_id}`} · ${people}`, `${unit.kind === "hero" ? "Herói" : "Tropa"} · ${HOUSE_NAMES[unit.house] || unit.house}`, `Vida ${unit.life}/${unit.life_max}`, states.length ? states.join(" · ") : "Sem estados públicos"].forEach((text, index) => {
    const node = document.createElement(index === 0 ? "strong" : "span");
    node.textContent = text;
    $("unitDetails").appendChild(node);
  });
}
function renderMap(view) {
  const players = new Map(view.players.map(player => [player.id, player]));
  document.querySelectorAll(".house-units").forEach(node => node.replaceChildren());
  [...view.board.units].sort((a,b) => a.owner_id-b.owner_id || Number(b.kind === "hero")-Number(a.kind === "hero") || a.id.localeCompare(b.id)).forEach(unit => {
    const player = players.get(unit.owner_id);
    const people = player?.people || "povo desconhecido";
    const house = document.querySelector(`[data-house="${CSS.escape(unit.house)}"] .house-units`);
    if (!house) return;
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = `unit-marker ${unit.kind === "hero" ? "hero" : "troop"}`;
    marker.setAttribute("aria-label", describeUnit(unit, player, people));
    marker.title = describeUnit(unit, player, people);
    if (PEOPLE_ICON[people]) {
      const image = document.createElement("img");
      image.src = `${ICON_ROOT}people-${PEOPLE_ICON[people]}-32.svg`;
      image.alt = "";
      marker.appendChild(image);
    } else {
      const fallback = document.createElement("span");
      fallback.className = "unknown-icon";
      fallback.textContent = "?";
      marker.appendChild(fallback);
    }
    const life = document.createElement("span");
    life.className = "unit-life";
    life.textContent = `${unit.life}/${unit.life_max}`;
    marker.appendChild(life);
    ["focus", "mouseenter", "click"].forEach(event => marker.addEventListener(event, () => showUnit(unit, player, people)));
    house.appendChild(marker);
  });
  document.querySelectorAll(".house").forEach(house => {
    const count = house.querySelectorAll(".unit-marker").length;
    house.querySelector("h3").dataset.count = count ? ` · ${count}` : " · vazia";
  });
}
function actionDetails(action) {
  const p = action.params;
  if (action.type === "collect_resources") return `${p.gold} Ouro + ${p.magic} Magia`;
  if (action.type === "raise_city_life") return `${p.times} aumento(s)`;
  if (action.type === "summon_troop") return `${p.archetype} · vida ${p.life} · ${HOUSE_NAMES[p.house] || p.house}`;
  if (action.type === "summon_hero") return p.hero_id || "herói escolhido";
  if (action.type === "move_unit") return `${p.unit_id} → ${HOUSE_NAMES[p.destination] || p.destination}`;
  if (action.type === "sell_artifact") return p.card_id;
  return "";
}
function renderActions(actions) {
  const root = $("actions");
  root.replaceChildren();
  const grouped = actions.reduce((map, action) => map.set(action.type, [...(map.get(action.type) || []), action]), new Map());
  grouped.forEach((items, type) => {
    const group = document.createElement("details");
    group.className = "action-group";
    group.open = ["collect_resources", "end_turn"].includes(type);
    const summary = document.createElement("summary");
    summary.textContent = `${items[0].label} (${items.length})`;
    group.appendChild(summary);
    if (items.length > 1) {
      const select = document.createElement("select");
      select.className = "action-select";
      select.setAttribute("aria-label", items[0].label);
      items.forEach((action, index) => {
        const option = document.createElement("option");
        option.value = index;
        option.textContent = actionDetails(action) || action.label;
        select.appendChild(option);
      });
      const button = document.createElement("button");
      button.className = "action action-submit";
      button.textContent = "Executar";
      button.onclick = () => act(items[Number(select.value)]);
      group.append(select, button);
    } else items.forEach(action => {
      const button = document.createElement("button");
      button.className = "action";
      button.textContent = actionDetails(action) || action.label;
      button.onclick = () => act(action);
      group.appendChild(button);
    });
    root.appendChild(group);
  });
}
function eventText(event) {
  const d = event.data || {};
  if (event.type === "resources_collected") return `J${d.player_id} recebeu ${d.gold} Ouro e ${d.magic} Magia.`;
  if (event.type === "city_life_raised") return `J${d.player_id} aumentou a Cidade de ${d.life_before} para ${d.life_after}.`;
  if (event.type === "monument_built") return `J${d.player_id} construiu um Monumento.`;
  if (event.type === "unit_summoned") return `J${d.player_id} invocou ${unitName(d.unit || {})}.`;
  if (event.type === "unit_moved") return `${d.unit_id} foi para ${HOUSE_NAMES[d.destination] || d.destination}.`;
  if (event.type === "player_turn_ended") return `J${d.player_id} encerrou sua janela do Dia.`;
  if (event.type === "artifact_obtained") return d.pending_choice ? "Escolha de artefato pendente." : `Artefato obtido: ${d.card_id}.`;
  if (event.type === "artifact_sold") return `J${d.player_id} vendeu ${d.card_id}.`;
  return event.type;
}
function renderEvents(events) {
  const root = $("events"); root.replaceChildren();
  events.slice(-12).reverse().forEach(event => {
    const node = document.createElement("div"); node.className = "event";
    const text = document.createElement("strong"); text.textContent = eventText(event);
    const meta = document.createElement("small"); meta.textContent = `Turno ${event.turn} · ${event.phase}`;
    node.append(text, document.createElement("br"), meta); root.appendChild(node);
  });
  if (!events.length) root.innerHTML = "<em>Nenhum acontecimento.</em>";
}
async function refresh() {
  const view = await api(`/matches/${matchId}/view?player_id=${playerId}`);
  playerId = view.active_player_id || playerId;
  const [actions, events] = await Promise.all([api(`/matches/${matchId}/actions?player_id=${playerId}`), api(`/matches/${matchId}/events?player_id=${playerId}`)]);
  $("status").textContent = `Turno ${view.turn} · ${view.phase} · jogador ativo: ${view.active_player_id ?? "—"}`;
  $("players").innerHTML = view.players.map(p => `<div class="player ${p.id === view.active_player_id ? "active" : ""}">J${p.id} ${p.name} — ${p.people}<br>Vida ${p.city.life}/${p.city.life_max} · Ouro ${p.city.gold} · Magia ${p.city.magic}</div>`).join("");
  const hand = view.self.hand.length ? view.self.hand.join(" · ") : "vazia";
  const bets = Object.entries(view.self.bets).filter(([, target]) => target).map(([suit,target]) => `${suit}→J${target}`).join(" · ") || "nenhuma";
  $("self").textContent = `Mão: ${hand} | Apostas: ${bets} | Corretas: ${view.self.correct_bets}`;
  renderMap(view); renderActions(actions); renderEvents(events);
}
async function act(action) {
  if (action.type === "end_turn" && !confirm("Encerrar a janela deste jogador?")) return;
  try {
    document.querySelectorAll("#actions button").forEach(button => button.disabled = true);
    await api(`/matches/${matchId}/actions`, {method:"POST", body:JSON.stringify(action)});
    $("message").textContent = "Ação concluída.";
    await refresh();
  } catch (error) {
    $("message").textContent = error.message;
    document.querySelectorAll("#actions button").forEach(button => button.disabled = false);
  }
}
async function enter(id) { matchId=id; $("start").hidden=true; $("game").hidden=false; await refresh(); }
$("create").onclick = async () => enter((await api("/matches", {method:"POST", body:JSON.stringify({seed:+$("seed").value})})).match_id);
$("load").onclick = async () => enter((await api("/matches/load", {method:"POST", body:JSON.stringify({save_id:$("saveId").value})})).match_id);
$("save").onclick = async () => { const data=await api(`/matches/${matchId}/save`, {method:"POST", body:"{}"}); $("message").textContent=`Save: ${data.save_id}`; };
