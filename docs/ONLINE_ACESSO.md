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
  abas/aparelhos**. Para invalidar a credencial antiga, use a troca descrita abaixo.
  Expiração automática e recuperação sem acesso válido continuam pendentes.
- Se não marcou a opção antes de fechar, apagou dados do navegador ou perdeu o
  aparelho, não há recuperação por nome/código de sala. O servidor não recupera
  a credencial original a partir do hash. Conta/código externo exigem outro fluxo.
- Armazenamento bloqueado gera aviso e não impede jogar na aba atual. Preserve a
  aba; não confunda salvar o banco com guardar sua credencial no navegador.

Regras, save e formato do banco não mudam. A recuperação valida
`GET /rooms/{code}` com Bearer antes de adotar o acesso lembrado; o snapshot e
as ações continuam filtrados pelo servidor.

## Revogar acessos antigos sem perder o jogador

Na sua sala, use **Revogar outros acessos ao meu jogador** e confirme. Não libera
vaga, não muda povo/herói, turno, RNG, estado ou histórico de ações. Funciona no
lobby e durante a partida, independentemente da vez do jogador. Não autoriza o
anfitrião a trocar a credencial de outra pessoa.

O navegador gera uma nova credencial aleatória de 256 bits e guarda a troca
pendente antes de enviar `POST /rooms/{code}/credential`, com `{credential}` e
Bearer antigo. O servidor substitui **somente o hash** do participante autenticado,
em transação; aumenta a revisão de sala, não o turno. Credencial inválida,
parâmetros extras ou colisão com outro participante são recusados. Repetir com
Bearer novo e a mesma credencial não produz outra revisão.

HTTP passa a recusar o acesso antigo e os WebSockets antigos são fechados com
código 1008 ao receber a notificação da troca. Outros jogadores permanecem
conectados. Esta aba adota a credencial nova, atualiza sua cópia lembrada se for
do mesmo acesso e reconecta sem mudar de jogador. Convite continua sem token.

Se a resposta se perde, verifica a nova credencial no servidor. Quando não dá
para confirmar, mantém a troca pendente e oferece **Confirmar troca de acesso
pendente**; não gere outra credencial nem limpe os dados nessa situação. Uma
retomada com troca já guardada tenta concluí-la usando a mesma candidata.
Armazenamento bloqueado impede iniciar a troca. Resolva comandos de gameplay
pendentes antes de iniciá-la; novas ações ficam bloqueadas enquanto não confirmar.

**Limites importantes:** revogar não remove informações já recebidas. Abas do
mesmo perfil podem ler a nova cópia lembrada; não isola pessoas que compartilham
o navegador. Quem possui um token válido tem a mesma autoridade do participante,
inclusive para trocá-lo; contas/fator adicional não estão implementados.
Se todos os tokens válidos forem perdidos, nome/código de sala não recupera acesso.

**Backups:** prefira cópia posterior à troca. Restaurar uma cópia antiga reverte
também credenciais: acessos revogados podem voltar e os novos parar de funcionar.
Não use restauração como mecanismo de recuperação de identidade; sem token
correspondente, ainda falta um fluxo administrativo seguro. Não publique o serviço
na internet sem concluir a preparação/validação de segurança.

## Verificações

`tests/web_online_access_ui.cjs`: consentimento/desmarcado, fechamento e retomada,
identidade fixa, recusa remota sem apagar acesso, registros inválidos, convite de
outra sala, comando sem resposta com mesmo ID, substituição confirmada, limpeza,
sincronização entre abas e falha de armazenamento. API também verifica os novos
controles no HTML, preservando o setup hotseat separado.
O teste também cobre cancelamento/troca, gravação prévia, resposta perdida,
retomada com troca pendente, repetição após falha de disco e reconexão WS.

`tests/test_online_credentials.py`: seis testes com HTTP/WS e SQLite reais:
identidade/estado/deduplicação preservados, autenticação/parâmetros/colisão,
concorrência, falha de gravação, restart/backup sem tokens em claro e fechamento
do canal antigo com outras sessões preservadas.

São testes automáticos de cliente e API. Playtest em aparelhos físicos e perda
real de conexão continuam pendentes.
