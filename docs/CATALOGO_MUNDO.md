# Jéssica — catálogo-base do mundo v0.1

04/10/2026. Expansão de textos pausada até estruturar e aprovar o mundo.
Dados: [catalog-v0.1.json](../content/world/catalog-v0.1.json).
Heróis: [HEROIS_INVENTARIO.md](HEROIS_INVENTARIO.md).
Guia de voz: [NARRATIVA.md](NARRATIVA.md).

## Divisão do catálogo

| Família | Catalogado agora | Limite atual |
| --- | --- | --- |
| Geografia geral | Continentes, grandes regiões, ligações e fronteiras como categorias | Ainda sem divisões inventadas |
| Locais | Várzea das Sete Voltas e Sertão da Pedra Miúda | Nomes aprovados; posição, escala e vínculos não definidos |
| Povos | Os 12 povos do jogo | Cultura e terra natal não inferidas das passivas |
| Heróis/figuras | 43 definições: 36 opções gerais, incluindo o grupo, mais 7 anões individuais | Habilidades não são biografias; história/aparência/personalidade pendentes |
| Artefatos | 13 tipos, incluindo Pena do Manto Sagrado | São 12 tipos de cartas da Loja + Pena, não 24 objetos diferentes |
| Outros itens | Capa, Adaga, Relógio de bolso, Bracelete de Rogue | Forma, criadores e origem não inventados |
| Feitiços | 12 definições | Efeitos declarados não confirmam rituais ou origem histórica |
| Pactos | Os 6 nomes atuais | Sem atribuir signatários históricos ou origem religiosa |
| Acontecimentos históricos | Nenhum estabelecido nesta etapa | Vitória de uma partida não vira história fixa do mundo automaticamente |
| Referências não resolvidas | Salomão, citado no artefato | Nome não importa personagem histórico/religioso |

## Estrutura de ficha

- Identificador estável e nome; referências ao ID do jogo quando existir.
- Tipo: região, local, povo, figura, artefato, item, feitiço, pacto ou acontecimento.
- Status: aprovado pelo usuário, referência extraída do código, proposta ou indefinido.
- Fonte e vínculos confirmados; relação ausente permanece vazia, não inventada.
- Descrição de mundo separada de atributos e efeitos mecânicos.

O JSON é referência editorial versionada, **não** novo motor de regras nem
substituto dos catálogos do core. Atualizações de mecânicas exigem revisar as
referências extraídas; testes apontam quando IDs, nomes ou valores-base divergem.
Campos vazios são decisões pendentes, não convites para completar automaticamente.

## O que já entendo dos heróis

- Jogador comanda a cidade; herói é uma figura escolhida, não governante geral por padrão.
- Barba Negra e Valtherion também são Bases móveis. Não são equivalentes entre si:
  Barba precisa ativar o modo Herói; Valtherion combate como Herói.
- Guarari é centauro permanentemente; a transformação temporária de aliados não
  define a espécie ou origem de outros heróis no mundo.
- Os sete anões têm nomes próprios e funções distintas. A opção coletiva não é
  um personagem adicional. IDs como `dain`/`din` permanecem técnicos.
- Rogue tem progresso persistente por pactos; isso não demonstra infância,
  parentesco, moralidade ou pertencimento a uma religião.
- Mortos-Vivos não têm escolha inicial de herói. O nome Cobra, o Pajé Caído,
  por exemplo, não conta por si só como ele caiu ou qual era seu povo anterior.
- Títulos são preservados, mas literalidade aguarda confirmação: Rei do Mundo,
  Rainha Maga, Pai da Primeira Aurora, Ancião Milenar, Protetora dos Espíritos.

Fichas individuais incluem nome, povo de associação mecânica, valor-base, chaves
de habilidades e resumo atual da UI, identificado como referência não auditada.
Cinco resumos foram sinalizados por incompletude/desatualização: Miyamoto,
Vovó Gamba, Mestre, Belial e Rogue. Nenhuma correção de regras ou UI foi aplicada.

## Próxima definição, antes de novas descrições

Confirmado pelo usuário: mundo conectado; cidades variáveis por partida.
Isso não define número de continentes, fronteiras, distâncias ou desaparecimento
das cidades após a partida. Nem toda cidade de gameplay precisa virar local fixo
do catálogo. Conexão geográfica não cria regras novas de movimento.

Proposta inicial, ainda não aprovada, de quatro famílias de grandes regiões:
serras e matas; sertões e chapadas; rios e várzeas; costa e manguezais.
Sem nomes próprios novos, posição no mapa ou exclusividade de povos por enquanto.

1. Aprovar/ajustar essas famílias e então nomear poucas regiões.
2. Posicionar os dois locais aprovados nesse esqueleto.
3. Definir convivência e vínculos dos povos, sem deduzir territórios por raça.
4. Escolher um povo para validar identidade dos heróis em lote pequeno.
5. Depois aprovar figuras secundárias, origem dos artefatos e acontecimentos.

Os nomes reais permitidos, como Minas Gerais, não trazem a história real para
Jéssica. Não conectar lugares pela geografia real sem confirmação.
