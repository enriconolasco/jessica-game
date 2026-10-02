# Atualização compartilhada — 02/10/2026

## Fonte única

`main` é a versão compartilhada e validada do projeto. Terminal e web local
distribuem o mesmo `jessica/core`, catálogo e serialização; não recebem patches
de mecânicas separados. O terminal é a referência comportamental, não uma cópia
de regras a duplicar. Há adaptadores e escolhas próprios de cada interface;
mudanças neles continuam exigindo testes de paridade.

As duas pastas locais são worktrees do **mesmo repositório Git**, não repositórios
independentes. `codex/terminal-playtest-round2` e `codex/web-vertical` ficam como
referências históricas/de trabalho; novas distribuições usam `main`.
Não criar branches permanentes por plataforma. A futura branch online é de
desenvolvimento: sua integração não cria outro motor nem obriga a reescrever o
cliente web local.

## Cada patch

1. Partir da `main` atual; alterar regras no core e apresentação no adaptador correto.
2. Adicionar regressão do bug e executar os testes afetados.
3. Antes de integrar/publicar: `python -B tests/run_all.py`, os cinco
   `node tests/web_*_ui.cjs` e `git diff --check`.
4. Para regras ou fluxo, executar também os testes diferenciais terminal/headless.
   Se houver uma instalação de referência congelada, usar
   `python -B tests/compare_terminal_reference.py --reference CAMINHO`.
   Nunca comparar uma pasta consigo mesma. Cobertura não prova todas as interações.
5. Integrar o commit validado à `main` sem force-push; distribuir o mesmo commit
   às instalações. Não aplicar patches manualmente nos dois diretórios.

Mudança de save, ações ou eventos exige revisão explícita de versões e migração.
Não prometer compatibilidade de saves antigos sem teste. Partidas em execução
continuam com o código carregado: salvar e fechar o jogo/servidor antes de atualizar.

## Atualizar para jogar

- Cópia com Git: abrir `ATUALIZAR.cmd`. Aceita apenas avanço fast-forward da
  `origin/main` oficial; recusa alterações versionadas e commits divergentes.
- Arquivos não rastreados, saves, ambientes e backups não são apagados. Um arquivo
  não rastreado que colida com a atualização faz o Git interromper a operação.
- Cópia ZIP sem Git: baixar a `main` em uma **nova pasta**, manter a anterior e
  importar/carregar somente saves compatíveis. O ZIP não vira clone automaticamente.
- Abrir `JOGAR.cmd` para terminal ou `JOGAR_WEB.cmd` para web local.
- Conferir a versão por `git rev-parse --short HEAD` antes de reportar bugs.

## Referência recuperável

Antes da consolidação: terminal `2cbc36c`, web `f9d1897`.
O histórico das duas branches é preservado por merge, sem mudar o código mecânico
da web já validada. A tag `web-local-pre-online-2026-10-02` identifica a referência
consolidada anterior ao online. Para inspecioná-la, usar outra pasta/worktree;
não fazer reset destrutivo na instalação com saves ou alterações locais.

## Validação da consolidação

Antes de atualizar a instalação terminal: 125 ações diurnas e dez noites mistas
comparadas contra `2cbc36c`, com estado, logs e RNG equivalentes. Os dois conflitos
de merge eram refatorações já validadas: Sonho Lúcido e seletor de alvos no core.
Nenhum parâmetro de balanceamento foi alterado.

Suíte consolidada: **454 testes Python aprovados, zero falhas**, mais cinco
testes de interface Node. O atualizador foi executado em clones temporários:
avanço limpo/idempotente, save local preservado, alteração local e histórico
divergente recusados. As duas instalações recebem exatamente o mesmo commit.
