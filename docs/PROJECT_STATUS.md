# Estado do projeto — 03/10/2026

## Atualização de configuração pré-jogo

Na branch `codex/online-rooms`: motor compartilhado e três clientes aceitam
2–5 jogadores; vida/Ouro/Magia/artefatos individuais; mapa com cidades distribuídas
ao redor do centro; recompensa por eliminação conta vivos antes da morte.
Saves e salas antigos de quatro jogadores mantêm compatibilidade.
Especificação: [CONFIGURACAO_PARTIDA.md](CONFIGURACAO_PARTIDA.md).
Verificação: suíte anterior executada; regressão do roteiro de ataque obrigatório
corrigida e cenários afetados reexecutados. Total atualizado: 535 testes Python,
sete testes Node, preparação terminal e navegador com 2–5 cidades verificados.
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
