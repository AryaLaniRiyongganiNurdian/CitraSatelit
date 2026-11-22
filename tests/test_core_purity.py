import ast
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[1] / "src" / "core"
FORBIDDEN_IMPORTS = {"scipy", "sklearn", "cv2", "PIL", "tifffile", "skimage", "colorsys"}
FORBIDDEN_NUMPY = {"corrcoef", "cov", "var", "std", "percentile", "quantile"}


def forbidden_numpy(name):
    return name.startswith("histogram") or name in FORBIDDEN_NUMPY


def test_core_avoids_forbidden_imports_and_numpy_functions():
    assert CORE_DIR.is_dir()
    violations = []
    for path in sorted(CORE_DIR.rglob("*.py")):
        nodes = list(ast.walk(ast.parse(path.read_text(encoding="utf-8"))))
        numpy_names = {"np", "numpy"}
        for node in nodes:
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name.split(".")[0] in FORBIDDEN_IMPORTS:
                        violations.append((path, node.lineno, name.name))
                    if name.name == "numpy":
                        numpy_names.add(name.asname or name.name)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                module = node.module or ""
                if module.split(".")[0] in FORBIDDEN_IMPORTS:
                    violations.append((path, node.lineno, module))
                if module == "numpy":
                    for name in node.names:
                        if forbidden_numpy(name.name) or name.name == "*":
                            violations.append((path, node.lineno, name.name))

        for node in nodes:
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in numpy_names
                and forbidden_numpy(node.attr)
            ):
                violations.append((path, node.lineno, node.attr))

    assert not violations, "\n".join(f"{path}:{line}: {name}" for path, line, name in violations)
