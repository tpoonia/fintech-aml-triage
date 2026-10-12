"""Leakage guard R1: decision-time code must not import label-generation or evaluation code."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
FORBIDDEN = ("qtrace.counterfactual", "qtrace.evaluation")
GUARDED_PACKAGES = ("qtrace.features", "qtrace.policies")
EXEMPT_MODULE_PREFIXES = ("qtrace.policies.oracle",)  # evaluation-only, non-deployable


def module_name(path: Path) -> str:
    parts = path.relative_to(SRC).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def imported_modules(source: str, module: str, is_package: bool) -> set[str]:
    package = module if is_package else module.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)]
                target = ".".join([*base, node.module] if node.module else base)
            else:
                target = node.module or ""
            found.add(target)
            found.update(f"{target}.{alias.name}" for alias in node.names)
    return found


def violations(source: str, module: str, is_package: bool = False) -> set[str]:
    return {
        imp
        for imp in imported_modules(source, module, is_package)
        if any(imp == f or imp.startswith(f + ".") for f in FORBIDDEN)
    }


def test_guarded_packages_do_not_import_label_generation():
    checked = 0
    for path in sorted(SRC.rglob("*.py")):
        module = module_name(path)
        if not module.startswith(GUARDED_PACKAGES) or module.startswith(EXEMPT_MODULE_PREFIXES):
            continue
        checked += 1
        bad = violations(path.read_text(), module, path.name == "__init__.py")
        assert not bad, f"{module} imports forbidden modules: {sorted(bad)}"
    assert checked >= 2  # features/ and policies/ exist


def test_checker_detects_absolute_and_relative_imports():
    assert violations("import qtrace.counterfactual", "qtrace.features.x")
    assert violations("from qtrace.evaluation import metrics", "qtrace.policies.x")
    assert violations("from ..counterfactual import run", "qtrace.policies.x")
    assert violations("from .. import evaluation", "qtrace.features.x")
    assert not violations("from qtrace.config import load_yaml", "qtrace.features.x")
