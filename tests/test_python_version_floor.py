"""Every tracked Python file must parse on the CI interpreter's version.

This exists because a real failure got through: two f-strings using PEP 701
syntax (a newline inside a replacement field; nested same-type quotes) parsed
fine on the developer's Python 3.12+ and were SyntaxErrors on the 3.11 CI
runners. Local validation was fully green while CI was red, which is the worst
shape for a check to be in -- the feedback arrives after a push instead of
before one.

`ast.parse(..., feature_version=...)` reproduces the older grammar on a newer
interpreter, so this closes the gap without anyone needing 3.11 installed.
"""
import ast
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# Keep in step with .github/workflows/quality.yml's setup-python version.
CI_PYTHON = (3, 11)


class TestPythonVersionFloor(unittest.TestCase):
    def test_every_tracked_file_parses_on_the_ci_interpreter(self):
        tracked = subprocess.check_output(
            ["git", "ls-files", "*.py"], text=True, cwd=ROOT).split()
        self.assertTrue(tracked, "expected tracked Python files")

        failures = []
        for relative in tracked:
            path = ROOT / relative
            if not path.exists():
                continue
            try:
                ast.parse(
                    path.read_text(encoding="utf-8"),
                    filename=relative,
                    feature_version=CI_PYTHON,
                )
            except SyntaxError as error:
                failures.append(f"{relative}:{error.lineno}: {error.msg}")

        self.assertEqual(
            failures, [],
            "These parse on this interpreter but not on Python "
            f"{CI_PYTHON[0]}.{CI_PYTHON[1]}, which CI uses:\n  "
            + "\n  ".join(failures))


if __name__ == "__main__":
    unittest.main()
