# Online — auditoria e primeiro corte — 02/10/2026

Referência recuperável: `web-local-pre-online-2026-10-02`, commit `bd1df00`.
Desenvolvimento: `codex/online-rooms`; hotseat/terminal permanecem na `main`.

## Diagnóstico

| Área | Hotseat atual | Adaptação online |
| --- | --- | --- |
| Identidade | `player_id` recebido do navegador; troca livre no handoff | Credencial vinculada ao participante; nunca alternar ao jogador ativo |
| Ações | `apply_action` valida as regras | Autenticar antes, serializar por sala, validar revisão e deduplicar comandos |
| Visão | `view_for_player` filtra dados privados | Escolher jogador exclusivamente pela sessão; não aceitar identidade na URL |
| Eventos | Eventos públicos/privados com destinatários | Filtrar para a sessão em respostas e futuras mensagens WebSocket |
| Save | Exportação completa, importação e refazer/Mola acessíveis | Não expor essas rotas; persistência online separada e recuperação controlada |
| Histórico | Em memória + saves locais | Persistir revisão, participantes, credenciais protegidas, comandos/resultados e RNG |
| Transporte | HTTP local e atualização sob demanda | Lobby HTTP, atualização WebSocket, reconexão e snapshot consistente |
| Operação | `http.server`, localhost, sem autenticação | Ainda não serve como implantação pública; requer HTTPS, limites e armazenamento |

Não basta disponibilizar o servidor hotseat na rede: `/export`, `/import`, `/system`
e a escolha de `player_id` vazariam dados ou permitiriam controle indevido.
O servidor online é separado e **não delega rotas de partida ao Handler hotseat**.
Compartilha catálogo, assets, inicialização e a porta do mesmo motor.

## Implementado neste primeiro corte

- Criar sala por código, quatro credenciais independentes, escolha de povo/herói,
  pronto e início pelo anfitrião. Credenciais aleatórias de 256 bits; somente hash
  permanece no participante do servidor. Não trafegam na URL ou visão pública.
- Seed aleatória gerada exclusivamente no servidor, não recebida do anfitrião
  nem enviada aos participantes. Estado/RNG determinísticos continuam no motor;
  previsibilidade a partir dos resultados públicos requer auditoria antes da internet.
- Snapshot atômico com a PlayerView, ações legais e eventos da sessão autenticada.
- Lobby no navegador: criar/entrar por convite, consultar regras, escolher povo e
  herói, confirmar presença e iniciar. Botões aguardam a resposta do servidor.
- Cliente completo reutilizado sem handoff: cada aba mantém sua identidade,
  mesmo fora da vez. Credencial em `sessionStorage` permite recarregar a aba;
  fechar a aba perde essa credencial. Link de convite não contém credenciais.
- WebSocket autenticado notifica novas revisões; o cliente busca o snapshot
  privado via HTTP. Nenhum estado, mão, evento privado ou credencial é difundido.
  Reconexão com espera progressiva de 1 a 15 segundos; consultas HTTP a cada dois
  segundos ficam como fallback enquanto o canal estiver indisponível.
  Comando sem resposta permanece pendente e é reenviado com o mesmo ID, sem duplicação.
- Ação com revisão esperada e ID de comando. Lock por sala; repetição idêntica
  retorna o mesmo resultado; reutilização do ID para outra ação é rejeitada.
- Execução em cópia transacional do estado: erro não altera estado, RNG ou revisão.
  Reações noturnas continuam sendo validadas pela porta do motor, não pela fase
  simplificada do lobby. Jogadores fora da vez recebem somente suas ações legais.
- Hotseat continua em `python -m jessica.web.server`, porta 8765. API experimental:
  `python -m jessica.web.online_server`, somente localhost, porta 8767.
  Na branch online, `JOGAR_ONLINE.cmd` inicia esse servidor; abra quatro abas
  independentes em `http://127.0.0.1:8767` e entre pelo mesmo código.
  Isso ainda não permite acesso por outros aparelhos ou pela internet.
  A dependência opcional `requirements-online.txt` é instalada pelo launcher
  somente no modo online. HTTP usa 8767; WebSocket usa 8768, ambos em localhost.
  Para testar sem interromper um servidor existente:
  `python -m jessica.web.online_server --port 8877` (WebSocket 8878).
  Porta ocupada é rejeitada; não iniciar outro servidor sobre uma partida ativa.

Contrato de transporte v1: `POST /rooms` (`name`),
`POST /rooms/{code}/join` (`name`), demais rotas com `Authorization: Bearer ...`:
`GET /rooms/{code}`, `POST .../select` (`people`, `hero_id`), `POST .../ready`
(`ready`), `POST .../start` (`{}`), `GET .../snapshot`, `POST .../actions`
(`command_id`, `revision`, `action`). Versões de ações/eventos/saves permanecem
as do core; revisão de sala é um contador independente.
`POST .../dream-preview` valida a identidade/ação legal e reutiliza a prévia
de Sonho Lúcido do motor, sem alterar estado ou RNG.

Transporte de notificações v1: `ws://127.0.0.1:8768/updates`. Autenticação na
primeira mensagem: `{version: 1, code, credential}`; nunca na URL. Origem HTTP
deve ser `http://127.0.0.1:8767` ou `http://localhost:8767`. Após autenticar,
envia a revisão atual e posteriores: `{type: "room_changed", version: 1, revision}`.
Ações continuam exclusivamente via HTTP. Filas retêm só a revisão mais recente;
limites: 4 KB por mensagem, cinco segundos para autenticar, 16 canais por sala.
Ping detecta interrupções; desconexão não modifica jogadores ou regras.
Base do transporte: [documentação oficial websockets](https://websockets.readthedocs.io/en/stable/reference/asyncio/server.html).

## Ainda não concluído

1. Validar reconexão após queda de rede em aparelhos físicos e revisar a topologia
   de duas portas para hospedagem HTTPS/reverse proxy.
2. Recuperação de credencial após fechar a aba, expiração/revogação e vagas abandonadas.
3. Persistência transacional e recuperação após reiniciar, limites de recursos,
   política de abandono/pausa e tratamento de refazer/Mola online.
4. Partida completa em Wi-Fi e aparelhos físicos, depois hospedagem privada,
   HTTPS, backups e testes entre redes distintas. Não publicar esta API ainda.

Não há contas, chat, matchmaking, derrota por desconexão ou mudança de regras.
Escolhas do lobby são concorrentes, com povos exclusivos; a preferência/ordem de
seleção do setup presencial não foi transportada como janela online neste corte.

## Verificações executadas

`python -B tests/test_online_rooms.py`: nove cenários HTTP aprovados, cobrindo
quatro credenciais, exclusividade de povo, Ent desabilitado, início pelo anfitrião,
visões/eventos privados, credencial de outra sala, personificação, fora da vez,
parâmetros inválidos, revisão antiga, duas requisições simultâneas iguais,
isolamento das rotas administrativas, reconexão por credencial e ciclo Dia/Noite.
Inclui Armadura: somente a sessão do defensor resolve a interrupção; mão e eventos
privados do defensor não chegam ao atacante. O teste usa seed controlada somente
via fixture do servidor; a API rejeita seed enviada pelo cliente.
Inclui raiz online com scripts compartilhados e prévia privada de Sonho Lúcido.

`node tests/web_online_ui.cjs`: identidade fixa, isolamento do transporte,
retorno após recarregar, reenvio após perda de resposta e bloqueio de cliques
concorrentes no lobby. Também cobre notificação WebSocket, ausência de consultas
periódicas com canal ativo, atualização adiada durante escolhas e reconexão
mantendo a credencial. Os cinco testes Node anteriores também passam.

`python -B tests/test_online_notifications.py`: cinco testes com sockets reais:
quatro sessões notificadas, isolamento entre salas, ações rejeitadas/repetidas
sem nova revisão, reconexão, fechamento/liberação de assinaturas, rejeição de
credenciais/protocolo/origem inválidos e proibição de ações no canal.

Teste no navegador com quatro abas: convite, escolhas/pronto, início, coleta,
troca de turno, ações apenas na aba autorizada e recarregamento mantendo J2.
Sem erros de console na aba verificada. A emulação de largura não foi aplicada
pelo navegador disponível; validação móvel permanece pendente.

WebSocket também validado no navegador, em servidor isolado nas portas 8877/8878:
duas sessões, escolha pública sincronizada entre abas, indicador de tempo real,
recarregamento mantendo identidade e restabelecendo o canal; sem erros de console.
O teste inicial em 8767 alcançava um servidor antigo ainda aberto. Nenhuma sessão
existente foi encerrada; o fallback HTTP funcionou durante essa divergência.

São testes de API/WebSocket em localhost, não playtest em quatro aparelhos,
auditoria de segurança externa ou validação de hospedagem.
Suíte completa após este corte: **468 testes Python aprovados, zero falhas**.
