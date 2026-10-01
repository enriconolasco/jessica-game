# Pendências de paridade — 01/10/2026

Este arquivo registra divergências conhecidas, não funcionalidades apenas sem playtest.
Ter um adaptador e testes aprovados não encerra automaticamente uma pendência.

## WEB-001 — Momento de decidir um pacto de Belial

- Condição: Belial vivo; um herói mata outro durante a Noite, gerando uma oferta.
- Terminal: `_declarar_casa` continua os combates e resolve escolhas de artefatos
  via `_resolver_qd_pendente`; não abre `_demon_pact_ui`. A oferta permanece e
  pode ser usada pelo beneficiário no menu diurno.
- Web: `night_actions.pending_owner` suspende a fila; oferece `night_pact` ou
  `night_decline_pact` imediatamente, antes da declaração seguinte.
- Impacto: altera quando entram artefatos/recompensas e penalidades, podendo
  modificar os combates restantes. Não é apenas uma diferença de apresentação.
- Decisão necessária: oferecer imediatamente na Noite ou guardar para o Dia?
  Nenhuma das duas interfaces foi alterada nesta revisão para escolher uma regra.

Fontes: `jessica/main.py::_declarar_casa`, `_menu_especiais`/`_do_action` (opção D),
`jessica/core/night_actions.py::pending_owner`/`legal`,
`tests/test_web_cycle_parity.py::test_armor_then_qd_then_belial_pact_resumes_original_queue`.

As partidas mistas deste lote usam Tuza, não Belial. Sua aprovação não fecha
WEB-001 nem certifica o timing de pactos de Belial.

## Cobertura ainda a ampliar

Partidas completas com heróis-base Dragões, pactos/quests de Rogue e várias
janelas especiais encadeadas, além de playtest real desktop/celular. São lacunas
de validação; não há, por isso só, evidência de mecânica ausente ou quebrada.
