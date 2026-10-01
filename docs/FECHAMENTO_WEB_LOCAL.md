# Web local: candidata a playtest — 01/10/2026

Base de conteúdo: `c652408`, mais os ajustes registrados junto deste guia,
branch `codex/web-vertical`. Não é certificação de
todas as combinações nem versão comercial. Escopo: quatro jogadores no mesmo
dispositivo, servidor Python local, sem bots ou multiplayer remoto.

## O que já pode ser testado

A auditoria de conteúdo mapeou todos os fluxos selecionáveis do terminal para
ações/consultas web. Não há ação mecânica faltante identificada nem divergência
funcional conhecida em aberto no registro de paridade.
450 testes aprovados; comparação independente de 125 ações e dez noites;
partidas completas dos 12 povos, Bases Dragões e progressão de Rogue; QA real
das principais escolhas complexas, desktop e largura móvel.
Isso é evidência do recorte testado, não prova exaustiva.

## Abrir

1. Na pasta da versão web, abra `JOGAR_WEB.cmd`.
2. A primeira execução prepara o ambiente Python/Rich e pode precisar de internet.
3. Mantenha a janela aberta e acesse `http://127.0.0.1:8765`.
4. Encerre com Ctrl+C. O servidor não é publicado na internet.

`JOGAR.cmd` sem argumento continua abrindo o terminal. Alternativa, com ambiente
já preparado: `.venv\Scripts\python.exe -m jessica.web.server`.
O atalho reutiliza o instalador existente; não altera saves ou regras.
Atalho verificado estruturalmente por teste; o primeiro duplo clique e a instalação
de dependências ainda precisam ser confirmados no Windows do usuário.

## Para reduzir retrabalho e tokens

Não é necessário reenviar regras ou conversas. Envie bugs em lote, de preferência
com o JSON de **Exportar partida** antes da ação que falha:

```text
[BUG] Web ou terminal; commit/versão; seed; turno e fase
Povo/herói e jogador:
Ação ou sequência para reproduzir:
Esperado:
Ocorrido / mensagem de erro:
Save anexado:
```

Não envie somente uma seed quando a partida já tiver decisões: ela não reconstrói
o caminho percorrido. Relate também [OK] para o fluxo corrigido; não é necessário
testar cada combinação possível nem ler os relatórios técnicos.

## Fechamento com escopo limitado

1. Concluído: partidas completas com adversários atacando e retaliações, seeds
   913/914, registradas em `VALIDACAO_PROGRESSAO_ROGUE.md`.
2. Reforço de cobertura: acrescentar cruzamentos de janelas somente quando
   houver risco concreto ou bug; não bloquear playtest esperando exaustividade.
3. Conferir o cliente físico por toque e registrar os bugs do playtest humano.
4. Corrigir divergências reproduzíveis; repetir testes afetados e a suíte completa
   antes de publicar a candidata. Não reauditar todo o conteúdo a cada patch.

Usar `PENDENCIAS_PARIDADE.md` para divergências e os relatórios de validação para
cobertura. Uma ausência de teste, sozinha, não significa funcionalidade ausente.
Novas regras, alterações visuais extensas e PWA instalada ficam em entregas
separadas. PWA não faz o Python rodar sozinho no celular: a instalação e o local
do motor precisam de validação própria. A web já pode receber playtest agora;
não precisa esperar cobertura exaustiva para começar.
