# Frontend Handoff

Frontend: React + Vite + TypeScript + Tailwind + shadcn/ui, dikerjakan Codex.
Otoritas: Figma di `docs/design` untuk tata letak, warna, dan tipografi. `docs/api-contract.md` dan `src/types/api.ts` untuk data. Bila Figma meminta data yang tidak ada di kontrak, jangan mengarang field: catat di `docs/frontend-gaps.md` dan tampilkan placeholder.

## Tumpukan dan konvensi
- Pustaka tambahan: `@tanstack/react-query`, `react-router-dom`, `recharts`, `katex` (+ `react-katex` atau komponen sendiri), `lucide-react`, `sonner` (untuk seluruh toast notifikasi), dan `[Magic UI / Aceternity UI]` (khusus untuk efek animasi yang ditentukan pada prompt Figma).
- **Aturan `shadcn/ui`:** Gunakan `shadcn/ui` untuk komponen dasar (`Button`, `Card`, `Input`, `Tabs`, `Select`, `Slider`, `Table`, `Badge`, `Dialog`), tetapi **jangan gunakan styling default shadcn**—wajib override penuh dengan token desain Figma (font, border radius, dan brand colors).
- **Batas animasi:** Gunakan `[Magic UI / Aceternity UI]` secara terukur sesuai instruksi per section agar tidak mengganggu keterbacaan grafik, angka, maupun rumus KaTeX.
- Proxy dev di `vite.config.ts`: `/api` ke `http://localhost:8000`. Build ke `frontend/dist`.
- Klien API satu pintu: `src/lib/api.ts` (kode di bawah). Dilarang `fetch` langsung dari komponen.
- Teks UI Bahasa Indonesia. Label kelas ramah: pakai `MetaResponse.class_labels_id`.
- Gambar `ImagePreview.data_uri` ditampilkan dengan `image-rendering: pixelated`.
- Setiap panggilan punya tiga keadaan (loading skeleton, galat dengan `error.message` pada toast, kosong). Untuk galat `SESSION_NOT_FOUND` tampilkan tombol "Buat ulang sesi".

## Rute dan halaman (peta ke Figma)

| Rute | Halaman | Komponen utama | Endpoint |
|---|---|---|---|
| `/` | Beranda | `HeroTwoTracks`, kartu ringkasan (jumlah citra, kelas, hasil terbaik C2), tautan ke Colab | `GET /meta`, `GET /experiments` |
| `/cbir` | CBIR | `ImagePicker` (galeri + upload), `FeatureControls` (mode, bins, metrik, k, database), `QueryPanel` (histogram per kanal, momen, MLE, MGF), `ResultGrid`, `EvalPanel` (P@5 per kelas, confusion), `LivePanel`, `BayesPanel` | `GET /images`, `POST /images/upload`, `POST /cbir/features`, `/cbir/search`, `/cbir/bayes`, `/cbir/gnb`, `GET /cbir/evaluate`, `POST /live/cbir`, `/live/bins` |
| `/sharing` | Secret Sharing | `ImagePicker`, `ShareControls` (n, band_mode, band_index, seed), `ShareGallery`, `ReconstructPanel` (centang share), `DownloadUploadPanel`, `TamperPanel`, `SecurityPanel`, `BitflipPanel`, `AttackTabs` (Reuse Key, RAID-5) | `POST /sharing/split`, `GET .../download`, `POST /sharing/reconstruct`, `/reconstruct-upload`, `/tamper`, `/security`, `/bitflip`, `/attacks/*` |
| `/boolean` | Boolean Lab | `ExpressionInput` (dengan tombol `'`, `+`, `^`), `TruthTable`, `CircuitView` (SVG dari `Circuit`), `ProveForm`, `XorGateDemo`, `KMapEditor` (klik sel mengatur minterm) dan `KMapView` (kelompok berwarna) | `POST /boolean/*` |
| `/percobaan` | Percobaan | tab C1..C4c, `ExperimentRenderer` generik (tabel, grafik, temuan, analisis) | `GET /experiments`, `GET /experiments/{id}` |
| `/inspector` | Math Inspector | pilih sumber (hasil terakhir dari CBIR, Sharing, Boolean atau `pixel-xor` bebas) dan render `InspectorView` penuh layar | `POST /inspector/pixel-xor`, dan `inspector` dari respons lain |

Panel Inspector juga tampil sebagai drawer di halaman `/cbir`, `/sharing`, `/boolean` dengan komponen yang sama (`InspectorView`).

## Komponen kunci

**`InspectorView({ inspector })`**: untuk tiap `MathStep` render judul, `explanation`, `latex_template` dan `latex_substituted` dengan KaTeX (`throwOnError:false`, mode blok), `values` sebagai tabel kecil, `table` dengan komponen tabel bersama, dan `chart` dengan `ChartRenderer`. Langkah dapat diciutkan; langkah pertama terbuka.

**`ChartRenderer({ spec: ChartSpec })`**: `bar` dan `line` memakai Recharts; `scatter` memakai `ScatterChart`; `heatmap` dibuat dari grid `div` bernuansa (nilai `z`), dengan label `x_labels`/`y_labels` dan angka di sel (untuk confusion matrix 10x10).

**`ImagePicker`**: grid galeri dari `GET /images?gallery_only=true&cls=...`, filter kelas, tombol unggah (terima `.jpg,.png,.tif,.tiff`, tolak lokal bila > 2 MB (jpg/png) atau > 5 MB (tif)). Hasil unggah `ImageMeta.id` dipakai seperti ID biasa. Tampilkan lencana `MS` bila `has_ms`.

**`ResultGrid`**: untuk `SearchHit` tampilkan `thumb_url`, kelas, jarak (4 desimal), tanda hijau/merah dari `same_class`.

**`TruthTable`**: dari `rows` dan `variables`; sorot baris `output=1`.

**`CircuitView`**: tata letak sederhana berlapis kiri ke kanan dari `Circuit` (graf berarah tanpa siklus); simbol gerbang SVG (AND, OR, NOT, XOR).

**`KMapView`**: tabel `grid` dengan label `row_labels`/`col_labels`; tiap `KMapGroup` digambar sebagai kotak berwarna (gunakan `cells_rc`; kelompok yang melipat tepi digambar dengan dua kotak putus-putus).

## State dan caching
React Query: kunci `['meta']`, `['images', params]`, `['search', req]`, `['features', req]`, `['experiment', id]` (`staleTime: Infinity`). Mutasi sesi sharing disimpan di `SharingContext` (`session_id`, parameter terakhir). Hasil terakhir tiap halaman disimpan di `InspectorContext` agar `/inspector` dapat menampilkannya.

## Interaksi khusus
- Slider live: debounce 400 ms sebelum memanggil `/live/*` atau `/sharing/bitflip`. Batalkan permintaan sebelumnya (`AbortController`).
- Download share: tautan langsung ke `download_urls`. Upload ulang: input berkas ganda (2..8), kirim ke `/sharing/reconstruct-upload` sebagai `multipart/form-data` dengan field `files`.
- Tamper: pilih share, mode, parameter. Tampilkan tiga gambar berdampingan: share terubah, hasil rekonstruksi, selisih.
- Format angka: `psnr_is_infinite=true` tampil sebagai "tak hingga" (jangan tampilkan `null`).
- Tema terang dan gelap mengikuti Figma. Responsif minimal 1280 px dan 768 px.

## Kriteria penerimaan UI
1. Dari `/cbir`, pilih citra galeri, jalankan pencarian, lihat 5 hasil dalam 1 detik (indeks lokal) dan buka Inspector berisi rumus dengan angka asli.
2. `/sharing` dengan `n=3` menampilkan 3 share, rekonstruksi "identik" dengan MSE 0 dan PSNR tak hingga; unduh dan unggah ulang share memberi hasil identik.
3. Tamper satu piksel menampilkan selisih tepat 1 piksel.
4. `/boolean`: input `ab'+a'b` menampilkan tabel XOR dan rangkaian; K-Map majority gate memberi `xy + xz + yz` (variabel nama `a,b,c` pada UI).
5. `/percobaan`: keenam percobaan tampil tanpa kode khusus per percobaan.
6. Tidak ada `any` pada tipe respons; `npm run build` dan `tsc --noEmit` bersih.

## `frontend/src/types/api.ts`
```ts
// ===== Primitif =====
export const CLASS_NAMES = [
  "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
  "Pasture", "PermanentCrop", "Residential", "River", "SeaLake",
] as const;
export type ClassName = (typeof CLASS_NAMES)[number];

export const FEATURE_MODES = [
  "gray", "rgb", "hsv", "grid2", "grid4", "mle",
  "ms13", "ndvi_ndwi", "ms13_idx", "ms_mle",
] as const;
export type FeatureMode = (typeof FEATURE_MODES)[number];

export const METRICS = ["euclid", "chi2", "intersection"] as const;
export type Metric = (typeof METRICS)[number];

export const BIN_OPTIONS = [8, 16, 32, 64, 128, 256] as const;
export type BinCount = (typeof BIN_OPTIONS)[number];

export type Split = "train" | "test";
export type ImageId = string; // "Forest_123" atau "up_ab12cd34"
export type EvidenceFeature = "mean_gray" | "mean_ndvi" | "mean_ndwi";
export type GnbMode = "mle" | "grid2" | "grid4" | "ms_mle";
export type BandMode = "gray" | "rgb" | "band" | "ms13";
export type ExperimentId = "C1" | "C2" | "C3" | "C4a" | "C4b" | "C4c";

export type ErrorCode =
  | "IMAGE_NOT_FOUND" | "SESSION_NOT_FOUND" | "NOT_PRECOMPUTED"
  | "INVALID_PARAM" | "MODE_REQUIRES_MULTISPECTRAL" | "TIF_NOT_13_BANDS"
  | "EXPRESSION_PARSE_ERROR" | "SHAPE_MISMATCH" | "LIVE_LIMIT_EXCEEDED"
  | "FORMAT_NOT_SUPPORTED" | "UPLOAD_TOO_LARGE" | "UNSUPPORTED_FILE"
  | "INTERNAL_ERROR";

export interface ApiErrorBody {
  error: { code: ErrorCode; message: string; details?: Record<string, unknown> };
}

// ===== Inspector =====
export interface MathTable {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  caption?: string;
}
export interface ChartSeries { name: string; y: number[]; x?: number[] }
export interface ChartSpec {
  kind: "bar" | "line" | "scatter" | "heatmap";
  title: string;
  x?: (number | string)[];
  series?: ChartSeries[];
  z?: number[][];
  x_labels?: string[];
  y_labels?: string[];
  x_label?: string;
  y_label?: string;
  log_x?: boolean;
  log_y?: boolean;
}
export interface MathStep {
  id: string;
  title: string;
  latex_template: string | null;
  latex_substituted: string | null;
  explanation: string;
  values: Record<string, number | string>;
  table: MathTable | null;
  chart: ChartSpec | null;
}
export interface Inspector { title: string; steps: MathStep[] }

// ===== Umum =====
export interface HealthResponse {
  status: "ok"; app_mode: "space" | "dev"; index_loaded: boolean; n_images: number; version: string;
}
export interface ModeInfo {
  mode: FeatureMode; label: string; kind: "pmf" | "moment";
  needs_multispectral: boolean; supports_bins: boolean; metrics: Metric[];
  dim_fixed: number | null; dim_by_bins: Record<string, number> | null;
}
export interface MetricInfo {
  metric: Metric; label: string; direction: "min" | "max"; formula_latex: string;
}
export interface MetaResponse {
  classes: ClassName[];
  class_labels_id: Record<ClassName, string>;
  feature_modes: ModeInfo[];
  metrics: MetricInfo[];
  bins_options: BinCount[];
  evidence_options: EvidenceFeature[];
  band_names: string[];
  defaults: { mode: FeatureMode; bins: BinCount; metric: Metric; k: number };
  limits: {
    max_upload_mb_image: number; max_upload_mb_tif: number; max_shares: number;
    live_max_db: number; live_max_queries: number;
  };
  dataset: {
    n_total: number; n_train: number; n_test: number; gallery_size: number;
    per_class: Record<ClassName, { train: number; test: number }>;
  };
}

// ===== Citra =====
export interface ImageMeta {
  id: ImageId; cls: ClassName | null; split: Split | null;
  width: number; height: number; bands: number;
  has_rgb: boolean; has_ms: boolean; in_gallery: boolean; is_upload: boolean;
  thumb_url: string;
}
export interface ImagesListResponse { total: number; items: ImageMeta[] }
export interface ImagePreview {
  data_uri: string; width: number; height: number; kind: string; note: string | null;
}
export type PreviewView = "rgb" | "synth_rgb" | "ndvi" | "ndwi" | "band";

// ===== CBIR =====
export interface FeaturesRequest { image_id: ImageId; mode: FeatureMode; bins: BinCount }
export interface Moments {
  mean: number; variance: number; std: number; skewness: number; kurtosis: number; degenerate: boolean;
}
export interface MgfCheck {
  t: number[]; m: number[];
  m1_fd: number; m1_exact: number; m2_fd: number; m2_exact: number; scale_note: string;
}
export interface ChannelStats {
  name: string; counts: number[]; pmf: number[]; moments: Moments;
  mle: { mu_hat: number; sigma2_hat: number }; mgf: MgfCheck;
}
export interface FeaturesResponse {
  image: ImageMeta; mode: FeatureMode; bins: BinCount; kind: "pmf" | "moment";
  dim: number; channels: ChannelStats[]; vector_head: number[]; elapsed_ms: number; inspector: Inspector;
}
export interface SearchRequest {
  image_id: ImageId; mode: FeatureMode; bins: BinCount; metric: Metric;
  k?: number; database?: "all" | "train";
}
export interface SearchHit {
  rank: number; id: ImageId; cls: ClassName; split: Split; distance: number;
  similarity: number | null; same_class: boolean | null; thumb_url: string;
}
export interface SearchResponse {
  query: ImageMeta; mode: FeatureMode; bins: BinCount; metric: Metric; k: number;
  database: "all" | "train"; db_size: number; hits: SearchHit[];
  precision_at_k: number | null; elapsed_ms: { feature: number; search: number };
  inspector: Inspector;
}
export interface BayesRequest { image_id: ImageId; evidence: EvidenceFeature; levels?: number; alpha?: number }
export interface BayesClassRow {
  cls: ClassName; prior: number; likelihood: number; joint: number; posterior: number;
}
export interface BayesResponse {
  image: ImageMeta; evidence: EvidenceFeature; levels: number;
  evidence_value: number; evidence_bin: number; evidence_total: number;
  rows: BayesClassRow[]; predicted: ClassName;
  conditional_example: {
    event_a: string; event_b: string; p_a_and_b: number; p_b: number; p_a_given_b: number;
  };
  inspector: Inspector;
}
export interface GnbRequest { image_id: ImageId; mode: GnbMode }
export interface GnbResponse {
  image: ImageMeta; mode: GnbMode; predicted: ClassName;
  rows: { cls: ClassName; prior: number; log_posterior_unnorm: number; posterior: number }[];
  inspector: Inspector;
}
export interface EvaluateResponse {
  mode: FeatureMode | string; bins: BinCount | null; metric: Metric | string;
  protocol: { n_queries: number; db_size: number; queries_per_class: number; k: number };
  classes: ClassName[];
  per_class: { cls: ClassName; n_queries: number; precision_at_k: number }[];
  macro_precision_at_k: number; knn_accuracy: number;
  confusion_matrix: number[][];
  source: "precomputed" | "live"; elapsed_ms?: number;
}
export interface LiveCbirRequest {
  mode: FeatureMode; bins: BinCount; metric: Metric;
  db_per_class?: number; queries_per_class?: number; k?: number; seed?: number;
}
export interface LiveBinsRequest {
  mode: FeatureMode; metric: Metric; bins_list: BinCount[];
  db_per_class?: number; queries_per_class?: number; seed?: number;
}
export interface LiveBinsResponse {
  points: { bins: BinCount; dim: number; macro_precision_at_k: number; search_ms_per_query: number }[];
  chart: ChartSpec;
}

// ===== Secret sharing =====
export interface Chi2Test { stat: number; df: number; p_value: number; uniform_at_alpha_0_05: boolean }
export interface ReconMetrics {
  identical: boolean | null; mse: number | null;
  psnr_db: number | null; psnr_is_infinite: boolean;
  pixels_different: number | null; max_abs_diff: number | null;
}
export interface ShareInfo {
  index: number; preview: ImagePreview; histogram: number[]; entropy_bits: number;
  chi2: Chi2Test; download_urls: { png: string | null; npy: string };
}
export interface SplitRequest {
  image_id: ImageId; n: number; band_mode: BandMode;
  band_index?: number | null; seed?: number | null;
}
export interface SplitResponse {
  session_id: string; n: number; band_mode: BandMode; shape: number[];
  dtype: "uint8" | "uint16"; bits: 8 | 16; seed: number;
  original_preview: ImagePreview; shares: ShareInfo[];
  reconstruction: ReconMetrics; inspector: Inspector;
}
export interface ReconstructRequest { session_id: string; share_indices?: number[] | null }
export interface ReconstructResponse {
  used_indices: number[]; n_total: number; is_complete: boolean;
  preview: ImagePreview; metrics: ReconMetrics | null; entropy_bits: number; inspector: Inspector;
}
export interface TamperRequest {
  session_id: string; share_index: number; mode: "pixel" | "bitflip" | "block";
  x?: number; y?: number; bit?: number; p?: number; block_size?: number; seed?: number;
}
export interface TamperResponse {
  share_index: number; changed_values: number;
  tampered_share_preview: ImagePreview; reconstruct_preview: ImagePreview; diff_preview: ImagePreview;
  metrics: ReconMetrics; inspector: Inspector;
}
export interface SecurityRequest {
  session_id: string; run_cbir?: boolean; mode?: FeatureMode; bins?: BinCount; metric?: Metric; k?: number;
}
export interface SubsetTest {
  label: string; k_shares: number; subset: number[];
  entropy_bits: number; chi2: Chi2Test;
  pearson_r_with_original: number | null; mse_vs_original: number;
  cbir: { precision_at_k: number; chance_level: number; hits: SearchHit[] } | null;
  reveals_secret: boolean;
}
export interface SecurityResponse {
  n: number; bits: 8 | 16; subsets: SubsetTest[];
  theory: { p_uniform: number; max_entropy_bits: number; statement: string };
  inspector: Inspector;
}
export interface BitflipRequest {
  session_id: string; p_list: number[]; trials?: number;
  corrupted_shares?: number; p_focus?: number | null; seed?: number;
}
export interface BitflipPoint {
  p: number; p_effective: number; empirical_pixel_error: number; empirical_std: number;
  theory_pixel_error: number; abs_diff: number; mean_wrong_pixels: number; n_pixels: number;
}
export interface BitflipResponse {
  bits: 8 | 16; n_pixels: number; points: BitflipPoint[];
  theory_curves: { bits: number; p: number[]; error: number[] }[];
  geometric: {
    p_wrong: number; k: number[]; pmf_theory: number[]; pmf_empirical: number[];
    mean_theory: number; mean_empirical: number;
  };
  chebyshev: {
    p_focus: number; mu: number; sigma: number;
    rows: { k_sigma: number; r: number; bound: number; empirical_tail: number }[];
  };
  chart: ChartSpec; inspector: Inspector;
}
export interface ReuseKeyRequest { image_id_1: ImageId; image_id_2: ImageId; seed?: number }
export interface ReuseKeyResponse {
  scalar_demo: {
    m1: string; m2: string; k: string; c1: string; c2: string;
    c1_xor_c2: string; m1_xor_m2: string; equal: boolean;
  };
  previews: {
    i1: ImagePreview; i2: ImagePreview; c1: ImagePreview; c2: ImagePreview;
    c1_xor_c2: ImagePreview; i1_xor_i2: ImagePreview;
  };
  identical: boolean; key_recovered_from_known_plaintext: boolean; inspector: Inspector;
}
export interface Raid5Request { image_ids: ImageId[]; failed_index: number }
export interface Raid5Response {
  scalar_demo: { d: string[]; p: string; failed_index: number; recovered: string; ok: boolean };
  previews: { disks: ImagePreview[]; parity: ImagePreview; recovered: ImagePreview };
  identical: boolean; limitation: string; inspector: Inspector;
}
export interface PixelXorRequest {
  image_id: ImageId; x: number; y: number; n: number;
  channel: "gray" | "r" | "g" | "b" | number; seed?: number;
}
export interface PixelXorResponse {
  value: number; value_bin: string;
  shares: { index: number; value: number; bin: string }[];
  reconstructed: number; ok: boolean; inspector: Inspector;
}

// ===== Boolean =====
export interface CircuitNode { id: string; type: "input" | "not" | "and" | "or" | "xor"; label: string }
export interface CircuitEdge { from: string; to: string }
export interface Circuit { nodes: CircuitNode[]; edges: CircuitEdge[]; output_id: string }
export interface TruthTableRequest { expression: string }
export interface TruthTableResponse {
  normalized: string; variables: string[];
  rows: { inputs: (0 | 1)[]; output: 0 | 1 }[];
  minterms: number[]; sop_canonical: string; circuit: Circuit; inspector: Inspector;
}
export interface ProveRequest { lhs: string; rhs: string }
export interface ProofStep { expression: string; reason: string }
export interface ProveResponse {
  equivalent: boolean; variables: string[]; table: MathTable;
  counterexample: { inputs: (0 | 1)[]; lhs: 0 | 1; rhs: 0 | 1 } | null;
  algebraic_proof: ProofStep[] | null;
  dual: { lhs: string; rhs: string; equivalent: boolean } | null;
  inspector: Inspector;
}
export interface XorGateResponse {
  definition: string; table: MathTable; circuit: Circuit; verified: boolean; inspector: Inspector;
}
export interface KMapRequest { variables: 2 | 3 | 4; minterms: number[] }
export interface KMapGroup {
  cells: number[]; cells_rc: [number, number][]; term: string; size: number; wraps: boolean;
}
export interface KMapResponse {
  variables: string[]; row_vars: string[]; col_vars: string[];
  row_labels: string[]; col_labels: string[];
  grid: (0 | 1)[][]; cell_minterm: number[][];
  prime_implicants: KMapGroup[]; selected: KMapGroup[];
  simplified: string; inspector: Inspector;
}

// ===== Percobaan =====
export interface ExperimentSummary {
  id: ExperimentId; title: string; description: string;
  generated_at: string | null; has_results: boolean;
}
export interface ExperimentResult {
  id: ExperimentId; title: string; description: string;
  generated_at: string; runtime_s: number; params: Record<string, unknown>;
  dataset: { n_images: number; n_queries: number | null; note: string };
  tables: MathTable[]; charts: ChartSpec[]; findings: string[]; analysis_md: string;
}
```

## `frontend/src/lib/api.ts`
```ts
import type { ApiErrorBody } from "../types/api";

export class ApiError extends Error {
  constructor(public code: string, message: string, public details?: Record<string, unknown>) {
    super(message);
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.ok) return (await res.json()) as T;
  let body: ApiErrorBody | null = null;
  try { body = (await res.json()) as ApiErrorBody; } catch { /* abaikan */ }
  throw new ApiError(body?.error.code ?? "INTERNAL_ERROR", body?.error.message ?? res.statusText, body?.error.details);
}

export async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>, signal?: AbortSignal): Promise<T> {
  const q = params
    ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])).toString()
    : "";
  return handle<T>(await fetch(`/api${path}${q}`, { signal }));
}

export async function post<T, B>(path: string, body: B, signal?: AbortSignal): Promise<T> {
  return handle<T>(await fetch(`/api${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal,
  }));
}

export async function postForm<T>(path: string, form: FormData, signal?: AbortSignal): Promise<T> {
  return handle<T>(await fetch(`/api${path}`, { method: "POST", body: form, signal }));
}
```