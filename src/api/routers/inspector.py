import numpy as np
from fastapi import APIRouter, Request

from src.api import schemas as s
from src.api.errors import ApiError, RESPONSES
from src.api.inspector import explain
from src.core.secret_sharing import reconstruct_xor, split_xor

router = APIRouter(prefix="/inspector", responses=RESPONSES)


@router.post("/pixel-xor", response_model=s.PixelXorResponse, response_model_exclude_unset=True)
def pixel_xor(req: s.PixelXorRequest, request: Request):
    data = request.app.state.data
    if not 2 <= req.n <= 8:
        raise ApiError("INVALID_PARAM", "Jumlah share harus 2 sampai 8.")
    if isinstance(req.channel, int):
        source = data.source(req.image_id, "band", req.channel)
    elif req.channel == "gray":
        source = data.source(req.image_id, "gray")
    else:
        source = data.rgb(req.image_id)[..., "rgb".index(req.channel)]
    if not (0 <= req.y < source.shape[0] and 0 <= req.x < source.shape[1]):
        raise ApiError("INVALID_PARAM", "Koordinat piksel di luar citra.")
    original = source[req.y, req.x]
    bits = np.iinfo(source.dtype).bits
    shares = split_xor(original, req.n, np.random.default_rng(data.settings.seed if req.seed is None else req.seed))
    restored = int(reconstruct_xor(shares))
    value = int(original)
    value_bin = f"{value:0{bits}b}"
    share_rows = [dict(index=i, value=int(share), bin=f"{int(share):0{bits}b}") for i, share in enumerate(shares)]
    xor_terms = r" \oplus ".join(rf"\mathtt{{{row['bin']}}}" for row in share_rows)
    detail = {
        "binary": {"values": {"nilai": value, "biner": value_bin, "bit": bits}},
        "xor": {"latex_template": r"S = S_1 \oplus \dots \oplus S_n",
                "latex_substituted": rf"{xor_terms} = \mathtt{{{restored:0{bits}b}}}"},
        "reconstruct": {"values": {"hasil XOR": restored}},
    }
    return dict(value=value, value_bin=value_bin, shares=share_rows, reconstructed=restored, ok=restored == value,
                inspector=explain("XOR piksel", "binary", "xor", "reconstruct", detail=detail))
