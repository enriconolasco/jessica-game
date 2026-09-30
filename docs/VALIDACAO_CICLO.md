# Ciclo da partida e reações — 2026-09-30

Comparador: `tests/test_web_cycle_parity.py`. Usa as funções originais de turno,
combate e resolução de escolhas como referência; não reimplementa seus efeitos.

## Correção funcional

A abertura diurna web selecionava o Curruna mesmo quando seu Dia estava pulado.
Ele recebia ações indevidas e não conseguia encerrar o Dia normalmente. Agora
`core/day_flow.open_day` consulta `turn.day_order` e inicia o primeiro jogador
elegível. O Curruna continua o mesmo; só o jogador ativo muda.

Apostas precedem a manhã mesmo se o gnomo tiver o Dia pulado. Após a confirmação,
o primeiro Dia elegível é aberto. Se todos os Dias forem pulados, o motor entra
na Noite. Ação normal de jogador com Dia pulado também é rejeitada em saves com
jogador ativo desatualizado. Nenhuma regra de dano, custo ou passiva foi alterada.

## Evidência

Doze testes cobrem:

- um, dois, três ou quatro Dias pulados na transição de turno;
- apostas do gnomo pulado antes da primeira manhã elegível;
- rejeição atômica de ação de jogador pulado;
- próxima manhã, juros e RNG para cada um dos 12 povos;
- devolução de unidade controlada, expiração de efeitos e remoção de espectro;
- morte adiada por Atim e ganho de Magia dos Demônios;
- Armadura seguida de morte de Luide, encerrando seu acesso noturno;
- vitória confirmada após pagamento da Armadura na retaliação de uma Cidade;
- Armadura → morte → escolha de Q♦ → pacto de Belial, aceito ou recusado,
  seguido da próxima manhã;
- API HTTP: troca do jogador ativo, ação inválida, cópia manual e load.
- Sonho Lúcido/Luna: invocar Ainai, aplicar buff nela, controlar uma tropa,
  declarar combates e devolver o controle na manhã seguinte;
- validar os metadados da janela final de Ainai e continuar saves antigos.

Cada decisão aceita é repetida em estado restaurado. Eventos, estado e RNG devem
coincidir; o resultado também atravessa o validador real de saves. Consultas dos
quatro jogadores não podem alterar o estado. Testes HTTP usam pasta temporária.

## Ainda não certificado

Todos os conteúdos em partidas cruzadas; Ainai/Luna/Mandinga intercalados com
Armadura/pactos; Sonho Lúcido múltiplo gerando interrupções; usabilidade manual
das escolhas complexas no navegador e celular. Partidas completas de ações
gerais já têm comparação: `VALIDACAO_PARTIDAS_COMPLETAS.md`.

PWA, bots e multiplayer não são necessários para equivalência mecânica com o
terminal passa-e-joga. Este lote não declara paridade total.

Verificação: 395 testes Python aprovados, zero falhas; os quatro scripts Node
de interface, sintaxe JavaScript e `git diff --check` aprovados. Sem novo playtest
manual de navegador neste lote.
