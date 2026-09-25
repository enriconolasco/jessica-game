# Cliente web vertical

Prova local da comunicação navegador → porta headless → motor → eventos → tela.

## Executar

Na raiz do projeto:

```powershell
python -m jessica.web.server
```

Abra `http://127.0.0.1:8765`. Não há dependências web externas.

## Corte atual

- cria e carrega partidas locais;
- entrega `PlayerView` e ações legais com rótulos;
- executa coleta, cidade, monumento, invocação, movimento, mercado de artefatos e fim da janela do jogador;
- atualiza a tela sem recarga e apresenta eventos recentes;
- salva manualmente e faz autosave após cada ação aceita;
- rejeita versões incompatíveis de save.
- renderiza as unidades num minimapa acessível de cinco casas com os ícones SVG v0.2;
- agrupa ações por tipo e confirma o encerramento da janela do jogador.
- compacta variantes de uma mesma ação em seletores adequados para celular;
- mostra a área privada do jogador ativo e descreve eventos estruturados em PT-BR.
- filtra eventos privados por jogador; cartas compradas não vazam para adversários.

Ao terminar as quatro janelas do Dia, a partida entra na Noite. Combate, feitiços e
o uso dos artefatos ainda permanecem no terminal nesta prova vertical.

Próximas etapas: [ROADMAP_WEB_LOCAL.md](ROADMAP_WEB_LOCAL.md).
