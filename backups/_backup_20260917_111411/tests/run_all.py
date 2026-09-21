"""Roda toda a bateria de testes. Salve em tests/."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
TEST_FILES = sorted(HERE.glob("test_*.py"))


def main():
    print(f"Encontrados {len(TEST_FILES)} arquivos de teste.\n")
    total_pass = 0
    total_fail = 0
    failed_files = []
    for tf in TEST_FILES:
        print(f"--- {tf.name} ---")
        result = subprocess.run(
            [sys.executable, str(tf)],
            capture_output=True, text=True, cwd=HERE.parent,
        )
        out = result.stdout + result.stderr
        # Extrai contagens
        import re
        m = re.search(r"(\d+) passaram, (\d+) falharam", out)
        if m:
            p, f = int(m.group(1)), int(m.group(2))
            total_pass += p
            total_fail += f
            if f > 0:
                failed_files.append(tf.name)
            print(f"  {p} passaram, {f} falharam")
        else:
            total_fail += 1
            failed_files.append(tf.name)
            print(f"  ERRO (sem contagem)")
            print(out[-500:])
    print()
    print(f"TOTAL: {total_pass} passaram, {total_fail} falharam")
    if failed_files:
        print(f"Arquivos com falha: {', '.join(failed_files)}")


if __name__ == "__main__":
    main()
