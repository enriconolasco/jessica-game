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

Legenda: **Core** = regra e validação no core; **Parcial** = execução no core, mas
legalidade/parâmetros ainda montados no terminal; **Terminal** = decisão/orquestração
permanece em `main.py`. Todas as linhas abaixo alteram estado, salvo “consultas”.

| Grupo | Ações | Situação | Informação privada |
|---|---|---|---|
| Setup | bans, escolha de povo/herói, nomes, ordem | Parcial | escolhas ainda não reveladas |
| Economia | coletar, subir vida, construir monumento | Parcial | não |
| Unidades | invocar tropa, invocar herói, mover, usar cura | Parcial | não |
| Artefatos | comprar, transmutar, vender, jogar, descartar campo | Parcial | mão e compras |
| Pendências | escolher cartas de J♦/Boin; recompensa de Q♦ | Parcial | cartas vistas/escolhidas |
| Feitiços | Resistência, Armadura de Ouro, Espoliar, Sonho Lúcido, Morcego, Licantropo, Linhagem Ancestral, Levantar Mortos, Decompor, Imitação Gnomérica | Parcial | mão no Sonho/Imitação |
| Combate | ataque diurno, ataque noturno a unidade/cidade | Parcial | não |
| Reação | pagamento de Armadura de Ouro | Terminal | ouro do próprio jogador |
| Heróis | Arken, Tin Tin, Dandara, Besouro, Luide, Guarari, Aiquara, Baobá-bá, Bimbo, Zebum | Parcial | mão em Besouro; compra de Bimbo |
| Povos | alocar apostas; usar/dar Pena | Parcial | apostas e mão |
| Fases | iniciar turno/dia, encerrar dia/turno | Core, orquestrado no terminal | não |
| Noite | ordem por casa/jogador, passar/atacar, janelas de Luide, Ainai, Luna, Vovó e Mandinga | Terminal | mão em Mandinga |
| Passar | encerrar o dia do jogador sem agir mais | Terminal | não |
| Sistema | undo, Mola e reiniciar | Terminal | snapshot integral |
| Consultas | mapa, board, loja, log, fichas, ajuda e relatórios | Terminal; não alteram estado | devem respeitar visão |

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
