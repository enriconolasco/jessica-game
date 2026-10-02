# Limites operacionais do protótipo online

Somente servidor online. Terminal/hotseat, motor, turnos e contratos de gameplay
não mudam. Sem derrota por desconexão, expiração ou exclusão automática de salas.

| Limite padrão | Comportamento |
| --- | --- |
| 64 conexões HTTP simultâneas | Sem slot, fecha a conexão sem executar o pedido; fila de aceitação 32 |
| 64 canais WS tratados simultaneamente | Inclui canais aguardando autenticação; excedente fechado com 1013 |
| 16 canais WS por sala | Limite anterior preservado; autenticação em 5 s e mensagens até 4 KiB |
| API: 20 pedidos/s, rajada de 120 por IP | Excedente recebe 429 e `Retry-After`; raiz/assets/static não consomem esse orçamento |
| Criar sala: 3/min, rajada de 8 por IP | Orçamento separado; consultar/jogar em salas existentes continua permitido |
| 256 salas guardadas | Conta lobby, partidas em andamento e encerradas; criação excedente recebe 503 |
| POST: 64 KiB; inatividade de socket 15 s | Tamanho/corpo completo conferidos antes de executar; não é prazo total de uma partida |

IP é o par TCP real, nunca um `X-Forwarded-For` enviado pelo cliente. Pessoas na
mesma rede podem compartilhar o orçamento. A tabela de rate limit tem até 2048
chaves IP/categoria e remove chaves inativas após dez minutos; cheia, recusa novas
chaves temporariamente. Contadores reiniciam junto ao processo, não ao GameState.

Na criação, um banco restaurado com mais salas que o limite permanece inteiro
e acessível; apenas novas salas ficam bloqueadas. Nenhum save/backups/histórico
é apagado para liberar espaço. Ainda falta definir arquivamento e retenção.

## Ajustar capacidade

Com servidor anterior parado e ambiente do projeto ativo:

```powershell
python -m jessica.web.online_server --max-connections 64 --max-rooms 256
```

HTTP aceita 1–1024 conexões; salas, 1–10000. Os launchers usam os padrões.
`--host`, `--lan`, `--port` e `--storage` continuam disponíveis. `--external-origin`
prepara um proxy HTTPS explícito com backend loopback; ver [ONLINE_HTTPS.md](ONLINE_HTTPS.md).
Aumentar esses
limites aumenta consumo potencial de memória/disco; não torna o serviço público
nem autoriza abrir firewall/roteador. Rate limits e limite WS estão no código,
não são parâmetros enviados pelos jogadores.

## Recusas e recuperação

- **400:** tamanho/enquadramento ambíguo (Content-Length duplicado, Transfer-Encoding,
  tamanho inválido) ou corpo incompleto. **413:** corpo acima de 64 KiB.
- **422:** JSON inválido, chave duplicada, NaN/Infinity, objeto inválido ou aninhamento
  excessivo. Nenhum desses pedidos chega às regras.
- **429:** aguardar o intervalo `Retry-After`; sem dados privados na resposta.
- **503:** falta de capacidade/armazenamento; verificar mensagem e console do servidor.
- Fechamento de conexão por falta de slot pode não ter resposta JSON. O cliente
  trata como resultado não confirmado, sem trocar de jogador.

Quando uma ação perde a resposta, depois recebe 429/503, o cliente **preserva o
mesmo comando e ID**. Use **Reenviar comando pendente** após resolver/aguardar;
não crie uma segunda ação supondo que a anterior não ocorreu. Deduplicação
continua no servidor e sobrevive ao reinício. Recusas não alteram RNG/revisão.

## O que ainda falta para internet

Não é proteção completa contra DDoS. Handshakes WS, timeouts absolutos, proxy
HTTPS real (origem explícita já preparada), quotas de histórico/disco, logs operacionais, backups
externos, manutenção/arquivamento e testes de carga precisam de preparação.
HTTP não é um servidor de produção. Os testes não equivalem a auditoria externa
ou partida completa em celulares. Nenhum serviço pago foi criado/publicado.

## Verificações

`tests/test_online_limits.py`: nove testes de orçamento concorrente/recarga,
memória limitada/expiração, 429 sem vazamento/mutação, criação separada, salas
preservadas acima do limite, JSON/corpo inválido, slots HTTP reutilizados após
conclusão/falha de worker e canais WS limitados antes de autenticar.
`tests/web_online_access_ui.cjs`: 429/503 depois de resposta perdida mantêm ID
e acesso lembrado, com uma única execução confirmada.
