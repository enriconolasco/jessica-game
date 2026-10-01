# Validação real do cliente local — 01/10/2026

Fonte: branch `codex/web-vertical`, base `38e8847`, com o patch de apresentação
registrado junto deste documento. Nenhuma regra ou contrato foi alterado.

## Cenários executados

Servidor descartável: `python -B tests/serve_ui_scenarios.py --port 8767`.
Os seis saves de QA e seus autosaves ficam em um diretório temporário separado.

- Rogue: invocação abriu exclusivamente pactos; seleção de quest + Bracelete,
  cancelamento por Escape preservando seleção, confirmação única, herói 2/2,
  item e artefato entregues imediatamente; quest permaneceu em andamento.
- Luide sem inimigos: feitiço seguido de movimento Cidade 1 → Centro na mesma
  janela; condições públicas mostraram Morcego e um dos dois movimentos usado.
  Inspeção acionada por Enter exibiu vida, povo, local e condições.
- Belial: nenhuma ação de pacto na Noite. Após encerrá-la e passar pelas jogadas
  de J2, J3 e J4, J1 recebeu a oferta no seu Dia. A passagem do aparelho ocultou
  a área privada e exigiu confirmação do próximo jogador.
- Larguras 360 e 1280: página sem transbordamento horizontal; mapa mantém sua
  rolagem interna. Nenhum erro ou aviso capturado no console.

## Correções de apresentação

Histórico traduz Dia/Noite e nomes de cartas/pactos via catálogo. Itens de Rogue
usam nomes legíveis na HUD, inspeção e consulta. Ações da janela de Luide mostram
nomes de unidades e destinos legíveis, sem mudar a ação enviada ao motor.
Valores desconhecidos mantêm fallback textual, sem inferir dados ausentes.

## Verificações e limites

443 testes Python aprovados, zero falhas; cinco scripts Node aprovados, sintaxe
JavaScript e `git diff --check` verificados. Os seis cenários também possuem
teste de restauração e disponibilidade de decisões legais.

QA real por mouse e teclado, com viewport móvel; não equivale a teste físico
de toque/PWA instalada. Sacrifício, Luna e Armadura continuam cobertos pelos
testes existentes e disponíveis no servidor, mas não foram rejogados neste ciclo.
Não certifica todas as combinações nem paridade integral. Próximas lacunas:
partidas completas das demais quests, aquisição dos quatro itens e cruzamentos
adicionais de janelas; consultar `PENDENCIAS_PARIDADE.md`.
