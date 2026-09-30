# Luide Vampa — locais sem inimigos (30/09/2026)

Correção baseada no pedido: com Luide vivo, os vampiros têm sua janela noturna
mesmo quando não há inimigos no local ocupado.

- A janela mantém a ordem por jogador/local; permite mover, lançar feitiço ou
  concluir sem atacar. Não permite ataques sem alvo nem altera custos ou recargas.
- Vale também para tropas sozinhas em um local, com Luide vivo em outro.
- Movimentos para locais futuros ou já processados continuam permitindo declarar
  no destino conforme a fila existente.
- Se Luide morrer em um combate de reentrada, a janela termina imediatamente:
  não oferece mais movimento nem feitiço noturno.
- Locais sem unidades vampiras continuam sendo pulados normalmente.

A condição de Luide vivo foi centralizada em `peoples.has_luide_bonus`.
Terminal: filtros de casa/jogador deixam de eliminar essa janela.
Web: a fila não exige alvos para abrir Luide; o aviso inclui a ordem da janela.
Também foi corrigida a apresentação do alvo Cidade no log web para usar o campo
existente `target_type`, sem alteração do contrato.

Validação automatizada:
- Regressão sem alvos reproduziu a falha antes do patch.
- Quatro testes da UI real do terminal: Luide sozinho, tropa sozinha com Luide
  distante, herói morto e morte durante reentrada.
- Web: feitiço e movimento sem inimigos, save/load determinístico, ausência de
  combate artificial e comparação com o terminal nos dois tipos de destino,
  com e sem inimigos na origem.
- Suítes completas: terminal 304 aprovados; web 408 aprovados; zero falhas.
- Cinco scripts Node, syntax check de app.js e diff check aprovados.
Não foi feito novo playtest manual no navegador neste patch.

Arquivos existentes de save não foram alterados. Reinicie o jogo/servidor para
carregar o código atualizado; janelas já puladas em uma Noite anterior não são
reabertas retroativamente.

