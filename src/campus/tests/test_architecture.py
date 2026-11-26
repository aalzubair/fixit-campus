"""Automatic check of the layered architecture rules in CLAUDE.md.

Each module of the campus app may import only the project modules listed
for it below. Imports go downwards only and never skip a layer.
"""

import ast
import shutil
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from campus import constants

APP_DIR = Path(__file__).resolve().parent.parent
APP_PACKAGE = "campus"

# The "May import" column of the CLAUDE.md table. urls.py also needs views.py
# because Django routes URLs to views; both are in the Presentation layer.
ALLOWED_IMPORTS = {
    "views": frozenset({"forms", "services", "constants"}),
    "urls": frozenset({"views", "constants"}),
    "middleware": frozenset({"constants"}),
    "forms": frozenset({"constants"}),
    "services": frozenset({"models", "delivery", "records", "constants"}),
    "models": frozenset({"constants"}),
    "delivery": frozenset({"constants"}),
    "records": frozenset({"constants"}),
    "constants": frozenset(),
    "apps": frozenset(),
}
IMMUTABLE_TYPES = (str, int, tuple, frozenset)
# Views could reach the database without importing models (get_user_model()),
# so the import check alone cannot catch this.
FORBIDDEN_VIEW_CODE = (".objects", ".save(")

# A views module that breaks the rules in each import style.
FORBIDDEN_VIEWS_SOURCE = """
import campus.models
from campus.records import find_member
from . import delivery
from .services import register_user
import os
"""

# A module that names constants in a docstring and a comment but uses only one.
DOCSTRING_AND_COMMENT_SOURCE = '''
"""Mentions MSG_IN_DOCSTRING."""
# Mentions MSG_IN_COMMENT.
print(MSG_IN_CODE, settings.MSG_AS_ATTRIBUTE)
'''


def app_modules() -> dict[str, Path]:
    """Find the Python modules of the app (not tests, not migrations).

    Returns:
        Module names mapped to their file paths.
    """
    return {path.stem: path for path in APP_DIR.glob("*.py") if path.stem != "__init__"}


def project_imports(path: Path) -> set[str]:
    """List the campus modules imported by a file.

    Handles ``import campus.x``, ``from campus.x import y``,
    ``from campus import x`` and relative imports.

    Args:
        path: The Python file to read.

    Returns:
        Names of the campus modules the file imports.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                # A relative import inside the app is an import from campus.
                module = f"{APP_PACKAGE}.{module}".rstrip(".")
            names = [module] + [f"{module}.{alias.name}" for alias in node.names]
        else:
            continue
        for name in names:
            parts = name.split(".")
            if parts[0] == APP_PACKAGE and len(parts) > 1:
                found.add(parts[1])
    return found


def names_used_in_code(path: Path) -> set[str]:
    """List the names a file reads in its code.

    Docstrings and comments are not code, so a name that appears only
    there is not a use. Assignments (like the definitions in
    ``constants.py``) are not uses either; reading a name or an
    attribute is.

    Args:
        path: The Python file to read.

    Returns:
        Every name read as a variable or an attribute.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
    return used


class ArchitectureTests(SimpleTestCase):
    """The dependency table and the constants rules are respected."""

    def test_every_module_has_a_rule(self) -> None:
        """A new module must be added to ALLOWED_IMPORTS on purpose."""
        self.assertEqual(set(app_modules()), set(ALLOWED_IMPORTS))

    def test_modules_import_only_allowed_layers(self) -> None:
        """No module imports upwards or skips a layer."""
        modules = app_modules()
        for name, path in modules.items():
            with self.subTest(module=name):
                imported = project_imports(path) & set(modules)
                self.assertLessEqual(imported, ALLOWED_IMPORTS[name])

    def test_parser_finds_forbidden_imports(self) -> None:
        """The check itself works: every import style is detected."""
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        bad_module = Path(temp_dir) / "bad_views.py"
        bad_module.write_text(FORBIDDEN_VIEWS_SOURCE, encoding="utf-8")
        forbidden = project_imports(bad_module) - ALLOWED_IMPORTS["views"]
        self.assertEqual(forbidden, {"models", "records", "delivery"})

    def test_views_do_not_touch_the_database_directly(self) -> None:
        """views.py has no ``.objects`` and no ``.save(``; services do that."""
        views_source = app_modules()["views"].read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_VIEW_CODE:
            with self.subTest(code=forbidden):
                self.assertNotIn(forbidden, views_source)

    def test_constants_are_immutable(self) -> None:
        """Every constant is a str, int, tuple or frozenset."""
        for name in dir(constants):
            if name.isupper():
                with self.subTest(constant=name):
                    value = getattr(constants, name)
                    self.assertIsInstance(value, IMMUTABLE_TYPES)

    def test_every_constant_is_used(self) -> None:
        """Every constant is read by app code (docstrings and comments do not count)."""
        used = set()
        for path in APP_DIR.glob("*.py"):
            used |= names_used_in_code(path)
        for name in dir(constants):
            if name.isupper():
                with self.subTest(constant=name):
                    self.assertIn(name, used)

    def test_usage_check_ignores_docstrings_and_comments(self) -> None:
        """The usage check itself works: only names in code are found."""
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        sample = Path(temp_dir) / "sample.py"
        sample.write_text(DOCSTRING_AND_COMMENT_SOURCE, encoding="utf-8")
        used = names_used_in_code(sample)
        self.assertIn("MSG_IN_CODE", used)
        self.assertIn("MSG_AS_ATTRIBUTE", used)
        self.assertNotIn("MSG_IN_DOCSTRING", used)
        self.assertNotIn("MSG_IN_COMMENT", used)
