import json
import re
from pathlib import Path

from src.api import schemas
from src.api.main import create_app

DOCS = Path(__file__).resolve().parents[1] / "docs"


def test_contract_examples_validate_with_pydantic():
    text = (DOCS / "api-contract.md").read_text(encoding="utf-8")
    examples = [json.loads(block) for block in re.findall(r"```json\s*(.*?)```", text, re.S)]
    models = (schemas.ApiErrorBody, schemas.Inspector, schemas.SearchRequest, schemas.SearchResponse,
              schemas.SplitRequest, schemas.SplitResponse, schemas.KMapRequest)
    assert len(examples) == len(models)
    for model, example in zip(models, examples):
        model.model_validate(example)


def test_documented_responses_are_declared_and_ts_files_exact():
    contract = (DOCS / "api-contract.md").read_text(encoding="utf-8")
    openapi = create_app().openapi()
    for method, path, response, _ in re.findall(r"\| `(GET|POST) ([^`]+)` \| [^\n]+? \| `(\w+)(\[\])?` \|", contract):
        route = re.sub(r"\{id\}", "{id}", path)
        schema = openapi["paths"][f"/api{route}"][method.lower()]["responses"]["200"]["content"]["application/json"]["schema"]
        if schema.get("type") == "array":
            schema = schema["items"]
        assert schema["$ref"].endswith("/" + response)
    handoff = (DOCS / "frontend-handoff.md").read_text(encoding="utf-8")
    root = DOCS.parent
    for path, expected in re.findall(r"## `(frontend/src/[^\x60]+)`\s*```ts\n(.*?)```", handoff, re.S):
        assert (root / path).read_text(encoding="utf-8") == expected
