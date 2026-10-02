"""Exercita o atualizador em clones descartáveis, sem tocar nas instalações."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = "https://github.com/enriconolasco/jessica-game.git"


def git(directory, *args):
    return subprocess.check_output(["git", "-C", str(directory), *args],
        stderr=subprocess.STDOUT, text=True).strip()


def exercise(mode):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        remote, source, target = (root / p for p in ("remote.git", "source", "target"))
        git(root, "init", "--bare", str(remote))
        git(root, "init", "-b", "main", str(source))
        git(source, "config", "user.name", "Jessica updater test")
        git(source, "config", "user.email", "updater@example.invalid")
        shutil.copy2(ROOT / "ATUALIZAR.cmd", source / "ATUALIZAR.cmd")
        (source / "rule.txt").write_text("baseline", encoding="utf-8")
        git(source, "add", ".")
        git(source, "commit", "-m", "test baseline")
        git(source, "remote", "add", "origin", str(remote))
        git(source, "push", "origin", "main")
        git(root, "clone", "--branch", "main", str(remote), str(target))
        git(target, "remote", "set-url", "origin", OFFICIAL)
        git(target, "config", f"url.{remote.as_posix()}.insteadOf", OFFICIAL)
        old = git(target, "rev-parse", "HEAD")
        (target / "local-save.json").write_text("keep", encoding="utf-8")
        if mode == "dirty":
            (target / "rule.txt").write_text("local change", encoding="utf-8")
        elif mode == "divergent":
            git(target, "config", "user.name", "Jessica updater test")
            git(target, "config", "user.email", "updater@example.invalid")
            (target / "local.txt").write_text("local commit", encoding="utf-8")
            git(target, "add", "local.txt")
            git(target, "commit", "-m", "local work")
            old = git(target, "rev-parse", "HEAD")
        (source / "rule.txt").write_text("updated", encoding="utf-8")
        git(source, "add", "rule.txt")
        git(source, "commit", "-m", "shared patch")
        git(source, "push", "origin", "main")
        run = subprocess.run(["cmd", "/d", "/c", "ATUALIZAR.cmd", "--no-pause"],
                             cwd=target, capture_output=True, timeout=30)
        assert (target / "local-save.json").read_text(encoding="utf-8") == "keep"
        if mode == "clean":
            assert run.returncode == 0, run.stdout
            assert git(target, "rev-parse", "HEAD") == git(source, "rev-parse", "HEAD")
            assert (target / "rule.txt").read_text(encoding="utf-8") == "updated"
            again = subprocess.run(["cmd", "/d", "/c", "ATUALIZAR.cmd", "--no-pause"],
                                   cwd=target, capture_output=True, timeout=30)
            assert again.returncode == 0
        else:
            assert run.returncode != 0
            assert git(target, "rev-parse", "HEAD") == old
            if mode == "dirty":
                assert (target / "rule.txt").read_text(encoding="utf-8") == "local change"


def test_clean_clone_updates_and_preserves_local_save():
    if os.name == "nt":
        exercise("clean")


def test_dirty_clone_is_not_overwritten():
    if os.name == "nt":
        exercise("dirty")


def test_divergent_commits_are_not_discarded():
    if os.name == "nt":
        exercise("divergent")


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test(); passed += 1
            except Exception as exc:
                failed += 1; print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(bool(failed))
