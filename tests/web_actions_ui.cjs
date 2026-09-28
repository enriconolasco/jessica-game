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
