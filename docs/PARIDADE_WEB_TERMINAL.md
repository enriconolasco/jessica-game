# Fechamento da versão web local

Referência: implementação terminal e testes do repositório, não conversas.
Marco anterior desta revisão: web 25584df. Atualizado em 2026-09-29.
Não há evidência suficiente para declarar paridade total ou estimar um percentual.

Revisão de 01/10/2026: três partidas mistas completas aprovadas, com feitiços,
habilidades, artefatos e apostas, mais comparação noturna dirigida de Armadura; ver
`VALIDACAO_PARTIDAS_COMPLETAS.md`. O timing dos pactos de Belial (**WEB-001**)
foi confirmado pelo usuário e corrigido: ofertas noturnas ficam para a jogada
do beneficiário no próximo Dia, como no terminal. Testes incluem ataque,
retaliação e retomada de save antigo; ver `PENDENCIAS_PARIDADE.md`.
Portanto, "todos os fluxos têm adaptador" não significa "paridade total".

Lote seguinte de 01/10: três partidas completas adicionais com Bases Dragões e
Rogue; Canastra, habilidades das Bases, pactos, reinvocação persistente e quest
Vida de um Líder verificadas. Prévia e confirmação de pactos implementadas na
web. Ver `VALIDACAO_BASES_E_PACTOS.md` para recorte e limites restantes.

Lote seguinte: quests Banho de Sangue/Cabeças de Heróis e janelas intercaladas
Luna/Luide/Armadura/Q♦/Ainai aprovadas em cenários dirigidos. Rogue com quatro
itens agora encontra Bases no seletor de alvos nas duas instalações; combinação
com Relógio testada. Ver `VALIDACAO_QUESTS_E_JANELAS.md`, sem confundir esses
cenários com partidas completas ou certificação de todos os cruzamentos.

Revisão de 2026-09-30: ver `AUDITORIA_PARIDADE_2026_09_30.md` para o mapeamento
de todos os menus, novos pagamentos de Armadura, consultas, histórico e refazer/Mola.
Não foi identificado outro fluxo mecânico selecionável sem adaptador; a validação
cruzada completa permanece pendente. Importação diurna compatível do terminal e
cinco autosaves anteriores implementados: `SAVES_E_RECUPERACAO.md`. Saves noturnos
sem fila ou Dias ambíguos são rejeitados.

Novo lote: ofertas de pacto inviáveis deixam de bloquear Dia/Noite; a HUD identifica
a janela atual, inclusive Luide sem unidades restantes. Onze habilidades diurnas e
seis noites mistas dos 12 povos comparadas em `VALIDACAO_COMBINACOES_WEB.md`.
Nenhuma regra de balanceamento foi alterada. Partidas mistas completas continuam
pendentes; não confundir cobertura de ações com certificação de todas as combinações.
Replay adicional em processo separado contra o terminal `51586c9`: 125 ações
diurnas e seis noites mistas com estado/logs/RNG equivalentes. O script é reutilizável
para conferir novas versões sem rastrear manualmente cada regra nos arquivos.

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

Terceiro lote: janelas reais de Ainai/Luna/Mandinga comparadas; corrigidos os
momentos das ofertas de Ainai. Sonho Lúcido múltiplo atravessa invocação, buff,
controle, combate e próxima manhã. Doze partidas básicas chegaram à vitória
com igualdade terminal/web: `VALIDACAO_PARTIDAS_COMPLETAS.md`. O recorte não
certifica todos os conteúdos em combinação nem a interface manual.

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

Escolhas complexas verificadas no navegador: Sacrifício, sequência de Luna e
Armadura, incluindo passagem de aparelho e largura de celular. Correções apenas
de apresentação e relatório em [VALIDACAO_ESCOLHAS_WEB.md](VALIDACAO_ESCOLHAS_WEB.md).

Luide também foi corrigido para abrir a janela sem inimigos no local ocupado,
em ambas as interfaces; testes e limites em [FIX_LUIDE_SEM_ALVOS.md](FIX_LUIDE_SEM_ALVOS.md).

## 5. Empacotar e entregar

- Comando/atalho único para iniciar, dependências fixadas e manual curto.
- Validar funcionamento sem internet com o servidor Python local.
- PWA instalável/cache é uma entrega adicional: não executa o motor Python sozinho
  no celular. Funcionamento autônomo no celular exige decidir onde o motor roda.
- Bots para jogar sozinho são uma frente posterior; não são requisito para
  equivalência com o terminal passa-e-joga. Multiplayer remoto permanece fora.
