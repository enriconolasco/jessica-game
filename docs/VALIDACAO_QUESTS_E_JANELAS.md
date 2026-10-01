# Quests e janelas encadeadas — 01/10/2026

## Rogue: quests restantes

`test_special_matches_parity.py` acrescenta dois cenários dirigidos, seeds
907/908: Banho de Sangue e Cabeças de Heróis. Não são partidas completas.
O estado inicial preparado contém três tropas normais e três heróis inimigos
feridos, de povos diferentes, no Centro. Depois da preparação, as escolhas são
ações reais: invocar Rogue, firmar a quest com Bracelete, passar os Dias e combater.

Os testes comprovam recompensa imediata ao firmar, progressão/conclusão da quest,
ausência de nova vida/item/artefato/RNG consumido ao concluir e persistência.
Cada ataque é comparado à orquestração terminal; as decisões web são repetidas
em saves restaurados. Não substituem os roteiros completos já documentados.

## Noite com múltiplas interrupções

`test_luna_luide_armor_qd_ainai_chain_matches_real_windows` compara esta sequência:

Luna retorna → Luide usa feitiço → ataque mata fada → pagamento de Armadura
→ escolha de recompensa Q♦ → Ainai reabre o Centro e declara.

As janelas originais de Luna, Luide e Ainai e a escolha Q♦ são executadas no
terminal. O comparador exige mesma ordem de ataques, estado, logs e RNG.
Pagamentos de Armadura deste cenário são zero. Consultas não modificam estado;
cada decisão web é repetida após serialização/restauração.

## Quatro itens e Relógio

`test_rogue_four_items_base_attack_and_real_clock_window` parte de um estado
dirigido com quatro itens, registra combate no Centro, permite ataque à Base e
usa a janela real de Relógio para voltar ao Centro antes de encerrar a Noite.
É um teste da combinação em campo, não de adquirir os quatro itens numa partida.

Encontrado e corrigido: o combate permitia ataque à Base, mas o seletor de alvos
o omitia. Terminal e web agora reutilizam `peoples.rogue_can_attack_base`; a visão
pública também informa essa permissão. Regra existente, não balanceamento novo.
`test_rogue_four_items.py` é compartilhado pelas duas instalações e verifica que
qualquer item ausente continua impedindo a seleção de Base.

Validação do lote: **442 testes web e 306 testes terminal, zero falhas**;
cinco scripts Node, sintaxe JavaScript e `git diff --check` aprovados.
Replay em processo separado: 125 ações diurnas e dez noites equivalentes à
instalação terminal, incluindo seleção/ataque de Rogue à Base com quatro itens.
Referência terminal corrigida e registrada: `2cbc36c`, branch
`codex/terminal-playtest-round2`. A correção também foi aplicada à cópia local
em Downloads, não apenas à web.

## Limites restantes

Os limites deste lote foram parcialmente cobertos depois: as partidas completas
de Banho de Sangue/Cabeças de Heróis e aquisição dos quatro itens estão em
`VALIDACAO_PROGRESSAO_ROGUE.md`; QA real em `VALIDACAO_NAVEGADOR.md`.
Permanecem outros cruzamentos, adversários atuantes e teste físico por toque/PWA.
