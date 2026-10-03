# Configuração pré-jogo — 03/10/2026

Terminal, web local e salas online usam o mesmo motor, com **2, 3, 4 ou 5 jogadores**.
Quatro continua sendo o padrão. Não há alteração de condições durante a partida.

## Condições iniciais

Cada jogador pode ter vida da Base, Ouro, Magia e quantidade de artefatos próprios.
Campos individuais vazios mantêm os padrões gerais e as exceções do povo/herói.
Valores explícitos substituem essas condições, inclusive a vida dos Heróis-Base;
quando necessário, a vida máxima inicial é elevada para comportar a vida escolhida.
Os bônus e juros normais da primeira manhã continuam sendo aplicados depois.

Artefatos iniciais são sorteados da loja, ficam na mão e não são ativados automaticamente.
A distribuição usa o RNG da partida e a ordem dos identificadores dos jogadores.
A soma solicitada não pode exceder as 24 cartas da loja. Nenhuma carta é criada.
Limites: vida 1–100; Ouro/Magia 0–999; artefatos 0–24, sujeitos ao estoque total.

- Terminal: escolha a quantidade, os padrões gerais e, opcionalmente, personalize cada jogador.
- Web local: selecione a quantidade e preencha os campos desejados em cada ficha.
- Online: o anfitrião escolhe a quantidade ao criar a sala e aplica condições individuais
  antes de iniciar. Todos veem os valores. Alterações desmarcam “pronto” para todos;
  apenas o anfitrião pode aplicá-las, com revisão atual da sala.

## Mapa e eliminação

Há um Centro e uma Cidade por participante, mesmo após sua eliminação.
Dois: cima/baixo; três: cima e diagonais inferiores; quatro: cruz existente;
cinco: cidades igualmente espaçadas ao redor do Centro. O layout não muda regras de
movimento: Cidade ↔ Centro. Ícones continuam inspecionáveis; casas e mapa são roláveis.
As prioridades, o Curuna e a ordem de declarações usam os participantes reais.

Destruir uma Base concede tantos artefatos quanto os jogadores vivos imediatamente
antes da eliminação, incluindo a vítima: em cinco jogadores, 5 → 4 → 3 → 2.
A loja continua limitada: sem estoque, só as cartas disponíveis são entregues.
A mesma contagem se aplica à morte de um Herói-Base com matador identificado.

## Contratos e compatibilidade

`POST /matches`: `players` aceita 2–5 entradas. Cada entrada pode conter
`initial: {city_life, city_life_max, gold, magic, artifacts}`; os campos são opcionais.
`config.artifacts` define um padrão geral, substituível por `initial.artifacts`.
`GET /setup-order?seed=...&num_players=...` usa a quantidade real (padrão 4).

`POST /rooms`: `{name, num_players?}`. A sala retorna `capacity` e
`initial_conditions`, indexado por IDs em texto. Antes da partida,
`POST /rooms/{code}/configure` recebe `{revision, initial_conditions}` autenticado.
Partidas online exigem exatamente `capacity` participantes prontos.

As versões de ações/eventos/visões/saves permanecem v0.1: extensão compatível de
configuração, sem mudança no significado das ações. Saves com quatro participantes
continuam válidos; salas antigas sem os campos novos assumem quatro e padrões atuais.

## Verificação

`tests/test_variable_players.py`: preparação, determinismo, privacidade, save/load,
ciclo diurno/noturno, recompensas progressivas, Heróis-Base e rejeição de cidades ausentes;
também capacidade, configuração autorizada e recuperação das salas de 2–5 participantes.
`tests/web_presentation_ui.cjs`: posicionamento, quantidade de casas, atalhos e inspeção.
Playtest humano de partidas completas com cada quantidade permanece necessário.
