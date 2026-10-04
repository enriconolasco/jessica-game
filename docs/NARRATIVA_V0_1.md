# Narrativa v0.1 — piloto terminal

Base auditada: `3dc7035`, branch `codex/online-rooms`. Sem mudança de regras.

## Voz PT-BR

Direta, literária sem solenidade constante. Pedra, mata, várzea, veredas e
travessias dão identidade brasileira sem caricatura regional. Uma ou duas frases;
introdução admite parágrafo curto. Não inventar passado, crenças, alianças ou
intenções dos jogadores. Evitar profecias, superlativos e frases épicas genéricas.
Clima/estação/território são cosméticos: nunca conferem bônus nem restrições.
Prosa não substitui custos, dano, resultados ou comandos. Sem novas pausas.

## Auditoria e gatilhos

| Momento | Fonte real no terminal | Gatilho |
| --- | --- | --- |
| Introdução | `setup_ui` concluído, heróis revelados | `match_started` |
| Turno geral | `start_turn`, turno e Curruna | `turn_started` |
| Passagem diurna | Retorno de `run_player_day` | `player_turn_ended` |
| Encerramento | `game_over`, `winner_id`, `show_victory` | `match_ended` |

`player_turn_ended` já existia no headless, mas não era emitido pelo fim direto
do dia no terminal. Os demais são novos eventos de apresentação de ciclo;
o adaptador chama `lifecycle_event` nos limites reais. Não constituem ainda um
stream universal emitido automaticamente pelo core. A web não renderiza narrativa
neste marco; poderá reutilizar o módulo puro.

Combate fica fora: existem `combat_house_opened`, `night_action_resolved` e
registros estruturados de ataques/mortes; falta normalizar eventos completos de
resultado entre clientes. `public_roll` parcialmente extraído de frases em
`web/session.py` também fica fora. Nunca interpretar `event_log`.

## Contrato e seleção

Catálogo: `content/narrative/pilot-v0.1.json`, envelope `version: narrative-v0.1`,
`entries`. São 30 entradas: 8 introduções, 8 turnos, 6 passagens, 4 vitórias e 4 empates.
Cada entrada tem exatamente `id`, `trigger`, `conditions`, `text`, `weight`.
ID único em `[a-z][a-z0-9_.-]{0,99}`; peso inteiro 1–100; texto de até 600 caracteres.
Variáveis simples: `territory`, `season`, `atmosphere`, `motive`, `peoples`, `turn`,
`curuna`, `player`, `next_player`, `winner`. Sem atributos, formatos ou código.
Condições: igualdade nos atributos dos perfis; `outcome: victory|draw`.
Entradas inválidas/duplicadas são omitidas e diagnosticadas. Catálogo ausente ou
incompatível não interrompe o jogo; ausência de entrada compatível omite a prosa.

`lifecycle_event(trigger, view, player_id, next_player_id)` produz evento público
`event-v0.1` com ID estável: `match:start`, `turn:N:start`, `turn:N:player:P:end`,
`match:end`. Não pressupõe que todo evento antigo tenha ID.
`observe(seed, session, event, view, mode)` retorna nova sessão e texto opcional.
Não recebe GameState nem lê logs, mãos, escolhas privadas ou `PlayerView.self`.
O piloto rejeita TODOS os eventos privados/restritos. Narrativa privada futura
exigirá sessões/audiências próprias.

Perfil escolhido uma vez entre três combinações compatíveis de território,
estação, atmosfera e motivo. RNG separado, derivado de SHA-256(namespace + seed),
sem consumir `state.rng`. Seleção ponderada entre entradas compatíveis menos usadas;
evita as duas últimas quando possível. Acontecimento sem texto também é consumido.

## Persistência e reprodução

`GameState.narrative` é apenas metadado de apresentação, excluído da igualdade
da dataclass; não altera regras, vencedor ou RNG mecânico. Serializado somente se
preenchido: versão, perfil, RNG próprio, histórico de IDs, campos resolvidos e textos.
`replay` recupera registros exatos mesmo após mudar o catálogo.
Save/load e snapshots de refazer/Mola restauram esse progresso. Prosa não vai para
`event_log`; metadado narrativo não aparece em PlayerView. Saves antigos funcionam.
Metadado narrativo corrompido é ignorado: perde reprodução narrativa, não regras.

## Executar nesta branch atualizada

```powershell
.\JOGAR.cmd --narrativa breve --salvar saves/terminal/partida.json
```

Retomar e continuar salvando:

```powershell
.\JOGAR.cmd --narrativa breve --carregar saves/terminal/partida.json --salvar saves/terminal/partida.json
```

Alternativa: `python -m jessica.main` com os mesmos argumentos e Rich instalado.
Padrão: narrativa desligada, sem gravação automática. `--narrativa desligada`
preserva metadados carregados sem avançar o RNG narrativo.

Checkpoint gravado atomicamente antes da primeira manhã, entre turnos completos
e no encerramento. Interromper no meio do turno perde jogadas desde o checkpoint.
Envelope próprio `{version:1,kind:terminal-turn-boundary,state:...}`. Não aceita saves
web/raw arbitrários: terminal não retoma filas intermediárias. O arquivo informado
é sobrescrito a cada checkpoint, inclusive ao começar outra partida com o mesmo
argumento; use nomes distintos para conservar partidas. Sem seleção de load na UI.

## Verificações e pendências

`tests/test_narrative.py`: 13 testes de catálogo, determinismo, sigilo, repetição,
save/load, replay, refazer, falhas de conteúdo, Rich literal, checkpoint e fluxo
terminal simulado; igualdade de estado mecânico/RNG/vencedor com modo ligado/desligado.
Revisados os 30 textos: variáveis, perfis e ausência de efeitos cosméticos.
Partida humana completa para avaliar ritmo ainda pendente.
Depois: normalizar combate, ampliar famílias e integrar web; crônica final pendente.
