# Auditoria de conteúdo e escolhas — web local

Referência terminal: `codex/terminal-playtest-round2`, commit `5b47dde`.
Base web anterior ao lote: `codex/web-vertical`, commit `9dfbff8`.
Escopo: quatro jogadores no mesmo dispositivo, com motor Python local. Não inclui
multiplayer remoto, bots ou execução autônoma do motor no celular.

## Mapeamento dos fluxos do terminal

| Fluxo | Porta web / apresentação |
|---|---|
| Seleção de povos, heróis, nomes, seed e recursos iniciais | `/catalog`, `POST /matches`; 12 povos, Ent desativado |
| D20 e Curuna inicial | `/setup-order`; usa os mesmos helpers do setup |
| Coleta, Muralha, Monumento | `collect_resources`, `raise_city_life`, `build_monument` |
| Invocar tropas e heróis, sequência dos anões e Mortos-vivos | `summon_troop`, `summon_hero`; validação original |
| Movimento, dois movimentos e restrições de invocação | `move_unit`; destinos legais enviados pelo motor |
| Compra, transmutação, venda e Feliz | ações de loja e `resolve_artifact_choice` |
| Todos os artefatos, Pena, alvos e escolhas posteriores | `play_artifact`, `use_pena`, `resolve_artifact_choice` |
| Feitiços dos 12 povos, cópia e rerroll gnômicos | `cast_spell`, `reroll_spell`, `sacrifice_spell` |
| Sonho Lúcido com Luna | `dream_multi`, prévia no servidor e sequência atômica |
| Canastra, sacrifício de cartas da mão/campo | escolhas estruturadas; regras no core |
| Arken, Dunga, Dandara, Púrpura, Barba Negra, Baobá, Bimbo | `hero_ability` |
| Guarari, Valtherion, Aiquara diurna e Zebum | `hero_ability`, com alvos e variantes |
| Curas pendentes da Roça | `use_heal` |
| Apostas antes dos Dias e passivas de São Tomé | `allocate_bets`; HUD privada e passivas vigentes |
| Pactos de Tuza, Belial e Rogue, itens e quests | `demon_pact`, `decline_pact`, janelas noturnas equivalentes |
| Ataque diurno de Miyamoto | `day_attack` |
| Declarações por jogador/local, ataques, retaliações e passar | `night_attack`, `night_pass` |
| Vovó, Aiquara e Luna na abertura noturna | `night_setup`, `night_aiquara` |
| Mandinga de Besouro | `night_mandinga` e escolhas pendentes |
| Ainai e reabertura de local | `night_ainai`, helper compartilhado com terminal |
| Luide vivo: movimento, feitiço e chegada a outro local | `night_luide_move`, `night_luide_spell`, `night_window_done` |
| Armadura de Ouro: pagamento facultativo em cada golpe | `armor_payment`; escolha do defensor, não pagamento automático |
| Relógio de Rogue e fim da Noite | `night_clock`, `night_skip_clock`, `finish_night` |
| Manhã, juros, Lua Cheia, recargas, mortes, eliminação e vitória | funções originais de turno/combat/peoples/victory |
| Refazer Dia / Mola | `POST /matches/{id}/system`; checkpoints de estado, RNG e histórico |
| Reiniciar, salvar e carregar | nova configuração, autosave, cópias, exportação/importação web |
| Consultas do terminal | catálogo, minimapa/fichas, loja, condições, artefatos ativos, previsões, estatísticas e economia |

O mapeamento não prova todas as combinações. Após esta revisão não foi identificada
uma ação mecânica selecionável do terminal sem adaptador, mas isso não certifica
equivalência total entre os dois fluxos de orquestração.

## Alterações deste lote

- Armadura suspende e reproduz a transação com o mesmo RNG. Pagamentos anteriores
  aparecem numa prévia pública para a próxima decisão; o estado só é confirmado ao
  concluir todas as defesas. Save/load preserva a decisão pendente. Consultas não
  chamam o prompt terminal nem gastam recursos. Respostas HTTP filtram eventos privados.
- Consulta de todos os povos, heróis (incluindo os sete anões), feitiços, artefatos,
  pactos e itens. Números básicos vêm dos catálogos/constantes. Textos de consulta
  estão em `core/reference.py`; ainda precisam acompanhar futuros patches.
- HUD mostra herói, Canastra, nomes de cartas, recarga, itens de Rogue e passivas
  herdadas. Relatórios mostram condições de unidades vivas e registros de empalados/
  infectados, alvos públicos dos artefatos, estoque da loja, estatísticas e economia.
- Histórico acrescenta mudanças públicas de recursos, vida, controle, estados,
  unidades e cartas reveladas; não transmite o log bruto com textos privados.
  Rolagens públicas e abertura de cada local, inclusive vazio, têm eventos próprios.
  Uma mudança agregada entre fases é identificada como transição, sem atribuir
  arbitrariamente cada efeito à manhã seguinte.
- Refazer/Mola restauram o começo do Dia após a manhã. É equivalente a restaurar
  o snapshot pré-manhã e reaplicar a manhã com o mesmo RNG, como faz o terminal.
  Checkpoints anteriores ao carregamento só existem se foram gravados no save.
- Confirmações agora usam diálogo HTML com cancelar/Escape; nome do save usa campo
  da página. Erros não habilitam botões que estavam corretamente desabilitados.

## Evidência e limites

Validação final do lote: 365 testes Python web aprovados, zero falhas; 300 testes
do terminal de referência aprovados, zero falhas. Sintaxe JavaScript, `git diff
--check`, `web_actions_ui.cjs` e `web_dialog_ui.cjs` aprovados.

Arquivos principais: `core/reactions.py`, `core/reference.py`, `core/headless.py`,
`core/combat.py`, `core/night_actions.py`, `core/interaction_actions.py`,
`core/models.py`, `core/serialize.py`; `web/session.py`, `web/server.py`,
`web/saves.py`, `web/static/{app.js,index.html,style.css}`; novos testes
`test_web_reactions.py`, `test_web_usability.py`, `web_dialog_ui.cjs` e ajustes nos
testes HTTP existentes. Contratos, checklist de paridade e guia web atualizados.

Testes adicionados: pagamentos sucessivos de Armadura, igualdade com combate direto,
privacidade da reação/HTTP, prévia, save/load, consultas sem prompt, catálogo completo,
D20, refazer/Mola, importação, condições, eventos projetáveis, cinco locais vazios,
uma partida inteira até vitória com save/load entre ações e uma chamada de feitiço
de cada um dos 12 povos comparada à execução direta do core.

DOM simulado: coleta, sequência de Luna e confirmação/cancelamento/Escape.
Navegador real: consulta durante setup, criação, passagem de jogador e coleta 1/1
verificadas. O reteste posterior de restauração foi interrompido pelo diálogo
JavaScript nativo da versão anterior na ferramenta; não foi declarado aprovado.

Ainda necessários para certificar paridade: partidas cruzando os 12 povos,
comparação local a local da Noite com o terminal e teste desktop/mobile das escolhas
complexas, especialmente Armadura + controle + pactos + mortes em sequência.
Saves brutos do terminal, especialmente no meio de declaração noturna, continuam
fora do importador web. PWA/instalação e bots são entregas separadas, não conteúdo
existente do terminal.
