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

Para backup simples, pare o servidor e copie `rooms.sqlite3` para um local privado.
Não precisa copiar `.lock`. Restaure apenas com o servidor parado. O banco contém
informações secretas de partidas; não publique, envie ao Git ou ofereça aos jogadores.
Backup automático e migrações ainda não estão implementados.

Versões independentes: schema SQLite 1, registro de sala 1 e versões existentes
de save/ação/evento. Banco incompatível, danificado ou com sala inválida impede
o início; nenhum registro é descartado nem substituído silenciosamente.

## Validação

`tests/test_online_persistence.py`: dez testes, incluindo recuperação de lobby,
estado/RNG e visões; equivalência durante novos turnos; repetição concorrente e
após reiniciar; falha de disco simulada; isolamento de dono; formato inválido;
Armadura pendente; resultado final; queda forçada e reinício do processo real.

Limites: uma instância por banco, snapshots completos a cada operação aceita,
sem expiração/limpeza automática. Otimização de volume, backups automáticos,
contas e hospedagem pública ficam para etapas posteriores.
