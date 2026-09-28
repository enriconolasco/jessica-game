# Roteiro para a versão web local

Status em 2026-09-28: ações e escolhas do Dia ampliadas no navegador. O motor continua
sendo a única autoridade mecânica. Multiplayer online não faz parte deste roteiro.

## Concluído

- servidor HTTP local, criação de partida, PlayerView e ações estruturadas;
- coleta, vida da Cidade, Monumento, invocação, movimento e encerramento da janela;
- compra, transmutação e venda de Artefatos;
- eventos públicos/privados, minimapa responsivo e painel privado;
- save manual, autosave, load e validação da versão do save.
- setup local com nomes, parâmetros iniciais, 12 povos e heróis válidos vindos do catálogo do motor.
- tela de passagem do dispositivo que oculta a área privada na troca do jogador ativo.
- motor do terminal integrado até `1f0588d`, com correção posterior de Rogue e Valtherion;
- uso dos 12 artefatos, Pena e escolhas pendentes J♦/Feliz/Q♦; curas pendentes;
- pactos de Rogue, Belial e Tuza, incluindo prioridade obrigatória da oferta de Rogue;
- habilidades diurnas de Arken, Dunga, Dandara, Púrpura, Barba Negra, Bimbo,
  Baobá, Guarari e Chamado de Valtherion;
- histórico de eventos preservado no save/load; novas ações atômicas e testadas
  contra as funções originais do motor.
- feitiços: Resistência, Armadura de Ouro, Espoliar, Transformar em Morcego,
  Licantropo, Linhagem Ancestral, Levantar os Mortos, Decompor e Ressonância Mágica;
  cópias desses feitiços pelos Gnomos e rerrolagem de São Tomé;
- histórico visível completo em ordem cronológica, com separadores por turno;
  Cabaça Cheia limita cada Caroço vivo a uma rolagem por turno, persistida no save.

## Passos restantes

Sacrifício de Demônio agora disponível: seleção de herói e múltiplas cartas da mão
ou campo, inclusive cópia pelos Gnomos. Validação e execução pelo core, sem enumerar
todas as combinações. Testes cobrem paridade, duplicatas, rejeição e save/load.
Sonho Lúcido continua pendente: a cópia gnômica no core apenas marca
`sonho_lucido_pending_turn`, diferente da transformação/ativação imediata das Fadas.
Essa divergência deve ser corrigida e testada no motor antes de anunciar paridade web.

1. **Sincronizar o motor atual:** concluído para o lote acima; sincronizar novos
   patches do terminal a cada marco.
2. **Finalizar setup:** consulta detalhada de regras a partir de conteúdo estruturado.
3. **Completar o Dia:** Sonho Lúcido (seleções compostas),
   sua cópia pelos Gnomos, apostas antes do Dia do Curruna,
   Aiquara, Zebum, Miyamoto diurno e demais janelas especiais.
   Artefatos, escolhas pendentes, curas e habilidades listadas acima já estão adaptados.
4. **Implementar a Noite:** ordem por local/jogador, declarar ou passar, ataques,
   retaliações e janelas especiais/reacionais. Nenhuma regra ficará no frontend.
5. **Fechar o ciclo da partida:** manhã, mudança de fase, fim do turno, vitória,
   eliminação e início automático do turno seguinte.
6. **Save local completo:** listar, nomear, exportar/importar, autosaves rotativos,
   recuperação e migrações explícitas de formato.
7. **PWA offline:** manifest, service worker, instalação no celular, cache versionado e
   funcionamento local sem internet depois da primeira carga.
8. **UX e acessibilidade:** escolhas complexas, confirmações, histórico filtrável,
   ajuda contextual, teclado, toque, leitores de tela e telas pequenas.
9. **Bots locais:** primeiro bots determinísticos de teste; depois IA suficiente para
   uma pessoa jogar contra três adversários sem servidor externo.
10. **Validação final:** matriz dos 12 povos, partidas completas, saves de referência,
    equivalência terminal/web, testes mobile e ausência de informação secreta vazada.

## Critério de versão web local completa

Uma partida pode ser configurada, jogada e encerrada integralmente no navegador, em
passa-e-joga ou contra bots locais, com save/load e instalação PWA. O navegador apenas
apresenta `PlayerView`, ações e eventos; todas as decisões mecânicas permanecem no motor.

## Fora do escopo

Contas, matchmaking, lobby remoto, WebSocket entre dispositivos, servidor público,
reconexão online, autenticação e proteção contra trapaça em rede.
