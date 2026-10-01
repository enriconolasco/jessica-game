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

Partidas completas com Barba Negra, Valtherion e Rogue agora aprovadas em
`VALIDACAO_BASES_E_PACTOS.md`, incluindo Canastra, Chamado, Mar de Chamas,
reinvocação e quest Vida de um Líder sem recompensa adicional ao concluir.

As outras duas quests, combinação de quatro itens com Relógio e cadeia
Luna/Luide/Armadura/Q♦/Ainai passaram em cenários dirigidos; ver
`VALIDACAO_QUESTS_E_JANELAS.md`.

Corrigida nas duas instalações a omissão de Bases no seletor de alvos de Rogue
com quatro itens, apesar de o combate já permitir esse ataque.

QA real de Rogue, Luide sem inimigos e oferta de Belial no próximo Dia, por
mouse/teclado em larguras desktop/móvel: `VALIDACAO_NAVEGADOR.md`.

Banho de Sangue, Cabeças de Heróis e aquisição dos quatro itens agora possuem
partidas completas até vitória, sem preparação artificial de unidades/itens:
`VALIDACAO_PROGRESSAO_ROGUE.md`. Histórico público de pactos também validado por HTTP.

Seeds 913/914 também validam as duas quests em partidas completas com adversários
atacando e mortes por retaliação; ver `VALIDACAO_PROGRESSAO_ROGUE.md`.

Ainda ampliar: outros cruzamentos de janelas/povos e playtest físico por toque/PWA.
São lacunas de validação; não há, por isso só, evidência de mecânica ausente.
