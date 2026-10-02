# Persistência online v1

O servidor atual grava automaticamente salas e operações aceitas em
`saves/online/rooms.sqlite3`. SQLite é nativo do Python; não há nova dependência.
O diretório é privado do servidor, não servido pela API e ignorado pelo Git.

## O que é preservado

- Participantes, escolhas/pronto e hashes das credenciais — nunca o token original.
- Revisão, GameState e RNG pelos serializadores existentes do motor.
- Eventos públicos/privados, log, estatísticas, decisões pendentes e resultado final.
- Ações aceitas, identificadores, resultados e fingerprints para deduplicação
  inclusive quando a resposta se perde e o comando é reenviado após reiniciar.

Gravação e revisão fazem parte da mesma transação SQLite (`synchronous=FULL`).
O servidor confirma e notifica somente após gravar. Falha de gravação devolve 503
sem mudar o estado em memória, RNG, revisão ou histórico. Operações rejeitadas
não são gravadas. Alterações do lobby também são transacionais.

Um bloqueio de arquivo permite só um servidor por banco e é liberado pelo sistema
ao encerrar ou cair o processo. Portas diferentes não autorizam compartilhar o
mesmo banco entre instâncias. Para testes paralelos, use outro `--storage`.

## Reiniciar e retomar

1. Mantenha as abas abertas: a identidade continua em `sessionStorage`.
2. Reinicie o servidor atual usando o mesmo banco/porta.
3. Os clientes reconectam; recarregar a aba também recupera o jogador e sua visão.

Não existe derrota, expiração de sala ou liberação de vaga por desconexão.
Se falta o jogador que deve decidir, a partida espera por ele. Pausa explícita,
abandono e recuperação de credencial após fechar a aba ainda exigem implementação.
O servidor não consegue recuperar um token original a partir do hash.

**Primeira atualização:** salas abertas por versões anteriores em memória não
são migradas automaticamente. Termine essas partidas antes de reiniciar.
O lobby só confirma persistência quando a instância servidora realmente a usa.

## Configuração e backup

`JOGAR_ONLINE.cmd` usa o banco padrão. Para outro ambiente:

```powershell
python -m jessica.web.online_server --port 8877 --storage "C:\caminho\privado\rooms.sqlite3"
```

Backups automáticos em `saves/online/backups/` (ou `backups/` ao lado do banco
configurado): ao iniciar, a cada hora se houver operações gravadas e ao encerrar
normalmente com Ctrl+C se houver mudanças. Usa a API de backup do SQLite, não
copia um arquivo enquanto ele está sendo alterado. Cada cópia é verificada,
sincronizada em disco e publicada por renomeação atômica, com nome UTC único.
O servidor aguarda requisições HTTP em andamento no encerramento normal;
conexões paradas têm timeout de 15 segundos.

Falha de backup imprime **AVISO** no console e é tentada novamente no próximo
intervalo; não desfaz ações já confirmadas nem apaga o banco/cópias anteriores.
Queda forçada não executa o backup final: a cópia pode ter até uma hora de atraso
em operação normal. O banco principal continua gravando cada operação aceita.
Sem mudanças, não gera cópias repetidas. Não há remoção automática: monitore
espaço e retenção. Migrações de schema continuam pendentes.

Para uma cópia manual extra, pare o servidor e copie `rooms.sqlite3` para um local
privado. Não precisa copiar `.lock`. Backups contêm informações secretas de
partidas; não publique, envie ao Git ou ofereça aos jogadores. Essas rotas não são
servidas pela API. Uma cópia no mesmo disco **não protege contra perda do disco**;
guarde cópias externas privadas antes de hospedagem real.

### Restaurar sem destruir o original

1. Pare o servidor. Preserve o banco original e as cópias existentes.
2. Copie o backup escolhido para **um novo arquivo privado**, por exemplo
   `saves/online/rooms-restaurado.sqlite3`.
3. Inicie com `python -m jessica.web.online_server --storage saves/online/rooms-restaurado.sqlite3`
   e o mesmo endereço/porta usados pelos clientes (inclua `--host IP_PRIVADO` se necessário).
4. Mantenha as abas/credenciais originais. Verifique sala, jogadores e revisão.

O arquivo restaurado precisa ser compatível; a validação existente recusa dados
incompatíveis sem descartá-los. Restaurar volta ao instante da cópia: ações
posteriores ao backup não são recuperadas. Não continue uma partida em dois bancos.

Versões independentes: schema SQLite 1, registro de sala 1 e versões existentes
de save/ação/evento. Banco incompatível, danificado ou com sala inválida impede
o início; nenhum registro é descartado nem substituído silenciosamente.

## Validação

`tests/test_online_persistence.py`: dez testes, incluindo recuperação de lobby,
estado/RNG e visões; equivalência durante novos turnos; repetição concorrente e
após reiniciar; falha de disco simulada; isolamento de dono; formato inválido;
Armadura pendente; resultado final; queda forçada e reinício do processo real.

`tests/test_online_backups.py`: oito testes de equivalência de estado/RNG/visões
e deduplicação após restaurar uma cópia, agenda horária/final sem duplicação,
falha/repetição sem desfazer ações, publicação atômica e preservação de cópias,
concorrência, revisão rejeitada/rotas privadas, criação e encerramento normal
no processo real, incluindo recuperação da cópia final com a credencial original.

Limites: uma instância por banco, snapshots completos a cada operação aceita,
sem expiração/limpeza automática. Otimização de volume, backups externos/retenção,
contas e hospedagem pública ficam para etapas posteriores.
