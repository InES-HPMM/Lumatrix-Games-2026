"""Prueft, dass die Einreichung nur lesbaren Sourcecode enthaelt."""

import os


FORBIDDEN_DIRECTORIES = {".venv", "__pycache__", ".pytest_cache"}
FORBIDDEN_SUFFIXES = {
    ".pyc", ".pyo", ".exe", ".dll", ".dylib", ".so", ".class", ".jar",
}


def forbidden_paths(root):
    problems = []
    for directory, names, files in os.walk(root):
        blocked = [name for name in names if name in FORBIDDEN_DIRECTORIES]
        for name in blocked:
            problems.append(os.path.relpath(os.path.join(directory, name), root))
            names.remove(name)
        for name in files:
            if os.path.splitext(name)[1].lower() in FORBIDDEN_SUFFIXES:
                problems.append(os.path.relpath(os.path.join(directory, name), root))
    return sorted(problems)


if __name__ == "__main__":
    project = os.path.dirname(os.path.abspath(__file__))
    problems = forbidden_paths(project)
    if problems:
        print("Nicht erlaubte Dateien:")
        for problem in problems:
            print("-", problem)
        raise SystemExit(1)
    print("OK: nur lesbarer Sourcecode und Dokumentation enthalten.")

