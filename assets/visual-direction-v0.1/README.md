# Kit visual modular v0.1

Este pacote é uma rodada de validação, não arte final.

- `font/`: fonte display funcional em TTF/WOFF2, espécime e licença da base tipográfica.
- `sprites/*-master.png`: concept masters separados, usados para aprovar identidade e silhueta.
- `sprites/*-48.png` e `*-32.png`: testes automáticos de escala real.
- `sprites/*-preview.png`: testes ampliados por vizinho mais próximo para inspeção dos pixels.
- `icons/people-*-16.png`: ícones nativos 16×16 desenhados diretamente na grade.
- `icons/*-preview.png`: ampliações por vizinho mais próximo; não são arquivos de produção.

Os testes reduzidos demonstram que os masters atuais ainda têm informação demais para 48×48. Após aprovação das silhuetas, a próxima etapa correta é redesenho/limpeza manual na grade, não nova redução automática.
