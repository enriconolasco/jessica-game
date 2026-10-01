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
let currentView = null;
const publicUnitNames = new Map();

async function api(path, options = {}) {
  const response = await fetch(path, {headers:{"Content-Type":"application/json"}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || data.error || "Falha");
  return data;
}

const peopleName = people => catalog?.peoples.find(item => item.id === people)?.label || people;
const troopNames = {light:"Tropa pequena", medium:"Tropa média", heavy:"Tropa grande", special:"Tropa Orc extra", extra:"Tropa extra", ghoul:"Ghoul", esqueleto:"Esqueleto", dragon_light:"Dragão pequeno", dragon_medium:"Dragão médio", dragon_heavy:"Dragão grande"};
const heroName = id => catalog?.heroes?.find(hero => hero.id === id)?.name || catalog?.peoples.flatMap(item => item.heroes).find(hero => hero.id === id)?.name || id;
const cardName = id => catalog?.artifacts?.find(card => card.id === id)?.name || id;
const unitName = unit => (unit.hero_id ? heroName(unit.hero_id) : null)
  || troopNames[unit.archetype]
  || unit.hero_id || unit.archetype || unit.id;
function rogueItemName(id) {
  return {capa:"Capa", adaga:"Adaga", relogio:"Relógio de bolso", bracelete:"Bracelete"}[id] || id;
}
function publicStates(unit) {
  const labels = {amaldicoado_until_turn:"Amaldiçoado até o turno", cannot_attack_on_turn:"Não ataca no turno",
    centauro_until_turn:"Centauro até o turno", espectro_until_turn:"Espectro até o turno",
    invisivel_until_turn:"Invisível até o turno", invulneravel_until_turn:"Invulnerável até o turno",
    lobisomem_until_turn:"Lobisomem até o turno", morcego_until_turn:"Morcego até o turno",
    sono_until_turn:"Dormindo até o turno", summoned_turn:"Invocado no turno",
    barba_hero_mode_turn:"Modo Herói no turno", mar_chamas_queued_turn:"Mar de Chamas preparado no turno",
    mar_chamas_cooldown_until_turn:"Mar de Chamas disponível no turno", rogue_items:"Itens de Rogue",
    rogue_resist_heroes:"Resistência contra heróis", demon_execute_weaker:"Executa inimigos menores",
    cabaca_used_turn:"Cabaça já usada no turno", dragon_base:"Herói-Base", permanent_centaur:"Centauro permanente",
    dragon_heart_resistance:"Resistência da Canastra", k_s_active:"Véu das Caçadoras",
    can_attack_city_until_turn:"Pode atacar Base até o turno", lupa_resist_until_turn:"Resistência de Lupã até o turno"};
  const states = Object.entries(unit.statuses || {}).filter(([key]) => labels[key]).map(([key, value]) =>
    `${labels[key]}${typeof value === "boolean" ? "" : `: ${Array.isArray(value) ? value.map(item => key === "rogue_items" ? rogueItemName(item) : item).join(", ") : value}`}`);
  if (unit.resistance_stacks) states.push(`resistência: ${unit.resistance_stacks}`);
  if (unit.double_damage) states.push("dano dobrado");
  if (unit.infected) states.push("infectado");
  if (unit.max_moves_this_turn > 1) states.push(`${unit.max_moves_this_turn} movimentos · usados ${unit.moves_this_turn}`);
  if (unit.effective_max_attacks > 1) states.push(`${unit.effective_max_attacks} ataques · usados ${unit.attacks_made_this_night}`);
  if (unit.hero_can_attack_city) states.push("pode atacar Base");
  if (unit.owner_invulnerable) states.push("invulnerável por efeito do jogador");
  if (unit.armor_active) states.push("Armadura de Ouro ativa");
  if (unit.first_strike) states.push("Bater Primeiro ativo");
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
      title.textContent = `J${unit.owner_id} ${player?.name || ""} · ${people}${unit.owner_id === currentView?.curuna_id ? " · ★ Curruna" : ""}`;
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
    marker.addEventListener("mouseenter", () => showUnit(unit, player, people, false));
    groups.get(unit.owner_id).appendChild(marker);
  });
}
function renderMap(view) {
  const players = new Map(view.players.map(player => [player.id, player]));
  const units = view.board.units.filter(unit => unit.life > 0).sort((a,b) => a.owner_id-b.owner_id || Number(b.kind === "hero")-Number(a.kind === "hero") || a.id.localeCompare(b.id));
  const curuna = players.get(view.curuna_id);
  $("mapCuruna").textContent = curunaLabel(view, peopleName);
  $("mapNavigation").replaceChildren();
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
    $("minimap").parentElement.after(roster);
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
    const present = units.filter(unit => unit.house === id);
    const player = view.players.find(player => id === `city_${player.id}`);
    const isCuruna = player?.id === curuna?.id && Boolean(player);
    house.className = `house ${HOUSE_POSITIONS[id]}${isCuruna ? " curuna-house" : ""}`;
    const button = document.createElement("button");
    button.className = "house-inspect";
    button.type = "button";
    button.dataset.house = id;
    button.dataset.mapHouse = id;
    button.setAttribute("aria-controls", "houseRoster");
    button.setAttribute("aria-label", `${HOUSE_NAMES[id]}${player ? ` · ${player.name} · ${peopleName(player.people)}` : ""}${isCuruna ? " · Curruna" : ""}: ${present.length} unidades visíveis. Consultar unidades.`);
    button.textContent = HOUSE_NAMES[id] + (isCuruna ? " · ★ Curruna" : "");
    const caption = document.createElement("span");
    caption.className = "house-caption";
    caption.textContent = player ? `J${player.id} ${player.name} · ${peopleName(player.people)} · Base ${player.city.life}/${player.city.life_max}` : "Encontro dos povos";
    button.appendChild(caption);
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
    const jump = document.createElement("button");
    jump.type = "button"; jump.dataset.mapHouse = id;
    jump.textContent = id === "center" ? "Centro" : `J${player?.id}${isCuruna ? " ★ Curruna" : ""}`;
    jump.title = button.getAttribute("aria-label");
    jump.onclick = () => { button.click(); button.focus(); };
    $("mapNavigation").appendChild(jump);
  });
  renderRoster();
  const selected = units.find(unit => unit.id === selectedUnitId);
  if (selected) showUnit(selected, players.get(selected.owner_id), peopleName(players.get(selected.owner_id)?.people || "Povo desconhecido"));
}
function publicUnitName(id, fallback = `Unidade ${id}`) {
  return publicUnitNames.get(id) || fallback;
}
function phaseName(phase) {
  return {day:"Dia", night:"Noite"}[phase] || phase || "—";
}
function rememberPublicUnitNames(view, events) {
  for (const event of events) {
    if (event.type !== "public_state_changed") continue;
    for (const change of event.data.changes) {
      if (change.kind !== "unit") continue;
      for (const unit of [change.before, change.after])
        if (unit) publicUnitNames.set(unit.id, unitName(unit));
    }
  }
  for (const unit of view?.board.units || []) publicUnitNames.set(unit.id, unitName(unit));
}
function actionDetails(action) {
  if (action.type === "night_luide_move") return `${publicUnitName(action.params.unit_id)} → ${HOUSE_NAMES[action.params.destination] || action.params.destination}`;
  if (action.type === "night_luide_spell") return `Feitiço vampiro: ${publicUnitName(action.params.unit_id)}`;
  if (action.description) return action.description;
  const p = action.params;
  if (action.type === "collect_resources") return `${p.gold} Ouro + ${p.magic} Magia`;
  if (action.type === "raise_city_life") return `${p.times} aumento(s)`;
  if (action.type === "summon_troop") return `${troopNames[p.archetype] || p.archetype} · vida ${p.life} · ${HOUSE_NAMES[p.house] || p.house}`;
  if (action.type === "summon_hero") return p.hero_id ? heroName(p.hero_id) : "herói escolhido";
  if (action.type === "move_unit") return `${currentView?.board.units.find(u => u.id === p.unit_id) ? unitName(currentView.board.units.find(u => u.id === p.unit_id)) : p.unit_id} → ${HOUSE_NAMES[p.destination] || p.destination}`;
  if (action.type === "sell_artifact") return cardName(p.card_id);
  return "";
}
function pactChoiceText(action, reference) {
  const pact = reference?.pacts?.find(p => p.id === action.params.pact_id);
  const item = action.params.item;
  const itemNames = {capa:"Capa", adaga:"Adaga", relogio:"Relógio de bolso", bracelete:"Bracelete"};
  return [pact?.description, item ? `${itemNames[item] || item}: ${reference?.rogue_items?.[item] || "efeito não disponível no catálogo"}` : ""].filter(Boolean).join(" ");
}
function renderActions(actions) {
  const root = $("actions");
  root.replaceChildren();
  const grouped = actions.reduce((map, action) => map.set(action.type, [...(map.get(action.type) || []), action]), new Map());
  grouped.forEach((items, type) => {
    const group = document.createElement("details");
    group.className = "action-group";
    group.setAttribute("data-action-type", type);
    group.open = ["collect_resources", "end_turn", "finish_night", "resolve_artifact_choice", "night_resolve_choice",
                  "demon_pact", "night_pact", "night_decline_pact", "night_clock", "night_skip_clock", "night_setup"].includes(type);
    const summary = document.createElement("summary");
    const label = {night_luide_move:"Mover na janela de Luide", night_luide_spell:"Feitiço na janela de Luide"}[type] || items[0].label;
    summary.textContent = `${label} (${items.length})`;
    group.appendChild(summary);
    if (type === "demon_pact" || type === "night_pact") {
      const select = document.createElement("select");
      select.className = "action-select";
      select.setAttribute("aria-label", "Pacto e item, quando disponível");
      items.forEach((action, index) => select.appendChild(new Option(actionDetails(action) || action.label, index)));
      select.value = "0";
      const preview = document.createElement("p");
      preview.className = "hint";
      preview.setAttribute("aria-live", "polite");
      select.onchange = () => { preview.textContent = pactChoiceText(items[Number(select.value)], catalog); };
      select.onchange();
      const button = document.createElement("button");
      button.className = "action action-submit";
      button.textContent = "Firmar pacto";
      button.onclick = () => act(items[Number(select.value)]);
      group.append(select, preview, button);
      root.appendChild(group);
      return;
    }
    if (type === "armor_payment") {
      group.open = true;
      const action = items[0], request = action.selection;
      const info = document.createElement("p");
      info.textContent = `${publicUnitName(request.unit_id, request.unit_name || "Unidade")}${request.house ? ` · ${HOUSE_NAMES[request.house]}` : ""}: dano recebido ${request.damage}. Ouro disponível: ${request.gold_available}. Escolha de 0 a ${request.max_gold} para absorver dano.`;
      const label = document.createElement("label");
      label.textContent = "Ouro a pagar ";
      const input = document.createElement("input");
      input.type = "number"; input.min = "0"; input.max = String(request.max_gold); input.step = "1";
      input.value = String(request.max_gold);
      label.appendChild(input);
      const button = document.createElement("button");
      button.textContent = "Confirmar defesa e continuar";
      button.onclick = () => { if (input.reportValidity()) act({...action, params:{gold:Number(input.value)}}); };
      group.append(info, label, button);
      root.appendChild(group);
      return;
    }
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
          label.append(input, document.createTextNode(` ${cardName(item.card_id)} · ${item.zone === "hand" ? "mão" : "campo"} `));
          fieldset.appendChild(label);
          return input;
        });
        const button = document.createElement("button");
        button.textContent = "Sacrificar herói e trocar cartas selecionadas";
        button.onclick = async () => {
          const artifacts = action.selection.options.filter((_, i) => inputs[i].checked);
          if (!artifacts.length) { $("message").textContent = "Selecione ao menos um artefato."; return; }
          if (await confirmAction(`${action.description}? O herói morrerá e as cartas selecionadas serão trocadas.`))
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
      select.setAttribute("aria-label", label);
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
  if (event.type === "match_imported") return "Partida importada do terminal. Estado e RNG preservados; o histórico web começa aqui.";
  if (event.type === "public_roll") return d.message || `J${d.player_id} · ${d.source}: ${d.results.join(", ")} (${d.results.map(n => ({1:"+1 Magia", 2:"+1 Ouro", 3:"cura 2 pendente", 4:"dano na Cidade"})[n] || n).join(" · ")}).`;
  if (event.type === "combat_house_opened") return `${HOUSE_NAMES[d.house] || d.house}: ${d.order.length ? `combate iniciado · declarações ${d.order.map(id => `J${id}`).join(" → ")}` : "não havia combates a declarar"}.`;
  if (event.type === "day_restored") return `J${d.player_id}: ${d.operation === "mola" ? "retomou a jogada anterior" : "refez sua jogada"}. Estado e RNG restaurados.`;
  if (event.type === "public_state_changed") return (d.from_turn !== event.turn || d.from_phase !== event.phase ? `Alterações na transição T${d.from_turn} ${phaseName(d.from_phase)} → T${event.turn} ${phaseName(event.phase)}:\n` : "") + d.changes.map(change => {
    if (change.kind === "pact") return `Pacto ${!change.after ? "removido" : !change.before ? "firmado" : "atualizado"}: ${pactLabel(change.after || change.before, catalog, peopleName)}.`;
    if (change.kind === "unit") {
      const a = change.before, b = change.after;
      if (!a) return `J${b.owner_id}: ${unitName(b)} entrou em ${HOUSE_NAMES[b.house]} com ${b.life}/${b.life_max} de vida.`;
      if (!b) return `J${a.owner_id}: ${unitName(a)} deixou o campo.`;
      const parts = [];
      if (a.life !== b.life || a.life_max !== b.life_max) parts.push(`vida ${a.life}/${a.life_max} → ${b.life}/${b.life_max}`);
      if (a.house !== b.house) parts.push(`${HOUSE_NAMES[a.house]} → ${HOUSE_NAMES[b.house]}`);
      if (a.owner_id !== b.owner_id) parts.push(`controle J${a.owner_id} → J${b.owner_id}`);
      if (JSON.stringify(publicStates(a)) !== JSON.stringify(publicStates(b))) parts.push(`condições: ${publicStates(b).join(" · ") || "nenhuma"}`);
      return parts.length ? `${unitName(b)}: ${parts.join("; ")}.` : "";
    }
    if (change.kind === "conditions") return "Registros de unidades empaladas/infectadas atualizados. Consulte Condições e relatórios.";
    const labels = {gold:"Ouro", magic:"Magia", life:"Vida da Base", life_max:"Vida máxima da Base", has_monument:"Monumento", hand_count:"Artefatos na mão", canastra:"Canastra", field_artifacts:"Artefatos ativos"};
    const format = value => Array.isArray(value) ? value.map(cardName).join(", ") || "vazio" : typeof value === "boolean" ? value ? "sim" : "não" : value;
    return `${change.name}: ${labels[change.field] || change.field} ${format(change.before)} → ${format(change.after)}.`;
  }).filter(Boolean).join("\n");
  if (event.type === "armor_payment_requested") return `Armadura de Ouro: decidir quanto pagar contra ${d.damage} de dano.`;
  if (event.type === "night_action_resolved") {
    if (d.action_type === "night_ainai") return `Ainai teleportou para ${HOUSE_NAMES[d.destination] || d.destination}.`;
    if (d.action_type === "night_luide_move") return `${publicUnitName(d.unit_id)} moveu para ${HOUSE_NAMES[d.destination] || d.destination} na janela de Luide.`;
    if (d.action_type === "night_luide_spell") return `Feitiço vampiro aplicado a ${publicUnitName(d.unit_id)}.`;
    if (d.action_type === "night_window_done") return "Janela opcional concluída.";
    if (d.action_type === "night_aiquara") return `Aiquara forçou ${publicUnitName(d.enemy_unit_id)} a atacar ${publicUnitName(d.target_id)}.`;
    if (d.action_type === "night_mandinga") return `Besouro usou Mandinga: ${cardName(d.card_id)}.`;
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
    if (d.action_type === "night_attack") return `${publicUnitName(d.attacker_unit_id)} atacou ${d.target_type === "city" ? HOUSE_NAMES[`city_${d.target_id}`] || `Cidade ${d.target_id}` : publicUnitName(d.target_id)}.`;
    if (d.action_type === "night_pass") return `${publicUnitName(d.unit_id)} não declarou ataque.`;
    return "Noite encerrada.";
  }
  if (event.type === "resources_collected") return `J${d.player_id} recebeu ${d.gold} Ouro e ${d.magic} Magia.`;
  if (event.type === "city_life_raised") return `J${d.player_id} aumentou a Cidade de ${d.life_before} para ${d.life_after}.`;
  if (event.type === "monument_built") return `J${d.player_id} construiu um Monumento.`;
  if (event.type === "unit_summoned") return `J${d.player_id} invocou ${unitName(d.unit || {})}.`;
  if (event.type === "unit_moved") return `${unitName(d.unit || {id:d.unit_id})} foi para ${HOUSE_NAMES[d.destination] || d.destination}.`;
  if (event.type === "player_turn_ended") return `J${d.player_id} encerrou sua janela do Dia.`;
  if (event.type === "artifact_obtained") return d.pending_choice ? "Escolha de artefato pendente." : `Artefato obtido: ${cardName(d.card_id)}.`;
  if (event.type === "artifact_sold") return `J${d.player_id} vendeu ${cardName(d.card_id)}.`;
  if (event.type === "interaction_resolved") {
    const labels = {play_artifact: "jogou", resolve_artifact_choice: "resolveu a escolha de artefato",
      use_pena: "usou uma Pena", use_heal: "aplicou uma cura", hero_ability: "usou uma habilidade",
      demon_pact: "firmou um pacto", decline_pact: "recusou um pacto",
      cast_spell: "usou um feitiço", sacrifice_spell: "usou Sacrifício de Demônio",
      allocate_bets: "confirmou as apostas",
      day_attack: "atacou durante o Dia com Miyamoto",
      dream_multi: "usou Sonho Lúcido com Luna",
      reroll_spell: "rerrolou o feitiço copiado"};
    const pact = d.pact_id && (catalog?.pacts?.find(p => p.id === d.pact_id)?.name || d.pact_id);
    return `J${d.player_id} ${labels[d.action_type] || "concluiu uma ação"}${d.card_id ? ` ${cardName(d.card_id)}` : ""}${pact ? `: ${pact}` : ""}.`;
  }
  return event.type;
}
function renderEvents(events) {
  rememberPublicUnitNames(currentView, events);
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
    if (!text.textContent) return;
    const meta = document.createElement("small"); meta.textContent = `Turno ${event.turn} · ${phaseName(event.phase)}`;
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
  currentView = view;
  const [actions, events] = await Promise.all([api(`/matches/${matchId}/actions?player_id=${playerId}`), api(`/matches/${matchId}/events?player_id=${playerId}`)]);
  rememberPublicUnitNames(view, events);
  const active = view.players.find(p => p.id === view.active_player_id);
  $("status").textContent = `Turno ${view.turn} · ${view.phase === "day" ? "Dia" : "Noite"} · Jogando: ${active?.name || "—"} · ${curunaLabel(view, peopleName)}`;
  if (view.self.armor_reaction) $("status").textContent += " · Armadura: resolução aguardando pagamento";
  if (view.game_over) {
    const winner = view.players.find(p => p.id === view.winner_id);
    $("status").textContent = `Partida encerrada · Vencedor: ${winner?.name || "sem vencedor"}`;
  }
  if (view.night_limitations?.length)
    $("status").textContent += " · Noite ainda indisponível: " + view.night_limitations.join(" ");
  if (view.night_window?.house) {
    const names = view.night_window.declaration_order.map(id =>
      view.players.find(p => p.id === id)?.name || `J${id}`).join(" → ");
    const windowLabel = view.night_window.kind === "luide" ? "Janela de Luide" : "Declarações";
    $("status").textContent += ` · ${windowLabel}: ${HOUSE_NAMES[view.night_window.house] || view.night_window.house} · Ordem restante: ${names || "nenhuma"}`;
  } else if (view.phase === "night" && !view.game_over && view.night_window?.kind) {
    const labels = {pending_choice:"Escolha pendente", vovo:"Vovó: ordem de combate",
      aiquara:"Aiquara: controle", luna:"Luna: retorno", ainai:"Ainai: teleporte",
      besouro:"Besouro: Mandinga", clock:"Rogue: Relógio de bolso", finish:"Encerramento da noite"};
    if (labels[view.night_window.kind]) $("status").textContent += ` · ${labels[view.night_window.kind]}`;
  }
  $("players").replaceChildren();
  const presence = hudPresence(view);
  const leader = document.createElement("p"); leader.className = "curuna-banner";
  leader.textContent = curunaLabel(view, peopleName);
  $("players").appendChild(leader);
  view.players.forEach(p => {
    const node = document.createElement("div");
    node.className = `player ${p.id === view.active_player_id ? "active" : ""}`;
    node.textContent = `${p.id === view.curuna_id ? "★ CURRUNA · " : ""}${p.id === view.active_player_id ? "▶ Jogando · " : ""}J${p.id} ${p.name} — ${peopleName(p.people)} · Herói: ${heroName(p.chosen_hero_id) || "escolha em jogo"} · Vida ${p.city.life}/${p.city.life_max} · Ouro ${p.city.gold} · Magia ${p.city.magic} · Em campo: ${(p.field_artifacts || []).map(cardName).join(", ") || "nenhum"}${presence.canastra ? ` · Canastra: ${(p.canastra || []).map(cardName).join(", ") || "vazia"}` : ""}`;
    $("players").appendChild(node);
  });
  const hand = view.self.hand.length ? view.self.hand.map(cardName).join(" · ") : "vazia";
  const suits = {H:"Copas", D:"Ouros", C:"Paus", S:"Espadas"};
  const bets = Object.entries(view.self.bets).filter(([, target]) => target).map(([suit,target]) => `${suits[suit] || suit} → J${target} ${view.players.find(p => p.id === target)?.name || ""}`).join(" · ") || "nenhuma";
  const pending = view.self.pending_choice ? " | Resolva a escolha pendente nas ações abaixo." : "";
  const deferredPacts = view.phase === "night" && view.self.demon_pact_offers?.some(o => o.source === "belial");
  const readyPacts = view.self.demon_pact_offers?.some(o => view.phase !== "night" || o.source !== "belial");
  const offers = presence.pacts ? (readyPacts ? " | Há uma oferta de pacto nas ações abaixo." : "")
    + (deferredPacts ? " | Pacto de Belial disponível na sua jogada do próximo Dia." : "") : "";
  const copiedSpell = view.self.spell_copia_id ? ` | Feitiço copiado: ${view.self.spell_copia_id.replaceAll("_", " ")}` : "";
  $("self").textContent = `Mão: ${hand}${presence.bets ? ` | Apostas: ${bets} | Corretas: ${view.self.correct_bets}` : ""} | Curas: ${view.self.pending_heals || 0}${copiedSpell}${pending}${offers}`;
  if (presence.pacts) {
    const pacts = document.createElement("p");
    pacts.textContent = `Pactos: ${(view.demon_pacts || []).map(p => pactLabel(p, catalog, peopleName)).join(" · ") || "nenhum firmado"}`;
    $("self").appendChild(pacts);
  }
  $("self").appendChild(document.createElement("br"));
  const extra = document.createElement("span");
  extra.textContent = `Feitiço disponível a partir de T${view.self.spell_cooldown_until_turn} · ${view.self.has_cast_spell_this_turn ? "já usado neste turno" : "não usado"}${view.self.baoba_payments ? ` · Baobá: ${view.self.baoba_payments}/3 pagamentos` : ""}${view.self.rogue_items?.length ? ` · Rogue: ${view.self.rogue_items.map(rogueItemName).join(", ")}` : ""}${view.self.inherited_peoples?.length ? ` · Passivas de São Tomé: ${view.self.inherited_peoples.map(peopleName).join(", ")}` : ""}`;
  $("self").appendChild(extra);
  ["undo", "mola"].forEach(id => { $(id).disabled = !view.local_controls?.[id]; });
  renderReports(view);
  renderMap(view); renderActions(actions); renderEvents(events);
  annotateShortcuts();
}
async function act(action) {
  if (action.type === "end_turn" && !await confirmAction("Encerrar a janela deste jogador?")) return;
  if (action.type === "finish_night" && !await confirmAction("Encerrar a Noite e avançar o turno?")) return;
  if (["demon_pact", "night_pact"].includes(action.type) &&
      !await confirmAction(`Firmar pacto: ${actionDetails(action) || action.label}. ${pactChoiceText(action, catalog)}`)) return;
  const controls = [...document.querySelectorAll("#actions button")].map(button => [button, button.disabled]);
  try {
    controls.forEach(([button]) => button.disabled = true);
    const result = await api(`/matches/${matchId}/actions`, {method:"POST", body:JSON.stringify(action)});
    $("message").textContent = result.pending ? "Resolução pausada para escolher o pagamento da Armadura." : "Ação concluída.";
    if (result.save_warning) $("message").textContent += ` ${result.save_warning}`;
    await refresh();
  } catch (error) {
    $("message").textContent = error.message;
    controls.forEach(([button, disabled]) => button.disabled = disabled);
  }
}
async function enter(id) { publicUnitNames.clear(); matchId=id; $("start").hidden=true; $("game").hidden=false; await refresh(); }
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
    const help = document.createElement("button");
    help.type = "button"; help.textContent = "Consultar povo e heróis";
    help.dataset.shortcut = `Alt+${index+1}`;
    help.onclick = () => showHelp(peopleSelect.value);
    row.appendChild(help);
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
             gold:+$("goldStart").value, magic:+$("magicStart").value,
             order_mode:$("orderMode").value},
  };
}

function showHelp(peopleId = null) {
  const root = $("helpContent");
  root.replaceChildren();
  const line = (parent, text, tag = "p") => {
    const node = document.createElement(tag); node.textContent = text; parent.appendChild(node);
  };
  const section = title => {
    const node = document.createElement("details"), heading = document.createElement("summary");
    heading.textContent = title; node.appendChild(heading); root.appendChild(node); return node;
  };
  line(root, "Consulta da implementação atual. Valores podem mudar com o balanceamento. O motor valida custos, alvos e restrições; somente ações legais são oferecidas.");
  if (!peopleId) {
    const rules = section("Regras gerais e custos"); rules.open = true;
    (catalog.rules || []).forEach(text => line(rules, text));
  }
  catalog.peoples.filter(p => !peopleId || p.id === peopleId).forEach(p => {
    const block = section(p.label); block.open = Boolean(peopleId);
    line(block, p.passive);
    if (p.spell) line(block, `${p.spell.name}: ${p.spell.description}`);
    (catalog.heroes || p.heroes).filter(h => !h.people || h.people === p.id).forEach(h => {
      line(block, `${h.name} · vida base ${h.life}`, "h3"); line(block, h.description);
    });
  });
  if (!peopleId) {
    const cards = section("Artefatos");
    catalog.artifacts.forEach(a => { line(cards, a.name, "h3"); line(cards, a.description); });
    const conditions = section("Condições");
    Object.entries(catalog.conditions).forEach(([name, text]) => line(conditions, `${name}: ${text}`));
    const pacts = section("Pactos e itens de Rogue");
    catalog.pacts.forEach(p => line(pacts, `${p.name}: ${p.description}`));
    Object.entries(catalog.rogue_items).forEach(([name, text]) => line(pacts, `${rogueItemName(name)}: ${text}`));
  }
  $("helpDialog").showModal();
  $("closeHelp").focus();
}

function confirmAction(message) {
  const dialog = $("confirmDialog");
  if (dialog.open) return Promise.resolve(false);
  $("confirmText").textContent = message;
  return new Promise(resolve => {
    const finish = accepted => { dialog.close(); resolve(accepted); };
    $("confirmAccept").onclick = () => finish(true);
    $("confirmCancel").onclick = () => finish(false);
    dialog.oncancel = event => { event.preventDefault(); finish(false); };
    dialog.showModal(); $("confirmCancel").focus();
  });
}

function renderReports(view) {
  const root = $("reports"); root.replaceChildren();
  const controls = document.createElement("div"); controls.className = "report-controls";
  const label = document.createElement("label"); label.textContent = "Relatório ";
  const select = document.createElement("select"); select.setAttribute("aria-label", "Escolher relatório");
  Object.entries(REPORT_NAMES).forEach(([key,name]) => select.appendChild(new Option(name,key)));
  select.value = reportSelection;
  select.onchange = () => { reportSelection = select.value; reportMetric = ""; renderReports(currentView); root.querySelector("select").focus(); };
  label.appendChild(select); controls.appendChild(label); root.appendChild(controls);
  if (REPORT_FIELDS[reportSelection]) {
    const fields = REPORT_FIELDS[reportSelection];
    if (!fields[reportMetric]) reportMetric = Object.keys(fields)[0];
    const metricLabel = document.createElement("label"); metricLabel.textContent = "Gráfico ";
    const metric = document.createElement("select"); metric.setAttribute("aria-label", "Escolher indicador do gráfico");
    Object.entries(fields).forEach(([key,name]) => metric.appendChild(new Option(name,key)));
    metric.value = reportMetric;
    metric.onchange = () => { reportMetric = metric.value; renderReports(currentView); root.querySelectorAll("select")[1].focus(); };
    metricLabel.appendChild(metric); controls.appendChild(metricLabel);
    drawReport(root, view, reportSelection, reportMetric); return;
  }
  const line = text => { const p = document.createElement("p"); p.textContent = text; root.appendChild(p); };
  if (reportSelection === "conditions") {
  let count = 0;
  view.board.units.filter(u => publicStates(u).length).forEach(u =>
    { count++; line(`J${u.owner_id} · ${unitName(u)} · ${HOUSE_NAMES[u.house]} · ${publicStates(u).join(" · ")}`); });
  (view.conditions || []).forEach(c => {
    count++;
    const sig = c.signature || {};
    line(`${c.condition} · ${sig.kind === "hero" ? heroName(sig.id) : troopNames[sig.id] || sig.id} · J${c.owner_id ?? "?"}${c.controller_id ? ` · infectado por J${c.controller_id}` : ""}${c.release_curuna_id ? ` · libera quando J${c.release_curuna_id} for Curuna` : ""}`);
  });
  if (!count) line("Nenhuma condição pública registrada.");
  return;
  }
  view.players.forEach(p => {
    const title = document.createElement("h3"); title.textContent = p.name; root.appendChild(title);
    if (p.armor_active_until_turn >= view.turn) line("Armadura de Ouro ativa: cada golpe permite escolher o pagamento.");
    if (p.spell_cooldown_until_turn > view.turn) line(`Feitiço disponível em T${p.spell_cooldown_until_turn}.`);
    if (p.next_monument_turn != null) line(`Monumento: próximo artefato em T${p.next_monument_turn}.`);
    if (p.skip_day_turn != null || p.skip_night_turn != null) line(`Dia pulado: ${p.skip_day_turn ?? "nenhum"} · Noite pulada: ${p.skip_night_turn ?? "nenhuma"}`);
    (p.active_artifacts || []).forEach(a => {
      const details = Object.entries(a.details).map(([key, value]) => key === "target_player_id" || key === "original_owner_id" ? `Jogador ${value}` : unitName(view.board.units.find(u => u.id === value) || {id:value}));
      line(`${cardName(a.card_id)}${details.length ? ` · ${details.join(" · ")}` : ""}`);
    });
  });
  line(`Loja: ${view.shop.size} artefatos · ${Object.entries(view.shop.counts || {}).sort().map(([id, count]) => `${cardName(id)}: ${count}`).join(" · ")}`);
  (view.scheduled_effects || []).forEach(e => line(`J${e.player_id}: ${cardName(e.kind)} previsto para T${e.due_turn}.`));
  line(view.turn < 13 ? "A partir de T13 não se pode aumentar Muralha." : "T13+: aumentar Muralha está bloqueado.");
}

function createGameplayControls() {
  const button = (root, text, handler, id = null) => {
    const node = document.createElement("button"); node.type = "button"; node.textContent = text;
    if (id) node.id = id; node.onclick = handler; root.appendChild(node); return node;
  };
  button($("start"), "Consultar todos os povos e artefatos", () => showHelp(), "setupRules");
  const toolbar = $("save").parentElement;
  button(toolbar, "Consultar regras", () => showHelp(), "rulesButton");
  ["undo", "mola"].forEach(operation => button(toolbar,
    operation === "undo" ? "Refazer meu Dia" : "Mola: jogador anterior", async () => {
      if (!await confirmAction("Restaurar estado, recursos e RNG? Ações posteriores a esse ponto serão desfeitas.")) return;
      try {
        const result = await api(`/matches/${matchId}/system`, {method:"POST", body:JSON.stringify({operation})});
        $("message").textContent = `Jogada restaurada.${result.save_warning ? ` ${result.save_warning}` : ""}`; await refresh();
      } catch (error) { $("message").textContent = error.message; }
    }, operation));
  button(toolbar, "Nova partida", async () => {
    if (!await confirmAction("Voltar à configuração? A partida atual fica preservada no autosave.")) return;
    $("game").hidden = true; $("start").hidden = false;
    currentView = null; matchId = null;
    refreshSaves().catch(error => { $("setupMessage").textContent = error.message; });
  }, "newGame");
  const reports = document.createElement("details"); reports.className = "card";
  const title = document.createElement("summary"); title.id = "reportsToggle"; title.textContent = "Condições e relatórios da partida";
  const body = document.createElement("div"); body.id = "reports"; reports.append(title, body);
  $("game").appendChild(reports);
  button(toolbar, "Relatórios", () => { reports.open = !reports.open; if (reports.open) title.focus(); }, "reportsButton");
  const map = $("minimap");
  const viewport = document.createElement("div"); viewport.className = "map-viewport";
  viewport.tabIndex = 0; viewport.setAttribute("aria-label", "Mapa rolável; use as setas ou os botões de casas");
  map.before(viewport); viewport.appendChild(map);
  const mapCuruna = document.createElement("p"); mapCuruna.id = "mapCuruna"; mapCuruna.className = "curuna-banner";
  const navigation = document.createElement("nav"); navigation.id = "mapNavigation";
  navigation.setAttribute("aria-label", "Ir para uma casa do mapa");
  viewport.before(mapCuruna, navigation);
  button(toolbar, "Mapa", () => { viewport.scrollLeft = (viewport.scrollWidth - viewport.clientWidth)/2; viewport.focus(); viewport.scrollIntoView({block:"center"}); }, "mapToggle");
  const mapHint = document.createElement("p"); mapHint.className = "hint";
  mapHint.textContent = "Ícones: tropas 32px, heróis 64px. Toque, foque ou passe o mouse para inspecionar. Arraste o mapa nas telas estreitas; cada casa tem sua própria rolagem de unidades. Atalhos aparecem ao passar o mouse nos botões.";
  viewport.before(mapHint);
  const order = document.createElement("label"); order.textContent = "Ordem inicial ";
  const select = document.createElement("select"); select.id = "orderMode";
  select.append(new Option("D20 — como no terminal", "d20"), new Option("Fixa J1 → J2 → J3 → J4", "fixed"));
  order.appendChild(select); $("seed").parentElement.after(order);
  const preview = document.createElement("p"); preview.className = "hint"; order.after(preview);
  const updateOrder = async () => {
    try {
      const data = await api(`/setup-order?seed=${encodeURIComponent($("seed").value)}`);
      preview.textContent = select.value === "fixed" ? "Ordem de turno: J1 → J2 → J3 → J4" :
        `Curuna inicial: J${data.initial_curuna_id} · Primeiro Dia: ${data.day_order.map(id => `J${id}`).join(" → ")} · Escolha de povos: ${data.selection_order.map(id => `J${id}`).join(" → ")}`;
    } catch (error) { preview.textContent = error.message; }
  };
  $("seed").onchange = updateOrder; select.onchange = updateOrder; updateOrder();
  $("closeHelp").onclick = () => $("helpDialog").close();
  const saveLabel = document.createElement("label"); saveLabel.textContent = "Nome do save ";
  const saveName = document.createElement("input"); saveName.id = "saveName";
  saveName.maxLength = 60; saveName.value = "Partida local"; saveLabel.appendChild(saveName);
  toolbar.appendChild(saveLabel);
}
$("create").onclick = async () => {
  try {
    $("setupMessage").textContent = "";
    const created = await api("/matches", {method:"POST", body:JSON.stringify(setupPayload())});
    await enter(created.match_id);
    $("message").textContent = created.save_warning || "";
  } catch (error) { $("setupMessage").textContent = error.message; }
};
$("load").onclick = async () => {
  try {
    const loaded = await api("/matches/load", {method:"POST", body:JSON.stringify({save_id:$("saveId").value})});
    await enter(loaded.match_id);
    $("message").textContent = loaded.save_warning || "";
  } catch (error) { $("setupMessage").textContent = error.message; }
};
$("save").textContent = "Salvar cópia";
$("save").onclick = async () => {
  const name = $("saveName").value;
  try {
    const data = await api(`/matches/${matchId}/save`, {method:"POST", body:JSON.stringify({name})});
    $("message").textContent = `Cópia salva: ${name} (${data.save_id}). O autosave continua separado.`;
    await refreshSaves();
  } catch (error) { $("message").textContent = error.message; }
};

async function refreshSaves() {
  const entries = await api("/saves");
  const select = $("savedGames");
  const selected = select.value;
  const filter = $("saveFilter").value;
  select.replaceChildren(new Option("Escolha uma partida salva", ""));
  entries.filter(entry => filter === "all" || (entry.kind === "recovery" ? filter === "recovery" : filter === "main")).forEach(entry => {
    const kind = {manual:"cópia", autosave:"autosave", recovery:"recuperação anterior"}[entry.kind] || entry.kind;
    const label = entry.invalid ? `${entry.name} (${entry.save_id})` :
      `${entry.name} · T${entry.turn} ${entry.phase === "day" ? "Dia" : "Noite"} · ${kind} · ${new Date(entry.updated_at).toLocaleString("pt-BR")}`;
    const option = new Option(label, entry.save_id);
    option.disabled = Boolean(entry.invalid);
    select.appendChild(option);
  });
  if ([...select.options].some(option => option.value === selected)) select.value = selected;
}

function createSaveControls() {
  const filterLabel = document.createElement("label"); filterLabel.textContent = "Mostrar saves ";
  const filter = document.createElement("select"); filter.id = "saveFilter";
  filter.append(new Option("Partidas e cópias", "main"), new Option("Recuperações anteriores", "recovery"), new Option("Todos", "all"));
  filter.onchange = () => refreshSaves().catch(error => { $("setupMessage").textContent = error.message; });
  filterLabel.appendChild(filter);
  const label = document.createElement("label");
  label.textContent = "Partidas salvas ";
  const select = document.createElement("select");
  select.id = "savedGames";
  select.onchange = () => { $("saveId").value = select.value; };
  label.appendChild(select);
  const update = document.createElement("button");
  update.id = "refreshSaves";
  update.textContent = "Atualizar lista";
  update.onclick = () => refreshSaves().catch(error => { $("setupMessage").textContent = error.message; });
  const importLabel = document.createElement("label");
  importLabel.textContent = "Importar save web ou terminal (.json) ";
  const file = document.createElement("input");
  file.type = "file";
  file.accept = ".json,application/json";
  file.onchange = async () => {
    const selected = file.files[0];
    if (!selected) return;
    try {
      if (selected.size > 10 * 1024 * 1024) throw new Error("Arquivo excede o limite de 10 MB.");
      const payload = JSON.parse(await selected.text());
      const imported = await api("/matches/import", {method:"POST", body:JSON.stringify(payload)});
      await enter(imported.match_id);
      $("message").textContent = imported.warnings?.join(" ") || "Partida importada.";
      if (imported.save_warning) $("message").textContent += ` ${imported.save_warning}`;
    } catch (error) { $("setupMessage").textContent = error.message; }
    finally { file.value = ""; }
  };
  importLabel.appendChild(file);
  const controls = document.createElement("div");
  controls.className = "save-controls";
  controls.append(filterLabel, label, update, importLabel);
  $("start").appendChild(controls);
  const hint = document.createElement("p"); hint.className = "hint";
  hint.textContent = "Recuperação: cinco autosaves anteriores por partida; cópias manuais não são substituídas. Saves do terminal precisam identificar uma jogada diurna já iniciada. Uma Noite sem fila de declarações não pode ser retomada com segurança.";
  $("start").appendChild(hint);
  const exportButton = document.createElement("button");
  exportButton.id = "exportGame";
  exportButton.textContent = "Exportar partida";
  exportButton.title = "Baixar estado completo, incluindo mãos dos jogadores";
  exportButton.onclick = async () => {
    try {
      const payload = await api(`/matches/${matchId}/export`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], {type:"application/json"}));
      const link = document.createElement("a");
      link.href = url;
      link.download = `jessica-${matchId}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      $("message").textContent = "Arquivo completo exportado, incluindo as mãos dos jogadores.";
    } catch (error) { $("message").textContent = error.message; }
  };
  $("save").parentElement.appendChild(exportButton);
}
$("revealPlayer").onclick = async () => {
  playerId = pendingPlayerId;
  pendingPlayerId = null;
  $("handoff").hidden = true;
  $("game").inert = false;
  await refresh(true);
  const next = $("actions").querySelector("input, select, button");
  if (next) { next.focus(); next.scrollIntoView({block:"nearest"}); }
};
createSaveControls();
createGameplayControls();
installShortcuts();
api("/catalog").then(async data => { catalog = data; renderSetup(); await refreshSaves(); }).catch(error => { $("setupMessage").textContent = error.message; });
