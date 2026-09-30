# Contratos headless v0.1

Especificação experimental para provar a arquitetura com uma ação real. Não é um
formato definitivo nem substitui ainda os saves e logs existentes.

## Versões

- `ACTION_VERSION = "action-v0.1"`
- `EVENT_VERSION = "event-v0.1"`
- `VIEW_VERSION = "view-v0.1"`
- `SAVE_VERSION = "save-v0.1"`

As versões evoluem separadamente. O save atual não possui campo de versão; sua futura
migração deve ser explícita e não faz parte da primeira prova.

## Action

```python
Action = {
    "version": "action-v0.1",
    "type": str,
    "label": str,
    "player_id": int,
    "params": dict,
}
```

Uma ação retornada por `legal_actions` é concreta: contém todos os parâmetros
necessários para execução, usa apenas identificadores estáveis e não contém callbacks
ou texto de terminal. Para a prova inicial:

```python
{
    "version": "action-v0.1",
    "type": "collect_resources",
    "player_id": 1,
    "params": {"gold": 0, "magic": 2},
}
```

## Event

```python
Event = {
    "version": "event-v0.1",
    "type": str,
    "turn": int,
    "phase": str,
    "participants": [int, ...],
    "data": dict,
    "visibility": {"kind": "public" | "private" | "players", "player_ids": [int, ...]},
}
```

`player_ids` só é usado em `players`; em `private`, os destinatários são os
participantes autorizados. Resultados secretos (carta comprada, mão, escolha privada)
nunca entram em evento público. Texto de interface é derivado do evento, não faz parte
do contrato.

## ActionResult

```python
ActionResult = {
    "success": bool,
    "error": None | {"code": str, "message": str, "details": dict},
    "events": [Event, ...],
}
```

Em erro, a ação é atômica: não altera estado, não avança RNG e não produz eventos de
sucesso. `message` é legível; consumidores devem depender de `code`, não do texto.

## PlayerView

```python
PlayerView = {
    "version": "view-v0.1",
    "viewer_id": int,
    "turn": int,
    "phase": str,
    "curuna_id": int,
    "game_over": bool,
    "winner_id": int | None,
    "players": list,
    "board": dict,
    "shop": {"size": int},
    "self": {"hand": list, "pending_choice": dict | None},
    "events": list,
}
```

`players` e `board` contêm apenas estado público: cidades, recursos públicos, unidades,
posições, vida e status visíveis, além da quantidade de cartas de cada adversário.
Somente `self` revela a própria mão e escolhas pendentes. Nunca expor ordem da loja,
estado interno do RNG, mãos adversárias, snapshots ou dados privados filtrando depois
um `state_to_dict`; a visão deve ser construída por lista permitida.

## Funções

### `legal_actions(state, player_id) -> list[Action]`

- Função pura: não altera estado nem consome RNG.
- Retorna apenas ações válidas para o jogador, fase e janela atuais.
- Não revela dados privados de outros jogadores.
- Ordem estável para o mesmo estado.
- Enumera as três divisões legais da coleta diária (`0/2`, `1/1`, `2/0`),
  aumentos de vida da Cidade que podem ser pagos e construção de Monumento
  quando seus requisitos estiverem satisfeitos.

`GameState.active_player_id` registra e valida a janela ativa do Dia no cliente web.
O valor `None` permanece compatível com os chamadores antigos do terminal.
A ordem e as janelas especiais da Noite ainda precisam de adaptação estruturada.

### `apply_action(state, action) -> ActionResult`

- Valida versão, formato, jogador, fase, janela e parâmetros.
- Reutiliza a função existente do core; não replica a regra mecânica.
- Captura erros de domínio em códigos estáveis e produz eventos estruturados.
- Despacha `collect_resources`, `raise_city_life`, `build_monument`,
  `summon_troop`, `summon_hero`, `move_unit` e `end_turn`; tipos ainda não adaptados retornam
  `unsupported_action` sem mutação.
- O `GameState` continua sendo alterado in-place nesta versão.

### `view_for_player(state, player_id) -> PlayerView`

- Não altera estado nem consome RNG.
- Valida que o observador participa da partida.
- Constrói uma projeção por lista permitida e filtra eventos por `visibility`.
- A mesma função deve servir terminal, IA local, testes e futura conexão online.

### `apply_event_to_view(view, event) -> PlayerView`

- Aplica somente eventos visíveis ao observador, sem acessar o `GameState` completo.
- Não altera a visão original.
- Reconstrói os efeitos públicos de `resources_collected`, `city_life_raised`,
  `monument_built`, `unit_summoned`, `unit_moved` e `player_turn_ended`.

## Invariantes da prova

### Extensão de apresentação e interações — 2026-09-28

Sem alterar as versões existentes, ações concretas podem incluir `description`, texto
de apresentação gerado no servidor. O navegador devolve `type/player_id/params`;
rótulos não concedem autorização. Novos tipos: `play_artifact`,
`resolve_artifact_choice`, `use_pena`, `use_heal`, `hero_ability`, `demon_pact`
e `decline_pact`. `interaction_actions.py` enumera escolhas e reutiliza o core em
cópias isoladas; só publica o estado depois do sucesso. Pendências obrigatórias
bloqueiam inclusive `end_turn`. Não há consumo do RNG ao consultar ações.

`PlayerView.players[].field_artifacts` expõe somente cartas ativas públicas;
`self.pending_heals` pertence à visão do jogador. Novos eventos:
`interaction_resolved` descreve a ação sem revelar a mão; `player_view_updated`
contém a visão posterior exclusivamente do próprio jogador, com visibilidade privada.
O projetor aceita ambos. O servidor mantém a filtragem de eventos por destinatário.
Saves anteriores sem `events` continuam carregáveis; novos saves preservam eventos.

Extensão adicional: `cast_spell` usa `params={"choice": {...}}`, com escolhas
concretas de alvo/arquetipos/canastra enumeradas em `spell_choices.py`; `reroll_spell`
usa parâmetros vazios e seu resultado é privado. Ambos passam pela transação existente.
`self` inclui `spell_copia_id`, `spell_cooldown_until_turn` e `has_cast_spell_this_turn`.
O evento `interaction_resolved.data.spell_id` identifica o feitiço executado;
não expõe o resultado aleatório antes da execução. Sonho Lúcido permite uma carta
com `choice={"flip_cards":[id],"artifact_choices":[escolha]}`;
`dream_multi` usa essas mesmas listas, com múltiplos elementos em ordem de execução.
A oferta `selection.kind="dream"` enumera opções individuais, sem gerar todas as
combinações. Servidor valida quantidades, Luna viva e opções antes de executar
a sequência em cópia transacional. `POST /matches/{id}/dream-preview` recebe
`{player_id, choice}` com o prefixo selecionado (listas vazias são permitidas)
e devolve somente `{options}` da próxima carta. A consulta simula o prefixo
com o mesmo helper de resolução do core, sem alterar estado, RNG, logs ou save.
Assim, alvos invocados ou modificados por cartas anteriores são oferecidos.
A confirmação `dream_multi` revalida cada escolha no estado correspondente e
executa a sequência inteira em uma transação; limpar a prévia não gasta o feitiço.
J♦ segue o agendamento T+3, sem restrição de posição.
não há promessa de cobertura total dos feitiços.

`sacrifice_spell` aceita `params={"hero_id": unit_id, "artifacts": [{"zone":
"hand" ou "field", "card_id": id}]}`. A oferta inclui `selection={"kind":
"artifacts", "options": [...]}` somente para o jogador ativo. Ocorrências repetidas
representam cartas distintas. A lista enviada deve ser não vazia e respeitar as
quantidades disponíveis; o servidor revalida o herói, as cartas e o feitiço na
transação. O frontend apresenta checkboxes e confirmação de morte, sem calcular
efeitos. Essa oferta parametrizada evita crescimento exponencial de combinações.
Eventos públicos não expõem as cartas privadas selecionadas.

Fatia noturna: `night_attack` recebe `attacker_unit_id,target_type,target_id`;
`night_pass`, `unit_id`; `finish_night`, parâmetros vazios.
Só o declarante atual recebe ações. A fila usa ordem por jogador/local do terminal;
ataques são validados e executados por `combat.resolve_attack` em cópia transacional.
`night_action_resolved` registra a decisão pública, seguido da projeção privada do
ator. As outras telas consultam novamente PlayerView; o evento público isolado
não reconstrói todo o dano. `night_window` mostra local, unidade e ordem restante;
`night_limitations` informa condições não adaptadas. `GameState.web_night` persiste
a fila; saves anteriores usam dicionário vazio e a inicializam ao entrar na Noite.
Ao encerrar a Noite, o motor executa fim de turno/vitória e início do próximo,
abrindo apostas pendentes antes do Dia do Curruna.

`night_resolve_choice` reutiliza os parâmetros de `resolve_artifact_choice`:
recurso para Q♦ ou cartas mantidas para J♦/Feliz. A fila é suspensa e
`active_player_id` passa ao dono da pendência. Apenas ele recebe as opções;
outras ações são rejeitadas. Resolução chama o core em cópia transacional,
retoma a fila e produz evento e projeção privados. A resolução de uma pendência
já criada continua possível se o ataque tiver encerrado a partida.

`night_pact` e `night_decline_pact` reutilizam os parâmetros e executores das
ofertas diurnas (`offer_index`, pacto e item quando aplicável). As opções são
revalidadas antes de exibir e executar; a pendência suspende a fila, inclusive
quando surge por morte em retaliação. Eventos de decisão são privados.
`night_clock` recebe `destination` entre os locais de combates ocorridos;
`night_skip_clock` recebe parâmetros vazios. A oportunidade só abre após as
declarações, para Rogue vivo com Relógio, e a conclusão fica em
`web_night.clock_done`. Não reabre ataques após esse deslocamento final.
Mar de Chamas é executado no preparo da Noite, protegido pelo marcador de
turno já persistido em `web_night`; consultas usam cópia e não alteram o estado.

`night_setup` recebe `{"kind":"vovo","position":1..4}` ou
`{"kind":"luna","return":true|false}`. `web_night.setup` preserva a sequência:
Vovós → Mar de Chamas → Lunas → montagem da fila. Heróis mortos antes da sua
janela são pulados. Save antigo sem `setup` preserva a fila já iniciada.
O retorno da Luna usa a mesma função em `night_rules.return_luna` no terminal
e na web; sincroniza a prioridade do local sem consumir movimento adicional.

`night_mandinga` recebe `card_id` e `choice`, validados por
`besouro_mandinga`. A janela vem após Luna e antes da fila de combate.
`night_setup {"kind":"besouro"}` recusa a habilidade. Cartas PENA não são
oferecidas; escolhas adicionais suspendem a fila pelo fluxo noturno de artefatos.

`day_attack` recebe `attacker_unit_id,target_type="unit",target_id` apenas
para Miyamoto vivo do jogador ativo, com alvo inimigo vivo no mesmo local.
O adaptador consulta o limite existente e executa `resolve_attack_day` em
cópia transacional. Visibilidade e limite final são validados pelo combate.
O contador do motor é preservado para a Noite e no save/load.

`allocate_bets`: `params={"bets":{"H":id_ou_null,"C":id_ou_null,
"D":id_ou_null,"S":id_ou_null}}`. A oferta contém `selection.kind="bets"`
e alvos vivos diferentes do próprio jogador. O servidor valida os quatro naipes,
aplica a alocação pelo core e libera o início do Dia. Enquanto pendente, o
jogador não recebe outras ações. Evento e projeção dessa escolha são privados.

1. Mesma seed + mesmo save + mesmas ações produz o mesmo estado e eventos.
2. Uma ação fora de `legal_actions` ainda é rejeitada por `apply_action`.
3. Falha não produz mutação parcial.
4. Nenhuma `PlayerView` revela mão adversária, RNG ou ordem da loja.
5. O terminal atual continua funcionando enquanto a camada v0.1 é introduzida.

### Transporte de saves locais

- `GET /saves`: metadados (`save_id,name,turn,phase,kind,updated_at`), sem estado privado.
- `POST /matches/{id}/save`: `{name}` cria cópia independente; devolve `{save_id,version}`.
- `GET /matches/{id}/export`: envelope completo `{version,state,events,name}`.
- `POST /matches/import`: envelope exportado; devolve novo `match_id` após validação.
- `POST /matches/load`: `{save_id}` restaura cópia ou autosave em nova partida.

Envelope continua `save-v0.1`. Estado, RNG, eventos e fila noturna são preservados;
incompatibilidade retorna 409, arquivo inválido 422, inexistente 404. Importar não
modifica partidas abertas. Exportação completa é ferramenta do dispositivo local;
não pertence à PlayerView e inclui informações secretas de todos os jogadores.

### Janelas Ainai e Luide (ações v0.1)

- `night_ainai`: `{destination}`; teleporte validado pelo helper compartilhado com o terminal.
- `night_luide_move`: `{unit_id, destination}`; usa `move_unit`.
- `night_luide_spell`: `{unit_id}`; usa `cast_spell`.
- `night_window_done`: `{}`; recusa teleporte ou conclui a janela de Luide.

As ofertas dependem da janela corrente e de heróis vivos. `web_night` persiste
marcadores de locais, locais processados e janela aberta. A prioridade de cada
local é calculada ao abri-lo; entrada em local processado antepõe a declaração
do recém-chegado sem renovar seu limite de ataques. Eventos usam
`night_action_resolved`, sem cálculos de regras no navegador.

### Revisão aditiva — 2026-09-30

- `armor_payment`: `{gold: int}`. A seleção informa dano, unidade/casa e limite de
  pagamento. Apenas o defensor corrente recebe a oferta. A transação original é
  reproduzida com os pagamentos escolhidos e o mesmo RNG; só então é confirmada.
- `web_reaction` guarda ação, pagamentos e prévia da próxima defesa. PlayerView
  compartilha apenas dados públicos da prévia e a área privada do próprio defensor.
  Consultas usam política de simulação isolada; não acionam callbacks do terminal.
- Novos eventos: `armor_payment_requested` (privado), `public_state_changed`,
  `public_roll`, `combat_house_opened`, `day_restored` (públicos). Mudanças e
  restauração podem ser projetadas; textos privados do log bruto não são enviados.
- Eventos básicos incluem `data.public_after` para manter a projeção dos novos
  campos públicos. Respostas de ações HTTP filtram eventos pelo jogador que enviou
  a ação, inclusive quando a próxima reação pertence a outro jogador.
- PlayerView acrescenta ordem, condições, infecção e limite efetivo de ataques,
  estatísticas, previsão de Monumento, efeitos agendados, economia e alvos públicos
  de artefatos. Loja mostra contagens, nunca ordem do baralho ou RNG.
- `POST /matches/{id}/system`: `{operation: "undo" | "mola"}`. Apenas no Dia e sem
  reação pendente. `local_controls` informa disponibilidade. Saves completos têm
  `history` opcional, com até quatro checkpoints do turno atual; sem aninhamento.
- `/catalog` inclui consulta de conteúdo completo; `/setup-order?seed=...` informa
  Curuna inicial e ordem de seleção. O core fixa a ordem do mapa em J1–J4 e começa
  pelo Curuna sorteado, exatamente como o terminal; não usa o ranking D20 inteiro
  como sequência de jogo.

Campos novos são aditivos no contrato experimental v0.1. Saves antigos sem reação
ou histórico continuam aceitos. A API continua local, sem autenticação multiplayer.

## Importação e recuperação — 30/09/2026

`POST /matches/import` aceita também estado bruto compatível do terminal, sem
`version`, após validar uma jogada diurna inequívoca. Não reaplica a manhã nem
consome RNG. Noite sem fila e Dia ambíguo são rejeitados (422); versão explícita
incompatível continua 409. Evento público adicional: `match_imported`.

Metadados locais opcionais de save: `checkpoint_skip: {turn, player_id}`,
`kind: recovery`, `source_match_id`, `recovery_generation`. Resposta de importação
inclui `warnings`. Respostas de operações aceitas podem informar `save_warning`
sem alterar sucesso/eventos mecânicos; falha ao salvar cópia responde 507.
`GET /saves` lista recuperações sem transmitir estado, RNG ou eventos. Ações inválidas
não criam recuperação. Formatos experimentais v0.1 permanecem; campos são aditivos.

## Metadados noturnos opcionais

Na fila interna de saves web, `end_house.occupied` indica se havia participantes
ao abrir o local; `web_night.final_ainai_queued` impede repetir a última janela
de Ainai. Ambos são booleanos opcionais, validados ao carregar. Não são ações,
regras de dano nem informação privada. Formatos v0.1 permanecem inalterados.
