# Retomar o mesmo jogador após fechar a aba

Sem contas: a credencial aleatória continua vinculada ao participante no servidor.
O servidor grava apenas seu hash. Não há escolha livre de `player_id` nem token
no convite, na URL, no histórico público ou na PlayerView.

## Aparelho pessoal

1. Entre/crie uma sala e marque **Lembrar meu acesso neste navegador**.
2. Volte ao mesmo endereço, navegador e perfil. Seu acesso é retomado após
   validação pelo servidor; fechar a aba não cria outro jogador nem libera vaga.
3. Se houver uma ação sem resposta confirmada, use **Reenviar comando pendente**.
   A mesma ação e identificador são preservados, evitando executar duas vezes.

Desmarcada por padrão. Guarda **um único acesso** por origem em `localStorage`;
o funcionamento temporário de cada aba continua em `sessionStorage`. Na mesma
origem, outras abas recebem aviso visual quando a cópia lembrada é removida ou
substituída. Lembrar outro jogador exige confirmação antes de substituir a cópia.
As abas já abertas mantêm suas identidades; não há mudança para o jogador ativo.

Se um convite aponta para outra sala, não entra automaticamente na sala lembrada:
mostra o convite e oferece **Retomar meu acesso** como escolha explícita. Dados
malformados ou sessão recusada não concedem acesso; uma recusa do servidor
preserva a cópia local para corrigir endereço/banco e tentar novamente.

## Cuidados e limites

- **Não habilite em aparelho compartilhado.** Quem usar esse perfil do navegador
  pode controlar o jogador. A credencial original passa a ficar nesse navegador,
  não no banco do servidor. Ainda não há HTTPS neste protótipo de rede privada.
- `localhost`, `127.0.0.1`, IP de Wi-Fi e portas diferentes são origens distintas.
  A cópia não migra entre elas, navegadores, perfis ou aparelhos. Mantenha o mesmo
  endereço durante a partida.
- **Desmarcar** remove só a cópia persistente; a aba atual continua funcionando.
  **Limpar sessão deste aparelho** limpa esta aba e a cópia lembrada se forem
  do mesmo acesso. Não apaga uma cópia lembrada de outro jogador/sala.
- **Esquecer acesso lembrado** remove a cópia local após confirmação. Essas ações
  não liberam vaga, não encerram a partida e **não revogam credenciais em outras
  abas/aparelhos**. Revogação, rotação e expiração no servidor seguem pendentes.
- Se não marcou a opção antes de fechar, apagou dados do navegador ou perdeu o
  aparelho, não há recuperação por nome/código de sala. O servidor não recupera
  a credencial original a partir do hash. Conta/código externo exigem outro fluxo.
- Armazenamento bloqueado gera aviso e não impede jogar na aba atual. Preserve a
  aba; não confunda salvar o banco com guardar sua credencial no navegador.

Contrato HTTP/WS, regras, save e formato do banco não mudam. A recuperação valida
`GET /rooms/{code}` com Bearer antes de adotar o acesso lembrado; o snapshot e
as ações continuam filtrados pelo servidor.

## Verificações

`tests/web_online_access_ui.cjs`: consentimento/desmarcado, fechamento e retomada,
identidade fixa, recusa remota sem apagar acesso, registros inválidos, convite de
outra sala, comando sem resposta com mesmo ID, substituição confirmada, limpeza,
sincronização entre abas e falha de armazenamento. API também verifica os novos
controles no HTML, preservando o setup hotseat separado.

São testes automáticos de cliente e API. Playtest em aparelhos físicos e perda
real de conexão continuam pendentes.
