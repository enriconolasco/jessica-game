# Validação final do P1

Data: 2026-09-22. Branch: `codex/p1-headless`.

## Evidências

- Suíte completa: 250 testes aprovados, zero falhas.
- Playtest terminal: dois turnos completos com seed `12345`; coleta `0/2`, `1/1`
  e `2/0` atravessou a porta nova. Segunda coleta no mesmo turno foi rejeitada sem
  alterar os recursos.
- Fluxo: terminal -> `legal_actions` -> `Action` -> `apply_action` -> regra existente
  `collect_resources` -> `resources_collected` -> apresentação terminal.
- Regra mecânica: existe somente em `core.actions.collect_resources`; terminal apenas
  escolhe uma ação legal e apresenta o evento.
- Contratos e `headless.py`: nenhuma dependência ou detalhe de Rich.
- `PlayerView`, determinismo, ação serializada, projeção de evento, equivalência entre
  fluxo antigo/novo e save/load possuem testes próprios.

## Conclusão

Os critérios definidos para P1 foram atendidos. A arquitetura permite migrar novas
ações individualmente sem interromper o fluxo antigo.

## Expansão posterior

- A família econômica começou a ser migrada na branch `codex/p1-economic-actions`.
- `raise_city_life` e `build_monument` usam a porta e produzem eventos públicos.
- Coleta, aumento de vida e Monumento são as três ações atualmente migradas.
