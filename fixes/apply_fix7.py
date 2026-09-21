"""apply_fix7: run_all imprime output completo dos testes que falham."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.resolve()
BACKUP_DIR = ROOT / f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

FILES["tests/run_all.py"] = '''\
"""Roda toda a bateria de testes. Salve em tests/."""
import subprocess
import sys
import re
from pathlib import Path

HERE = Path(__file__).parent.resolve()
TEST_FILES = sorted(HERE.glob("test_*.py"))


def main():
    print(f"Encontrados {len(TEST_FILES)} arquivos de teste.\\n")
    total_pass = 0
    total_fail = 0
    failed_files = []
    for tf in TEST_FILES:
        result = subprocess.run(
            [sys.executable, str(tf)],
            capture_output=True, text=True, cwd=HERE.parent,
        )
        out = result.stdout + result.stderr
        m = re.search(r"(\\d+) passaram, (\\d+) falharam", out)
        if m:
            p, f = int(m.group(1)), int(m.group(2))
            total_pass += p
            total_fail += f
            status = "OK " if f == 0 else "FAIL"
            print(f"[{status}] {tf.name}: {p}/{p+f}")
            if f > 0:
                failed_files.append(tf.name)
                print("  --- output completo ---")
                for line in out.splitlines():
                    print(f"  | {line}")
                print("  -----------------------")
        else:
            total_fail += 1
            failed_files.append(tf.name)
            print(f"[ERRO] {tf.name}: sem contagem (sintaxe ou crash)")
            print("  --- output completo ---")
            for line in out.splitlines():
                print(f"  | {line}")
            print("  -----------------------")
    print()
    print(f"TOTAL: {total_pass} passaram, {total_fail} falharam")
    if failed_files:
        print(f"Arquivos com falha: {', '.join(failed_files)}")


if __name__ == "__main__":
    main()
'''

def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for rel_path, content in FILES.items():
        full = ROOT / rel_path
        if full.exists():
            backup_path = BACKUP_DIR / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, backup_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        print(f"OK  - {rel_path}")
    print(f"\\n{len(FILES)} arquivos escritos.")
    print(f"Backup: {BACKUP_DIR}")


if __name__ == "__main__":
    main()