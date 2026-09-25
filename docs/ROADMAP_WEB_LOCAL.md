# Roteiro para a versão web local

Status em 2026-09-25: corte vertical do Dia funcionando no navegador. O motor continua
sendo a única autoridade mecânica. Multiplayer online não faz parte deste roteiro.

## Concluído

- servidor HTTP local, criação de partida, PlayerView e ações estruturadas;
- coleta, vida da Cidade, Monumento, invocação, movimento e encerramento da janela;
- compra, transmutação e venda de Artefatos;
- eventos públicos/privados, minimapa responsivo e painel privado;
- save manual, autosave, load e validação da versão do save.
- setup local com nomes, parâmetros iniciais, 12 povos e heróis válidos vindos do catálogo do motor.

## Passos restantes

1. **Sincronizar o motor atual:** transportar seletivamente os patches validados do
   terminal, preservar servidor/assets e comprovar paridade pelas mesmas seeds.
2. **Finalizar setup e passagem local:** consulta detalhada de regras e ocultação da
   tela durante a passagem do dispositivo entre jogadores.
3. **Completar o Dia:** jogar Artefatos, escolhas pendentes, feitiços, habilidades,
   curas, apostas e demais ações especiais usando contratos estruturados.
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
