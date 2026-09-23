# Direção visual — Jéssica

Status: direção provisória em validação  
Versão: 0.4 — 2026-09-23

## Norte visual

- Fantasia clássica em pixel art, usando jogos de estratégia e RPGs legados como gramática visual, sem imitação direta.
- Legibilidade estratégica acima de ornamentação.
- Identidade brasileira presente em paisagens, materiais, cores e curvas orgânicas; evitar medieval europeu genérico e folclore literal.
- Referência de ambição para personagens: silhuetas laterais expressivas e poses fortes, com produção mais econômica que sprites altamente detalhados.

## Tipografia

- Título `JÉSSICA`: lettering próprio, caligráfico e pixelado, com `J` marcante, ritmo manuscrito e acento agudo inequívoco.
- Explorar híbridos entre caligrafia de fantasia clássica, serifas lapidares e construção em pixels.
- Evitar blackletter gótica, excesso de arabescos, bevel 3D e lettering que dependa de textura para ser lido.
- Logotipo final deve ser redesenhado manualmente; geração por IA serve apenas para composição e direção.
- Interface: fonte pixelada somente em títulos e rótulos curtos. Textos, números e tooltips usam fonte de tela altamente legível.

## Sprites de unidades

- Visão exclusivamente lateral; o mesmo sprite pode ser espelhado horizontalmente.
- Sem animação de caminhada: deslocamento entre as cinco casas será representado por transição de posição e efeito breve.
- Conjunto futuro mínimo por unidade: repouso, ataque e recebimento de golpe.
- Escala provisória: aproximadamente 32–48 px de altura lógica para tropas e até 56 px para heróis, sujeita a teste no mapa.
- Poucos pixels, clusters deliberados, paleta limitada e silhueta reconhecível antes dos detalhes internos.
- Heróis se distinguem por altura, contorno, base e detalhe focal; não apenas por maior resolução.
- Não produzir folhas de animação antes da aprovação do sprite-base lateral.

## Mapa e cinco casas

- A visão geral começa como um minimapa abstrato em cruz: uma casa central e quatro casas nas posições cardinais.
- O template inicial não contém cenário, construções, objetos, ícones, rótulos ou identidades de povo.
- O fundo pode usar geometria original inspirada em padrões africanos, com opacidade máxima de 4%, sem reproduzir símbolos sagrados ou identificáveis.
- As cinco casas devem permanecer vazias e oferecer áreas equivalentes para conteúdos futuros; a casa central pode receber destaque apenas por contraste de borda.
- Devem existir exatamente cinco grandes áreas espaciais, cada uma capaz de exibir mais de 20 unidades sem sobreposição.
- No zoom geral, unidades podem ser simplificadas para marcadores/silhuetas agrupadas; no zoom próximo, sprites e estados aparecem integralmente.
- Organização padrão: posicionamento automático por povo, em fileiras curvas ou grupos compactos, com espaçamento estável.
- Ordem sugerida do agrupamento: povo → heróis → tropas → identificador estável. A interface apenas organiza dados recebidos; não deduz regras.
- Arraste manual é uma opção posterior de organização puramente visual. Não altera casa, ordem, alcance ou qualquer estado mecânico.
- Quando a capacidade visual for excedida, reduzir moderadamente o espaçamento e usar agrupamento/contagem; nunca sobrepor sprites sem indicação explícita.

## Indicadores sobre unidades

### Ícones dos povos — proposta v0.2

- A linha anterior de retratos pixelados 16×16 está descontinuada e não deve ser integrada.
- Novo conjunto modular: um SVG por povo, em viewport 32×32, com formas simples, silhueta forte e poucos detalhes. Os vetores simulam a leitura de ícones de fantasia clássica em baixa resolução, sem exigir pixel art manual.
- Todos usam moldura escura e borda de cor distinta. A distinção principal é a forma e o atributo do rosto/símbolo; a cor é secundária.
- Humanos: mulher negra. Orcs: pele verde. Fadas: elfa loira, orelhas pontudas e olhos verdes.
- Estado atual: concept. Avaliar em tamanho real no mapa antes de promover a intermediário. Não substituir os arquivos antigos em telas sem aprovação desta proposta.

- Toda unidade exibe vida atual/máxima no formato `4/6`; barras isoladas não substituem os números.
- Preferência: cápsula numérica compacta abaixo ou ao lado do sprite, visível no zoom próximo.
- Modificadores ocupam de um a três slots junto à vida; estados adicionais aparecem em painel/tooltip acessível.
- Todo modificador combina ícone, forma e cor. Tooltip e texto acessível informam nome, origem e duração quando disponíveis na PlayerView/eventos.
- Seleção usa contorno forte e base geométrica; povo usa cor e forma de base, nunca somente cor.
- Invisibilidade, resistência e dano aumentado devem ter silhuetas distintas e rótulo textual no foco/seleção.

## Movimento, câmera e interação

- Zoom contínuo ou em níveis previsíveis, com enquadramento da casa selecionada.
- Mouse: roda/pinça equivalente e arraste do mapa. Toque: pinça e arraste. Teclado: controles equivalentes e foco navegável.
- Transição de unidade entre casas curta e funcional; sem simular caminhada.
- Respeitar `prefers-reduced-motion` e oferecer alternativa instantânea aos efeitos.

## Estratégia de produção

1. **Placeholder:** formas, bases, números e ícones provisórios usados para validar escala e densidade.
2. **Intermediário:** sprite lateral aprovado, paleta controlada e estados visuais testáveis; sem animação final.
3. **Arte final:** limpeza manual, consistência de pixels, ataque, recebimento de golpe, efeitos e exportação otimizada.

## Processo modular obrigatório

- Validar separadamente: fonte, silhueta de tropa, herói, retrato/ícone, terreno, arquitetura, mapa e UI.
- Não compor cenários completos antes da aprovação dos módulos que os constituem.
- Cada recurso recebe ID, estágio e arquivos no `assets/manifest.json`.
- Uma imagem gerada por IA é `concept` até passar por teste de escala e limpeza manual na grade.
- Reduções automáticas servem para testar legibilidade; não promovem um concept master a sprite final.
- Animações só começam após aprovação do sprite-base lateral em tamanho lógico real.

## Decisões abertas

- Escolha do lettering entre as novas explorações caligráficas.
- Tamanho lógico exato das tropas após teste com 20–30 unidades numa única casa.
- Forma das bases de cada povo e taxonomia completa de ícones de estado.
- Necessidade real de arraste manual após validar o posicionamento automático.
