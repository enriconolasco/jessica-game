# Cliente web vertical

Lote de conteúdo/usabilidade de 2026-09-30: consultas completas, relatórios e
condições, pagamentos de Armadura por golpe, abertura de locais no histórico e
Refazer/Mola. Consulte `AUDITORIA_PARIDADE_2026_09_30.md` para cobertura e limites.

Saves locais: a tela inicial lista cópias nomeadas e autosaves. Escolha uma entrada
e clique em Carregar; também é possível importar um JSON exportado pela web.
“Salvar cópia” cria um ponto independente, que ações posteriores não sobrescrevem.
“Exportar partida” baixa estado completo (incluindo todas as mãos), RNG e eventos.
Autosave é atualizado após ações aceitas, usando escrita temporária e substituição
do arquivo. A lista indica arquivos inválidos sem impedir acesso aos demais.
Versões incompatíveis e arquivos malformados são rejeitados antes de criar partida.
Saves brutos do terminal ainda não são importados automaticamente.

Sonho Lúcido com Luna: ao adicionar uma carta, o servidor simula a sequência e
atualiza as opções seguintes, incluindo heróis recém-invocados. A prévia não gasta
recursos nem altera a partida; “Lançar Sonho Lúcido” confirma toda a sequência.
Limpar a sequência permite recomeçar. Validação de alvos e resultados fica no core.

Coleta: as três distribuições de recursos são apresentadas como botões separados,
sem pré-seleção automática. O motor continua limitando a coleta a uma por turno.
Teste de apresentação e envio: `node tests/web_actions_ui.cjs` (DOM simulado;
não substitui teste manual em navegador).

Prova local da comunicação navegador → porta headless → motor → eventos → tela.

## Executar

Na raiz do projeto:

```powershell
python -m jessica.web.server
```

Abra `http://127.0.0.1:8765`. Não há dependências web externas.

## Corte atual

- cria e carrega partidas locais;
- configura nomes, recursos iniciais, quatro povos distintos e heróis pelo catálogo do motor;
- oculta a partida na passagem local do dispositivo até o próximo jogador confirmar;
- entrega `PlayerView` e ações legais com rótulos;
- executa coleta, cidade, monumento, invocação, movimento, mercado de artefatos e fim da janela do jogador;
- atualiza a tela sem recarga e apresenta eventos recentes;
- salva manualmente e faz autosave após cada ação aceita;
- rejeita versões incompatíveis de save.
- renderiza as unidades num minimapa acessível de cinco casas com os ícones SVG v0.2;
- preserva a orientação do terminal (Cidade 1 ao sul, Cidade 3 ao norte) e a geometria
  do SVG em qualquer largura; telas compactas usam contagens com lista ampliada por casa;
- agrupa ações por tipo e confirma o encerramento da janela do jogador.
- compacta variantes de uma mesma ação em seletores adequados para celular;
- mostra a área privada do jogador ativo e descreve eventos estruturados em PT-BR.
- filtra eventos privados por jogador; cartas compradas não vazam para adversários.

Também estão disponíveis os 12 artefatos com escolhas de alvo, Pena, escolhas pendentes,
curas, pactos e habilidades diurnas listadas no roteiro. Uma escolha pendente bloqueia
outras ações até ser resolvida. Rogue recebe vida, item e artefato ao firmar qualquer
pacto; concluir uma quest não concede outra recompensa.

Há nove feitiços adaptados (lista no roteiro), incluindo Ressonância Mágica com
adicionar/remover/trocar, cópias desses feitiços pelos Gnomos e rerrolagem de São Tomé.
O histórico mostra todos os eventos visíveis, separados por turno. Cabaça Cheia
rola apenas para Caroços que ainda não rolaram naquele turno.

Ao terminar as quatro janelas do Dia, a partida entra na Noite. A fatia básica
permite tropas e os heróis liberados em `night_actions.SUPPORTED_HEROES`:
atacar, receber retaliação, passar e
iniciar o próximo turno. Q♦ interrompe a fila para a escolha de Ouro/Magia e
retoma o combate após resolvida, inclusive ao carregar um save. Pactos também
interrompem e retomam a fila; Rogue tem a janela do Relógio no fim da Noite.
Mar de Chamas preparado no Dia é resolvido uma única vez.
Janelas de herói não adaptadas ainda bloqueiam a Noite com aviso nominal;
não são ignoradas. Sacrifício de Demônio permite selecionar herói e múltiplas
cartas da mão/campo, inclusive quando copiado pelos Gnomos. Sonho Lúcido oferece
uma carta com escolha imediata; Luna também monta uma sequência de várias cartas
com seus alvos atuais. J♦ segue o agendamento T+3 do core, sem posição obrigatória.
Escolhas intercaladas e algumas habilidades
ainda aguardam adaptação: o cliente
não é uma partida completa. O histórico de eventos agora acompanha o save.

Próximas etapas: [ROADMAP_WEB_LOCAL.md](ROADMAP_WEB_LOCAL.md).
