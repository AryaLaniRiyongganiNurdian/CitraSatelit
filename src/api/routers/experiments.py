from fastapi import APIRouter, Request

from src.api import schemas as s
from src.api.errors import ApiError, RESPONSES
from src.api.state import read_json

router = APIRouter(prefix="/experiments", responses=RESPONSES)
TITLES = {"C1": "Pengaruh bin", "C2": "Metode pencarian", "C3": "Galat bit-flip",
          "C4a": "Modalitas", "C4b": "Share parsial", "C4c": "Kompleksitas"}


@router.get("", response_model=list[s.ExperimentSummary])
def list_experiments(request: Request):
    folder = request.app.state.data.results
    output = []
    for key, title in TITLES.items():
        payload = read_json(folder / f"{key}.json")
        summary = {name: payload[name] for name in ("title", "description", "generated_at")} if payload else {
            "title": title, "description": title, "generated_at": None,
        }
        output.append(dict(id=key, has_results=payload is not None, **summary))
    return output


@router.get("/{id}", response_model=s.ExperimentResult, response_model_exclude_unset=True)
def experiment(id: s.ExperimentId, request: Request):
    artifact = read_json(request.app.state.data.results / f"{id}.json")
    if artifact is None:
        raise ApiError("NOT_PRECOMPUTED", "Hasil percobaan belum tersedia.", id=id)
    return artifact
