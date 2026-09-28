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
  Option: function(text, value) { this.textContent = text; this.value = value; },
  document: {createElement: tag => new Element(tag)},
  $: () => root,
  act: action => sent.push(action),
});
const source = fs.readFileSync(path.join(__dirname, "../jessica/web/static/app.js"), "utf8");
vm.runInContext(source.slice(source.indexOf("function actionDetails("),
                            source.indexOf("function eventText(")), context);
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
const dream = {type:"dream_multi", label:"Luna", params:{}, selection:{options:[
  {label:"Primeira", choice:{flip_cards:["K_H"], artifact_choices:[{}]}},
  {label:"Segunda", choice:{flip_cards:["K_S"], artifact_choices:[{unit_id:"target"}]}},
]}};
context.renderActions([dream]);
const group = root.children[0];
const select = group.children.find(el => el.tag === "select");
const controls = group.children.filter(el => el.tag === "button");
select.value = "1";
controls[0].onclick();
select.value = "0";
controls[0].onclick();
controls[2].onclick();
assert.equal(JSON.stringify(sent.at(-1).params.choice), JSON.stringify({
  flip_cards:["K_S","K_H"], artifact_choices:[{unit_id:"target"},{}],
}));
controls[1].onclick();
assert.equal(group.children.find(el => el.tag === "ol").children.length, 0);
console.log("UI: ordem e limpeza da sequência de Luna verificadas.");
