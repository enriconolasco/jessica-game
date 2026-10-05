# Estado do projeto — 04/10/2026

## Catálogo-base do mundo

Produção de novos textos pausada por decisão do usuário. Base editorial estruturada:
dois locais com nomes aprovados, 12 povos, 43 definições de heróis, 13 tipos de
artefato, quatro itens de Rogue, 12 feitiços e seis pactos. Não há história,
fronteiras, biografias ou culturas preenchidas por inferência. Cinco resumos de
heróis na UI sinalizados; nenhum patch mecânico aplicado nesta etapa.
Índice/fichas e perguntas: [CATALOGO_MUNDO.md](CATALOGO_MUNDO.md).
Confirmado: mundo conectado e cidades variáveis por partida.
Quatro famílias geográficas aprovadas; dois locais enquadrados nas famílias.
Próximo marco: validar identidade dos heróis e nomear poucas regiões quando necessário.
Quatro testes do catálogo e 16 narrativos passaram; somente dados/documentos adicionados.

## Piloto narrativo terminal

Na mesma branch `codex/online-rooms`: 25 textos ativos v0.2, introdução/transições/encerramento
opcionais, RNG separado, perfil persistente e reprodução de escolhas. Rich literal;
sem combate narrado ou alteração de regras. Checkpoints CLI entre turnos completos,
com retomada sem repetir introdução. Web ainda não renderiza narrativa.
Contrato/voz/comandos: [NARRATIVA_V0_1.md](NARRATIVA_V0_1.md).
16 testes narrativos aprovados; nesta atualização, 51 testes pertinentes passaram
(narrativa, serialização, contrato headless e recuperação web). A suíte completa
da entrega anterior teve 549 aprovados e três testes
do atualizador impedidos por permissões; os três aprovados na reexecução autorizada
(552 no conjunto). Oito testes Node aprovados. Playtest humano do ritmo pendente.
`main` e instalação Downloads não alterados.
Introduções incluem os heróis públicos escolhidos e o estilo dos exemplos 2/3.
Nomes novos de regiões ainda não oficializados; v0.1/saves antigos preservados.

## Atualização de configuração pré-jogo

Na branch `codex/online-rooms`: motor compartilhado e três clientes aceitam
2–5 jogadores; vida/Ouro/Magia/artefatos individuais; mapa com cidades distribuídas
ao redor do centro; recompensa por eliminação conta vivos antes da morte.
Saves e salas antigos de quatro jogadores mantêm compatibilidade.
Especificação: [CONFIGURACAO_PARTIDA.md](CONFIGURACAO_PARTIDA.md).
Preparação: todos confirmam povos públicos antes de escolher heróis secretos;
a última confirmação revela os heróis e inicia a partida. Online filtra as escolhas
no servidor, inclusive para o anfitrião; terminal/hotseat usam passagem do aparelho.
Salas antigas não iniciadas exigem nova confirmação dos povos.
Verificação: 539 testes Python e oito testes Node aprovados; navegador verificado
com passagem privada no hotseat e duas sessões online, sigilo e revelação conjunta.
Preparação terminal e navegador com 2–5 cidades também verificados.
Não comprova todas as combinações: partidas humanas completas por quantidade pendentes.
Esta alteração de regras/configuração ainda não foi integrada à referência `main`.

## Referência e transporte anteriores

- Versão compartilhada de playtest: `main`, `bd1df00`.
- Referência recuperável: tag `web-local-pre-online-2026-10-02`.
- Terminal/Hotseat: motor e atualizador consolidados; 454 testes Python,
  cinco testes Node e comparação independente de 125 ações/dez noites aprovados.
- Online: `codex/online-rooms`; API autenticada e lobby ligados ao cliente completo,
  sem handoff, identidade fixa e retorno após recarregar. WebSocket/reconexão
  implementados com fallback HTTP. Persistência SQLite implementada no servidor;
  dez testes de recuperação/durabilidade aprovados, incluindo reinício real.
  Suíte completa: 526 testes Python e sete testes Node aprovados.
  WebSocket verificado no navegador em duas abas,
  com escolha sincronizada e identidade/reconexão preservadas após recarregar.
  Nenhuma regra alterada; terminal/hotseat de referência permanecem na `main`.
- Acesso LAN opcional preparado (`JOGAR_REDE_LOCAL.cmd`), com bind/origem restritos
  e oito testes próprios aprovados. Nenhuma interface LAN/firewall ativada nesta entrega.
- Backups automáticos privados de SQLite implementados; oito testes próprios
  aprovados. Cópias antigas não são apagadas; recuperação usa banco separado.
- Retomada após fechar aba: opt-in de acesso lembrado no navegador pessoal,
  validado no servidor, com pendência deduplicada e um teste Node próprio aprovado.
- Revogação/troca de credencial implementada para o próprio participante, com
  recuperação de resposta perdida e invalidação HTTP/WS; seis testes próprios aprovados.
- Limites HTTP/WS/API/criação/salas implementados, sem excluir partidas;
  nove testes próprios aprovados. JSON ambíguo/incompleto é recusado; 429/503
  preservam o comando pendente para reenvio sem duplicação.
- Transporte preparado para proxy HTTPS explícito, backend loopback e WSS na mesma
  origem; oito testes próprios aprovados. Exemplo TLS local separado não executado.
- Piloto gratuito com amigos: `JOGAR_AMIGOS.cmd`, Caddy/cloudflared portáteis oficiais,
  PC como servidor e túnel temporário. Nove testes próprios aprovados; Caddy real
  em loopback e HTTPS/WSS externo verificados com quatro sessões/ação/deduplicação.
  Encerramento Windows corrigido e retestado: três portas/filhos liberados. Todos
  os túneis de teste encerrados; nenhum serviço pago, certificado local ou conta criado.
- Próxima integração: partida completa e interrupções em aparelhos físicos na mesma rede.
  Partida completa humana entre redes distintas e retomada quando o link muda
  pendentes; banco é preservado, credencial no navegador não migra de origem.
  Recuperação sem token válido, expiração, pausa/abandono e backups externos/retenção
  pendentes. Sem hospedagem contratada em vista.

Contratos/limites: [ONLINE_AUDITORIA.md](ONLINE_AUDITORIA.md).
Atualização comum: [FLUXO_ATUALIZACAO.md](FLUXO_ATUALIZACAO.md).
Roteiro de rede: [ONLINE_REDE_LOCAL.md](ONLINE_REDE_LOCAL.md).
Retomada/privacidade: [ONLINE_ACESSO.md](ONLINE_ACESSO.md).
Operação/limites: [ONLINE_OPERACAO.md](ONLINE_OPERACAO.md).
Preparação HTTPS: [ONLINE_HTTPS.md](ONLINE_HTTPS.md).
Piloto gratuito: [ONLINE_AMIGOS.md](ONLINE_AMIGOS.md).
