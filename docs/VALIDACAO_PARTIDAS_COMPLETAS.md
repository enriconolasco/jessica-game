# Partidas completas comparadas — 2026-09-30

Teste: `tests/test_full_match_terminal_parity.py`.

São 12 partidas com seeds 110–121: cada povo assume o atacante J1 uma vez,
contra três adversários. Seguem da configuração até a vitória, sem editar o
estado durante a partida. Coleta, invocação e movimento usam funções originais
como referência; as declarações executam `main.run_night_phase` separadamente
da fila web. Mudança de turno e manhã também são comparadas.

Após cada decisão diurna e após cada Noite, exige-se igualdade de estado
mecânico, logs e RNG. Cada decisão aceita atravessa serialização, restauração
e validação do save. Consultas não podem alterar estado. As ações noturnas
também são repetidas em saves restaurados pelo comparador de janelas.

## Recorte deliberado

Partidas curtas, com Bases iniciando em 1 de vida e 20 Ouro/Magia. Os adversários
coletam e passam; o atacante invoca tropas, desloca-se e destrói as Bases.
Dragões usam Púrpura para manter uma Base convencional neste roteiro.

Isso prova fechamento do ciclo para cada povo, incluindo suas passivas que
ocorrem nesse caminho. Não prova todas as combinações, feitiços, heróis-base,
artefatos, pactos ou decisões de interface. Os testes específicos dessas ações
permanecem complementares, não substituídos por estas partidas.

## Próximo critério

Rodar cenários mistos de escolhas complexas e verificar a interface real em
desktop/celular. Só então reavaliar equivalência funcional; não usar a contagem
de testes como percentual de fidelidade.

Verificação do lote: 402 testes Python aprovados, zero falhas; quatro scripts
Node de interface, sintaxe JavaScript e `git diff --check` aprovados. Não foi
realizado novo playtest manual no navegador.

## Partidas mistas — 01/10/2026

`python -B tests/test_mixed_matches_parity.py` executa três partidas adicionais,
sem editar o estado depois da configuração inicial:

| Seed | Participantes/heróis |
|---|---|
| 901 | Humanos/Miyamoto, Anões/Ori, Orcs/Vovó, Fadas/Luna |
| 902 | Vampiros/Drácula, Lobisomens/Cigana, Gigantes/Caroço, Mortos-vivos/Cova Rasa |
| 903 | Filhos/Guarari, Gnomos/São Tomé, Dragões/Púrpura, Demônios/Tuza |

Bases iniciam com 2 de vida, 25 Ouro e 25 Magia. Todos os jogadores invocam
heróis, coletam recursos, visitam a Loja, utilizam feitiços e habilidades quando
permitidos. O atacante percorre as cidades; os defensores não declaram ataques.
A política evita pactos opcionais e sacrifícios repetidos da própria força atacante;
isso é uma escolha do roteiro de teste, não uma regra nova no motor.

Cada partida termina em vitória. Após cada ação diurna e cada Noite, compara-se
estado mecânico, logs e RNG com os caminhos de referência. Saves são restaurados
e validados depois de cada decisão. As noites executam a orquestração terminal
separadamente. Os três roteiros não produziram solicitações de pagamento de
Armadura; esse cruzamento é comprovado separadamente por
`test_armor_reaction_in_real_terminal_night_matches_web`, com pagamento zero.
Os testes específicos de reações também validam pagamentos positivos.

| Seed | Vitória | Decisões | Feitiços usados |
|---|---|---|---|
| 901 | Turno 10 | 153 | 12 |
| 902 | Turno 10 | 154 | 18 |
| 903 | Turno 10 | 149 | 6 |

O lote não inclui novo teste manual no navegador nem partida completa com pactos
de Belial. O timing foi posteriormente confirmado e corrigido com testes dirigidos;
ver `PENDENCIAS_PARIDADE.md`.
Não cobre todas as combinações de heróis, todas as cartas nem todas as decisões.

`tests/run_all.py` agora retorna código 1 quando houver falhas, crash de processo
ou nenhuma suíte encontrada. O comportamento é protegido por cinco testes de
contrato; uma contagem aparentemente verde não encobre um subprocesso quebrado.

Verificação deste lote: **430 testes Python e cinco scripts Node aprovados**;
replay independente com 125 ações diurnas e sete cenários noturnos aprovado;
`git diff --check` limpo. Regras do motor e instalação terminal não foram alteradas.

Correção posterior de Belial: **433 testes Python, zero falhas**, cinco scripts
Node e sintaxe JavaScript aprovados; replay independente de 125 ações diurnas
e nove cenários noturnos equivalente. Ofertas noturnas persistem até o Dia do
beneficiário, inclusive após save/load; uma oferta em save antigo não bloqueia
o próximo declarante. A instalação terminal continua sem alterações.
