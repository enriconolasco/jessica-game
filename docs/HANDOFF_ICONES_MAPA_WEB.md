# Handoff — ícones de povos no mapa web

Status: integrado no cliente web  
Versão visual: v0.2

## Fonte e contrato

O mapa usa exclusivamente dados públicos da `PlayerView`:

- `view.players[].id`, `name` e `people`;
- `view.board.units[].owner_id`, `kind`, `house`, `life`, `life_max`;
- identificador, `hero_id`/`archetype`, modificadores e `statuses` públicos da unidade.

O povo é resolvido apenas por `unit.owner_id → view.players[].people`.

## Ativos vigentes

Use `assets/visual-direction-v0.2/icons/people-<povo>-32.svg` para os 12 povos.
Tropas aparecem em 32×32. Heróis usam retratos individuais em 64×64,
resolvidos exclusivamente por `unit.hero_id` no índice aprovado
`assets/visual-direction-v0.2/hero-portraits/index.json` (43 retratos).
O controlador atual determina o agrupamento e o rótulo de povo, não o retrato.
Os emblemas de `hero-icons/` foram rejeitados e não devem ser integrados. Os PNGs
16×16 de `visual-direction-v0.1` estão descontinuados e não devem ser integrados.

O fundo estrutural continua sendo
`assets/visual-direction-v0.1/map/minimap-template-cross-v0.1.svg`, sem cenário.

## Implementação

- cinco casas fixas, conforme `show_map` do terminal: centro, norte/cidade 3,
  leste/cidade 2, sul/cidade 1 e oeste/cidade 4;
- ordenação estável por jogador, heróis antes de tropas e identificador;
- geometria 3:2 e coordenadas percentuais do SVG, centralizadas em `map.css`;
  o fundo não usa `cover`, e nenhuma casa muda de posição nos breakpoints;
- ícones agrupados por jogador dentro de cada casa em todas as larguras, com rolagem;
  em telas estreitas, o mapa de largura mínima 1100 px rola horizontalmente;
- navegação direta para as cinco casas e lista ampliada abaixo, preservando os tamanhos
  32×32/64×64 e acesso individual a todas as unidades, sem substituí-las por contagens;
- foco, mouse ou toque abrem os mesmos detalhes públicos;
- vida numérica sempre visível; imagem/ID desconhecido ou indisponível tem fallback
  textual com nome do herói ou povo, sem substituir retratos por emblemas;
- índice carregado uma vez antes da seleção de partida; falha do índice não bloqueia
  o jogo e preserva inspeção, vida e fallback textual;
- seleção por clique/foco persistente; passar o mouse não desfaz uma seleção;
- dono, povo e vida da Base no título de cada cidade; Curruna destacado textualmente;
- título da lista anuncia a troca de casa para leitores de tela.

## Verificação reproduzível

`python tools/preview_web_map.py` abre um servidor em `http://127.0.0.1:8766`.
A prévia usa somente uma PlayerView pública sintética: 36 unidades, 28 no centro,
heróis/tropas nas quatro cidades e um povo desconhecido para testar o fallback.
Não cria partidas nem altera saves. Verificar 320, 390, 900 e 1280 px; orientação,
contagens, seleção por teclado/toque, rolagem e vida legível.

Os ícones de povos permanecem em estágio `concept`. Os retratos estão em
`intermediate`, aprovados para integração em 2026-10-01, conforme o manifesto.

Integração validada em 2026-10-01: 43 IDs do catálogo e SVGs servidos por HTTP;
testes de 64×64/32×32, mudança de controlador, índice/arquivo indisponível e ID
desconhecido. Prévia inspecionada em 1280 e 360 px, com 36 unidades e seleção
por clique/teclado. A largura de celular foi emulada; toque em aparelho real
permanece para playtest. Contratos e regras do motor não foram alterados.
