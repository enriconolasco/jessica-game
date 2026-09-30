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
Tropas aparecem em 32×32; heróis reutilizam o mesmo SVG em 64×64. Os PNGs
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
- vida numérica sempre visível e fallback `?` com descrição textual para povo desconhecido.
- seleção por clique/foco persistente; passar o mouse não desfaz uma seleção;
- dono, povo e vida da Base no título de cada cidade; Curruna destacado textualmente;
- título da lista anuncia a troca de casa para leitores de tela.

## Verificação reproduzível

`python tools/preview_web_map.py` abre um servidor em `http://127.0.0.1:8766`.
A prévia usa somente uma PlayerView pública sintética: 36 unidades, 28 no centro,
heróis/tropas nas quatro cidades e um povo desconhecido para testar o fallback.
Não cria partidas nem altera saves. Verificar 320, 390, 900 e 1280 px; orientação,
contagens, seleção por teclado/toque, rolagem e vida legível.

Os ícones permanecem em estágio `concept` conforme `assets/manifest.json`.
