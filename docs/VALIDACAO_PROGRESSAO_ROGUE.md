# Progressão de Rogue em partidas completas — 01/10/2026

Fonte: branch `codex/web-vertical`, base `8a0bcbe` e patch registrado junto deste
documento. Nenhuma regra, atributo ou balanceamento foi modificado.

## Roteiros reproduzíveis

Executar `python -B tests/test_rogue_complete_progression.py`.
Preparação normal: quatro jogadores, Bases com 2 de vida, 25 Ouro/Magia,
ordem fixa. Demônios/Rogue, Humanos/Miyamoto, Orcs/Arken e Fadas/Luna.
Não são inseridas unidades, ferimentos, itens ou pactos artificialmente.

| Seed | Foco | Vitória de J1 | Decisões |
| --- | --- | --- | --- |
| 909 | Banho de Sangue, três abates na mesma Noite | T10 | 149 |
| 910 | Cabeças de Heróis, todos os povos exigidos | T8 | 131 |
| 911 | Quatro itens adquiridos por pactos, persistência e ataque à Base | T11 | 170 |

Cada ação web é repetida após save/load, com validação real de saves. Decisões
diurnas são comparadas às funções de regras usadas pelo terminal; cada Noite é
reexecutada por `jessica.main.run_night_phase`, comparando estado, logs e RNG.

## Reforço: adversários atacando

Seeds 913/914 acrescentam partidas completas das duas quests com adversários
declarando ataques contra J1. Ambas chegam à vitória, somando 494 decisões e
com duração máxima T25. O teste exige ataques inimigos e mortes dos atacantes
por retaliação, além das recompensas/progressão/persistência já verificadas.
A política escolhe alvos legais e é comparada à orquestração terminal;
não é um bot de produção nem seleção aleatória de todas as interações.
Revalidação com este reforço e o atalho web: 449 testes Python e cinco scripts
Node aprovados, zero falhas; `git diff --check` aprovado.

O terceiro roteiro usa Sacrifício e reinvocação para obter os itens por ações
legais. Confirma três sacrifícios, persistência de vida/itens e seleção/execução
de ataques à Base pelo Rogue completo. As recompensas são imediatas ao firmar;
concluir quests não concede outra recompensa. O teste de conclusão compara a
mesma ação sem a quest, preservando espólio legítimo da eliminação.

## Histórico web

Alterações nos pactos já públicos agora produzem `changes[].kind: pact` em
`public_state_changed`. A interface reutiliza os nomes e estados da HUD para
mostrar firma, progresso, conclusão, recompensa e liberação. Não deduz resultados.

Teste HTTP: mesmo histórico público para dois jogadores, nenhuma mão exposta,
eventos preservados em exportação/importação e ação inválida sem mutação.
Os roteiros completos também verificam os eventos de firma e conclusão.

Validação do lote: **447 testes Python aprovados, zero falhas**; cinco scripts
Node, sintaxe JavaScript e `git diff --check` aprovados. A instalação terminal
não foi alterada neste ciclo.

## Limites

Nos três primeiros roteiros os adversários passam; nos dois adicionais atacam.
São partidas completas dirigidas, não adversários inteligentes nem exploração
de todas as combinações.
Relógio é adquirido, mas seu uso continua validado no cenário específico de
`VALIDACAO_QUESTS_E_JANELAS.md`, não nestas partidas.

O comparador independente existente aprovou 125 ações diurnas e dez noites
contra a instalação terminal em Downloads. Não reproduz todos os passos dos
três novos roteiros naquele processo: essa comparação usa a orquestração terminal
da cópia web. Esta distinção evita certificar equivalência sem evidência.

Este lote não inclui nova inspeção manual do navegador ou teste físico de PWA.
Permanecem outros cruzamentos de janelas/povos a ampliar.
