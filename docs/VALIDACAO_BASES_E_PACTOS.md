# Bases Dragões e pactos de Rogue — 01/10/2026

Teste reproduzível: `python -B tests/test_special_matches_parity.py`.

| Seed | Participantes/heróis | Vitória | Decisões |
|---|---|---|---|
| 904 | Humanos/Miyamoto, Dragões/Barba Negra, Orcs/Vovó, Demônios/Rogue | T11 | 137 |
| 905 | Humanos/Miyamoto, Dragões/Valtherion, Orcs/Vovó, Demônios/Rogue | T12 | 184 |
| 906 | Demônios/Rogue, Dragões/Barba Negra, Orcs/Vovó, Fadas/Luna | T7 | 99 |

Mesma configuração das partidas mistas anteriores: Bases convencionais com 2
de vida, 25 Ouro/Magia, ordem fixa. Bases Dragões usam sua configuração própria
do motor. Não há edição do estado depois da preparação nem geração artificial
de cartas, pactos ou mortes.

Cada ação diurna compara estado, logs e RNG com o executor original. Cada Noite
executa também a orquestração terminal separadamente e compara seu resultado ao
roteiro web realmente escolhido. Cada decisão web atravessa save/load, validação
real do servidor, determinismo e consultas sem mutação.

Cobertura afirmada explicitamente pelos testes:

- Barba Negra prepara Mar de Chamas, ativa combate como herói e manipula Canastra.
- Valtherion manipula Canastra e invoca tropas por Chamado.
- Rogue firma pactos e recebe vida persistente/artefato ao firmar; reinvocação
  conserva vida e itens. O roteiro 906 firma a quest Vida de um Líder com Bracelete.
- Ao concluir essa quest, não há outra recompensa de pacto. O teste compara
  mão, Loja e RNG com o mesmo ataque sem a quest, preservando a recompensa
  universal por destruir uma Cidade; ela não deve ser confundida com prêmio da quest.

## Apresentação web

A escolha de pacto mostra sua descrição e o efeito do item selecionado, vindos
do catálogo do servidor. Firmar exige confirmação; cancelar/Escape não envia
requisição. A HUD distingue recompensa entregue de recompensa pendente a partir
dos campos públicos já existentes. Sem novos cálculos mecânicos ou contratos.

Validação automatizada de apresentação: `web_actions_ui.cjs`,
`web_dialog_ui.cjs` e `web_presentation_ui.cjs`.

Suíte completa: **436 testes Python, zero falhas**; cinco scripts Node,
sintaxe de `app.js`/`presentation.js` e `git diff --check` aprovados. O replay
independente existente continua igual à instalação terminal em 125 ações
diurnas e nove cenários noturnos; é complementar às três partidas deste lote.

## Limites

Não é certificação de todas as escolhas: faltam partidas completas que concluam
as outras duas quests, combinem os quatro itens de Rogue e encadeiem várias
janelas especiais. Os adversários destes roteiros não declaram ataques; o jogador
1 é o atacante. Playtest real desktop/celular permanece necessário. Este lote
não inclui inspeção manual no navegador nem altera a instalação terminal.
