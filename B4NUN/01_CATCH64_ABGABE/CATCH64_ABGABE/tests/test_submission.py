import ast
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import check_submission


class SubmissionTest(unittest.TestCase):
    def test_no_compiled_or_runtime_files(self):
        # Der laufende unittest-Prozess erzeugt seine eigenen __pycache__-Ordner.
        # Alle anderen Binaer- oder Laufzeitdateien bleiben trotzdem verboten;
        # die separate Abgabepruefung kontrolliert nach dem Aufraeumen auch Caches.
        problems = [
            path for path in check_submission.forbidden_paths(ROOT)
            if "__pycache__" not in path
        ]
        self.assertEqual(problems, [])

    def test_all_python_source_parses(self):
        for directory, names, files in os.walk(ROOT):
            names[:] = [name for name in names if name not in {".venv", "__pycache__"}]
            for filename in files:
                if filename.endswith(".py"):
                    path = os.path.join(directory, filename)
                    with open(path, "r", encoding="utf-8") as handle:
                        ast.parse(handle.read(), filename=path)


if __name__ == "__main__":
    unittest.main()
