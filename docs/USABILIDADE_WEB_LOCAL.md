# Mapa, HUD, relatórios e teclado — 30/09/2026

Apresentação sobre os contratos existentes. Nenhuma alteração nas regras, RNG,
ações, eventos ou formato de save/PlayerView.

## Mapa e HUD

- Curruna identificado pelo nome, jogador e povo no mapa, cidade e HUD.
  Não confundir com o jogador que está agindo; ambos têm indicação textual.
- Cinco casas fixas no template SVG. Cada cidade informa dono, povo e vida da Base.
- Cada unidade viva visível tem um SVG v0.2: tropa 32×32, herói 64×64,
  com vida atual/máxima. Ordenação por dono, heróis primeiro, identificador.
- Foco, mouse e toque permitem inspecionar somente os dados públicos recebidos.
  O painel abaixo do mapa mantém os detalhes legíveis; imagens desconhecidas têm fallback.
- Ícones nunca são substituídos apenas por contagens em breakpoints. O mapa tem
  largura mínima de 1100 px e rolagem horizontal em telas estreitas; os cinco botões
  de navegação permitem chegar às casas. Cada casa tem rolagem interna para grupos grandes,
  além da lista ampliada. Não há sobreposição ou descarte silencioso de unidades.
- Apostas somente se Gnomos e Duendes participarem; Canastra somente com Dragões;
  Pactos somente com Demônios. Presença inclui jogadores eliminados, pois participaram
  da partida. O filtro é de HUD, não restringe ações ou a consulta geral de regras.
  Apostas de adversários não são reconstruídas a partir de dados privados ausentes.

## Relatórios

Seletor de condições, produção/invocações, combate, artefatos, evolução por turno
e efeitos/recargas/loja. Produção, combate e artefatos têm tabela completa e gráfico
de barras com indicador selecionável. Evolução tem tabela e linhas de Ouro, Magia
ou vida da Base nos registros públicos de fim de turno.

Fonte exclusiva: `PlayerView.players[].stats`, `timeline`, condições e efeitos
públicos já expostos. Nenhuma inspeção do GameState ou mão de adversários.
Contadores inexistentes dentro de `stats` valem zero, como nos relatórios do terminal;
estatísticas indisponíveis e registros históricos ausentes permanecem sem valor.
Sem snapshots não há curva inventada. As linhas têm padrões distintos além da cor;
as tabelas preservam nomes e valores completos. Tabelas e gráficos rolam em telas pequenas.

## Atalhos

O tooltip de cada botão/summary informa seu atalho e a ativação nativa por
Enter/Espaço quando focado. Tab/Shift+Tab circulam pelos controles; selects mantêm
as setas nativas. Nenhum atalho executa uma opção desabilitada, oculta, atrás de um
diálogo ou da passagem de dispositivo. Digitação em campos não dispara teclas numéricas.

| Tecla | Função |
|---|---|
| 1 / 2 / 3 / 4 / 5 | Abrir recursos / Muralha / tropa / herói / movimento |
| 6 / 7 / 8 / 9 / 0 | Abrir compra por Ouro / transmutação por Magia / venda / feitiço / encerrar |
| Alt+1…9, com foco dentro de uma ação | Acionar o respectivo botão daquela ação |
| Alt+Shift+A…Z | Abrir grupos adicionais; conferir a atribuição atual no tooltip |
| Alt+Shift+1…5 | Centro / Cidade 1 / Cidade 2 / Cidade 3 / Cidade 4 |
| Alt+M / Alt+R / Alt+H | Mapa / relatórios / consulta de regras |
| Alt+S / Alt+E | Salvar cópia / exportar |
| Alt+Z / Alt+Y | Refazer meu Dia / Mola |
| Alt+N / Alt+L / Alt+U | Nova partida / carregar / atualizar saves |
| Alt+1…4 na configuração | Consultar povo e heróis daquele jogador |
| Alt+P | Confirmar passagem do aparelho |
| Alt+Enter / Escape no diálogo | Confirmar / cancelar |

Teclas de grupo abrem/focam opções; não enviam uma ação automaticamente. Encerrar,
restaurar e iniciar nova partida preservam suas confirmações. Atalhos com números
usam a tecla física, evitando diferenças de pontuação com Shift em layouts PT-BR.

## Verificação

```powershell
python -B tests/run_all.py
node --check jessica/web/static/app.js
node --check jessica/web/static/presentation.js
node tests/web_actions_ui.cjs
node tests/web_dialog_ui.cjs
node tests/web_presentation_ui.cjs
```

Suíte Python: 365 aprovados, zero falhas. Testes Node incluem oito combinações
de presença dos povos, 25 unidades vivas em uma casa, exclusão de mortos, inspeção,
modelos de relatórios, SVGs e proteção/contexto dos atalhos.
Navegador: desktop e largura 360 px, SVG carregado, 64×64 preservado, vida dentro
da casa, ausência de overflow da página, passagem de aparelho, navegação por
atalhos, consulta e relatórios. Toque em aparelho físico permanece para playtest.

Isso não certifica, por si só, a paridade integral de todas as regras terminal/web.

## Atualização: escolhas complexas

Sacrifício usa confirmação HTML; passagem de jogador foca a próxima decisão;
barra móvel deixa de cobrir ações; encerramento da Noite aparece expandido;
relatos e defesa usam nomes públicos. Validação atual: 402 testes Python e cinco
scripts Node aprovados. Cenários reais, limites e servidor descartável em
[VALIDACAO_ESCOLHAS_WEB.md](VALIDACAO_ESCOLHAS_WEB.md).
