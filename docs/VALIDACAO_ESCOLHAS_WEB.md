# Escolhas complexas no navegador — 30/09/2026

Base: `8bfd0fa`, branch `codex/web-vertical`. Este patch altera apresentação e
testes; não modifica regras, contratos, motor ou saves do usuário.

## Correções

- Sacrifício de Demônio usa o diálogo HTML do cliente, não `window.confirm`.
  As cartas mostram nomes do catálogo e zona. Cancelar mantém a seleção.
- Após passar o dispositivo, a próxima escolha recebe foco e fica à vista.
- Em até 820 px, a barra de comandos acompanha a rolagem. A barra fixa anterior
  cobria os controles em 360 px e impedia cliques.
- Encerrar Noite fica expandido. Defesa e relatos de combate usam nomes públicos
  conhecidos; unidades mortas podem ser identificadas pelos eventos públicos.
  Nomes não são extraídos de mãos nem de projeções privadas de eventos.

## Validação real

Servidor separado em `127.0.0.1:8766`, com saves descartáveis em diretório
temporário. Navegador in-app, desktop e viewport 360×800:

- Sacrifício: ausência de seleção rejeitada; cartas da mão e do campo;
  Escape cancela sem consumo; confirmar remove o herói e troca as cartas.
- Luna: a prévia oferece Ainai recém-invocada como alvo do próximo artefato;
  limpar restaura as opções; sequência J♦, K♠ e Q♠ resolve invocação, efeito
  e controle imediatamente, com lançamento pelo teclado.
- Armadura: pagamento acima do limite rejeitado; defesa com 2 Ouro e retaliação
  com 0; passagem de jogador oculta a mão; clique funciona após remover a barra
  fixa. Resultado: atacante morto, defensor 2/4, Ouro 8→6.
- Foco na decisão, nomes legíveis, encerramento aberto e nenhuma rolagem
  horizontal da página em 360 px (a rolagem interna do minimapa é intencional).
- Nenhum erro no console observado nos cenários.

## Reproduzir sem tocar nos saves normais

Na raiz do projeto, com as dependências do jogo disponíveis:

```powershell
python -B tests/serve_ui_scenarios.py
```

Abra `http://127.0.0.1:8766`, escolha um dos três saves de teste e Carregar.
`--port` permite outra porta. Ctrl+C encerra o servidor e descarta somente os
dados temporários deste teste; não modifica `saves/web`.

Regressões: `python -B tests/run_all.py` (402 aprovados, zero falhas) e os cinco
scripts `tests/web_{actions,dialog,presentation,saves,events}_ui.cjs` (todos
aprovados). Syntax check de `app.js` e `git diff --check` aprovados.

Isso não certifica todas as combinações mecânicas. Toque em celular físico,
partidas longas pelo navegador e combinações restantes da matriz de paridade
continuam pendentes. A skill de computer-use orientou a verificação na interface
real; o navegador foi operado pelo controle de browser disponível.
