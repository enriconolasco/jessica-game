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
