import ast
import json
from pathlib import Path

import nbformat

from tools.build_notebook import build

ROOT = Path(__file__).resolve().parents[1]


def test_notebook_is_deterministic_matches_core_and_supports_both_modes(tmp_path):
    first = tmp_path / "demo.ipynb"
    build(first)
    assert first.read_bytes() == (ROOT / "notebooks/citrasatelit.ipynb").read_bytes()
    notebook = json.loads(first.read_bytes())
    nbformat.validate(nbformat.read(first, as_version=4))
    assert notebook["nbformat"] == 4
    assert len({cell["id"] for cell in notebook["cells"]}) == len(notebook["cells"])
    source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert "colab_instant" in source and "full_local" in source and "D:\\\\" not in source
    core = {}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            tree = ast.parse("".join(cell["source"]))
            if "core-generated" in cell["metadata"].get("tags", []):
                assignment = tree.body[0]
                core[ast.literal_eval(assignment.targets[0].slice)] = ast.literal_eval(assignment.value)
    assert core == {file.relative_to(ROOT).as_posix(): file.read_text(encoding="utf-8")
                    for file in (ROOT / "src/core").glob("*.py")}
