from dataclasses import dataclass

@dataclass
class Card:
    id: int = ''
    name: str = ''
    rarity: str = ''
    type: str = ''
    attribute: str = ''
    cost: str = ''
    power: str = ''
    counter: str = ''
    color: str = ''
    card_type: str = ''
    effect: str = ''
    image_url: str = ''
    alternate_art: bool = ''
    series_id: int = ''
    series_name: str = ''