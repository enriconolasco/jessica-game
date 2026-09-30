# Saves e recuperação local — 30/09/2026

## Usar no navegador

- Tela inicial: **Mostrar saves → Recuperações anteriores**, selecionar e **Carregar**.
  Cada partida mantém seu autosave atual e os cinco anteriores.
- **Salvar cópia** continua independente: cópias manuais e arquivos de outras
  partidas nunca são rotacionados. Ao ultrapassar cinco recuperações, somente a
  recuperação automática mais antiga daquela partida é removida.
- **Importar save web ou terminal (.json)** aceita exportações web e saves brutos
  compatíveis do terminal. Limite: 10 MB. Mensagens explicam o que foi retomado.
- Carregar recuperação cria uma nova partida local. Não sobrescreve o ponto escolhido.
- Erro de disco não desfaz uma ação aceita: o servidor informa que a partida
  continua em memória e recomenda exportar antes de fechá-lo. Uma cópia manual
  que falhou não recebe confirmação falsa; a API responde 507.

## Compatibilidade do terminal

Referência: terminal `5b47dde`. Seu serializador foi comparado com o da web:
diferenças são os campos de orquestração `active_player_id`, `web_night` e
`web_reaction`, não os dados mecânicos dos jogadores.

O Dia precisa ter exatamente um jogador vivo, não pulado, com manhã já realizada
e jogada ainda não encerrada. Esse jogador é identificado pelos flags persistidos;
não é adivinhado pela ordem ou pelo conteúdo do log. Um `active_player_id` explícito
contraditório também é rejeitado. Estado, recursos, cartas, unidades e RNG são
preservados; não se executa manhã, sorteio, feitiço ou mudança de fase na importação.

Saves ambíguos, versões futuras e uma Noite do terminal sem fila serializada são
rejeitados antes de criar uma partida ou arquivos. Reiniciar as declarações poderia
repetir ataques, portanto não é utilizado como conversão. Partidas já encerradas
podem ser consultadas. Saves web com fila/reação preservam seu fluxo existente.

O log bruto antigo fica no save completo, mas não é publicado: pode conter cartas
privadas. O histórico estruturado começa com o evento público `match_imported`.
Timeline e estatísticas já presentes continuam nos relatórios. Não existe um
checkpoint inventado de início do Dia importado; Refazer/Mola só passam a usar
jogadas cujo começo foi realmente registrado pela web.

## Contratos e armazenamento

Formato continua `save-v0.1`, com metadados opcionais:

- `checkpoint_skip: {turn, player_id}`: impede um falso checkpoint do Dia importado;
- `kind: recovery`, `source_match_id`, `recovery_generation`: identificam recuperações
  automáticas e sua ordem, sem depender da resolução do relógio do sistema de arquivos;
- resposta de importação: `warnings`; respostas de operações aceitas: `save_warning`
  quando a persistência falhou. Não alteram regras nem o resultado da ação.

Arquivos permanecem em `saves/web/`. Escrita valida o payload, usa arquivo temporário
e substituição atômica. Antes de atualizar o autosave, o estado anterior é arquivado.
Identificadores novos são checados contra arquivos existentes para evitar sobrescrita.
Rotação é exclusiva de arquivos `recovery` com a origem correspondente; saves manuais,
backups históricos e `fixes/` não são apagados. Recuperações antigas já descartadas
não podem ser recuperadas pelo cliente; as cinco mais recentes permanecem disponíveis.

## Evidência e próximos passos

`tests/test_web_save_recovery.py`: dez testes, incluindo importação dos 12 povos,
mesma próxima ação/estado/RNG, privacidade, rejeição sem efeitos, recuperação de
RNG/checkpoints, isolamento por partida mesmo com timestamps iguais, limites de
rotação, colisão de IDs e falha de disco.
`node tests/web_saves_ui.cjs`: filtros, seleção, importação e avisos no DOM simulado.

Ainda pendentes: comparação integrada local a local da Noite, cruzamentos complexos
de reações e partidas de paridade; migrações de formatos futuros, PWA e bots.
Isso não certifica a paridade integral do jogo nem converte saves noturnos ambíguos.
