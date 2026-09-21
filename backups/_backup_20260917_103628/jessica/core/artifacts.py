from __future__ import annotations
from dataclasses import dataclass, field
from .constants import ARTIFACTS_PER_CARD_IN_SHOP
from .rng import DeterministicRNG


@dataclass(frozen=True)
class ArtifactDefinition:
    card_id: str
    rank: str
    suit: str
    name: str
    description: str


ARTIFACT_CATALOG: dict[str, ArtifactDefinition] = {
    "J_H": ArtifactDefinition("J_H", "J", "H", "Memórias Ancestrais",
        "Invoque outro Herói do seu povo. Volta à Loja quando o Herói morre."),
    "Q_H": ArtifactDefinition("Q_H", "Q", "H", "Bênção da Natureza",
        "Aliados e sua Cidade ficam invulneráveis neste turno; "
        "não pode atacar outras Cidades."),
    "K_H": ArtifactDefinition("K_H", "K", "H", "Aquilombar",
        "+1 Vida na Cidade e +1 Vida máxima toda manhã. "
        "Só retorna à Loja quando a Cidade for destruída."),
    "J_D": ArtifactDefinition("J_D", "J", "D", "Tabaréu que Vem do Sertão",
        "Daqui a 3 Dias, veja 3 Artefatos e escolha 2."),
    "Q_D": ArtifactDefinition("Q_D", "Q", "D", "Mel de Ouro Encantado",
        "Escolha uma unidade. Você e o matador ganham a vida máxima dela "
        "em Ouro ou Magia se ela morrer em combate."),
    "K_D": ArtifactDefinition("K_D", "K", "D", "Balança que Pesa Ouro",
        "+2 Ouro e +1 Magia toda manhã até o fim do jogo."),
    "J_S": ArtifactDefinition("J_S", "J", "S", "Chamado da Lua",
        "Invoque uma Tropa com 5 de vida em qualquer lugar do mapa. "
        "Volta à Loja quando ela morre."),
    "Q_S": ArtifactDefinition("Q_S", "Q", "S", "Chama Eterna da Revolução",
        "Aliados dão o dobro de dano durante a Noite."),
    "K_S": ArtifactDefinition("K_S", "K", "S", "Véu das Caçadoras da Meia-Noite",
        "Seus Heróis atacam Cidades. Aliados próximos a um Herói batem 2 vezes."),
    "J_C": ArtifactDefinition("J_C", "J", "C", "Travessura Gnômica",
        "Pule o próximo Dia e a próxima Noite de um Jogador."),
    "Q_C": ArtifactDefinition("Q_C", "Q", "C", "Maldição das Almas Acorrentadas",
        "Controle um Inimigo neste turno."),
    "K_C": ArtifactDefinition("K_C", "K", "C", "Pacto de Salomão",
        "Um aliado dá o dobro de dano e tem Resistência até ser morto. "
        "Volta à Base quando ele morre."),
}


SUIT_SYMBOL = {"H": "♥", "D": "♦", "S": "♠", "C": "♣"}


def card_display(card_id: str) -> str:
    d = ARTIFACT_CATALOG[card_id]
    return f"{d.rank}{SUIT_SYMBOL[d.suit]} {d.name}"


def get_definition(card_id: str) -> ArtifactDefinition:
    if card_id not in ARTIFACT_CATALOG:
        raise KeyError(f"Carta desconhecida: {card_id}")
    return ARTIFACT_CATALOG[card_id]


def make_full_deck() -> list[str]:
    deck: list[str] = []
    for card_id in ARTIFACT_CATALOG:
        deck.extend([card_id] * ARTIFACTS_PER_CARD_IN_SHOP)
    return deck


@dataclass
class Shop:
    deck: list[str] = field(default_factory=make_full_deck)

    def is_empty(self) -> bool:
        return not self.deck

    def size(self) -> int:
        return len(self.deck)

    def draw_random(self, rng: DeterministicRNG) -> str:
        if not self.deck:
            raise ValueError("Loja vazia.")
        idx = rng.randrange(len(self.deck))
        return self.deck.pop(idx)

    def return_card(self, card_id: str) -> None:
        self.deck.append(card_id)

    def copies_of(self, card_id: str) -> int:
        return self.deck.count(card_id)