let matchId = null;
let playerId = 1;
let catalog = null;
let pendingPlayerId = null;
const $ = id => document.getElementById(id);
const ICON_ROOT = "/assets/visual-direction-v0.2/icons/";
const PEOPLE_ICON = {humanos:"humanos", anoes:"anoes", orcs:"orcs", fadas:"fadas", vampiros:"vampiros", lobisomens:"lobisomens", gigantes:"gigantes", mortos_vivos:"mortos-vivos", filhos_floresta:"filhos-floresta", gnomos_duendes:"gnomos-duendes", dragoes:"dragoes", demonios:"demonios"};
const HOUSE_NAMES = {center:"Centro", city_1:"Cidade 1 (Sul)", city_2:"Cidade 2 (Leste)", city_3:"Cidade 3 (Norte)", city_4:"Cidade 4 (Oeste)"};
const HOUSE_POSITIONS = {center:"center", city_1:"south", city_2:"east", city_3:"north", city_4:"west"};
let selectedHouse = "center";
let selectedUnitId = null;

async function api(path, options = {}) {
  const response = await fetch(path, {headers:{"Content-Type":"application/json"}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || data.error || "Falha");
  return data;
}

const peopleName = people => catalog?.peoples.find(item => item.id === people)?.label || people;
const unitName = unit => catalog?.peoples.flatMap(item => item.heroes).find(hero => hero.id === unit.hero_id)?.name
  || ({light:"Tropa pequena", medium:"Tropa média", heavy:"Tropa grande"})[unit.archetype]
  || unit.hero_id || unit.archetype || unit.id;
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
function showUnit(unit, player, people, select = true) {
  if (select) {
    selectedUnitId = unit.id;
    document.querySelectorAll(".unit-marker").forEach(marker => marker.setAttribute("aria-pressed", String(marker.dataset.unitId === unit.id)));
  }
  const states = publicStates(unit);
  $("unitDetails").replaceChildren();
  [unitName(unit), `${player?.name || `Jogador ${unit.owner_id}`} · ${people}`, `${unit.kind === "hero" ? "Herói" : "Tropa"} · ${HOUSE_NAMES[unit.house] || unit.house}`, `Vida ${unit.life}/${unit.life_max}`, states.length ? states.join(" · ") : "Sem estados públicos"].forEach((text, index) => {
    const node = document.createElement(index === 0 ? "strong" : "span");
    node.textContent = text;
    $("unitDetails").appendChild(node);
  });
}
function renderUnitGroups(root, units, players) {
  root.replaceChildren();
  const groups = new Map();
  units.forEach(unit => {
    const player = players.get(unit.owner_id);
    const people = peopleName(player?.people || "Povo desconhecido");
    if (!groups.has(unit.owner_id)) {
      const group = document.createElement("section");
      group.className = "unit-group";
      const title = document.createElement("h4");
      title.textContent = `J${unit.owner_id} · ${people} · ${units.filter(item => item.owner_id === unit.owner_id).length}`;
      const items = document.createElement("div");
      items.className = "unit-group-items";
      group.append(title, items);
      root.appendChild(group);
      groups.set(unit.owner_id, items);
    }
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = `unit-marker ${unit.kind === "hero" ? "hero" : "troop"}`;
    marker.setAttribute("aria-label", describeUnit(unit, player, people));
    marker.dataset.unitId = unit.id;
    marker.setAttribute("aria-pressed", String(unit.id === selectedUnitId));
    marker.title = describeUnit(unit, player, people);
    const fallback = () => {
      const text = document.createElement("span");
      text.className = "unknown-icon";
      text.textContent = "?";
      text.title = people;
      return text;
    };
    if (PEOPLE_ICON[player?.people]) {
      const image = document.createElement("img");
      image.src = `${ICON_ROOT}people-${PEOPLE_ICON[player.people]}-32.svg`;
      image.alt = "";
      image.onerror = () => image.replaceWith(fallback());
      marker.appendChild(image);
    } else {
      marker.appendChild(fallback());
    }
    const life = document.createElement("span");
    life.className = "unit-life";
    life.textContent = `${unit.life}/${unit.life_max}`;
    marker.appendChild(life);
    ["focus", "click"].forEach(event => marker.addEventListener(event, () => showUnit(unit, player, people)));
    marker.addEventListener("mouseenter", () => { if (!selectedUnitId) showUnit(unit, player, people, false); });
    groups.get(unit.owner_id).appendChild(marker);
  });
}
function renderMap(view) {
  const players = new Map(view.players.map(player => [player.id, player]));
  const units = [...view.board.units].sort((a,b) => a.owner_id-b.owner_id || Number(b.kind === "hero")-Number(a.kind === "hero") || a.id.localeCompare(b.id));
  if (!units.some(unit => unit.id === selectedUnitId)) {
    selectedUnitId = null;
    $("unitDetails").textContent = "Selecione uma unidade para consultar vida e condições públicas.";
  }
  let roster = $("houseRoster");
  if (!roster) {
    roster = document.createElement("section");
    roster.id = "houseRoster";
    roster.className = "house-roster";
    roster.setAttribute("aria-labelledby", "rosterTitle");
    const title = document.createElement("h3");
    title.id = "rosterTitle";
    title.setAttribute("aria-live", "polite");
    title.setAttribute("aria-atomic", "true");
    const list = document.createElement("div");
    list.className = "roster-units";
    roster.append(title, list);
    $("minimap").after(roster);
  }
  const renderRoster = () => {
    const present = units.filter(unit => unit.house === selectedHouse);
    const title = $("rosterTitle");
    title.textContent = `${HOUSE_NAMES[selectedHouse]} · ${present.length} unidade${present.length === 1 ? "" : "s"}`;
    const list = roster.querySelector(".roster-units");
    renderUnitGroups(list, present, players);
    if (!present.length) list.textContent = "Nenhuma unidade visível nesta casa.";
    document.querySelectorAll(".house-inspect").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.house === selectedHouse)));
  };
  document.querySelectorAll(".house").forEach(house => {
    const id = house.dataset.house;
    house.className = `house ${HOUSE_POSITIONS[id]}`;
    const present = units.filter(unit => unit.house === id);
    const player = view.players.find(player => id === `city_${player.id}`);
    const button = document.createElement("button");
    button.className = "house-inspect";
    button.type = "button";
    button.dataset.house = id;
    button.setAttribute("aria-controls", "houseRoster");
    button.setAttribute("aria-label", `${HOUSE_NAMES[id]}${player ? ` · ${player.name} · ${peopleName(player.people)}` : ""}: ${present.length} unidades visíveis. Consultar unidades.`);
    button.textContent = id === "center" ? "Centro" : `Cidade ${player?.id || id.slice(-1)}`;
    const caption = document.createElement("span");
    caption.className = "house-caption";
    caption.textContent = player ? peopleName(player.people) : "Encontro dos povos";
    const count = document.createElement("span");
    count.className = "house-count";
    count.textContent = `${present.length} unidade${present.length === 1 ? "" : "s"}`;
    button.append(caption, count);
    button.onclick = () => {
      if (selectedHouse !== id) {
        selectedUnitId = null;
        document.querySelectorAll(".unit-marker").forEach(marker => marker.setAttribute("aria-pressed", "false"));
        $("unitDetails").textContent = "Selecione uma unidade desta casa para consultar seus detalhes.";
      }
      selectedHouse = id;
      renderRoster();
    };
    house.querySelector("h3").replaceChildren(button);
    renderUnitGroups(house.querySelector(".house-units"), present, players);
  });
  renderRoster();
  const selected = units.find(unit => unit.id === selectedUnitId);
  if (selected) showUnit(selected, players.get(selected.owner_id), peopleName(players.get(selected.owner_id)?.people || "Povo desconhecido"));
}
function actionDetails(action) {
  if (action.description) return action.description;
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
    group.open = ["collect_resources", "end_turn", "resolve_artifact_choice", "night_resolve_choice",
                  "demon_pact", "night_pact", "night_decline_pact", "night_clock", "night_skip_clock", "night_setup"].includes(type);
    const summary = document.createElement("summary");
    summary.textContent = `${items[0].label} (${items.length})`;
    group.appendChild(summary);
    if (type === "dream_multi") {
      const action = items[0];
      const selected = [];
      let options = action.selection.options;
      group.open = true;
      const select = document.createElement("select");
      select.setAttribute("aria-label", "Carta transformada e alvo");
      const refreshOptions = () => {
        select.replaceChildren();
        options.forEach((option, i) => select.appendChild(new Option(option.label, i)));
        select.value = "0";
        select.disabled = options.length === 0;
        add.disabled = options.length === 0;
        submit.disabled = selected.length === 0;
      };
      const sequenceChoice = sequence => ({
        flip_cards: sequence.map(o => o.choice.flip_cards[0]),
        artifact_choices: sequence.map(o => o.choice.artifact_choices[0]),
      });
      const list = document.createElement("ol");
      const add = document.createElement("button");
      add.textContent = "Adicionar à sequência";
      add.onclick = async () => {
        const option = options[Number(select.value)];
        if (!option) return;
        [select, add, clear, submit].forEach(control => { control.disabled = true; });
        try {
          const preview = await api(`/matches/${matchId}/dream-preview`, {method:"POST", body:JSON.stringify({
            player_id: action.player_id, choice: sequenceChoice([...selected, option]),
          })});
          selected.push(option);
          options = preview.options;
          const row = document.createElement("li");
          row.textContent = option.label;
          list.appendChild(row);
          $("message").textContent = options.length ? "Escolha a próxima carta ou confirme o feitiço." : "Sequência pronta para confirmar.";
        } catch (error) { $("message").textContent = error.message; }
        finally { clear.disabled = false; refreshOptions(); }
      };
      const clear = document.createElement("button");
      clear.textContent = "Limpar sequência";
      clear.onclick = () => {
        selected.length = 0; list.replaceChildren();
        options = action.selection.options;
        refreshOptions();
      };
      const submit = document.createElement("button");
      submit.textContent = "Lançar Sonho Lúcido";
      submit.onclick = () => {
        if (selected.length) act({...action, params: {choice: sequenceChoice(selected)}});
      };
      const hint = document.createElement("p");
      hint.textContent = "A prévia resolve cada carta para atualizar os próximos alvos. Confirme para lançar a sequência inteira.";
      refreshOptions();
      group.append(hint, select, add, list, clear, submit);
      root.appendChild(group);
      return;
    }
    if (type === "allocate_bets") {
      const action = items[0];
      const fields = {};
      for (const [suit, name] of Object.entries({H:"Copas", C:"Paus", D:"Ouros", S:"Espadas"})) {
        const label = document.createElement("label");
        label.textContent = name + " ";
        const select = document.createElement("select");
        select.appendChild(new Option("Deixar vazio", ""));
        action.selection.targets.forEach(p => select.appendChild(new Option(p.name, p.id)));
        label.appendChild(select);
        group.appendChild(label);
        fields[suit] = select;
      }
      group.open = true;
      const button = document.createElement("button");
      button.textContent = "Confirmar apostas e iniciar o Dia";
      button.onclick = () => act({...action, params: {bets: Object.fromEntries(
        Object.entries(fields).map(([suit, select]) => [suit, select.value === "" ? null : Number(select.value)]))}});
      group.appendChild(button);
      root.appendChild(group);
      return;
    }
    if (type === "collect_resources") {
      const hint = document.createElement("p");
      hint.textContent = "Escolha uma distribuição. A coleta só pode ser feita uma vez neste turno.";
      group.appendChild(hint);
      items.forEach(action => {
        const button = document.createElement("button");
        button.className = "action";
        button.textContent = actionDetails(action);
        button.onclick = () => act(action);
        group.appendChild(button);
      });
      root.appendChild(group);
      return;
    }
    if (items.every(action => action.selection?.kind === "artifacts")) {
      items.forEach(action => {
        const fieldset = document.createElement("fieldset");
        const legend = document.createElement("legend");
        legend.textContent = action.description;
        fieldset.appendChild(legend);
        const inputs = action.selection.options.map(item => {
          const label = document.createElement("label");
          const input = document.createElement("input");
          input.type = "checkbox";
          label.append(input, document.createTextNode(` ${item.card_id} · ${item.zone === "hand" ? "mão" : "campo"} `));
          fieldset.appendChild(label);
          return input;
        });
        const button = document.createElement("button");
        button.textContent = "Sacrificar herói e trocar cartas selecionadas";
        button.onclick = () => {
          const artifacts = action.selection.options.filter((_, i) => inputs[i].checked);
          if (!artifacts.length) { $("message").textContent = "Selecione ao menos um artefato."; return; }
          if (confirm(`${action.description}? O herói morrerá e as cartas selecionadas serão trocadas.`))
            act({...action, params: {...action.params, artifacts}});
        };
        fieldset.appendChild(button);
        group.appendChild(fieldset);
      });
      root.appendChild(group);
      return;
    }
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
  if (event.type === "night_action_resolved") {
    if (d.action_type === "night_ainai") return `Ainai teleportou para ${HOUSE_NAMES[d.destination] || d.destination}.`;
    if (d.action_type === "night_luide_move") return `${d.unit_id} moveu para ${HOUSE_NAMES[d.destination] || d.destination} na janela de Luide.`;
    if (d.action_type === "night_luide_spell") return `Feitiço vampiro aplicado a ${d.unit_id}.`;
    if (d.action_type === "night_window_done") return "Janela opcional concluída.";
    if (d.action_type === "night_aiquara") return `Aiquara forçou ${d.enemy_unit_id} a atacar ${d.target_id}.`;
    if (d.action_type === "night_mandinga") return `Besouro usou Mandinga: ${d.card_id}.`;
    if (d.action_type === "night_setup") {
      if (d.kind === "aiquara") return "Aiquara não usou controle no início da Noite.";
      if (d.kind === "besouro") return "Besouro não usou Mandinga.";
      if (d.kind === "vovo") return `Vovó escolheu a posição ${d.position} nas declarações.`;
      return d.return ? "Luna retornou à origem." : "Luna permaneceu no local.";
    }
    if (d.action_type === "night_pact") return "Pacto firmado durante a Noite.";
    if (d.action_type === "night_decline_pact") return "Oferta de pacto recusada.";
    if (d.action_type === "night_clock") return `Rogue usou o Relógio de bolso: ${HOUSE_NAMES[d.destination] || d.destination}.`;
    if (d.action_type === "night_skip_clock") return "Rogue não usou o Relógio de bolso.";
    if (d.action_type === "night_resolve_choice") return "Escolha de artefato resolvida; combate liberado para continuar.";
    if (d.action_type === "night_attack") return `${d.attacker_unit_id} atacou ${d.target_id}.`;
    if (d.action_type === "night_pass") return `${d.unit_id} não declarou ataque.`;
    return "Noite encerrada.";
  }
  if (event.type === "resources_collected") return `J${d.player_id} recebeu ${d.gold} Ouro e ${d.magic} Magia.`;
  if (event.type === "city_life_raised") return `J${d.player_id} aumentou a Cidade de ${d.life_before} para ${d.life_after}.`;
  if (event.type === "monument_built") return `J${d.player_id} construiu um Monumento.`;
  if (event.type === "unit_summoned") return `J${d.player_id} invocou ${unitName(d.unit || {})}.`;
  if (event.type === "unit_moved") return `${d.unit_id} foi para ${HOUSE_NAMES[d.destination] || d.destination}.`;
  if (event.type === "player_turn_ended") return `J${d.player_id} encerrou sua janela do Dia.`;
  if (event.type === "artifact_obtained") return d.pending_choice ? "Escolha de artefato pendente." : `Artefato obtido: ${d.card_id}.`;
  if (event.type === "artifact_sold") return `J${d.player_id} vendeu ${d.card_id}.`;
  if (event.type === "interaction_resolved") {
    const labels = {play_artifact: "jogou", resolve_artifact_choice: "resolveu a escolha de artefato",
      use_pena: "usou uma Pena", use_heal: "aplicou uma cura", hero_ability: "usou uma habilidade",
      demon_pact: "firmou um pacto", decline_pact: "recusou um pacto",
      cast_spell: "usou um feitiço", sacrifice_spell: "usou Sacrifício de Demônio",
      allocate_bets: "confirmou as apostas",
      day_attack: "atacou durante o Dia com Miyamoto",
      dream_multi: "usou Sonho Lúcido com Luna",
      reroll_spell: "rerrolou o feitiço copiado"};
    return `J${d.player_id} ${labels[d.action_type] || "concluiu uma ação"}${d.card_id ? ` ${d.card_id}` : ""}${d.pact_id ? `: ${d.pact_id.replaceAll("_", " ")}` : ""}.`;
  }
  return event.type;
}
function renderEvents(events) {
  const root = $("events"); root.replaceChildren();
  const visible = events.filter(event => event.type !== "player_view_updated");
  let previousTurn = null;
  visible.forEach(event => {
    if (event.turn !== previousTurn) {
      const heading = document.createElement("h3");
      heading.textContent = `Turno ${event.turn}`;
      root.appendChild(heading);
      previousTurn = event.turn;
    }
    const node = document.createElement("div"); node.className = "event";
    const text = document.createElement("strong"); text.textContent = eventText(event);
    const meta = document.createElement("small"); meta.textContent = `Turno ${event.turn} · ${event.phase}`;
    node.append(text, document.createElement("br"), meta); root.appendChild(node);
  });
  if (!visible.length) root.textContent = "Nenhum acontecimento.";
}
async function refresh(allowPlayerSwitch = false) {
  const view = await api(`/matches/${matchId}/view?player_id=${playerId}`);
  if (!allowPlayerSwitch && view.active_player_id && view.active_player_id !== playerId) {
    pendingPlayerId = view.active_player_id;
    const next = view.players.find(player => player.id === pendingPlayerId);
    $("handoffText").textContent = `Entregue o aparelho a ${next?.name || `Jogador ${pendingPlayerId}`}. A área privada permanece oculta.`;
    $("handoff").hidden = false;
    $("game").inert = true;
    $("revealPlayer").focus();
    return;
  }
  playerId = view.active_player_id || playerId;
  const [actions, events] = await Promise.all([api(`/matches/${matchId}/actions?player_id=${playerId}`), api(`/matches/${matchId}/events?player_id=${playerId}`)]);
  $("status").textContent = `Turno ${view.turn} · ${view.phase} · jogador ativo: ${view.active_player_id ?? "—"}`;
  if (view.game_over) {
    const winner = view.players.find(p => p.id === view.winner_id);
    $("status").textContent = `Partida encerrada · Vencedor: ${winner?.name || "sem vencedor"}`;
  }
  if (view.night_limitations?.length)
    $("status").textContent += " · Noite ainda indisponível: " + view.night_limitations.join(" ");
  if (view.night_window?.house) {
    const names = view.night_window.declaration_order.map(id =>
      view.players.find(p => p.id === id)?.name || `J${id}`).join(" → ");
    $("status").textContent += ` · Combate: ${HOUSE_NAMES[view.night_window.house] || view.night_window.house} · Ordem restante: ${names}`;
  }
  $("players").replaceChildren();
  view.players.forEach(p => {
    const node = document.createElement("div");
    node.className = `player ${p.id === view.active_player_id ? "active" : ""}`;
    node.textContent = `J${p.id} ${p.name} — ${p.people} · Vida ${p.city.life}/${p.city.life_max} · Ouro ${p.city.gold} · Magia ${p.city.magic} · Em campo: ${(p.field_artifacts || []).join(", ") || "nenhum"} · Canastra: ${(p.canastra || []).join(", ") || "vazia"}`;
    $("players").appendChild(node);
  });
  const hand = view.self.hand.length ? view.self.hand.join(" · ") : "vazia";
  const bets = Object.entries(view.self.bets).filter(([, target]) => target).map(([suit,target]) => `${suit}→J${target}`).join(" · ") || "nenhuma";
  const pending = view.self.pending_choice ? " | Resolva a escolha pendente nas ações abaixo." : "";
  const offers = view.self.demon_pact_offers?.length ? " | Há uma oferta de pacto nas ações abaixo." : "";
  const copiedSpell = view.self.spell_copia_id ? ` | Feitiço copiado: ${view.self.spell_copia_id.replaceAll("_", " ")}` : "";
  $("self").textContent = `Mão: ${hand} | Apostas: ${bets} | Corretas: ${view.self.correct_bets} | Curas: ${view.self.pending_heals || 0}${copiedSpell}${pending}${offers}`;
  renderMap(view); renderActions(actions); renderEvents(events);
}
async function act(action) {
  if (action.type === "end_turn" && !confirm("Encerrar a janela deste jogador?")) return;
  if (action.type === "finish_night" && !confirm("Encerrar a Noite e avançar o turno?")) return;
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
function updateHeroSelect(row, peopleId) {
  const people = catalog.peoples.find(item => item.id === peopleId);
  const select = row.querySelector(".setup-hero");
  select.replaceChildren();
  if (peopleId === "mortos_vivos") {
    select.appendChild(new Option("Escolha feita durante a partida", ""));
    select.disabled = true;
  } else {
    people.heroes.forEach(hero => select.appendChild(new Option(`${hero.name} · ${hero.life} vida`, hero.id)));
    select.disabled = false;
  }
}
function updatePeopleAvailability() {
  const selected = [...document.querySelectorAll(".setup-people")].map(select => select.value);
  document.querySelectorAll(".setup-people").forEach(select => [...select.options].forEach(option => {
    option.disabled = option.value !== select.value && selected.includes(option.value);
  }));
}
function renderSetup() {
  const root = $("setupPlayers");
  root.replaceChildren();
  const defaults = ["humanos", "anoes", "orcs", "fadas"];
  defaults.forEach((defaultPeople, index) => {
    const row = document.createElement("section");
    row.className = "setup-player";
    row.innerHTML = `<h3>Jogador ${index + 1}</h3><label>Nome <input class="setup-name" maxlength="40" value="Jogador ${index + 1}"></label><label>Povo <select class="setup-people"></select></label><label>Herói <select class="setup-hero"></select></label>`;
    const peopleSelect = row.querySelector(".setup-people");
    catalog.peoples.forEach(people => peopleSelect.appendChild(new Option(people.label, people.id)));
    peopleSelect.value = defaultPeople;
    peopleSelect.onchange = () => { updateHeroSelect(row, peopleSelect.value); updatePeopleAvailability(); };
    updateHeroSelect(row, defaultPeople);
    root.appendChild(row);
  });
  updatePeopleAvailability();
}
function setupPayload() {
  return {
    seed: +$("seed").value,
    players: [...document.querySelectorAll(".setup-player")].map(row => ({
      name: row.querySelector(".setup-name").value,
      people: row.querySelector(".setup-people").value,
      hero_id: row.querySelector(".setup-hero").value,
    })),
    config: {city_life:+$("cityLife").value, city_life_max:+$("cityLifeMax").value,
             gold:+$("goldStart").value, magic:+$("magicStart").value},
  };
}
$("create").onclick = async () => {
  try {
    $("setupMessage").textContent = "";
    await enter((await api("/matches", {method:"POST", body:JSON.stringify(setupPayload())})).match_id);
  } catch (error) { $("setupMessage").textContent = error.message; }
};
$("load").onclick = async () => enter((await api("/matches/load", {method:"POST", body:JSON.stringify({save_id:$("saveId").value})})).match_id);
$("save").onclick = async () => { const data=await api(`/matches/${matchId}/save`, {method:"POST", body:"{}"}); $("message").textContent=`Save: ${data.save_id}`; };
$("revealPlayer").onclick = async () => {
  playerId = pendingPlayerId;
  pendingPlayerId = null;
  $("handoff").hidden = true;
  $("game").inert = false;
  await refresh(true);
};
api("/catalog").then(data => { catalog = data; renderSetup(); }).catch(error => { $("setupMessage").textContent = error.message; });
