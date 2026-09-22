# Inventário do motor — P1

Estado observado em `codex/p1-headless`, derivada de `main` no commit `8b2d40d`.
A baseline P0 permanece em `baseline-v0.1` (`94db32b`) e a versão mecânica anterior em
`v5.11.0` (`d222715`). A suíte atual tem 240 testes aprovados.

## Fluxo atual da partida

1. `main.setup_ui` coleta nomes, bans, povos e heróis; `core.setup.run_setup` cria o
   `GameState` e define ordem/Curuna.
2. `_run_one_game` chama `start_turn`, executa os dias em `day_order`, recebe escolhas
   do terminal e chama funções de `core.actions`.
3. `end_day` muda a fase; `run_night_phase` mantém no terminal a ordem das casas,
   janelas especiais e declarações. O combate real é resolvido por `core.combat`.
4. `end_turn` limpa efeitos, registra a linha do tempo, chama `check_victory`, avança
   Curuna e turno. O laço termina quando `GameState.game_over` é verdadeiro.
5. Saves usam `state_to_dict/state_from_dict`. Undo/Mola guardam snapshots desse mesmo
   formato em memória.

## Estado, RNG e registros

- `GameState` concentra jogadores, unidades, loja, turno/fase, efeitos pendentes,
  prioridade noturna, logs e resultado da partida.
- O RNG de execução é `state.rng` (`DeterministicRNG`) e seu estado é serializado.
  O sorteio inicial usa uma instância local criada com a mesma seed; é determinístico,
  mas separado do fluxo de RNG salvo em `GameState`.
- `event_log` contém texto global para apresentação. `action_log` contém alguns
  registros estruturados, mas a cobertura não é completa e não há visibilidade.
- Não existe hoje uma fila canônica de eventos estruturados nem uma visão segura por
  jogador.

## Ações existentes

Variantes de povos, heróis, feitiços e artefatos ficam na ação estrutural comum.
**Core** = porta e regra no motor; **Parcial** = parâmetros/fluxo ainda no terminal;
**Terminal** = validação ou mutação relevante ainda em `main.py`.

| Ação e parâmetros | Recebida em | Validada em | Altera estado em | RNG | Eventos/logs | Privado | Classe |
|---|---|---|---|---|---|---|---|
| `setup(names, bans, peoples, heroes)` | `setup_ui` | `setup_ui`, `run_setup` | `run_setup` | ordem inicial | `event_log` | escolhas | Parcial |
| `collect_resources(gold, magic)` | `_do_action` | `headless.apply_action`, `actions.collect_resources` | `actions.collect_resources` | não | `Event resources_collected`, `action_log`, `event_log` | não | Core |
| `raise_city_life(times)` | `_do_action` | `actions.raise_city_life` | mesma função | não | `action_log`, `event_log` | não | Parcial |
| `summon_troop(archetype, life)` | `_do_action` | `main` e `actions.summon_troop` | `actions.summon_troop` | não | `action_log`, `event_log` | não | Parcial |
| `summon_hero(hero_id?)` | `_do_action` | `main` e `actions.summon_hero` | `actions.summon_hero` | não | `action_log`, `event_log` | não | Parcial |
| `move_unit(unit_id, destination)` | `_do_action`, janela Luide | `valid_destinations`, `actions.move_unit` | `actions.move_unit` | não | `action_log`, `event_log` | não | Parcial |
| `build_monument()` | `_do_action` | `actions.build_monument` | mesma função | não | `action_log`, `event_log` | não | Parcial |
| `buy_artifact_gold()` | `_do_action` | `actions.buy_artifact_with_gold` | mesma função | sim | `action_log`, `event_log` | carta obtida | Parcial |
| `transmute_artifact_magic()` | `_do_action` | `actions.transmute_artifact_with_magic` | mesma função | sim | `action_log`, `event_log` | carta obtida | Parcial |
| `sell_artifact(card_id)` | `_do_action` | `actions.sell_artifact` | mesma função | não | `action_log`, `event_log` | mão | Parcial |
| `play_artifact(card_id, choice)` | `_do_action`, Mandinga | `actions.play_artifact`, `artifacts_effects.on_play` | mesmas funções | conforme carta | `action_log`, `event_log` | mão/escolha | Parcial |
| `resolve_artifact_choice(choice)` | `_resolve_pending_choice_if_any` | `actions.resolve_pending_artifact_choice` | mesma função | não | `event_log` | cartas/recompensa | Parcial |
| `cast_spell(choice)` | `_do_action`, janela Luide | `actions.cast_spell` e variante | mesmas funções | conforme feitiço | `action_log`, `event_log` | Sonho/Imitação | Parcial |
| `use_heal(unit_id)` | `_do_action` | `actions.use_heal` | mesma função | não | `action_log`, `event_log` | não | Parcial |
| `attack(attacker_id, target_type, target_id)` | dia e `_declarar_casa` | `combat.resolve_attack*` | `core.combat` | conforme atacante | `action_log`, `event_log` | não | Parcial |
| `use_special(ability_id, choice)` | `_menu_especiais`, janelas | `main` e função específica de `actions` | função específica de `actions` | conforme habilidade | principalmente `event_log` | conforme habilidade | Parcial |
| `allocate_bet(suit, target_id)` | `_gnomo_bets_menu` | `actions.gnomo_alocar_aposta` | mesma função | não | `event_log` | apostas | Parcial |
| `armor_reaction(gold)` | `_armor_choice_prompt` | callback em `combat._apply_armor` | `core.combat` | não | `event_log` | decisão/ouro | Terminal |
| `night_decision(pass/attack)` | `_declarar_casa` | `main`; ataque no `core.combat` | `main`/`core.combat` | conforme ataque | `action_log`, `event_log` | não | Terminal |
| `pass_day()` | `run_player_day` | `main` | `Player.has_played_day_this_turn` em `main` | não | nenhum | não | Terminal |
| `system_action(undo/mola/restart)` | `_menu_sistema` | `_run_one_game` | substituição de snapshot em `main` | não | nenhum | snapshot total | Terminal |
| `inspect(view_type, params)` | menus de informação | `main` | não altera | não | nenhum | depende da visão | Terminal |

As funções de mutação já existentes devem ser reutilizadas; P1 não deve duplicar suas
regras. Os principais pontos de entrada estão em `core.actions`, `core.combat`,
`core.turn`, `core.artifacts_effects` e `core.setup`.

## Decisões ainda acopladas a `main.py`

- Descoberta das ações disponíveis (`_get_actions`) e passagem de vez.
- Enumeração de unidades, destinos, alvos, valores e escolhas de feitiços/artefatos.
  `valid_destinations` ainda está no terminal.
- Resolução das escolhas pendentes de artefatos e das decisões privadas da mão.
- Sequenciamento do dia, snapshots de undo/Mola e toda a orquestração declarativa da
  noite, inclusive reabertura de casas.
- Reações de Armadura de Ouro por callback global ligado ao prompt.
- Janelas de Ainai, Luna, Vovó, Besouro e Luide, além da alocação inicial de apostas.
- Formatação e filtragem de informações. Algumas telas recebem o `GameState` completo,
  portanto ainda não existe uma fronteira de privacidade confiável.

## Primeiro corte recomendado

Usar `collect_resources` como única ação real do protótipo headless: é determinística,
já está inteiramente validada no core, não usa informação secreta e permite provar
`legal_actions -> apply_action -> eventos -> view_for_player` sem alterar as demais
mecânicas.
