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

1. Mesma seed + mesmo save + mesmas ações produz o mesmo estado e eventos.
2. Uma ação fora de `legal_actions` ainda é rejeitada por `apply_action`.
3. Falha não produz mutação parcial.
4. Nenhuma `PlayerView` revela mão adversária, RNG ou ordem da loja.
5. O terminal atual continua funcionando enquanto a camada v0.1 é introduzida.
