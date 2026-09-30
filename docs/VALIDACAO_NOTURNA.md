# Comparação noturna terminal/web — 2026-09-30

Referência executada: `jessica.main.run_night_phase` deste repositório, com o
motor sincronizado do terminal. Comparador: `tests/test_night_terminal_parity.py`.
Não é uma simulação que reutiliza a fila web como referência.

## Método

O terminal recebe escolhas programadas, sem prompts nem desenho de telas.
A web recebe as mesmas decisões pela porta `legal_actions` / `apply_action`.
Comparam-se sequência dos ataques, estado mecânico completo, logs e RNG ao fim
das declarações. Somente os três campos exclusivos da sessão web são excluídos
da comparação final: `active_player_id`, `web_night`, `web_reaction`.

Cada escolha web é repetida em um estado serializado/restaurado. Resultado,
eventos e estado completo devem coincidir. Consultas de ações e PlayerView dos
quatro jogadores não podem alterar o estado nem consumir RNG.

## Cobertura deste lote

Nove testes, com 30 cenários:

- ocupação inicial, chegada posterior, abandono completo e reentrada;
- ordem das quatro cidades para cada um dos quatro Currunas;
- morte por retaliação interrompendo ataques adicionais de Pé Descalço;
- morte de Vovó retirando o bônus do próximo aliado imediatamente;
- posição de Vovó e prioridade de Bater Primeiro;
- Noite pulada: unidade continua alvo e retalia, mas não declara ataque;
- Iúna atacando e retaliando, com oito seeds para cada caso;
- tropa controlada por Q♣ declarando pelo controlador contra o dono original;
- local ocupado sem alvos: sozinho, todos invisíveis ou todos espoliados.

Corrigido um erro de apresentação: locais ocupados sem alvos anunciavam
“combate iniciado”. Agora o evento tem ordem vazia e o histórico informa
“não havia combates a declarar”. Fila, dano e regras não foram alterados.

## Limites e próxima integração

Não certifica toda combinação nem substitui playtest. Este comparador não
aciona as janelas de Ainai, Luna, Besouro ou Luide; seus testes existentes
continuam separados. Não inclui fim da Noite/próxima manhã, pagamentos de
Armadura, pactos ou escolhas privadas no meio destes cenários.

Próximo lote: cruzar essas interrupções com mortes/eliminação e conferir a
transição para a manhã seguinte. Persistência de cada janela já tem testes;
a comparação integrada desses cruzamentos permanece pendente.

Verificação deste marco: suíte completa com 384 aprovações e zero falhas;
quatro testes de interface Node, sintaxe de `app.js` e `git diff --check`
aprovados. Nenhum novo playtest manual de navegador foi feito neste lote.
