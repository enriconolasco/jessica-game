const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

class Element {
  constructor(tag) { this.tag = tag; this.children = []; }
  appendChild(child) { this.children.push(child); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute() {}
}
const root = new Element("div");
const sent = [];
const context = vm.createContext({
  matchId: "preview-test",
  Option: function(text, value) { this.textContent = text; this.value = value; },
  document: {createElement: tag => new Element(tag), createTextNode: text => ({textContent:text})},
  $: () => root,
  act: action => sent.push(action),
  cardName: id => ({K_H:"Rei de Copas", K_D:"Rei de Ouros"}[id] || id),
  publicUnitName: (id, fallback) => fallback,
  HOUSE_NAMES:{center:"Centro"},
});
const source = fs.readFileSync(path.join(__dirname, "../jessica/web/static/app.js"), "utf8");
vm.runInContext(source.slice(source.indexOf("function actionDetails("),
                            source.indexOf("function eventText(")), context);
context.publicUnitName = (id, fallback) => id === 'luide' ? 'Luide Vampa' : fallback;
assert.equal(context.actionDetails({type:'night_luide_move',params:{unit_id:'luide',destination:'center'}}), 'Luide Vampa → Centro');
assert.equal(context.actionDetails({type:'night_luide_spell',params:{unit_id:'luide'}}), 'Feitiço vampiro: Luide Vampa');
const actions = [0, 1, 2].map(gold => ({
  type: "collect_resources", label: "Coletar recursos", player_id: 1,
  params: {gold, magic: 2 - gold},
}));
context.renderActions(actions);
const buttons = root.children[0].children.filter(el => el.tag === "button");
assert.deepEqual(buttons.map(b => b.textContent),
                 ["0 Ouro + 2 Magia", "1 Ouro + 1 Magia", "2 Ouro + 0 Magia"]);
buttons.forEach(button => button.onclick());
assert.deepEqual(sent, actions);
context.renderActions([]);
assert.equal(root.children.length, 0);
console.log("UI: três distribuições exibidas e enviadas corretamente.");
context.catalog = {pacts:[{id:"vida_lider", description:"Elimine um jogador."},
                         {id:"sacrifique_futuro", description:"Base atual e máxima em 4."}],
                   rogue_items:{bracelete:"Resistência contra heróis e +1 de vida."}};
const pactActions = [
  {type:"demon_pact",label:"Firmar pacto",description:"Vida de um líder · bracelete",player_id:1,
   params:{offer_index:0,pact_id:"vida_lider",item:"bracelete"}},
  {type:"demon_pact",label:"Firmar pacto",description:"Sacrifique seu futuro",player_id:1,
   params:{offer_index:0,pact_id:"sacrifique_futuro",item:null}},
];
context.renderActions(pactActions);
const pactGroup = root.children[0];
const pactSelect = pactGroup.children.find(el => el.tag === "select");
const pactPreview = pactGroup.children.find(el => el.tag === "p");
assert.match(pactPreview.textContent, /Elimine um jogador.*Bracelete.*Resistência/);
pactSelect.value = "1"; pactSelect.onchange();
assert.equal(pactPreview.textContent, "Base atual e máxima em 4.");
pactGroup.children.find(el => el.tag === "button").onclick();
assert.equal(sent.at(-1), pactActions[1]);
context.renderActions([{...pactActions[0], type:"night_pact"}]);
assert.match(root.children[0].children.find(el => el.tag === "p").textContent, /Bracelete/);
assert.equal(context.pactChoiceText({params:{pact_id:"unknown",item:"unknown"}}, {}),
             "unknown: efeito não disponível no catálogo");
console.log("UI: prévia de pacto/item atualiza e envia a escolha exata, sem calcular regras.");
(async () => {
const dream = {type:"dream_multi", label:"Luna", player_id:1, params:{}, selection:{options:[
  {label:"Primeira", choice:{flip_cards:["K_H"], artifact_choices:[{}]}},
  {label:"Segunda", choice:{flip_cards:["K_S"], artifact_choices:[{unit_id:"target"}]}},
]}};
context.renderActions([dream]);
const group = root.children[0];
const select = group.children.find(el => el.tag === "select");
const controls = group.children.filter(el => el.tag === "button");
assert.equal(controls[2].disabled, true);
const previews = [];
context.api = async (route, options) => {
  previews.push({route, body:JSON.parse(options.body)});
  return {options: [dream.selection.options[0]]};
};
select.value = "1";
await controls[0].onclick();
assert.equal(previews[0].route, "/matches/preview-test/dream-preview");
assert.equal(select.children.length, 1);
select.value = "0";
await controls[0].onclick();
controls[2].onclick();
assert.equal(JSON.stringify(sent.at(-1).params.choice), JSON.stringify({
  flip_cards:["K_S","K_H"], artifact_choices:[{unit_id:"target"},{}],
}));
controls[1].onclick();
assert.equal(group.children.find(el => el.tag === "ol").children.length, 0);
assert.equal(controls[2].disabled, true);
assert.equal(select.children.length, 2);
context.api = async () => { throw new Error("Prévia indisponível"); };
await controls[0].onclick();
assert.equal(group.children.find(el => el.tag === "ol").children.length, 0);
assert.equal(controls[0].disabled, false);
assert.equal(controls[1].disabled, false);
assert.equal(controls[2].disabled, true);
assert.equal(root.textContent, "Prévia indisponível");
console.log("UI: prévia, atualização dos alvos, ordem e limpeza da sequência de Luna verificadas.");

const sacrifice = {type:"sacrifice_spell", label:"Sacrifício", player_id:1,
  description:"Sacrificar Tuza", params:{hero_id:"tuza"}, selection:{kind:"artifacts", options:[
    {card_id:"K_H", zone:"hand", index:0}, {card_id:"K_D", zone:"field", index:0},
  ]}};
context.renderActions([sacrifice]);
const fieldset = root.children[0].children.find(el => el.tag === "fieldset");
const labels = fieldset.children.filter(el => el.tag === "label");
const sacrificeButton = fieldset.children.find(el => el.tag === "button");
const originalSent = sent.length;
let confirmationCount = 0;
context.confirmAction = async text => { confirmationCount++; assert.match(text, /Tuza/); return false; };
await sacrificeButton.onclick();
assert.equal(confirmationCount, 0);
assert.equal(sent.length, originalSent);
assert.match(root.textContent, /Selecione ao menos um/);
assert.equal(labels[0].children[1].textContent.trim(), "Rei de Copas · mão");
labels[1].children[0].checked = true;
await sacrificeButton.onclick();
assert.equal(sent.length, originalSent);
assert.equal(labels[1].children[0].checked, true);
context.confirmAction = async () => true;
await sacrificeButton.onclick();
assert.equal(JSON.stringify(sent.at(-1).params), JSON.stringify({
  hero_id:"tuza", artifacts:[sacrifice.selection.options[1]],
}));
assert.equal(sent.length, originalSent + 1);
assert.doesNotMatch(source, /\bconfirm\(/);
console.log("UI: Sacrifício valida seleção, permite cancelar e envia somente as cartas confirmadas.");

context.renderActions([{type:"armor_payment", label:"Armadura", player_id:2, params:{},
  selection:{damage:3, gold_available:5, max_gold:3, unit_name:"Tropa"}}]);
const armorGroup = root.children[0];
const armorInput = armorGroup.children.find(el => el.tag === "label").children[0];
const armorButton = armorGroup.children.find(el => el.tag === "button");
armorInput.reportValidity = () => false;
const armorBefore = sent.length;
armorInput.value = "4"; armorButton.onclick();
assert.equal(sent.length, armorBefore);
armorInput.reportValidity = () => true;
armorInput.value = "0"; armorButton.onclick();
assert.equal(sent.at(-1).params.gold, 0);
assert.equal(armorInput.max, "3");
console.log("UI: pagamento inválido da Armadura não é enviado; zero é preservado.");
})().catch(error => { console.error(error); process.exitCode = 1; });
