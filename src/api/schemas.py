"""Pydantic wire models for the frontend handoff."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


ClassName = Literal["AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial", "Pasture", "PermanentCrop", "Residential", "River", "SeaLake"]


FeatureMode = Literal["gray", "rgb", "hsv", "grid2", "grid4", "mle", "ms13", "ndvi_ndwi", "ms13_idx", "ms_mle"]


Metric = Literal["euclid", "chi2", "intersection"]


BinCount = Literal[8, 16, 32, 64, 128, 256]


Split = Literal["train", "test"]


ImageId = str


EvidenceFeature = Literal["mean_gray", "mean_ndvi", "mean_ndwi"]


GnbMode = Literal["mle", "grid2", "grid4", "ms_mle"]


BandMode = Literal["gray", "rgb", "band", "ms13"]


ExperimentId = Literal["C1", "C2", "C3", "C4a", "C4b", "C4c"]


ErrorCode = Literal["IMAGE_NOT_FOUND", "SESSION_NOT_FOUND", "NOT_PRECOMPUTED", "INVALID_PARAM", "MODE_REQUIRES_MULTISPECTRAL", "TIF_NOT_13_BANDS", "EXPRESSION_PARSE_ERROR", "SHAPE_MISMATCH", "LIVE_LIMIT_EXCEEDED", "FORMAT_NOT_SUPPORTED", "UPLOAD_TOO_LARGE", "UNSUPPORTED_FILE", "INTERNAL_ERROR"]


class ApiErrorBodyError(Model):
    code: ErrorCode
    message: str
    details: dict[str, Any] = None


class ApiErrorBody(Model):
    error: ApiErrorBodyError


class MathTable(Model):
    columns: list[str]
    rows: list[list[str | float | bool | None]]
    caption: str = None


class ChartSeries(Model):
    name: str
    y: list[float]
    x: list[float] = None


class ChartSpec(Model):
    kind: Literal["bar", "line", "scatter", "heatmap"]
    title: str
    x: list[float | str] = None
    series: list[ChartSeries] = None
    z: list[list[float]] = None
    x_labels: list[str] = None
    y_labels: list[str] = None
    x_label: str = None
    y_label: str = None
    log_x: bool = None
    log_y: bool = None


class MathStep(Model):
    id: str
    title: str
    latex_template: str | None
    latex_substituted: str | None
    explanation: str
    values: dict[str, float | str]
    table: MathTable | None
    chart: ChartSpec | None


class Inspector(Model):
    title: str
    steps: list[MathStep]


class HealthResponse(Model):
    status: Literal["ok"]
    app_mode: Literal["space", "dev"]
    index_loaded: bool
    n_images: int
    version: str


class ModeInfo(Model):
    mode: FeatureMode
    label: str
    kind: Literal["pmf", "moment"]
    needs_multispectral: bool
    supports_bins: bool
    metrics: list[Metric]
    dim_fixed: int | None
    dim_by_bins: dict[str, int] | None


class MetricInfo(Model):
    metric: Metric
    label: str
    direction: Literal["min", "max"]
    formula_latex: str


class MetaResponseDefaults(Model):
    mode: FeatureMode
    bins: BinCount
    metric: Metric
    k: int


class MetaResponseLimits(Model):
    max_upload_mb_image: float
    max_upload_mb_tif: float
    max_shares: float
    live_max_db: int
    live_max_queries: int


class MetaResponseDatasetPerClass(Model):
    train: float
    test: float


class MetaResponseDataset(Model):
    n_total: int
    n_train: int
    n_test: int
    gallery_size: int
    per_class: dict[ClassName, MetaResponseDatasetPerClass]


class MetaResponse(Model):
    classes: list[ClassName]
    class_labels_id: dict[ClassName, str]
    feature_modes: list[ModeInfo]
    metrics: list[MetricInfo]
    bins_options: list[BinCount]
    evidence_options: list[EvidenceFeature]
    band_names: list[str]
    defaults: MetaResponseDefaults
    limits: MetaResponseLimits
    dataset: MetaResponseDataset


class ImageMeta(Model):
    id: ImageId
    cls: ClassName | None
    split: Split | None
    width: int
    height: int
    bands: int
    has_rgb: bool
    has_ms: bool
    in_gallery: bool
    is_upload: bool
    thumb_url: str


class ImagesListResponse(Model):
    total: float
    items: list[ImageMeta]


class ImagePreview(Model):
    data_uri: str
    width: int
    height: int
    kind: str
    note: str | None


PreviewView = Literal["rgb", "synth_rgb", "ndvi", "ndwi", "band"]


class FeaturesRequest(Model):
    image_id: ImageId
    mode: FeatureMode
    bins: BinCount


class Moments(Model):
    mean: float
    variance: float
    std: float
    skewness: float
    kurtosis: float
    degenerate: bool


class MgfCheck(Model):
    t: list[float]
    m: list[float]
    m1_fd: float
    m1_exact: float
    m2_fd: float
    m2_exact: float
    scale_note: str


class ChannelStatsMle(Model):
    mu_hat: float
    sigma2_hat: float


class ChannelStats(Model):
    name: str
    counts: list[int]
    pmf: list[float]
    moments: Moments
    mle: ChannelStatsMle
    mgf: MgfCheck


class FeaturesResponse(Model):
    image: ImageMeta
    mode: FeatureMode
    bins: BinCount
    kind: Literal["pmf", "moment"]
    dim: int
    channels: list[ChannelStats]
    vector_head: list[float]
    elapsed_ms: float
    inspector: Inspector


class SearchRequest(Model):
    image_id: ImageId
    mode: FeatureMode
    bins: BinCount
    metric: Metric
    k: int = None
    database: Literal["all", "train"] = None


class SearchHit(Model):
    rank: int
    id: ImageId
    cls: ClassName
    split: Split
    distance: float
    similarity: float | None
    same_class: bool | None
    thumb_url: str


class SearchResponseElapsedMs(Model):
    feature: float
    search: float


class SearchResponse(Model):
    query: ImageMeta
    mode: FeatureMode
    bins: BinCount
    metric: Metric
    k: int
    database: Literal["all", "train"]
    db_size: int
    hits: list[SearchHit]
    precision_at_k: float | None
    elapsed_ms: SearchResponseElapsedMs
    inspector: Inspector


class BayesRequest(Model):
    image_id: ImageId
    evidence: EvidenceFeature
    levels: int = None
    alpha: float = None


class BayesClassRow(Model):
    cls: ClassName
    prior: float
    likelihood: float
    joint: float
    posterior: float


class BayesResponseConditionalExample(Model):
    event_a: str
    event_b: str
    p_a_and_b: float
    p_b: float
    p_a_given_b: float


class BayesResponse(Model):
    image: ImageMeta
    evidence: EvidenceFeature
    levels: int
    evidence_value: float
    evidence_bin: int
    evidence_total: float
    rows: list[BayesClassRow]
    predicted: ClassName
    conditional_example: BayesResponseConditionalExample
    inspector: Inspector


class GnbRequest(Model):
    image_id: ImageId
    mode: GnbMode


class GnbResponseRows(Model):
    cls: ClassName
    prior: float
    log_posterior_unnorm: float
    posterior: float


class GnbResponse(Model):
    image: ImageMeta
    mode: GnbMode
    predicted: ClassName
    rows: list[GnbResponseRows]
    inspector: Inspector


class EvaluateResponseProtocol(Model):
    n_queries: int
    db_size: int
    queries_per_class: int
    k: int


class EvaluateResponsePerClass(Model):
    cls: ClassName
    n_queries: int
    precision_at_k: float


class EvaluateResponse(Model):
    mode: FeatureMode | str
    bins: BinCount | None
    metric: Metric | str
    protocol: EvaluateResponseProtocol
    classes: list[ClassName]
    per_class: list[EvaluateResponsePerClass]
    macro_precision_at_k: float
    knn_accuracy: float
    confusion_matrix: list[list[int]]
    source: Literal["precomputed", "live"]
    elapsed_ms: float = None


class LiveCbirRequest(Model):
    mode: FeatureMode
    bins: BinCount
    metric: Metric
    db_per_class: int = None
    queries_per_class: int = None
    k: int = None
    seed: int = None


class LiveBinsRequest(Model):
    mode: FeatureMode
    metric: Metric
    bins_list: list[BinCount]
    db_per_class: int = None
    queries_per_class: int = None
    seed: int = None


class LiveBinsResponsePoints(Model):
    bins: BinCount
    dim: int
    macro_precision_at_k: float
    search_ms_per_query: float


class LiveBinsResponse(Model):
    points: list[LiveBinsResponsePoints]
    chart: ChartSpec


class Chi2Test(Model):
    stat: float
    df: int
    p_value: float
    uniform_at_alpha_0_05: bool


class ReconMetrics(Model):
    identical: bool | None
    mse: float | None
    psnr_db: float | None
    psnr_is_infinite: bool
    pixels_different: int | None
    max_abs_diff: int | None


class ShareInfoDownloadUrls(Model):
    png: str | None
    npy: str


class ShareInfo(Model):
    index: int
    preview: ImagePreview
    histogram: list[float]
    entropy_bits: float
    chi2: Chi2Test
    download_urls: ShareInfoDownloadUrls


class SplitRequest(Model):
    image_id: ImageId
    n: int
    band_mode: BandMode
    band_index: int | None = None
    seed: int | None = None


class SplitResponse(Model):
    session_id: str
    n: int
    band_mode: BandMode
    shape: list[int]
    dtype: Literal["uint8", "uint16"]
    bits: Literal[8, 16]
    seed: int
    original_preview: ImagePreview
    shares: list[ShareInfo]
    reconstruction: ReconMetrics
    inspector: Inspector


class ReconstructRequest(Model):
    session_id: str
    share_indices: list[int] | None = None


class ReconstructResponse(Model):
    used_indices: list[int]
    n_total: int
    is_complete: bool
    preview: ImagePreview
    metrics: ReconMetrics | None
    entropy_bits: float
    inspector: Inspector


class TamperRequest(Model):
    session_id: str
    share_index: int
    mode: Literal["pixel", "bitflip", "block"]
    x: int = None
    y: int = None
    bit: int = None
    p: float = None
    block_size: int = None
    seed: int = None


class TamperResponse(Model):
    share_index: int
    changed_values: int
    tampered_share_preview: ImagePreview
    reconstruct_preview: ImagePreview
    diff_preview: ImagePreview
    metrics: ReconMetrics
    inspector: Inspector


class SecurityRequest(Model):
    session_id: str
    run_cbir: bool = None
    mode: FeatureMode = None
    bins: BinCount = None
    metric: Metric = None
    k: int = None


class SubsetTestCbir(Model):
    precision_at_k: float
    chance_level: float
    hits: list[SearchHit]


class SubsetTest(Model):
    label: str
    k_shares: float
    subset: list[float]
    entropy_bits: float
    chi2: Chi2Test
    pearson_r_with_original: float | None
    mse_vs_original: float
    cbir: SubsetTestCbir | None
    reveals_secret: bool


class SecurityResponseTheory(Model):
    p_uniform: float
    max_entropy_bits: float
    statement: str


class SecurityResponse(Model):
    n: int
    bits: Literal[8, 16]
    subsets: list[SubsetTest]
    theory: SecurityResponseTheory
    inspector: Inspector


class BitflipRequest(Model):
    session_id: str
    p_list: list[float]
    trials: int = None
    corrupted_shares: int = None
    p_focus: float | None = None
    seed: int = None


class BitflipPoint(Model):
    p: float
    p_effective: float
    empirical_pixel_error: float
    empirical_std: float
    theory_pixel_error: float
    abs_diff: float
    mean_wrong_pixels: float
    n_pixels: int


class BitflipResponseTheoryCurves(Model):
    bits: int
    p: list[float]
    error: list[float]


class BitflipResponseGeometric(Model):
    p_wrong: float
    k: list[int]
    pmf_theory: list[float]
    pmf_empirical: list[float]
    mean_theory: float
    mean_empirical: float


class BitflipResponseChebyshevRows(Model):
    k_sigma: int
    r: float
    bound: float
    empirical_tail: float


class BitflipResponseChebyshev(Model):
    p_focus: float
    mu: float
    sigma: float
    rows: list[BitflipResponseChebyshevRows]


class BitflipResponse(Model):
    bits: Literal[8, 16]
    n_pixels: int
    points: list[BitflipPoint]
    theory_curves: list[BitflipResponseTheoryCurves]
    geometric: BitflipResponseGeometric
    chebyshev: BitflipResponseChebyshev
    chart: ChartSpec
    inspector: Inspector


class ReuseKeyRequest(Model):
    image_id_1: ImageId
    image_id_2: ImageId
    seed: int = None


class ReuseKeyResponseScalarDemo(Model):
    m1: str
    m2: str
    k: str
    c1: str
    c2: str
    c1_xor_c2: str
    m1_xor_m2: str
    equal: bool


class ReuseKeyResponsePreviews(Model):
    i1: ImagePreview
    i2: ImagePreview
    c1: ImagePreview
    c2: ImagePreview
    c1_xor_c2: ImagePreview
    i1_xor_i2: ImagePreview


class ReuseKeyResponse(Model):
    scalar_demo: ReuseKeyResponseScalarDemo
    previews: ReuseKeyResponsePreviews
    identical: bool
    key_recovered_from_known_plaintext: bool
    inspector: Inspector


class Raid5Request(Model):
    image_ids: list[ImageId]
    failed_index: int


class Raid5ResponseScalarDemo(Model):
    d: list[str]
    p: str
    failed_index: int
    recovered: str
    ok: bool


class Raid5ResponsePreviews(Model):
    disks: list[ImagePreview]
    parity: ImagePreview
    recovered: ImagePreview


class Raid5Response(Model):
    scalar_demo: Raid5ResponseScalarDemo
    previews: Raid5ResponsePreviews
    identical: bool
    limitation: str
    inspector: Inspector


class PixelXorRequest(Model):
    image_id: ImageId
    x: int
    y: int
    n: int
    channel: Literal["gray", "r", "g", "b"] | int
    seed: int = None


class PixelXorResponseShares(Model):
    index: int
    value: int
    bin: str


class PixelXorResponse(Model):
    value: int
    value_bin: str
    shares: list[PixelXorResponseShares]
    reconstructed: int
    ok: bool
    inspector: Inspector


class CircuitNode(Model):
    id: str
    type: Literal["input", "not", "and", "or", "xor"]
    label: str


class CircuitEdge(Model):
    from_: str = Field(alias="from")
    to: str


class Circuit(Model):
    nodes: list[CircuitNode]
    edges: list[CircuitEdge]
    output_id: str


class TruthTableRequest(Model):
    expression: str


class TruthTableResponseRows(Model):
    inputs: list[Literal[0, 1]]
    output: Literal[0, 1]


class TruthTableResponse(Model):
    normalized: str
    variables: list[str]
    rows: list[TruthTableResponseRows]
    minterms: list[int]
    sop_canonical: str
    circuit: Circuit
    inspector: Inspector


class ProveRequest(Model):
    lhs: str
    rhs: str


class ProofStep(Model):
    expression: str
    reason: str


class ProveResponseCounterexample(Model):
    inputs: list[Literal[0, 1]]
    lhs: Literal[0, 1]
    rhs: Literal[0, 1]


class ProveResponseDual(Model):
    lhs: str
    rhs: str
    equivalent: bool


class ProveResponse(Model):
    equivalent: bool
    variables: list[str]
    table: MathTable
    counterexample: ProveResponseCounterexample | None
    algebraic_proof: list[ProofStep] | None
    dual: ProveResponseDual | None
    inspector: Inspector


class XorGateResponse(Model):
    definition: str
    table: MathTable
    circuit: Circuit
    verified: bool
    inspector: Inspector


class KMapRequest(Model):
    variables: Literal[2, 3, 4]
    minterms: list[int]


class KMapGroup(Model):
    cells: list[int]
    cells_rc: list[tuple[int, int]]
    term: str
    size: float
    wraps: bool


class KMapResponse(Model):
    variables: list[str]
    row_vars: list[str]
    col_vars: list[str]
    row_labels: list[str]
    col_labels: list[str]
    grid: list[list[Literal[0, 1]]]
    cell_minterm: list[list[int]]
    prime_implicants: list[KMapGroup]
    selected: list[KMapGroup]
    simplified: str
    inspector: Inspector


class ExperimentSummary(Model):
    id: ExperimentId
    title: str
    description: str
    generated_at: str | None
    has_results: bool


class ExperimentResultDataset(Model):
    n_images: int
    n_queries: int | None
    note: str


class ExperimentResult(Model):
    id: ExperimentId
    title: str
    description: str
    generated_at: str
    runtime_s: float
    params: dict[str, Any]
    dataset: ExperimentResultDataset
    tables: list[MathTable]
    charts: list[ChartSpec]
    findings: list[str]
    analysis_md: str
