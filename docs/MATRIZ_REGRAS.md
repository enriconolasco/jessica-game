# Matriz de regras e rastreabilidade

Use este arquivo como índice antes de procurar regras pelo repositório. Cada mudança
de mecânica deve atualizar sua linha e possuir ao menos um teste comportamental.

| Domínio | Definição/conteúdo | Execução principal | Integrações | Testes |
|---|---|---|---|---|
| Povos e passivas | `core/peoples.py` | `core/turn.py` | `core/combat.py`, `core/actions.py` | `tests/test_*` do povo |
| Heróis e atributos | `core/heroes.py` | `core/actions.py` | `core/combat.py`, `core/setup.py` | `tests/test_heroes.py`, teste do povo |
| Feitiços | `core/spells.py` | `core/actions.py::cast_spell` | `main.py` | teste do povo/feitiço |
| Artefatos | `core/artifacts.py` | `core/artifacts_effects.py` | `core/actions.py` | `tests/test_artifact*` |
| Combate | `core/combat.py` | `resolve_attack` | `core/peoples.py` | `tests/test_combat.py`, teste do povo |
| Turno/manhã/noite | `core/turn.py` | `start_turn`, `end_turn` | `main.py` | `tests/test_turn.py` |
| Persistência | `core/models.py` | `core/serialize.py` | — | `tests/test_serialize.py` |
| Porta headless | `core/headless.py` | `legal_actions`, `apply_action`, `view_for_player` | `main.py` | `tests/test_headless_v0_1.py` |

## Povos adicionados ou alterados

| Povo | Regras centrais | Teste canônico |
|---|---|---|
| Dragões | Canastra, Bases móveis, Púrpura, Mar de Chamas e Chamado | `tests/test_dragoes.py` |
| Anões | Sete Anões e empalamento temporário | `tests/test_7_dwarves.py`, `tests/test_seven_dwarves_abilities.py` |
| Filhos da Floresta | Guarari/Centauro e Cabaça Cheia | `tests/test_filhos_floresta.py`, `tests/test_gigantes.py` |
| Gnomos e Duendes | Apostas por fatos gerais: vida da Base, artefato obtido, invocação e artefato jogado | `tests/test_gnomos_duendes.py` |
| Demônios | Banco de Almas, seis pactos, Belial, Tuza, Rogue Devil e Sacrifício | `tests/test_demonios.py` |

## Fluxo mínimo de alteração

1. Atualizar regra no core, sem duplicá-la no terminal.
2. Atualizar a interface apenas para coletar escolhas e exibir resultados.
3. Atualizar/adicionar o teste comportamental canônico.
4. Rodar o teste focal e `tests/run_all.py`.
5. Atualizar esta matriz somente se surgirem novos pontos de entrada.
