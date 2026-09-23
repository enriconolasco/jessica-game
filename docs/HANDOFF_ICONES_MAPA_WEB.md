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

- cinco casas fixas: centro, norte/cidade 1, leste/cidade 2, sul/cidade 3 e oeste/cidade 4;
- ordenação estável por jogador, heróis antes de tropas e identificador;
- quebra de linha e rolagem interna sem sobreposição;
- contagem explícita em cada casa;
- foco, mouse ou toque abrem os mesmos detalhes públicos;
- vida numérica sempre visível e fallback `?` com descrição textual para povo desconhecido.

Os ícones permanecem em estágio `concept` conforme `assets/manifest.json`.
