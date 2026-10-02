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
- Ação com revisão esperada e ID de comando. Lock por sala; repetição idêntica
  retorna o mesmo resultado; reutilização do ID para outra ação é rejeitada.
- Execução em cópia transacional do estado: erro não altera estado, RNG ou revisão.
  Reações noturnas continuam sendo validadas pela porta do motor, não pela fase
  simplificada do lobby. Jogadores fora da vez recebem somente suas ações legais.
- Hotseat continua em `python -m jessica.web.server`, porta 8765. API experimental:
  `python -m jessica.web.online_server`, somente localhost, porta 8767.

Contrato de transporte v1: `POST /rooms` (`name`),
`POST /rooms/{code}/join` (`name`), demais rotas com `Authorization: Bearer ...`:
`GET /rooms/{code}`, `POST .../select` (`people`, `hero_id`), `POST .../ready`
(`ready`), `POST .../start` (`{}`), `GET .../snapshot`, `POST .../actions`
(`command_id`, `revision`, `action`). Versões de ações/eventos/saves permanecem
as do core; revisão de sala é um contador independente.

## Ainda não concluído

1. Interface de lobby e associação da sessão ao cliente web completo, sem handoff.
   O protótipo atual é de API; quatro clientes HTTP não substituem quatro aparelhos.
2. WebSocket, retomada da credencial após recarregar e política de expiração/revogação.
3. Persistência transacional e recuperação após reiniciar, limites de recursos,
   política de abandono/pausa e tratamento de refazer/Mola online.
4. Partida completa em Wi-Fi e aparelhos físicos, depois hospedagem privada,
   HTTPS, backups e testes entre redes distintas. Não publicar esta API ainda.

Não há contas, chat, matchmaking, derrota por desconexão ou mudança de regras.
Escolhas do lobby são concorrentes, com povos exclusivos; a preferência/ordem de
seleção do setup presencial não foi transportada como janela online neste corte.

## Verificações executadas

`python -B tests/test_online_rooms.py`: sete cenários HTTP aprovados, cobrindo
quatro credenciais, exclusividade de povo, Ent desabilitado, início pelo anfitrião,
visões/eventos privados, credencial de outra sala, personificação, fora da vez,
parâmetros inválidos, revisão antiga, duas requisições simultâneas iguais,
isolamento das rotas administrativas, reconexão por credencial e ciclo Dia/Noite.
Inclui Armadura: somente a sessão do defensor resolve a interrupção; mão e eventos
privados do defensor não chegam ao atacante. O teste usa seed controlada somente
via fixture do servidor; a API rejeita seed enviada pelo cliente.

São testes de API em localhost, não playtest em quatro aparelhos, WebSocket,
auditoria de segurança externa ou validação de hospedagem.
Suíte completa após este corte: **461 testes Python aprovados, zero falhas**.
