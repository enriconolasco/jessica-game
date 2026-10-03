# Jogar com amigos — PC como servidor, sem hospedagem contratada

Piloto no branch `codex/online-rooms`. O PC executa o mesmo motor Python; um
Quick Tunnel gratuito fornece HTTPS/WSS temporário. Não exige conta, cartão ou
domínio próprio. Não instala serviço permanente, certificados locais ou firewall.

## Neste computador

1. Feche o servidor **online** anterior antes de iniciar; não encerre uma partida
   em andamento. Terminal e hotseat podem continuar abertos em suas próprias portas.
2. Abra `JOGAR_AMIGOS.cmd`, na raiz deste projeto.
3. Aguarde **“Abra no PC e nos celulares”**. Abra o link HTTPS mostrado também no PC.
4. Crie uma sala. Envie aos amigos o convite da sala, não sua credencial.
5. O anfitrião define 2–5 vagas ao criar e pode personalizar as condições iniciais.
   Cada um escolhe povo/herói e marca pronto; a partida começa com todas as vagas prontas.
6. Mantenha PC, internet e janela do iniciador abertos durante a partida. Um Ctrl+C
   encerra túnel e processos deste iniciador; aguarde a janela terminar.

Não é preciso configurar roteador ou usar Caddy manualmente. Se uma porta estiver
ocupada, o iniciador recusa sem interromper outro servidor. Para um teste isolado,
com ambiente Python ativo:

```powershell
python -m jessica.web.quick_tunnel --port 8877 --storage saves/online/amigos-teste.sqlite3
```

Usa três portas consecutivas: HTTP 8877, WS 8878 e proxy 8879, todas em loopback.
O link externo não contém essas portas. `--storage` diferente mantém bancos separados.

## Ferramentas gratuitas

Neste computador foram colocados executáveis **portáteis**, sem instalação global:

- `tools/runtime/cloudflared.exe`: 2026.9.3;
- `tools/runtime/caddy.exe`: 2.11.6.

Downloads vieram dos releases oficiais; SHA256 conferido contra o digest das
respectivas releases. A pasta é ignorada pelo Git; binários não vão ao GitHub.
O iniciador prefere esses arquivos, depois procura no PATH. Não baixa ferramentas
nem entra em conta automaticamente. A preparação Python normal do `JOGAR.cmd`
continua instalando as dependências gratuitas na `.venv` quando necessário.

Em outro PC Windows 64 bits, baixar [cloudflared oficial](https://developers.cloudflare.com/tunnel/downloads/)
e [Caddy oficial](https://caddyserver.com/docs/install). Colocar os executáveis com
esses nomes em `tools/runtime/`, ou disponibilizá-los no PATH. Conferir origem e
hash dos downloads; não usar instaladores aleatórios. Não precisam rodar como serviço.

## Limites e cuidados

- Compartilhar apenas com convidados. **Conhecer o link permite acessar o site**;
  link não é senha. Credenciais individuais continuam controlando cada jogador.
- Link muda quando o túnel reinicia; o gratuito não garante disponibilidade.
- **Retomada por um novo link ainda é pendência:** o banco preserva a partida, mas
  o acesso lembrado no navegador fica preso ao endereço antigo. Por enquanto,
  use para partidas de playtest completas sem reiniciar o túnel. Não apagar saves
  nem criar outro jogador achando que isso recupera uma posição antiga.
- Interrupção temporária no mesmo link usa a reconexão existente, sem derrota.
- Cloudflare intermedeia o tráfego HTTPS. Não transmitir tokens em convites/logs;
  não abrir dados de outras pessoas em computador compartilhado.
- SQLite/backups ficam no PC; queda/perda do disco não é coberta pelo túnel.
- Todos compartilham o orçamento por IP do proxy; limites atuais bastam para o
  piloto pequeno, não equivalem a proteção de serviço público ou teste de carga.
- O serviço gratuito limita 200 pedidos simultâneos; não suporta SSE. Nosso
  cliente usa WebSocket e fallback HTTP, não SSE.

O iniciador usa config Cloudflare vazia explícita, não a configuração de outra
conta/túnel no computador. Desativa autoupdate e remove variáveis `TUNNEL_*` do
ambiente dos filhos. Caddy valida antes de iniciar o motor, fica em loopback,
com admin/HTTPS automático desativados e Host restrito ao link recebido. HTTPS
público é fornecido pelo túnel, sem instalar autoridade certificadora no PC.
Falha inicial tem prazo limitado e fecha os filhos criados; não mata servidores alheios.

## Validação realizada

- Nove testes automáticos do iniciador: pré-validação, configuração, portas,
  timeout, sinais de encerramento e preservação de processo não relacionado.
- `python tests/probe_quick_proxy.py`: Caddy real em loopback, quatro identidades,
  autorização/visões, WebSocket, coleta, deduplicação e rejeição de origem inválida.
- Teste externo isolado: quatro sessões via HTTPS, início da partida, coleta,
  rejeição de ação de outro jogador, WSS/notificação e repetição sem duplicar ação.
- `python tests/probe_quick_tunnel.py`: teste **opt-in que abre acesso externo
  temporário**; confirma HTTPS/WSS e fechamento dos três processos/portas. Usa
  somente sala e banco fictícios, apagados no fim. Não roda na suíte normal.

Os túneis de validação foram encerrados. Não há link permanente ou servidor de
amigos deixado aberto. Ainda falta partida completa humana entre PC/celulares
em redes diferentes e solução de retomada quando o endereço muda.

Referências: [Quick Tunnels e limitações](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/),
[parâmetros cloudflared](https://developers.cloudflare.com/tunnel/reference/run-parameters/)
e [proxy Caddy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
