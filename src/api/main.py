from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from src.api import schemas as s
from src.api.errors import RESPONSES, install_handlers
from src.api.routers import boolean, cbir, experiments, images, inspector, live, sharing
from src.api.state import State
from src.core.cbir import MODE_INFO
from src.data.env import PROJECT_ROOT, load_settings
from src.data.manifest import CLASSES
from src.experiments.common import BINS
from tools.build_index import MOMENT_DIMS

VERSION = "1.0"
BAND_NAMES = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"]
CHANNELS = {"gray": 1, "rgb": 3, "hsv": 3, "ms13": 13, "ndvi_ndwi": 2, "ms13_idx": 15}
CLASS_LABELS = dict(zip(CLASSES, [
    "Tanaman semusim", "Hutan", "Vegetasi herba", "Jalan raya", "Industri", "Padang rumput",
    "Tanaman tahunan", "Permukiman", "Sungai", "Laut atau danau",
]))
LABELS = dict(gray="Keabuan", rgb="RGB", hsv="HSV", ms13="13 band", ndvi_ndwi="NDVI dan NDWI",
              ms13_idx="13 band dan indeks", grid2="Grid 2 × 2", grid4="Grid 4 × 4",
              mle="MLE RGB", ms_mle="MLE multispektral")


def _round(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, list):
        return [_round(item) for item in value]
    if isinstance(value, dict):
        return {key: _round(item) for key, item in value.items()}
    return value


class RoundedJSON(JSONResponse):
    def render(self, content):
        return super().render(_round(content))


def create_app(settings=None, *, results_dir=None, dist_dir=None, gallery_dir=None):
    settings = settings or load_settings()
    results_dir = results_dir if results_dir is not None else PROJECT_ROOT / "results"
    dist_dir = dist_dir if dist_dir is not None else PROJECT_ROOT / "frontend" / "dist"
    gallery_dir = gallery_dir if gallery_dir is not None else PROJECT_ROOT / "app_assets" / "gallery"

    @asynccontextmanager
    async def lifespan(app):
        app.state.data = State(settings, results_dir, gallery_dir)
        yield

    app = FastAPI(title="CitraSatelit API", version=VERSION, lifespan=lifespan, default_response_class=RoundedJSON)
    install_handlers(app)
    if settings.app_mode == "dev":
        app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                           allow_methods=["GET", "POST"], allow_headers=["*"])

    @app.get("/api/health", response_model=s.HealthResponse, responses=RESPONSES)
    def health(request: Request):
        data = request.app.state.data
        return dict(status="ok", app_mode=settings.app_mode, index_loaded=bool(data.index),
                    n_images=len(data.ids), version=VERSION)

    @app.get("/api/meta", response_model=s.MetaResponse, responses=RESPONSES)
    def meta(request: Request):
        data = request.app.state.data
        classes = {name: {"train": 0, "test": 0} for name in CLASSES}
        gallery_size = 0
        for key in data.ids:
            info = data.meta(key)
            classes[info["cls"]][info["split"]] += 1
            gallery_size += info["in_gallery"]
        train = sum(info["train"] for info in classes.values())
        modes = [dict(mode=key, label=LABELS[key], kind=info["kind"],
                      needs_multispectral=info["needs_multispectral"], supports_bins=key in CHANNELS,
                      metrics=list(info["metrics"]), dim_fixed=MOMENT_DIMS.get(key),
                      dim_by_bins={str(b): CHANNELS[key] * b for b in BINS} if key in CHANNELS else None)
                 for key, info in MODE_INFO.items()]
        return dict(classes=list(CLASSES), class_labels_id=CLASS_LABELS, feature_modes=modes,
                    metrics=[dict(metric=key, label=label, direction=direction, formula_latex=cbir.FORMULA[key])
                             for key, label, direction in (("euclid", "Euclidean", "min"),
                                                          ("chi2", "Chi-square", "min"),
                                                          ("intersection", "Irisan histogram", "min"))],
                    bins_options=list(BINS), evidence_options=["mean_gray", "mean_ndvi", "mean_ndwi"],
                    band_names=BAND_NAMES, defaults=dict(mode="rgb", bins=32, metric="chi2", k=5),
                    limits=dict(max_upload_mb_image=2, max_upload_mb_tif=5, max_shares=8,
                                live_max_db=600, live_max_queries=100),
                    dataset=dict(n_total=len(data.ids), n_train=train, n_test=len(data.ids)-train,
                                 gallery_size=gallery_size, per_class=classes))

    for router in (images, cbir, sharing, boolean, experiments, live, inspector):
        app.include_router(router.router, prefix="/api")
    entry = dist_dir / "index.html"
    if entry.is_file():
        def frontend_shell():
            return FileResponse(entry)

        for path in ("/cbir", "/sharing", "/boolean", "/percobaan", "/inspector"):
            app.add_api_route(path, frontend_shell, methods=["GET", "HEAD"], include_in_schema=False)
    if dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")
    return app


app = create_app()
