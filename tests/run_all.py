"""Roda toda a bateria de testes."""
import subprocess
import sys
import os
import re
from pathlib import Path

HERE = Path(__file__).parent.resolve()
TEST_FILES = sorted(HERE.glob("test_*.py"))


def main():
    print(f"Encontrados {len(TEST_FILES)} arquivos de teste.\n")
    total_pass = 0
    total_fail = 0
    failed_files = []
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for tf in TEST_FILES:
        result = subprocess.run(
            [sys.executable, str(tf)],
            capture_output=True, text=True, cwd=HERE.parent, env=env,
            encoding="utf-8", errors="replace",
        )
        out = (result.stdout or "") + (result.stderr or "")
        m = re.search(r"(\d+) passaram, (\d+) falharam", out)
        if m:
            p, f = int(m.group(1)), int(m.group(2))
            total_pass += p
            total_fail += f
            status = "OK " if f == 0 else "FAIL"
            print(f"[{status}] {tf.name}: {p}/{p+f}")
            if f > 0:
                failed_files.append(tf.name)
                print("  --- output ---")
                for line in out.splitlines():
                    if line.startswith("FALHOU"):
                        print(f"  | {line}")
        else:
            total_fail += 1
            failed_files.append(tf.name)
            print(f"[ERRO] {tf.name}: sem contagem")
            for line in out.splitlines():
                if "Error" in line or "Exception" in line:
                    print(f"  | {line}")
                    break
    print()
    print(f"TOTAL: {total_pass} passaram, {total_fail} falharam")
    if failed_files:
        print(f"Arquivos com falha: {', '.join(failed_files)}")


if __name__ == "__main__":
    main()
