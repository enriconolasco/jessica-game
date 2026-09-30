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

Quatorze testes, com 37 cenários:

- ocupação inicial, chegada posterior, abandono completo e reentrada;
- ordem das quatro cidades para cada um dos quatro Currunas;
- morte por retaliação interrompendo ataques adicionais de Pé Descalço;
- morte de Vovó retirando o bônus do próximo aliado imediatamente;
- posição de Vovó e prioridade de Bater Primeiro;
- Noite pulada: unidade continua alvo e retalia, mas não declara ataque;
- Iúna atacando e retaliando, com oito seeds para cada caso;
- tropa controlada por Q♣ declarando pelo controlador contra o dono original;
- local ocupado sem alvos: sozinho, todos invisíveis ou todos espoliados.
- Luide: feitiço e movimento na mesma janela, seguido de ataque em local futuro
  ou já processado; executa a janela real do terminal com escolhas programadas.
- Luna retorna ou permanece depois de Mar de Chamas, antes dos ataques;
- Mandinga invoca um herói que participa das declarações na mesma Noite;
- Ainai reage à morte de uma fada e reabre o Centro já processado;
- momentos das ofertas de Ainai, inclusive com casas vazias e a janela final.

Corrigido um erro de apresentação: locais ocupados sem alvos anunciavam
“combate iniciado”. Agora o evento tem ordem vazia e o histórico informa
“não havia combates a declarar”. Fila, dano e regras não foram alterados.

Corrigida também a orquestração de Ainai: não se oferece uma janela após local
sem ocupantes; há uma última oferta antes do Relógio/fim da Noite, como no
terminal. `occupied` e `final_ainai_queued` são metadados booleanos opcionais da
fila persistida. Saves anteriores continuam aceitos; filas antigas em andamento
mantêm suas entradas e recebem a etapa final quando terminam.

## Limites e próxima integração

Não certifica toda combinação nem substitui playtest. O comparador aciona as
janelas reais de Luide, Ainai, Luna e Mandinga com decisões programadas. Ainda
não cruza todas elas com pagamentos de Armadura e pactos simultâneos.

Próximo lote: cruzar essas interrupções com mortes/eliminação e conferir a
transição para a manhã seguinte. Persistência de cada janela já tem testes;
a comparação integrada desses cruzamentos permanece pendente.

O lote seguinte já cobre transição diurna e reações encadeadas:
ver `VALIDACAO_CICLO.md`.

Verificação do marco anterior: 395 testes aprovados. Resultado ampliado e partidas
completas estão em `VALIDACAO_PARTIDAS_COMPLETAS.md`. Sem novo playtest manual
de navegador neste lote.
