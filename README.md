# Jéssica

Um motor Python, dois clientes locais: terminal e navegador (quatro jogadores
no mesmo aparelho). `main` contém a versão compartilhada, validada para playtest;
o multiplayer remoto ainda está em desenvolvimento separado.

- Terminal: abrir `JOGAR.cmd`.
- Web local: abrir `JOGAR_WEB.cmd`, manter o servidor aberto e acessar
  <http://127.0.0.1:8765>.
- Atualização de clone Git: fechar o jogo/servidor e abrir `ATUALIZAR.cmd`.
- Cópia ZIP: baixar a `main` em outra pasta e preservar a instalação/saves antigos.

Requer Python e Rich; os atalhos locais preparam o ambiente na primeira execução.
Sem Git, o atualizador informa a alternativa ZIP, sem modificar a pasta.

Fluxo de desenvolvimento: [docs/FLUXO_ATUALIZACAO.md](docs/FLUXO_ATUALIZACAO.md).
Escopo e playtest web: [docs/FECHAMENTO_WEB_LOCAL.md](docs/FECHAMENTO_WEB_LOCAL.md).
