"""apply_fix_v5v10_11b: garante devaneio_ativo_turn + adapta testes ao novo contrato."""
from pathlib import Path
from datetime import datetime
import os
import re
import shutil

def _find_project_root() -> Path:
    env = os.environ.get("JESSICA_ROOT")
    if env:
        p = Path(env)
        if (p / "jessica" / "main.py").exists():
            return p
    candidates = [
        Path.home() / "Downloads" / "jessica",
        Path.home() / "jessica",
        Path.cwd(),
        Path(__file__).resolve().parent.parent,
    ]
    for c in candidates:
        if (c / "jessica" / "main.py").exists():
            return c
    return Path.home() / "Downloads" / "jessica"

ROOT = _find_project_root()
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v10_11b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _patch_models() -> bool:
    full = ROOT / "jessica" / "core" / "models.py"
    if not full.exists():
        print("AVISO - models.py nao existe.")
        return False
    txt = full.read_text(encoding="utf-8")
    if "devaneio_ativo_turn" in txt:
        print("OK  - devaneio_ativo_turn ja existe em models.py")
        return True
    # Tenta dois anchors, na ordem
    for anchor in (
        "    miyamoto_life_max_bonus: int = 0\n",
        "    garoche_life_max_bonus: int = 0\n",
        "    zebum_seven_dwarves: bool = False\n",
    ):
        if anchor in txt:
            new = anchor + "    devaneio_ativo_turn: int = -1\n"
            txt = txt.replace(anchor, new, 1)
            break
    else:
        print("AVISO - nenhum anchor encontrado em models.py.")
        return False
    backup = BACKUP_DIR / "jessica" / "core" / "models.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print("OK  - models.py: devaneio_ativo_turn adicionado")
    return True


def _patch_serialize() -> bool:
    full = ROOT / "jessica" / "core" / "serialize.py"
    if not full.exists():
        print("AVISO - serialize.py nao existe.")
        return False
    txt = full.read_text(encoding="utf-8")
    changed = False
    if "devaneio_ativo_turn" not in txt:
        for anchor in (
            '        "miyamoto_life_max_bonus": p.miyamoto_life_max_bonus,\n',
            '        "garoche_life_max_bonus": p.garoche_life_max_bonus,\n',
        ):
            if anchor in txt:
                txt = txt.replace(
                    anchor,
                    anchor + '        "devaneio_ativo_turn": p.devaneio_ativo_turn,\n',
                    1,
                )
                changed = True
                break
        for anchor in (
            '        miyamoto_life_max_bonus=d.get("miyamoto_life_max_bonus", 0),\n',
            '        garoche_life_max_bonus=d.get("garoche_life_max_bonus", 0),\n',
        ):
            if anchor in txt:
                txt = txt.replace(
                    anchor,
                    anchor + '        devaneio_ativo_turn=d.get("devaneio_ativo_turn", -1),\n',
                    1,
                )
                changed = True
                break
    if not changed:
        print("OK  - serialize.py ja tem devaneio ou nao precisou mudar")
        return True
    backup = BACKUP_DIR / "jessica" / "core" / "serialize.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print("OK  - serialize.py atualizado")
    return True


def _patch_test_sonho_lucido() -> bool:
    full = ROOT / "tests" / "test_sonho_lucido.py"
    if not full.exists():
        print("AVISO - test_sonho_lucido.py nao existe.")
        return False
    txt = full.read_text(encoding="utf-8")
    original = txt

    # 1. test_sonho_lucido_flips_played_artifact
    txt = txt.replace(
        '''\
    p.city.magic = 10
    cast_spell(state, 4)
    assert p.sonho_lucido_pending_turn == state.turn
    # Coloca um K_H na mão e joga
    p.hand.append("K_H")
    play_artifact(state, 4, "K_H")
    # Deve ter virado K_D no campo
    field_ids = [a.card_id for a in p.field_artifacts]
    assert "K_D" in field_ids, f"K_H deveria ter virado K_D, campo: {field_ids}"
    print("OK  - Sonho Lucido trocou K_H para K_D ao jogar")''',
        '''\
    p.city.magic = 10
    p.hand.append("K_H")
    cast_spell(state, 4, choice={"flip_cards": ["K_H"]})
    # K_H deve ter sido invertido para K_D E jogado automaticamente
    field_ids = [a.card_id for a in p.field_artifacts]
    assert "K_D" in field_ids, f"K_H deveria ter virado K_D, campo: {field_ids}"
    print("OK  - Sonho Lucido inverteu e jogou K_D imediatamente")'''
    )

    # 2. test_sonho_lucido_only_that_turn
    txt = txt.replace(
        '''\
    p.city.magic = 10
    cast_spell(state, 4)
    # "Avança" turno manualmente
    state.turn += 1
    p.hand.append("K_H")
    play_artifact(state, 4, "K_H")
    field_ids = [a.card_id for a in p.field_artifacts]
    assert "K_H" in field_ids, f"K_H nao deveria ter virado em outro turno, campo: {field_ids}"
    print("OK  - Sonho Lucido so vale naquele turno")''',
        '''\
    p.city.magic = 10
    p.hand.append("K_H")
    cast_spell(state, 4, choice={"flip_cards": ["K_H"]})
    state.turn += 1
    # Novo K_H no proximo turno deve jogar normal, sem inverter
    p.hand.append("K_H")
    play_artifact(state, 4, "K_H")
    field_ids = [a.card_id for a in p.field_artifacts]
    assert "K_H" in field_ids, f"K_H nao deveria ter virado em outro turno, campo: {field_ids}"
    print("OK  - Sonho Lucido so vale no turno do cast")'''
    )

    if txt == original:
        print("AVISO - test_sonho_lucido.py nao mudou (snippets nao casaram).")
        return False
    backup = BACKUP_DIR / "tests" / "test_sonho_lucido.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print("OK  - test_sonho_lucido.py adaptado")
    return True


def _patch_test_valendar_luna() -> bool:
    full = ROOT / "tests" / "test_valendar_luna.py"
    if not full.exists():
        print("AVISO - test_valendar_luna.py nao existe.")
        return False
    txt = full.read_text(encoding="utf-8")
    original = txt

    # 1. test_valendar_blocks_sonho_lucido -> agora cast chama Devaneio
    txt = txt.replace(
        '''\
def test_valendar_blocks_sonho_lucido():
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    summon_hero(state, 4)
    try:
        cast_spell(state, 4)
        raise AssertionError("Deveria bloquear Sonho Lucido com Valendar viva")
    except ActionError as e:
        print(f"OK  - Valendar bloqueia Sonho Lucido: {e}")''',
        '''\
def test_valendar_usa_devaneio():
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    summon_hero(state, 4)
    cast_spell(state, 4)
    assert p4.devaneio_ativo_turn == state.turn, (
        f"Devaneio nao ativado: {p4.devaneio_ativo_turn}"
    )
    print("OK  - Valendar ativa Devaneio Onirico (nao mais Sonho Lucido)")'''
    )

    # 2. test_valendar_heart_heals_heroes
    txt = txt.replace(
        '''\
    p4.hand.append("K_H")
    play_artifact(state, 4, "K_H")
    assert val.life == val.life_max, f"Valendar deveria estar curada (1 -> {val.life})"
    print(f"OK  - Valendar C: heroi curado ao maximo ({val.life}/{val.life_max})")''',
        '''\
    cast_spell(state, 4)
    p4.hand.append("K_H")
    play_artifact(state, 4, "K_H")
    assert val.life == val.life_max, f"Valendar deveria estar curada (1 -> {val.life})"
    print(f"OK  - Devaneio + K_H: heroi curado ao maximo ({val.life}/{val.life_max})")'''
    )

    # 3. test_valendar_diamond_magic_sell
    txt = txt.replace(
        '''\
    p4.hand.append("K_D")
    play_artifact(state, 4, "K_D")
    assert p4.vender_por_magia_turn == state.turn
    print("OK  - Valendar O: vender por magia ativo")''',
        '''\
    cast_spell(state, 4)
    p4.hand.append("K_D")
    play_artifact(state, 4, "K_D")
    assert p4.vender_por_magia_turn == state.turn
    print("OK  - Devaneio + K_D: vender por magia ativo")'''
    )

    # 4. test_valendar_clubs_2_moves
    txt = txt.replace(
        '''\
    val = summon_hero(state, 4)
    p4.hand.append("K_C")
    play_artifact(state, 4, "K_C", choice={"unit_id": val.id})
    assert val.max_moves_this_turn == 2, f"Esperado 2, veio {val.max_moves_this_turn}"
    print("OK  - Valendar P: 2 movimentos ativos")''',
        '''\
    val = summon_hero(state, 4)
    cast_spell(state, 4)
    p4.hand.append("K_C")
    play_artifact(state, 4, "K_C", choice={"unit_id": val.id})
    assert val.max_moves_this_turn == 2, f"Esperado 2, veio {val.max_moves_this_turn}"
    print("OK  - Devaneio + K_C: 2 movimentos ativos")'''
    )

    # 5. test_valendar_spades_first
    txt = txt.replace(
        '''\
    summon_hero(state, 4)
    p4.hand.append("K_S")
    play_artifact(state, 4, "K_S")
    assert p4.bater_primeiro_turn == state.turn
    print("OK  - Valendar E: bater primeiro ativo")''',
        '''\
    summon_hero(state, 4)
    cast_spell(state, 4)
    p4.hand.append("K_S")
    play_artifact(state, 4, "K_S")
    assert p4.bater_primeiro_turn == state.turn
    print("OK  - Devaneio + K_S: bater primeiro ativo")'''
    )

    # 6. test_valendar_reverts_when_dead
    txt = txt.replace(
        '''\
    val.life = 0
    p4.units = [u for u in p4.units if u.is_alive()]
    assert peoples.valendar_is_alive(p4) is False
    cast_spell(state, 4)
    assert p4.sonho_lucido_pending_turn == state.turn
    print("OK  - Valendar morta: Sonho Lucido volta")''',
        '''\
    val.life = 0
    p4.units = [u for u in p4.units if u.is_alive()]
    assert peoples.valendar_is_alive(p4) is False
    p4.hand.append("K_H")
    cast_spell(state, 4, choice={"flip_cards": ["K_H"]})
    field_ids = [a.card_id for a in p4.field_artifacts]
    assert "K_D" in field_ids, f"Sem Valendar, Sonho Lucido normal. Campo: {field_ids}"
    print("OK  - Valendar morta: Sonho Lucido normal volta")'''
    )

    # 7. test_luna_multi_artifact
    txt = txt.replace(
        '''\
    luna = summon_hero(state, 4)
    assert luna.hero_id == "luna", f"Esperado luna, veio {luna.hero_id}"
    assert peoples.luna_is_alive(p4)
    cast_spell(state, 4)
    assert p4.sonho_lucido_multi_turn == state.turn,         f"Multi nao setado: {p4.sonho_lucido_multi_turn}"
    p4.hand.append("K_H")
    p4.hand.append("J_H")
    play_artifact(state, 4, "K_H")
    play_artifact(state, 4, "J_H")
    field_ids = [a.card_id for a in p4.field_artifacts]
    assert "K_D" in field_ids, f"K_H deveria ter virado K_D. Campo: {field_ids}"
    assert "J_D" in field_ids, f"J_H deveria ter virado J_D. Campo: {field_ids}"
    print("OK  - Luna: Sonho Lucido aplicou a 2 artefatos")''',
        '''\
    luna = summon_hero(state, 4)
    assert luna.hero_id == "luna", f"Esperado luna, veio {luna.hero_id}"
    assert peoples.luna_is_alive(p4)
    p4.hand.append("K_H")
    p4.hand.append("J_H")
    cast_spell(state, 4, choice={"flip_cards": ["K_H", "J_H"]})
    field_ids = [a.card_id for a in p4.field_artifacts]
    assert "K_D" in field_ids, f"K_H deveria ter virado K_D. Campo: {field_ids}"
    assert "J_D" in field_ids, f"J_H deveria ter virado J_D. Campo: {field_ids}"
    print("OK  - Luna: Sonho Lucido aplicou a 2 artefatos em sequencia")'''
    )

    if txt == original:
        print("AVISO - test_valendar_luna.py nao mudou.")
        return False
    backup = BACKUP_DIR / "tests" / "test_valendar_luna.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print("OK  - test_valendar_luna.py adaptado")
    return True


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    _patch_models()
    _patch_serialize()
    _patch_test_sonho_lucido()
    _patch_test_valendar_luna()

    print(f"\nBackup: {BACKUP_DIR}")
    print("\nRode:")
    print("  python tests\\run_all.py")


if __name__ == "__main__":
    main()