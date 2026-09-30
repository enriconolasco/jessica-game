"""Textos de consulta compartilhados; valores básicos vêm dos catálogos do motor."""
PASSIVA_DESC = {
    "humanos": "Roca de Quilombo: rola 1D4 (+1 por Pena ativa) toda manha.",
    "anoes": "Mineiro Carreiro: +1 Ouro por unidade ana viva, toda manha.",
    "orcs": "Berco de Guerreiros: -1 Magia em invocacoes. Arquetipo extra.",
    "fadas": "Asas Encantadas: +1 Magia ao mover. Herois ganham artefato ao matar Heroi.",
    "vampiros": "Sede de Sangue: mata -> cura 2. Empata -> sobrevive com 2. Nao vale contra Cidades.",
    "lobisomens": "Maldicao da Lua: em Lua Cheia, dobro de dano. Unidades mortas ficam infectadas.",
    "gigantes": "Estatura Colossal: herois custam 4 Magia. Turnos x4 dobram vida de Joao e Pe.",
    "mortos_vivos": "Heróis custam 2 Magia, sem escolha no setup. Os 3 disponiveis na partida.",
    "filhos_floresta": "Florescimento Exuberante: Cidade comeca com 1 vida; no turno 13 recebe +2 Vida, +2 Ouro, +2 Magia.",
    "gnomos_duendes": "Continue Apostando: 4 apostas (H/C/D/S) alocadas em outros jogadores no inicio do turno.",
    "dragoes": "Envolvimento Cosmologico: ate 1 Artefato por naipe na Canastra fortalece Herois Dragoes.",
    "demonios": "Banco de Almas: +1 Magia sempre que qualquer unidade morre.",
}

HERO_ABILITY_DESC = {
    "miyamoto": "Ataca de Dia. Ao matar atacando ou retaliando, acumula vida máxima igual à vida atual anterior do alvo; bônus persiste. Dois ataques se for o mais forte da casa.",
    "besouro": "o Maioral: dobro + resistencia vs >=. Mandinga: artefato na Noite.",
    "iuna": "Aguia Negra: 1 de dano fixo recebido. 1D4 ao atacar. Adiciona 4 Penas.",
    "barbadourada": "Filho das Cachoeiras: +1 Magia por artefato na mao.",
    "ori": "Velho Mestre Ferreiro: ele + aliados na casa ganham Resistencia.",
    "seven_dwarves": "Os 7 Anoes: 7 herois em corrente. Sem Tropas.",
    "dain": "Atim: quem declara combate contra ele morre no fim da Noite.",
    "buin": "Dengoso: Invulneravel contra Herois.",
    "bein": "Soneca: mortos por ele ficam empalados ate os Anoes serem Curuna.",
    "boin": "Feliz: ve 2, escolhe 1 ao comprar/transmutar.",
    "tintin": "Dunga: fica Invisivel (recarga 1 turno).",
    "don": "Um ataque mais um por outro herói aliado próximo, conforme o motor atual.",
    "din": "Heróis aliados próximos podem atacar Bases.",
    "garoche": "Rei do Sertao: executa sem aliados proximos. +1 vida por execucao.",
    "arken": "Cacador: Espoliar todo Dia.",
    "vovo_gamba": "Enquanto viva, concede +1 de dano global às tropas Orcs do dono. Escolhe sua posição nas declarações noturnas do local.",
    "ainai": "Fada da Vinganca: teleporta para onde Fada/Elfo morreu. +1 Magia.",
    "valendar": "Rainha Maga: substitui Sonho Lucido por bonus de naipe.",
    "luna": "Sonhadora: Sonho Lucido multi. Retorna ao local de origem.",
    "dracula": "Dracula: mata -> empala. Mata -> feitico sai da recarga.",
    "dandara": "Dandara: torna ela + aliados da casa invisiveis.",
    "luide_vampa": "Enquanto vivo, permite mover e usar feitiço na janela noturna do jogador em cada local, antes dos ataques; chega a locais resolvidos e ainda pode declarar.",
    "lupa_lider": "Enquanto viva, concede Resistência na Lua Cheia e aos aliados transformados pelo feitiço.",
    "cigana": "Em Lua Cheia ou ao usar Licantropo, concede invisibilidade aos transformados enquanto viva. Na Lua Cheia, sua habilidade permite atacar Cidades.",
    "luarado": "Custa sempre 2 Magia; em Lua Cheia ou transformado, anda duas vezes (uma no turno da invocação) e infecta ao causar dano.",
    "joao_grandao": "Joao Grandao: Presenca Magnetica forca ataques inimigos.",
    "pe_descalco": "Pe Descalco: +1 ataque sempre. Grito de Guerra: aliados x2 dano.",
    "caroco": "Grátis no turno 1; gera Caroços ao longo da partida. Cabaça Cheia: cada Caroço rola uma vez por turno: invulnerável, atacar Base, +1 Ouro ou +1 Magia.",
    "cobra": "Cobra: herois mortos retornam como Espectros por 1 turno.",
    "zoia": "Zoia: 2 tropas extras (Ghoul e Esqueleto com 1 vida).",
    "cova_rasa": "Cova Rasa: amaldicoa inimigos proximos no inicio da Noite.",
    "guarari": "Centauro permanente: anda 2x (1x ao ser invocado). Transforma aliado por 1 Magia.",
    "aiquara": "Ninfa: controla inimigo da casa (mover no Dia, atacar na Noite).",
    "baoba_ba": "Anciao: 1 Magia x 3 turnos para invocar. Tropas aliadas na casa dele.",
    "bimbo_do_mal": "Gastar aposta: invisivel (1) ou artefato da Loja (5).",
    "sao_tome": "Herda passivas dos jogadores apostados e pode rerrolar o feitico copiado.",
    "zebum": "Mistico: apostas corretas compram herois estrangeiros.",
    "barba_negra": "Base móvel com 3 de vida. Fora do modo Herói, não declara ataques, recebe/retalia como Base e não pode ser alvo de heróis. Prepara Mar de Chamas e ativa modo Herói durante o Dia. Morto, perde a partida.",
    "purpura": "3 de vida base, mais 1 atual/máxima por manhã par já passada, inclusive ao reinvocar. Invisibilidade até o fim do turno, recarga de um turno.",
    "valtherion": "Base móvel de 20 de vida que combate como Herói; imune a controle e infecção. Sem invocação paga de tropas ou construção de muralha. Chamado invoca tropa Dragão conforme mão + Canastra, dentro dos limites do arquétipo.",
    "belial": "No início da Noite, ganha +1 vida atual/máxima, cura 1 de aliados próximos e causa 1 de dano em inimigos próximos, sujeito às defesas. Herói que mata herói recebe oferta de pacto enquanto Belial estiver vivo.",
    "tuza": "Tem Resistencia. Inimigos podem firmar pactos no turno Curuna dos Demonios.",
    "rogue_devil": "Vida base 0. Ao ser invocado abre pacto obrigatório. Firmar pacto dá artefato da loja, +1 vida atual/máxima persistente e um item. Concluir quest não concede outra recompensa. Quatro itens permitem atacar Bases.",
}

STATUS_DESC = {
    "invisivel": "Nao pode ser atacado ate o fim do turno. Atacar remove a invisibilidade.",
    "sono": "Nao pode atacar. Acorda se for atacado.",
    "amaldicoado": "Recebe o DOBRO de dano de TODAS as fontes ate o fim do turno (Cova Rasa).",
    "morcego": "Vampiro: pode se mover 2x neste turno (ou 1x se recem-invocado).",
    "lobisomem": "Em Lua Cheia: dobro de dano, infeccao ao causar dano (Luarado) ou ao matar.",
    "Ks (Veu das Cacadoras)": "Aliados perto de Heroi do dono batem 2x. Herois podem atacar Cidades.",
    "Centauro (Guarari)": "Guarari é permanente. Transformação de aliados: dois movimentos (um no turno da invocação), até o fim da Noite.",
    "Resistencia": "Cada Resistência divide o dano recebido por 2, arredondado para baixo. Dano de 1 vira 0, inclusive em área.",
    "Invulneravel": "Nao recebe dano ate o fim do turno (Qh).",
    "Armadura de Ouro": "Durante um golpe, escolha quanto Ouro pagar: de zero ao menor valor entre dano e Ouro disponível.",
    "Esploiado": "Nao pode atacar no turno (Arken Espoliou a casa).",
    "Empalado": "Unidade destruida por Dracula nao pode ser reinvocada pelo dono.",
    "Envenenado (Infeccao)": "Se o alvo morrer em Lua Cheia do Lobisomem, vira Lobisomem controlado.",
}

HERO_ABILITY_DESC["ent"] = "Desativado na seleção enquanto aguarda rework."
PASSIVA_DESC["humanos"] = "Roça de Quilombo: um D4 por manhã, mais um dado por Pena ativa. Resultados: 1 = +1 Magia; 2 = +1 Ouro; 3 = cura 2 pendente; 4 = 1 dano aos inimigos na sua Cidade."
PASSIVA_DESC["gnomos_duendes"] = "Quatro apostas antes do primeiro Dia de cada turno. Copas: alvo ganha vida na Base; Paus: usa artefato; Ouros: obtém artefato; Espadas: invoca unidade. Um evento coletivo pode cumprir uma aposta apenas uma vez. A aposta cumprida sai do alvo."
PASSIVA_DESC["dragoes"] = "Canastra pública, no máximo uma carta por naipe. Efeitos nos heróis Dragões: ♥ Resistência; ♦ artefatos custam 5 Ouro/Magia; ♣ dois movimentos; ♠ podem atacar Bases. Valetes: ao entrar/sair um Valete, ganha Ouro conforme o número de Valetes presente antes da ação. Damas: +2 vida máxima e cura 2; ao sair, remove apenas 2 de vida máxima. Reis: +1 Magia por manhã."

SPELL_NOTES = {
    "sonho_lucido": "Escolha um artefato da mão, troque seu naipe e resolva o novo artefato imediatamente, incluindo escolhas adicionais. Luna permite uma sequência; Valendar substitui o efeito por bônus de naipe.",
    "imitacao_gnomerica": "Usa o feitiço sorteado entre os outros povos participantes, vivos ou mortos. São Tomé permite um rerroll antes do uso. Segue a recarga do feitiço copiado.",
    "ressonancia_magica": "Adiciona, remove ou troca na Canastra. Um uso no turno não gera recarga; vários usos geram recarga no próximo turno. Cada artefato pode ser movimentado até duas vezes no turno.",
    "sacrificio_de_demonio": "Sacrifique um herói vivo e devolva à loja os artefatos escolhidos da mão ou do campo, recebendo a mesma quantidade. Efeitos ativos removidos cessam imediatamente.",
}

PACT_NOTES = {
    "sacrifique_futuro": "Base passa a 4 de vida atual e máxima; sua vida máxima não pode aumentar enquanto o pacto estiver ativo.",
    "sacrifique_militar": "Tropas combatem como heróis.",
    "sacrifique_mente": "Aliados ganham +1 de dano e devem declarar combate à Noite.",
    "cabecas_herois": "Mate um herói de cada povo vivo exigido pelo pacto.",
    "banho_sangue": "Mate três tropas ou heróis na mesma Noite.",
    "vida_lider": "Elimine um jogador.",
}

ROGUE_NOTES = {
    "capa": "Ao derrotar um inimigo, fica invisível.",
    "adaga": "Executa inimigos isolados com vida atual menor que a sua.",
    "relogio": "Antes do fim da Noite, pode ir a uma casa onde houve combate efetivo.",
    "bracelete": "Resistência contra heróis e +1 de vida.",
}

