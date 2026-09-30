const REPORT_FIELDS = {
  production: {gold_collected:"Ouro coletado", magic_collected:"Magia coletada", troops_summoned:"Tropas invocadas", heroes_summoned:"Heróis invocados", spells_cast:"Feitiços"},
  combat: {damage_dealt:"Dano causado", damage_taken:"Dano recebido", kills:"Abates", deaths:"Mortes"},
  artifacts: {artifacts_bought:"Comprados", artifacts_played:"Jogados", artifacts_sold:"Vendidos"},
  economy: {gold:"Ouro", magic:"Magia", life:"Vida da Base"},
};
const REPORT_NAMES = {conditions:"Condições das unidades", production:"Produção e invocações", combat:"Combate", artifacts:"Artefatos", economy:"Evolução por turno", info:"Efeitos, recargas e loja"};
let reportSelection = "conditions", reportMetric = "";
function hudPresence(view) {
  const peoples = new Set(view.players.map(p => p.people));
  return {bets:peoples.has("gnomos_duendes"), canastra:peoples.has("dragoes"), pacts:peoples.has("demonios")};
}
function curunaLabel(view, name) {
  const p = view.players.find(p => p.id === view.curuna_id);
  return p ? `★ Curruna: J${p.id} ${p.name} · ${name(p.people)}` : "Curruna não informado";
}
function pactLabel(pact, reference, name) {
  const label = reference?.pacts?.find(p => p.id === pact.pact_id)?.name || pact.pact_id;
  const status = pact.released ? "liberado" : pact.completed ? "concluído" : "em andamento";
  const progress = pact.required_peoples ? ` · povos registrados: ${(pact.killed_peoples || []).map(name).join(", ") || "nenhum"} · exigidos: ${pact.required_peoples.map(name).join(", ")}` :
    pact.blood_count != null ? ` · ${pact.blood_count} abates registrados${pact.blood_turn > 0 ? ` na noite T${pact.blood_turn}` : ""}` : "";
  return `${label} · J${pact.owner_id} · ${status}${progress}`;
}
function reportData(view, kind, metric) {
  const fields = REPORT_FIELDS[kind], keys = Object.keys(fields);
  const number = value => typeof value === "number" && Number.isFinite(value) ? value : null;
  const players = view.players.map(p => ({id:p.id, label:`J${p.id} ${p.name}`}));
  const counter = (p,k) => p.stats == null ? null : k in p.stats ? number(p.stats[k]) : 0;
  if (kind === "economy") {
    const timeline = view.timeline || [];
    return {title:fields[metric], headers:["Turno", "Jogador", ...Object.values(fields)],
      rows:timeline.flatMap(t => players.map(p => [`T${t.turn}`, p.label, ...keys.map(k => number(t.resources?.[p.id]?.[k]))])),
      series:players.map(p => ({label:p.label, points:timeline.map(t => ({turn:t.turn, value:number(t.resources?.[p.id]?.[metric])}))}))};
  }
  return {title:fields[metric], headers:["Jogador", ...Object.values(fields)],
    rows:view.players.map((p,i) => [players[i].label, ...keys.map(k => counter(p,k))]),
    bars:view.players.map((p,i) => ({label:players[i].label, value:counter(p,metric)}))};
}
function drawReport(root, view, kind, metric) {
  const data = reportData(view, kind, metric);
  const heading = document.createElement("h3"); heading.textContent = data.title; root.appendChild(heading);
  const note = document.createElement("p"); note.className = "hint";
  note.textContent = kind === "economy" ? "Registros públicos ao fim de cada turno. Sem registro, nenhum ponto é inventado." : "Totais públicos acumulados na partida. Contadores ainda não registrados valem zero, como no terminal; dados indisponíveis aparecem como —.";
  root.appendChild(note);
  const wrap = document.createElement("div"); wrap.className = "report-table-scroll";
  const table = document.createElement("table"); table.className = "report-table";
  const caption = document.createElement("caption"); caption.textContent = REPORT_NAMES[kind]; table.appendChild(caption);
  const header = document.createElement("thead"), headerRow = document.createElement("tr");
  data.headers.forEach(text => { const th = document.createElement("th"); th.scope = "col"; th.textContent = text; headerRow.appendChild(th); });
  header.appendChild(headerRow); table.appendChild(header);
  const body = document.createElement("tbody");
  data.rows.forEach(row => {
    const tr = document.createElement("tr");
    row.forEach((value,i) => { const cell = document.createElement(i === 0 ? "th" : "td"); if (i === 0) cell.scope = "row"; cell.textContent = value ?? "—"; tr.appendChild(cell); });
    body.appendChild(tr);
  });
  table.appendChild(body); wrap.appendChild(table); root.appendChild(wrap);
  const values = data.bars ? data.bars.map(b => b.value) : data.series.flatMap(s => s.points.map(p => p.value));
  if (!values.some(v => v !== null)) {
    const empty = document.createElement("p"); empty.textContent = "Ainda não há dados para este gráfico."; root.appendChild(empty); return;
  }
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const height = data.bars ? 52 + data.bars.length * 45 : 280;
  svg.setAttribute("viewBox", `0 0 720 ${height}`); svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `${data.title}: comparação dos jogadores. Valores completos na tabela.`);
  svg.classList.add("report-chart");
  const add = (tag, attrs, text) => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs).forEach(([key,value]) => node.setAttribute(key, String(value)));
    if (text != null) node.textContent = text; svg.appendChild(node); return node;
  };
  const max = Math.max(1, ...values.filter(v => v !== null));
  if (data.bars) {
    data.bars.forEach((b,i) => {
      const y = 30 + i * 45;
      add("text", {x:8, y:y+19}, b.label.length > 27 ? b.label.slice(0,26)+"…" : b.label);
      if (b.value !== null) add("rect", {x:230, y, width:Math.max(0,b.value/max*420), height:28, fill:"#d0a75d"});
      add("text", {x:665, y:y+19}, b.value ?? "—");
    });
  } else {
    const turns = data.series.flatMap(s => s.points.map(p => p.turn));
    const first = Math.min(...turns), last = Math.max(...turns);
    const x = turn => 50 + (turn-first)/Math.max(1,last-first)*580, y = value => 222-value/max*180;
    const colors = ["#e0bb72", "#85cdbc", "#9aaeff", "#ffa68d"], dashes = ["none", "8 4", "2 4", "12 3 2 3"];
    add("path", {d:"M50 35V222H650", fill:"none", stroke:"#aec1bc"});
    add("text", {x:8, y:42}, max); add("text", {x:24, y:226}, "0");
    [...new Set(turns)].filter((t,i,a) => i % Math.max(1,Math.ceil(a.length/10)) === 0 || i === a.length-1).forEach(t => add("text", {x:x(t), y:244, "text-anchor":"middle"}, `T${t}`));
    data.series.forEach((s,i) => {
      let segment = [];
      const flush = () => { if (segment.length) add("polyline", {points:segment.join(" "), fill:"none", stroke:colors[i%4], "stroke-width":3, "stroke-dasharray":dashes[i%4]}); segment=[]; };
      s.points.forEach(p => {
        if (p.value === null) { flush(); return; }
        segment.push(`${x(p.turn)},${y(p.value)}`);
        const point = add("circle", {cx:x(p.turn), cy:y(p.value), r:4, fill:colors[i%4]});
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title"); title.textContent = `${s.label} · T${p.turn}: ${p.value}`; point.appendChild(title);
      });
      flush();
      add("line", {x1:10+i*180, x2:30+i*180, y1:270, y2:270, stroke:colors[i%4], "stroke-width":3, "stroke-dasharray":dashes[i%4]});
      add("text", {x:35+i*180, y:275}, s.label.length > 17 ? s.label.slice(0,16)+"…" : s.label);
    });
  }
  const chartWrap = document.createElement("div"); chartWrap.className = "report-chart-scroll";
  chartWrap.appendChild(svg); root.appendChild(chartWrap);
}

const ACTION_KEYS = {collect_resources:"1", raise_city_life:"2", summon_troop:"3", summon_hero:"4", move_unit:"5", buy_artifact_gold:"6", transmute_artifact_magic:"7", sell_artifact:"8", cast_spell:"9", end_turn:"0"};
const BUTTON_KEYS = {save:"Alt+S", load:"Alt+L", create:"Alt+N", rulesButton:"Alt+H", setupRules:"Alt+H", refreshSaves:"Alt+U", reportsToggle:"Alt+R", reportsButton:"Alt+R", mapToggle:"Alt+M", undo:"Alt+Z", mola:"Alt+Y", exportGame:"Alt+E", newGame:"Alt+N", revealPlayer:"Alt+P", closeHelp:"Escape", confirmAccept:"Alt+Enter", confirmCancel:"Escape"};
function shortcutFor(node) {
  if (BUTTON_KEYS[node.id]) return BUTTON_KEYS[node.id];
  if (node.dataset.shortcut) return node.dataset.shortcut;
  if (node.dataset.mapHouse) return `Alt+Shift+${["center","city_1","city_2","city_3","city_4"].indexOf(node.dataset.mapHouse)+1}`;
  const group = node.closest(".action-group");
  if (group && node.tagName === "SUMMARY") return ACTION_KEYS[group.dataset.actionType] || node.dataset.auxKey || "";
  if (group && node.tagName === "BUTTON") {
    const i = [...group.querySelectorAll("button")].indexOf(node);
    if (i < 9) return `Alt+${i+1}`;
  }
  return "";
}
function annotateShortcuts() {
  let extra = 0;
  document.querySelectorAll(".action-group summary").forEach(node => {
    const type = node.closest(".action-group").dataset.actionType;
    node.dataset.auxKey = !ACTION_KEYS[type] && extra < 26 ? `Alt+Shift+${"ABCDEFGHIJKLMNOPQRSTUVWXYZ"[extra++]}` : "";
  });
  document.querySelectorAll("button, summary").forEach(node => {
    const key = shortcutFor(node);
    if (!node.dataset.baseTitle) node.dataset.baseTitle = node.title || " ";
    const hint = key ? `Atalho: ${key}${node.closest(".action-group") && node.tagName === "BUTTON" ? " dentro desta ação" : ""}` : "";
    node.title = [node.dataset.baseTitle.trim(), hint, "Enter/Espaço quando focado"].filter(Boolean).join(" · ");
    node.setAttribute("aria-keyshortcuts", key || "Enter Space");
  });
}
function shortcutScope(node, doc) {
  if (node.disabled || node.closest("[hidden], [inert]")) return false;
  const modal = doc.querySelector("dialog[open]");
  if (modal && !modal.contains(node)) return false;
  const handoff = doc.getElementById("handoff");
  if (handoff && !handoff.hidden && !handoff.contains(node)) return false;
  return node.getClientRects().length > 0;
}
function handleShortcut(event, doc = document) {
  if (event.repeat || event.ctrlKey || event.metaKey || event.isComposing) return;
  const editable = event.target.closest("input, select, textarea, [contenteditable]");
  if (editable && !event.altKey) return;
  const digit = /^Digit[0-9]$/.test(event.code || "") ? event.code.slice(5) : null;
  const key = `${event.altKey ? "Alt+" : ""}${event.shiftKey ? "Shift+" : ""}${digit ?? (event.key.length === 1 ? event.key.toUpperCase() : event.key)}`;
  const focusedGroup = doc.activeElement?.closest(".action-group");
  const found = [...doc.querySelectorAll("button, summary")].find(node => {
    if (shortcutFor(node) !== key || !shortcutScope(node, doc)) return false;
    return !node.closest(".action-group") || node.tagName === "SUMMARY" || node.closest(".action-group") === focusedGroup;
  });
  if (!found) return;
  event.preventDefault();
  if (found.tagName === "SUMMARY" && found.closest(".action-group")) {
    const group = found.closest(".action-group"); group.open = true;
    (group.querySelector("select, input, button:not(:disabled)") || found).focus();
  } else found.click();
}
function installShortcuts() {
  document.addEventListener("keydown", handleShortcut);
  new MutationObserver(annotateShortcuts).observe(document.body, {childList:true, subtree:true});
  annotateShortcuts();
}
