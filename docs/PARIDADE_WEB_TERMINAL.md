# Fechamento da versão web local

Referência: implementação terminal e testes do repositório, não conversas.
Marco anterior desta revisão: web 25584df. Atualizado em 2026-09-29.
Não há evidência suficiente para declarar paridade total ou estimar um percentual.

Revisão de 2026-09-30: ver `AUDITORIA_PARIDADE_2026_09_30.md` para o mapeamento
de todos os menus, novos pagamentos de Armadura, consultas, histórico e refazer/Mola.
Não foi identificado outro fluxo mecânico selecionável sem adaptador; a validação
cruzada completa permanece pendente. Importação diurna compatível do terminal e
cinco autosaves anteriores implementados: `SAVES_E_RECUPERACAO.md`. Saves noturnos
sem fila ou Dias ambíguos são rejeitados.

## 1. Fechar fluxos mecânicos ainda ausentes

- Ainai: implementado teleporte e reabertura de local; validar em playtest.
- Luide Vampa: implementada janela por jogador/local, movimento, feitiço e reabertura;
  morte interrompe a janela. Validar em playtest.
- Aiquara: controle noturno implementado na abertura; falta playtest integrado.
- Miyamoto diurno implementado: falta playtest integrado de cruzamentos e reações.
- Luna/Sonho Lúcido: prévia intercalada implementada; permite alvos surgidos
  durante a sequência e confirma tudo atomicamente. J♦ mantém agendamento T+3.
  Validar em playtest, incluindo reações/pactos gerados por artefatos.
- Auditar todas as ações do inventário contra as opções realmente oferecidas
  pela porta comum. Não assumir que liberar um hero_id equivale a completar
  todas as suas habilidades.

Mandinga de Besouro agora usa o core, incluindo escolha de alvo e pendências
J♦/Feliz/Q♦. Iúna foi liberada no combate; dano/dado são os do motor. Pena já
possui ação diurna. Estes fluxos ainda precisam de playtest integrado.

## 2. Auditar ordem e interrupções da partida

Primeiro lote diferencial aprovado: `VALIDACAO_NOTURNA.md` — ordem, reentrada,
Vovó, Bater Primeiro, morte durante ataques múltiplos, Noite pulada, Q♣ e RNG de
Iúna. Executa a orquestração terminal e a web separadamente; não certifica ainda
os cruzamentos com as janelas especiais abaixo.

Segundo lote aprovado: `VALIDACAO_CICLO.md` — Dias pulados, próxima manhã nos
12 povos, controle/expiração, mortes adiadas, Armadura/Q♦/Belial e vitória durante
reação. Luide também tem comparação com a janela real do terminal, incluindo
chegada a local futuro ou processado. Continuam pendentes partidas cruzadas
completas e outras janelas intercaladas.

- Comparar filas web e terminal local a local, incluindo Bater Primeiro, Vovó,
  entrada/saída, morte, controle temporário e múltiplos ataques.
- Validar Dia/Noite pulados, jogador eliminado, vitória durante reação,
  mortes no fim da Noite, novas pendências e mudanças de Curruna.
- Conferir que manhã, juros, recarga, Lua Cheia e apostas ocorrem uma única vez.
- Validar pactos, infecção, empalamento e perda imediata de passivas de herói.
- Importar saves de referência do terminal e explicar/rejeitar incompatibilidades,
  em especial saves no meio de uma declaração não representada na fila web.

## 3. Consolidar contratos e experiência local

- Nenhuma escolha disponível no terminal pode depender de editar JSON.
- Consultas de povos, heróis, feitiços e artefatos; custos/limites claros.
- Histórico completo compreensível e eventos suficientes para acompanhar efeitos,
  sem revelar mão, sorteios futuros ou informações proibidas.
- Saves web: lista, cópias nomeadas, exportação/importação e restauração de
  autosave implementadas. Estado/RNG/eventos preservados; versões e arquivos
  inválidos são rejeitados. Rotação com cinco recuperações anteriores implementada;
  cópias manuais permanecem independentes.
- Navegação por teclado/toque, passagem segura de jogador e mensagens de erro.

## 4. Provar a paridade

- Matriz dos 12 povos: passivas, heróis, feitiços, artefatos e cruzamentos críticos.
- Mesma seed/save/decisões no terminal e na web: comparar estado, RNG e resultado
  após cada ação, não apenas vitória final.
- Testes de rejeição atômica, privacidade, recarga e save/load em cada janela.
- Partidas completas automatizadas e playtest manual em navegador desktop/mobile.
- Registrar divergências separadamente; não alterar regras para fazer testes passar.

Critério de conclusão: nenhuma ação mecânica faltante, nenhuma divergência conhecida
sem decisão registrada, matriz aprovada e partidas completas verificadas.
Contagem de testes isolada não certifica 100% de fidelidade.

## 5. Empacotar e entregar

- Comando/atalho único para iniciar, dependências fixadas e manual curto.
- Validar funcionamento sem internet com o servidor Python local.
- PWA instalável/cache é uma entrega adicional: não executa o motor Python sozinho
  no celular. Funcionamento autônomo no celular exige decidir onde o motor roda.
- Bots para jogar sozinho são uma frente posterior; não são requisito para
  equivalência com o terminal passa-e-joga. Multiplayer remoto permanece fora.
