import io
import uuid
from pathlib import Path

import numpy as np
import tifffile
from fastapi import APIRouter, File, Query, Request, UploadFile
from PIL import Image, UnidentifiedImageError
from starlette.responses import Response

from src.api import schemas as s
from src.api.errors import ApiError, RESPONSES
from src.api.inspector import preview
from src.core.spectral import ndi_to_level, ndvi, ndwi, synth_rgb

router = APIRouter(prefix="/images", responses=RESPONSES)


@router.get("", response_model=s.ImagesListResponse)
def images(request: Request, cls: s.ClassName | None = None, split: s.Split | None = None,
           gallery_only: bool = True, limit: int = Query(50, ge=1), offset: int = Query(0, ge=0)):
    data = request.app.state.data
    items = []
    for key in data.ids:
        item = data.meta(key)
        if (not gallery_only or item["in_gallery"]) and (cls is None or item["cls"] == cls) and (
            split is None or item["split"] == split
        ):
            items.append(item)
    return {"total": len(items), "items": items[offset:offset + limit]}


@router.get("/{id}/thumb", response_class=Response,
            responses={200: {"content": {"image/jpeg": {}, "image/png": {}}}})
def thumb(id: str, request: Request):
    data = request.app.state.data
    meta = data.meta(id)
    if not meta["is_upload"]:
        return Response(data.packed(id), media_type="image/jpeg")
    output = io.BytesIO()
    Image.fromarray(data.rgb(id)).save(output, format="PNG")
    return Response(output.getvalue(), media_type="image/png")


@router.get("/{id}/preview", response_model=s.ImagePreview)
def image_preview(id: str, request: Request, view: s.PreviewView = "rgb",
                  band: int = Query(0, ge=0, le=12), scale: int = Query(4, ge=1)):
    data = request.app.state.data
    if view == "rgb":
        image = data.rgb(id)
    else:
        bands = data.bands(id)
        if view == "synth_rgb":
            image = synth_rgb(bands, data.scale)
        elif view == "band":
            image = bands[..., band]
        else:
            image = ndi_to_level((ndvi if view == "ndvi" else ndwi)(bands))
    return preview(image, view, scale)


async def read_upload(file: UploadFile, limit: int):
    payload = await file.read(limit + 1)
    if len(payload) > limit:
        raise ApiError("UPLOAD_TOO_LARGE", "Ukuran berkas melebihi batas.", max_bytes=limit)
    return io.BytesIO(payload)


@router.post("/upload", response_model=s.ImageMeta)
async def upload(request: Request, file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
        raise ApiError("UNSUPPORTED_FILE", "Format citra tidak didukung.")
    tiff = suffix in (".tif", ".tiff")
    stream = await read_upload(file, (5 if tiff else 2) * 1024**2)
    rgb = bands = None
    if tiff:
        try:
            with tifffile.TiffFile(stream) as image:
                series = image.series[0]
                axes = [i for i, value in enumerate(series.shape) if value == 13]
                if len(series.shape) != 3 or len(axes) != 1 or series.dtype.kind != "u" or series.dtype.itemsize != 2:
                    raise ApiError("TIF_NOT_13_BANDS", "TIFF harus berisi 13 band uint16.")
                if max(series.shape) > 1024:
                    raise ApiError("UPLOAD_TOO_LARGE", "Sisi citra melebihi 1024 piksel.")
                bands = np.moveaxis(series.asarray(), axes[0], -1).astype(np.uint16, copy=False)
        except (ValueError, OSError, IndexError, tifffile.TiffFileError) as exc:
            raise ApiError("TIF_NOT_13_BANDS", "Data TIFF 13 band tidak dapat dibaca.") from exc
    else:
        try:
            with Image.open(stream, formats=["JPEG", "PNG"]) as image:
                if max(image.size) > 1024:
                    raise ApiError("UPLOAD_TOO_LARGE", "Sisi citra melebihi 1024 piksel.")
                rgb = np.array(image.convert("RGB"))
        except Image.DecompressionBombError as exc:
            raise ApiError("UPLOAD_TOO_LARGE", "Sisi citra melebihi batas.") from exc
        except (UnidentifiedImageError, OSError) as exc:
            raise ApiError("UNSUPPORTED_FILE", "Data JPG atau PNG tidak dapat dibaca.") from exc
    return request.app.state.data.add_upload(f"up_{uuid.uuid4().hex[:8]}", rgb, bands)
