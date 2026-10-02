# Preparação HTTPS — sem contratação ou publicação

O online aceita uma origem HTTPS explícita e usa `/updates` na mesma origem
para WebSocket. Terminal/hotseat, regras, ações, saves e identidade não mudam.
O acesso HTTP local/LAN continua usando duas portas como antes.

Isto prepara o transporte: **não inicia TLS, proxy, hospedagem ou domínio**.
Nenhum serviço pago foi contratado e nenhum certificado foi instalado.
Piloto gratuito com HTTPS/WSS externo já validado por túnel temporário:
[ONLINE_AMIGOS.md](ONLINE_AMIGOS.md). O exemplo TLS local abaixo é separado.

## Contrato do proxy

```text
navegador HTTPS/WSS → proxy → HTTP 127.0.0.1:8767
                          → WS   127.0.0.1:8768 (/updates)
```

- Python fica em loopback no mesmo computador do proxy; modo HTTPS recusa LAN.
- Preservar `Host`, `Origin`, `Authorization`, URI e corpo dos pedidos.
- `/updates` vai ao WS; todas as demais rotas vão ao HTTP. Não remover o caminho.
- Informar exatamente a origem pública HTTPS, sem caminho/query/fragmento.
- `Host` aceita somente o endereço configurado; `Origin`, quando presente, precisa
  corresponder à origem HTTPS. WS exige essa origem e autenticação própria.
- `Forwarded`/`X-Forwarded-*` **não** concedem confiança ou identidade. Não permitir
  que cabeçalhos enviados pelo navegador substituam a configuração do servidor.
- Credencial continua no Bearer HTTP/primeira mensagem WS, nunca em links.
- Não publicar 8767/8768, SQLite, backups, certificados ou endpoints de hotseat.
- Não registrar Authorization, corpos ou mensagens WS em logs do proxy.

O modo proxy injeta apenas uma marca pública `onlineTransport=same-origin` na
página; o cliente deriva `wss://<origem>/updates` do endereço aberto, sem porta+1.
Não recebe estado privado, segredo ou configuração de outra sala nessa marca.

## Exemplo opcional: HTTPS somente no próprio computador

[Caddyfile.local.example](../deploy/Caddyfile.local.example) é uma referência
para Caddy gratuito/open source, **não executada nesta entrega**. Usa loopback,
porta 9443 e certificado de autoridade local, sem solicitar certificado público
ou comprar domínio. Desativa o redirecionamento HTTP automático.

Se Caddy já estiver instalado, com o servidor anterior parado e o ambiente
Python do projeto ativo, em um terminal na raiz do projeto:

```powershell
python -m jessica.web.online_server --external-origin https://localhost:9443
```

Em outro terminal, validar primeiro e, somente depois, iniciar o proxy:

```powershell
caddy validate --config deploy/Caddyfile.local.example --adapter caddyfile
caddy run --config deploy/Caddyfile.local.example --adapter caddyfile
```

Abrir `https://localhost:9443/`. Não abrir o backend HTTP como se fosse a página
de jogo neste modo: seu Host local é intencionalmente rejeitado.

Na etapa inicial, Caddy não estava instalado. Agora há uma cópia portátil validada
no fluxo de túnel gratuito, sem TLS local. **Este exemplo `tls internal` não foi
executado.** Seu certificado local exige confiança explícita no navegador/sistema;
Caddy pode tentar instalar sua autoridade local ao executar. Avaliar isso antes
de iniciar: não instalar certificados automaticamente como parte do jogo e não
desativar validação TLS. Não serve como certificado público para convidados.

Trocar origem/porta cria outro armazenamento de acesso no navegador. Para o
piloto HTTPS, criar uma sala de teste; acesso lembrado do HTTP não é transferido.
O banco permanece o mesmo se `--storage` não mudar; nunca executar dois processos
sobre ele. Para testes isolados, escolher outro banco e outro par de portas,
ajustando também o proxy. Encerrar o proxy não elimina jogadores; reconexão e
deduplicação continuam pelo protocolo existente.

## Antes de acesso pela internet

Proxy real e HTTPS/WSS externo foram validados no piloto gratuito. Ainda faltam
partida completa em aparelhos, limites de produção, revisão de segurança,
armazenamento/backup externo e retomada após mudar o link. Não há hospedagem
contratada em vista. Não publicar esta API como serviço amplo apenas trocando um
domínio no exemplo. Em modo proxy, os limites por IP veem o proxy loopback:
**todos compartilham o orçamento**; cabeçalhos de IP não são confiáveis e não são
usados. Um rate limit por cliente precisa ser configurado na borda antes de
abertura pública. O protótipo continua com um único processo Python/banco.

Sem contratar nada pago: este trabalho fica no projeto/local. Uma eventual
alternativa gratuita será avaliada separadamente, sem cadastrar serviços agora.

## Verificação

`tests/test_online_proxy.py`: oito testes, incluindo validação de origem,
rejeição antes de criar banco, Host/Origin duplicados/falsos, página sem segredo,
WS autenticado e origem estrita, além de processo CLI real em loopback.
O teste HTTP simula o trecho atrás do proxy: não afirma ter testado TLS.
`tests/web_online_ui.cjs`: WSS na mesma origem em 443/8443 e modo LAN anterior.

Referências: [reverse_proxy/Host/WebSocket](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
e [HTTPS automático/local](https://caddyserver.com/docs/automatic-https).
