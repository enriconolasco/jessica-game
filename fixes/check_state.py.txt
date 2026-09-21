"""check_state: mostra o que esta aplicado no projeto."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

print(f"Projeto: {ROOT}\n")

try:
    from jessica.core.models import Player, GameState
    from jessica.core import combat
    print("=== Estado do motor ===")
    print(f"Player.stats              {'OK' if 'stats' in Player.__dataclass_fields__ else 'FALTA'}")
    print(f"GameState.timeline        {'OK' if 'timeline' in GameState.__dataclass_fields__ else 'FALTA'}")
    print(f"Player.garoche_life_max_bonus  {'OK' if 'garoche_life_max_bonus' in Player.__dataclass_fields__ else 'FALTA'}")
    print(f"Player.armor_active_until_turn {'OK' if 'armor_active_until_turn' in Player.__dataclass_fields__ else 'FALTA'}")
    print(f"Player.zebum_seven_dwarves     {'OK' if 'zebum_seven_dwarves' in Player.__dataclass_fields__ else 'FALTA'}")
    print(f"combat.set_armor_choice_fn     {'OK' if hasattr(combat, 'set_armor_choice_fn') else 'FALTA'}")
except Exception as e:
    print(f"Erro ao importar core: {e}")
    sys.exit(1)

try:
    from jessica import main as m
    print("\n=== Estado da UI ===")
    for name in ("show_hud", "show_board", "show_turn_log",
                 "_menu_analisar", "_menu_sistema", "_menu_ajuda",
                 "_menu_relatorios", "_menu_acoes_turno", "_menu_artefatos",
                 "_do_action", "handle_action", "_ajuda_tutorial"):
        print(f"main.{name:22s} {'OK' if hasattr(m, name) else 'FALTA'}")
except Exception as e:
    print(f"\nErro ao importar main: {e}")