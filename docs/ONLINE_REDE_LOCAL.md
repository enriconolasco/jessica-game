# Teste online na rede local

Modo opcional para PC e celulares na mesma rede privada/confiável. Não é
hospedagem na internet: o PC precisa permanecer ligado. HTTP/WS ainda não têm
TLS; não use Wi-Fi público, não abra portas no roteador e não publique este servidor.

## Quando quiser testar

1. Termine partidas antigas antes de trocar de modo/endereço. Feche o servidor
   online anterior, mas não precisa fechar o jogo de terminal ou hotseat.
2. No PC, abra `JOGAR_REDE_LOCAL.cmd`. Escolha o IPv4 da conexão Wi-Fi/Ethernet
   usada pelos celulares. Havendo interfaces virtuais/VPN, confira qual é a rede
   doméstica. `0` cancela sem iniciar servidor.
3. Abra **o endereço mostrado na janela** no PC e nos celulares, por exemplo
   `http://192.168.1.10:8767`. Não use `localhost` no celular: ele apontaria para
   o próprio aparelho. Todos devem usar o mesmo endereço do PC.
4. Crie uma sala no PC. Os demais entram pelo link/código, escolhem povo/herói e
   marcam pronto; o anfitrião inicia quando os quatro estiverem prontos.

O link contém só o código da sala. Cada aparelho recebe sua própria credencial,
mantida na aba e, opcionalmente, lembrada no navegador pessoal. Não compartilhe
credenciais nem mude a origem/IP durante a partida: armazenamento é isolado por
endereço. Marque **Lembrar meu acesso neste navegador** antes de fechar a aba se
quiser retomar nesse mesmo perfil/endereço; detalhes: [ONLINE_ACESSO.md](ONLINE_ACESSO.md).
Salas persistidas não são apagadas ao trocar de modo, mas a credencial não migra
automaticamente entre `localhost` e o IP da rede.

Alternativa, com o ambiente do projeto ativo:

```powershell
python -m jessica.web.online_server --host 192.168.1.10
```

O servidor escuta apenas no IPv4 escolhido: HTTP 8767 e WebSocket 8768. Portas
diferentes podem ser escolhidas com `--port`; WS sempre usa a seguinte. O padrão
`JOGAR_ONLINE.cmd` continua restrito ao próprio computador.

## Se não abrir no celular

- Confirme mesma rede, IP escolhido e servidor aberto. Evite rede de convidados,
  isolamento entre clientes e VPN durante o teste.
- Caso Windows/navegador peça autorização de rede, decida manualmente e limite
  à rede privada. O launcher não muda firewall nem concede permissões.
- Confira TCP 8767/8768 somente na rede privada; nunca desative o firewall.
- Se HTTP funcionar mas WS não, a interface usa fallback HTTP. O indicador
  deve mostrar **tempo real** quando o canal WebSocket estiver ativo.

## Roteiro de validação humana

Quatro aparelhos: conferir identidade/mão própria, troca de turno, coleta,
combate e escolhas especiais. Tentar agir fora da vez. Recarregar um aparelho,
interromper/restaurar sua conexão, reenviar comando pendente e reiniciar o
servidor mantendo as abas/banco. Estado, revisão e recursos devem permanecer
consistentes; nenhum recurso pode ser concedido duas vezes. Concluir uma partida.

**Ainda pendente:** executar esse roteiro em aparelhos físicos e registrar bugs.
Testes automáticos não equivalem a uma partida completa por Wi-Fi.

## Proteções e verificações

IPv4 limitado a loopback/RFC1918; `0.0.0.0`, IP público e domínio arbitrário
são recusados. Hosts/origens HTTP e origens WS são explícitos, sem curingas.
Identidade, ações, visões privadas, deduplicação e persistência permanecem no
servidor. Não houve alteração de regras/motor.

`tests/test_online_network.py`: oito testes de seleção/endereço, host/origem,
recusa de bind público, launchers e servidor real em interface loopback específica.
Teste de interface também confirma convite/WS usando o IP da rede, sem cálculos
mecânicos no navegador.
