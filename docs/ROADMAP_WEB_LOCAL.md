# Roteiro para a versão web local

**Estado atual (01/10/2026):** candidata a playtest, base `c652408` e lote de fechamento, 449 testes
aprovados. A auditoria já mapeia todos os fluxos selecionáveis do terminal.
Ver `FECHAMENTO_WEB_LOCAL.md` para abrir, reportar bugs e o fechamento limitado.
O texto abaixo conserva o histórico de implementação; não indica que as antigas
restrições de heróis ainda estejam presentes. PWA é planejada, não entregue.

Status em 2026-09-29: Dia ampliado e Noite expandida em lote. O motor continua
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

Noite disponível para tropas e os heróis enumerados em
`night_actions.SUPPORTED_HEROES`; prioridade por local/jogador,
ataque/retaliação, passar, encerramento e próxima manhã. Fila persistida em save/load.
Seleção de alvos e ordem foram extraídas do terminal para `night_rules.py`; ambos
reutilizam essas funções. Dano e mortes continuam em `combat.resolve_attack`.
Heróis com janelas ainda não adaptadas bloqueiam essa fatia com aviso nominal
explícito. Não interpretar isso como cobertura noturna dos 12 povos.
Q♦ ativo já é permitido: quando dispara, a Noite passa ao dono da carta,
oferece Ouro/Magia e retoma a fila. Escolhas J♦/Feliz já pendentes também usam
a resolução existente. A interrupção é preservada em save/load.

Lote noturno adicional: heróis de combate/passivas já resolvidos no core,
incluindo anões, lobisomens, gigantes, mortos-vivos e dragões; ofertas de Rogue;
Belial guarda ofertas para o Dia seguinte (decisão de 01/10/2026);
Relógio de bolso opcional uma vez antes
do encerramento; Mar de Chamas preparado no Dia aplicado uma vez ao preparar
a Noite. Belial já executa seu efeito pelo hook existente de início da Noite.
Matriz de paridade cobre ataque de cada herói liberado, não todas as combinações.
Vovó e Luna também adaptadas: posição da Vovó antes de Mar de Chamas e
retorno opcional da Luna depois dele, antes da montagem da fila de combate.
Cada escolha persiste no save e não se repete ao recarregar.
Mandinga de Besouro e combate de Iúna também adaptados. Mandinga abre antes das
declarações e resolve escolhas de artefato pendentes antes de continuar.
Aiquara noturna adaptada na abertura (após Mar de Chamas, antes de Luna e Mandinga),
conforme decisão do usuário. Terminal também recebeu essa janela antes ausente.
Ainai e Luide Vampa integrados: teleporte no início e entre locais, janela de movimento/feitiço por jogador/local e retorno a locais resolvidos. Fila e escolhas persistem no save; falta playtest manual de paridade.
Roteiro de fechamento e critérios de paridade: [PARIDADE_WEB_TERMINAL.md](PARIDADE_WEB_TERMINAL.md).

Apostas: novas partidas abrem a alocação dos quatro naipes antes do Dia do
Curruna. A confirmação libera o Dia; escolhas vazias são permitidas como no
terminal. Save/load preserva a etapa. Saves antigos já no Dia não voltam ao
Curruna ao resolver apostas pendentes. A recorrência funciona após noites
compatíveis com a fatia noturna acima.

Habilidades diurnas adicionais: Aiquara move inimigos; Zebum obtém/reinvoca
heróis e oferece a sequência de anões quando disponível. Escolhas passam pelas
funções originais do core; sem mudança de custo, imunidade ou restrição.

Sacrifício de Demônio agora disponível: seleção de herói e múltiplas cartas da mão
ou campo, inclusive cópia pelos Gnomos. Validação e execução pelo core, sem enumerar
todas as combinações. Testes cobrem paridade, duplicatas, rejeição e save/load.
Sonho Lúcido disponível para uma carta, incluindo escolha do artefato transformado.
Cópia gnômica corrigida no motor e terminal: usa a mesma transformação/ativação
imediata das Fadas. Luna agora permite uma sequência de várias cartas e alvos.
A prévia resolve cada carta no servidor e atualiza os próximos alvos, incluindo
unidades invocadas na sequência. Confirmar executa tudo atomicamente; limpar não
gasta o feitiço. Falta playtest integrado de reações durante a sequência.
A antiga restrição de J♦ por último foi removida: o core agenda sua escolha para T+3.
Devaneio usa o caminho existente do core.

1. **Sincronizar o motor atual:** concluído para o lote acima; sincronizar novos
   patches do terminal a cada marco.
2. **Setup e consultas:** implementados catálogo completo e consulta estruturada,
   configurações e Curuna inicial sorteado como no terminal. Validar em playtest.
3. **Completar o Dia:** auditar demais decisões diurnas,
   demais janelas especiais. Miyamoto diurno, Aiquara diurna e Zebum já adaptados.
   Artefatos, escolhas pendentes, curas e habilidades listadas acima já estão adaptados.
4. **Validar a Noite:** implementados ordem por local/jogador, declarar ou passar,
   ataques, retaliações, janelas especiais e escolhas de Armadura. Nenhuma regra
   foi movida para o frontend. Primeiro lote diferencial terminal/web aprovado:
   `VALIDACAO_NOTURNA.md`. Luide e o primeiro encadeamento Armadura/Q♦/Belial
   comparados; faltam outras janelas intercaladas e partidas cruzadas completas.
5. **Fechar o ciclo da partida:** manhã, mudança de fase, fim do turno, vitória,
   eliminação e início automático do turno seguinte implementados e cobertos em
   `VALIDACAO_CICLO.md`; corrigido Curruna com Dia pulado. Ampliar cruzamentos.
6. **Save local completo:** lista, cópias nomeadas, exportar/importar e recuperar
   autosave implementados. Cinco recuperações anteriores e importação diurna do
   terminal implementadas; pendentes migrações futuras e saves noturnos sem fila.
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
