"""apply_fix_v5b1b: atualiza contagens em test_sanity.py pos-v5a."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5b1b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}


def _patch_sanity(original: str) -> str:
    # 31 -> 37 herois, 8 -> 10 feiticos
    new = original.replace("Esperado 31 herois", "Esperado 37 herois")
    new = new.replace("Esperado 8 feiticos", "Esperado 10 feiticos")
    new = new.replace("esperado 31 herois", "esperado 37 herois")
    new = new.replace("esperado 8 feiticos", "esperado 10 feiticos")
    new = new.replace("== 31", "== 37")
    new = new.replace("== 8", "== 10")
    new = new.replace("!= 31", "!= 37")
    new = new.replace("!= 8", "!= 10")
    new = new.replace("len(HERO_CATALOG) == 31", "len(HERO_CATALOG) == 37")
    new = new.replace("len(SPELL_CATALOG) == 8", "len(SPELL_CATALOG) == 10")
    return new


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    target = ROOT / "tests" / "test_sanity.py"
    if not target.exists():
        print(f"ERRO: {target} nao existe.")
        return

    original = target.read_text(encoding="utf-8")
    patched = _patch_sanity(original)

    if patched == original:
        print("Nenhuma substituicao textual funcionou.")
        print("Abra tests/test_sanity.py e ajuste manualmente para 37 herois / 10 feiticos.")
        return

    backup_path = BACKUP_DIR / "tests" / "test_sanity.py"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup_path)
    target.write_text(patched, encoding="utf-8")
    print(f"OK  - tests/test_sanity.py")
    print(f"Backup: {BACKUP_DIR}")


if __name__ == "__main__":
    main()