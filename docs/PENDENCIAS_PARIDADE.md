# Pendências de paridade — 01/10/2026

Este arquivo registra divergências conhecidas, não funcionalidades apenas sem playtest.
Ter um adaptador e testes aprovados não encerra automaticamente uma pendência.

## WEB-001 — Momento de decidir um pacto de Belial — resolvida

- Condição: Belial vivo; um herói mata outro durante a Noite, gerando uma oferta.
- Terminal: `_declarar_casa` continua os combates e resolve escolhas de artefatos
  via `_resolver_qd_pendente`; não abre `_demon_pact_ui`. A oferta permanece e
  pode ser usada pelo beneficiário no menu diurno.
- Decisão do usuário em 01/10/2026: pacto no próximo Dia, na jogada do beneficiário.
- Web corrigida: a oferta de Belial permanece salva, não interrompe a Noite e
  não permite aceitar/recusar nessa fase. As ações diurnas existentes a resolvem.
- A HUD informa o adiamento. Saves antigos parados nessa oferta apresentam o
  próximo declarante correto, sem alterar estado/RNG durante consultas.
- Ofertas de Rogue continuam imediatas; esta correção não altera suas recompensas.

Fontes: `jessica/main.py::_declarar_casa`, `_menu_especiais`/`_do_action` (opção D),
`jessica/core/night_actions.py::pending_owner`/`legal`,
`tests/test_web_cycle_parity.py::test_armor_then_qd_preserves_belial_pact_for_next_day`,
`tests/test_night_terminal_parity.py` (morte por ataque, retaliação e save antigo).

Os testes dirigidos comparam a Noite ao terminal e confirmam oferta no Dia seguinte,
rejeição atômica de pacto noturno e persistência no save. As partidas mistas completas
usam Tuza, não Belial; não certificam todos os cruzamentos de pactos.

## Cobertura ainda a ampliar

Partidas completas com heróis-base Dragões, pactos/quests de Rogue e várias
janelas especiais encadeadas, além de playtest real desktop/celular. São lacunas
de validação; não há, por isso só, evidência de mecânica ausente ou quebrada.
