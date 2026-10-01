"""A automação não pode tratar testes quebrados como execução bem-sucedida."""
import contextlib
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("suite_runner", Path(__file__).with_name("run_all.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def run(output, returncode=0, files=None):
    completed = SimpleNamespace(stdout=output, stderr="", returncode=returncode)
    with patch.object(runner, "TEST_FILES", [Path("sample.py")] if files is None else files), \
            patch.object(runner.subprocess, "run", return_value=completed), \
            contextlib.redirect_stdout(io.StringIO()):
        return runner.main()


def test_sucesso_retorna_zero():
    assert run("3 passaram, 0 falharam") == 0


def test_falha_reportada_retorna_erro_mesmo_se_script_retornar_zero():
    assert run("2 passaram, 1 falharam") == 1


def test_crash_apos_contagem_verde_retorna_erro():
    assert run("3 passaram, 0 falharam", returncode=2) == 1


def test_sem_contagem_retorna_erro():
    assert run("Traceback: ValueError", returncode=1) == 1


def test_suite_vazia_nao_certifica_sucesso():
    assert run("", files=[]) == 1


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test()
                passed += 1
            except Exception as exc:
                failed += 1
                print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(1 if failed else 0)
