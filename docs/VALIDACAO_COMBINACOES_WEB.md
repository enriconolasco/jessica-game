# Escolhas e combinações — 30/09/2026

Referência terminal: `51586c9`. Base web anterior: `903d73b`.
Escopo: passa-e-joga local; não multiplayer remoto nem novo balanceamento.

## Correções

- Uma oferta de Rogue impossível de cumprir não bloqueia as demais ações: pactos
  esgotados, fonte demoníaca indisponível, perda da passiva copiada ou herói ausente.
  Ofertas viáveis continuam obrigatórias. O adaptador consulta o próprio core em
  cópias; não cria pactos, recompensas ou vida para contornar a indisponibilidade.
- Ofertas de jogadores eliminados não tomam o controle da Noite. Recusar uma
  oferta opcional continua possível, inclusive depois do esgotamento dos pactos.
- A HUD usa a janela noturna atual, não o próximo ataque da fila. Uma janela de
  Luide continua mostrando sua casa mesmo depois de a última unidade sair dela.
  Preparação, escolhas, Relógio e encerramento possuem identificação distinta.

As ofertas inviáveis permanecem no estado, como na referência; apenas deixam de
interromper o fluxo web. A invocação normal de Rogue continua sujeita às validações
originais. O caso de J♥ sem pactos cria o mesmo estado do core, sem recompensa.

## Verificação reproduzível

`python -B tests/test_web_mechanics_combinations.py`: 13 testes, incluindo:

- sete cenários de ofertas, rejeição atômica e retomada após save/load;
- onze habilidades diurnas, comparadas com chamadas diretas ao core: Arken, Dunga,
  Dandara, Púrpura, duas de Barba Negra, Baobá, duas de Bimbo, Guarari e Chamado;
  todas as opções legais desses cenários são serializadas e comparadas quanto
  a estado, logs e RNG; parâmetros extras são rejeitados sem mutação;
- janela de Luide vazia e preparação de Vovó, sem antecipar o combate seguinte;
- seis noites mistas, nos turnos 1 e 4, cobrindo os 12 povos em três grupos.
  Executam separadamente a orquestração real do terminal e a fila web, com
  ataques/retaliações, São Tomé copiando Canastra, Resistência e efeitos de morte.
  Cada ação web também é repetida a partir de save restaurado.

Os testes complementam `test_interaction_actions.py`, `test_night_web.py` e
`test_night_terminal_parity.py`, que cobrem Zebum, Aiquara, demais feitiços,
artefatos e janelas especiais.

### Instalação terminal independente

```powershell
python -B tests/compare_terminal_reference.py --reference C:/Users/UsuarioPc/Downloads/jessica
```

Comparação adicional aprovada: **125 ações diurnas e seis noites mistas** contra
a instalação terminal em Downloads, importada em processo Python separado.
Abrange escolhas concretas de artefatos, os 12 povos/feitiços e as onze habilidades
acima. As noites executam `run_night_phase` da referência com ataques programados;
as janelas facultativas não acionadas pelo roteiro são recusadas/suprimidas.

Compara estado completo, RNG e logs; exclui apenas `active_player_id`, `web_night`
e `web_reaction`, metadados exclusivos da orquestração web. Não grava na referência.
O caminho é um argumento, não uma dependência fixa: outro ambiente pode apontar
para seu checkout terminal. O script não integra a suíte padrão porque requer
uma segunda instalação independente.

Validação geral do lote: **421 testes Python, zero falhas**, cinco scripts Node
aprovados e sintaxe JavaScript validada.

Atualização de 01/10: o replay independente inclui também uma Noite com Armadura
e pagamento zero, passando a 125 ações diurnas e **sete** cenários noturnos.
As três partidas mistas completas estão em `VALIDACAO_PARTIDAS_COMPLETAS.md`.

## Limites e próximos passos

Não foi encontrado outro menu mecânico selecionável sem adaptador nesta revisão.
Isso não equivale a certificar todas as combinações. Permanecem a validação de
partidas mistas completas com múltiplas janelas/recompensas encadeadas e o
playtest real desktop/celular. Este lote não inclui nova inspeção visual no
navegador; inclui os testes automatizados existentes da interface.
