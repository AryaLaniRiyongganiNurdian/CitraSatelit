"""Generate the portable CitraSatelit notebook from the project's source files."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "notebooks/citrasatelit.ipynb"


def _cell(kind, name, source, tags=()):
    cell = {"cell_type": kind, "id": name, "metadata": {"tags": list(tags)} if tags else {},
            "source": source.strip("\n").splitlines(keepends=True)}
    if kind == "code":
        cell.update(execution_count=None, outputs=[])
    return cell


def _source_assignment(path):
    relative = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    body = "\n".join(f"    {line!r}" for line in text.splitlines(keepends=True))
    return f"embedded_sources[{relative!r}] = (\n{body or '    ' + repr('')}\n)"


def build(destination=DEFAULT):
    """Build an unexecuted, deterministic nbformat 4 notebook."""
    cells = []
    def md(name, source):
        cells.append(_cell("markdown", name, source))

    def code(name, source, *tags):
        cells.append(_cell("code", name, source, tags))

    md("tujuan", """
# CitraSatelit — CBIR dan Berbagi Rahasia dengan XOR

Gunakan EuroSAT untuk menguji histogram, pencarian citra, Bayes, dan rekonstruksi XOR.
Enam percobaan di bagian akhir memakai protokol serta modul yang sama dengan aplikasi web.
""")
    md("petunjuk-setup", """
## 1. Setup dan pilihan data

Pilih **Jalankan semua** di Google Colab. Mode bawaan **colab_instant** memakai 1.600 citra latih dan 400 citra uji.
Notebook mengambil **eurosat_subset_v1.zip.sha256** dan **eurosat_subset_v1.zip** dari
[GitHub Releases v1.0](https://github.com/AryaLaniRiyongganiNurdian/CitraSatelit/releases/tag/v1.0).
SHA-256 arsip diperiksa sebelum ekstraksi, lalu setiap berkas dataset diperiksa terhadap **SHA256SUMS**.
Unduhan dan dataset hasil ekstraksi disimpan di **/content/data**.

Untuk arsip lokal, unggah ZIP dan berkas **.sha256** ke **/content**, atau atur **COLAB_ARCHIVE** ke lokasi ZIP.
**COLAB_SUBSET_URL** dapat diubah, **COLAB_SUBSET_MIRROR** menyediakan URL cadangan, dan **COLAB_SUBSET_SHA256**
menerima hash arsip yang sudah diketahui.
Mode **full_local** membaca direktori EuroSAT dan indeks yang telah dibangun melalui konfigurasi proyek.
**REPO_URL** opsional untuk mengkloning repositori. Sumber yang tertanam digunakan jika URL kosong.
""")
    code("setup", """
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

DATASET_MODE = os.getenv("DATASET_MODE", "colab_instant")
REPO_URL = os.getenv("CITRASATELIT_REPO_URL", "")
COLAB_SUBSET_URL = os.getenv(
    "COLAB_SUBSET_URL",
    "https://github.com/AryaLaniRiyongganiNurdian/CitraSatelit/releases/download/v1.0/eurosat_subset_v1.zip",
)
COLAB_SUBSET_MIRROR = os.getenv("COLAB_SUBSET_MIRROR", "")
COLAB_SUBSET_SHA256 = os.getenv("COLAB_SUBSET_SHA256", "")
COLAB_ARCHIVE = os.getenv("COLAB_ARCHIVE", "")
in_colab = Path("/content").is_dir()
workspace = Path(os.getenv("CITRASATELIT_PROJECT", str(Path.cwd()))).resolve()
cache = Path(os.getenv("COLAB_CACHE_DIR", str(Path("/content/data") if in_colab else workspace / ".colab-cache")))
cache.mkdir(parents=True, exist_ok=True)

if in_colab:
    import importlib.util
    dependencies = {"numpy": "numpy", "PIL": "pillow", "tifffile": "tifffile",
                    "matplotlib": "matplotlib", "dotenv": "python-dotenv"}
    missing = [package for module, package in dependencies.items() if importlib.util.find_spec(module) is None]
    if missing:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=True)
embedded_sources = {}
""")
    md("sumber", """
## 2. Sumber modul
Sel berikut dihasilkan dari **src/core**. Sunting modul proyek lalu jalankan **python -m tools.build_notebook** untuk memperbarui notebook.
""")
    for path in sorted((ROOT / "src/core").glob("*.py")):
        code("core-" + path.stem, _source_assignment(path), "core-generated")
    dependencies = [
        *(ROOT / "src/data").glob("*.py"),
        *(ROOT / "src/experiments").glob("*.py"),
        ROOT / "tools/build_index.py", ROOT / "tools/colab_runtime.py",
    ]
    code("support", "\n\n".join(_source_assignment(path) for path in sorted(dependencies)), "generated")
    code("bootstrap", """
source_tree = TemporaryDirectory(prefix="citrasatelit-")
project = Path(source_tree.name) / "project"
if REPO_URL:
    subprocess.run(["git", "clone", "--depth", "1", "--", REPO_URL, str(project)], check=True)
else:
    for relative, source in embedded_sources.items():
        file = project / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(source, encoding="utf-8")
sys.path.insert(0, str(project))

import json

import matplotlib.pyplot as plt
import numpy as np

from src.core import boolean_lab, cbir, color, probability, secret_sharing, security_demos, spectral, stats
from src.experiments import run_all
from src.experiments.common import evaluate
from tools.colab_runtime import ARCHIVE_NAME, EXPERIMENTS, dataset_from_mode
""")
    md("data", "## 3. Data dan manifest\nChecksum anggota diverifikasi sebelum data dipakai. ID indeks diperiksa terhadap manifest.")
    code("load-data", """
archive_candidates = [Path(COLAB_ARCHIVE)] if COLAB_ARCHIVE else [
    workspace / "artifacts" / ARCHIVE_NAME, workspace / ARCHIVE_NAME, Path("/content") / ARCHIVE_NAME,
]
if DATASET_MODE == "colab_instant" and COLAB_ARCHIVE and not archive_candidates[0].is_file():
    raise FileNotFoundError(f"COLAB_ARCHIVE tidak ditemukan: {COLAB_ARCHIVE}")
archive = next((file for file in archive_candidates if file.is_file()), None)
data, artifacts = dataset_from_mode(DATASET_MODE, workspace, cache, archive=archive,
                                    urls=(COLAB_SUBSET_URL, COLAB_SUBSET_MIRROR), digest=COLAB_SUBSET_SHA256)
train = data.split_rows(0, data.classes)
test = data.split_rows(1, data.classes)
if DATASET_MODE == "colab_instant":
    assert len(train) == 1600 and len(test) == 400
else:
    assert len(data.rows) == 27000
print(f"{DATASET_MODE} · {len(train):,} latih · {len(test):,} uji")
i = test[0]
rgb, bands = data.rgb(i), data.bands(i)
scale = json.loads((artifacts / "scale.json").read_text(encoding="utf-8"))

def show_figure(fig):
    fig.tight_layout()
    fig.canvas.draw()
    if plt.get_backend().lower() != "agg":
        plt.show()
    plt.close(fig)
""")
    md("histogram", "## 4. Histogram, momen dan spektrum\nHistogram yang dinormalisasi adalah PMF. NDVI dan NDWI memakai kanal berbeda.")
    code("stats-color", """
gray = color.rgb_to_gray(rgb)
counts = stats.histogram_counts(gray, 256)
pmf = stats.counts_to_pmf(counts)
moments = stats.moments_from_counts(counts)
assert np.isclose(pmf.sum(), 1) and np.isclose(moments["mean"], gray.mean())
assert np.isclose(stats.mle_gaussian(gray)[0], gray.mean())
mgf = stats.mgf_check(counts)
assert np.isclose(mgf["m1_fd"], mgf["m1_exact"], atol=1e-5)
assert color.rgb_to_hsv(rgb).shape == rgb.shape
assert spectral.synth_rgb(bands, scale).shape == rgb.shape
fig, axes = plt.subplots(1, 3, figsize=(11, 3))
axes[0].bar(np.arange(256), pmf)
axes[0].set_title("PMF keabuan")
for axis, image, title in zip(axes[1:], (spectral.ndvi(bands), spectral.ndwi(bands)), ("NDVI", "NDWI")):
    shown = axis.imshow(image, vmin=-1, vmax=1)
    axis.set_title(title)
    axis.axis("off")
    fig.colorbar(shown, ax=axis)
show_figure(fig)
print(moments)
""")
    md("cbir", "## 5. CBIR dan Precision@5\nKueri berasal dari split uji. Tetangga dicari hanya di split latih.")
    code("evaluate-cbir", """
summary, _ = evaluate(data, "rgb", "chi2", 32)
assert 0 <= summary["macro_precision_at_k"] <= 1
assert cbir.extract_counts("rgb", rgb=rgb).sum() == rgb.size
for row in summary["per_class"]:
    print(f'{row["cls"]:<22} {row["precision_at_k"]:.1%} ({row["n_queries"]} kueri)')
print(f'P@5 makro {summary["macro_precision_at_k"]:.1%}')
""")
    md("bayes", "## 6. Teorema Bayes\nBandingkan peluang awal dengan posterior kasus Transjakarta dan Gateway.")
    code("verify-bayes", """
posterior, evidence = probability.bayes_posterior([0.60, 0.40], [0.10, 0.05])
assert np.isclose(evidence, 0.08) and np.isclose(posterior[0], 0.75)
assert np.isclose(probability.cond_prob(0.06, 0.08), 0.75)
gateway, probability_error = probability.bayes_posterior([0.70, 0.30], [0.02, 0.08])
assert np.isclose(probability_error, 0.038) and np.isclose(gateway[1], 0.024 / 0.038)
print("P(TL) =", evidence, "· P(T | TL) =", posterior[0], "· P(Y | E) =", gateway[1])
""")
    md("sharing", "## 7. Tiga share XOR\nGabungkan semua share untuk memulihkan citra. Paritas XOR juga dapat memulihkan satu blok yang hilang.")
    code("verify-sharing", """
shares = secret_sharing.split_xor(bands[..., 3], 3, np.random.default_rng(data.seed))
restored = secret_sharing.reconstruct_xor(shares)
assert np.array_equal(restored, bands[..., 3]) and secret_sharing.mse(restored, bands[..., 3]) == 0
assert np.isinf(secret_sharing.psnr(restored, bands[..., 3], 65535))
parity = security_demos.raid5_parity(shares)
assert np.array_equal(security_demos.raid5_recover([shares[0], None, shares[2]], parity, 1), shares[1])
fig, axes = plt.subplots(1, 4, figsize=(10, 3))
for axis, image, title in zip(axes, [*shares, restored], ["Share 1", "Share 2", "Share 3", "Pulih"]):
    axis.imshow(image, cmap="gray")
    axis.set_title(title)
    axis.axis("off")
show_figure(fig)
""")
    md("boolean", "## 8. Aljabar Boolean dan peta Karnaugh\nUji identitas XOR, De Morgan, dan fungsi mayoritas.")
    code("verify-boolean", """
assert boolean_lab.equivalent("ab'+a'b", "a^b")
assert boolean_lab.equivalent("(a+b)'", "a'b'")
assert boolean_lab.equivalent(boolean_lab.dual_expr("a+a'b"), boolean_lab.dual_expr("a+b"))
truth = boolean_lab.truth_table("a^b")
assert [row["output"] for row in truth["rows"]] == [0, 1, 1, 0]
majority = boolean_lab.kmap(3, [3, 5, 6, 7])
assert boolean_lab.equivalent(majority["simplified"], "ab+ac+bc")
print("Tabel XOR:", truth["rows"], "· SOP mayoritas:", majority["simplified"])
""")
    md("experiments", """
## 9. Percobaan C1–C4c
Hitung ulang enam percobaan dengan data aktif. Keluaran JSON berisi tabel lengkap dan parameter.
Pratinjau menampilkan hingga 12 baris setiap tabel. Pada C4b, grafik dibuat dari kolom P@5 di tabel hasil.
""")
    code("run-experiments", """
output = cache / "results" / DATASET_MODE
run_all.run(data, output)
results = {name: json.loads((output / (name + ".json")).read_text(encoding="utf-8")) for name in EXPERIMENTS}
assert all(item["tables"] and item["findings"] for item in results.values())
""")
    code("display-experiments", """
def show_text(text):
    if "ipykernel" in sys.modules:
        from IPython.display import Markdown, display
        display(Markdown(text))
    else:
        print(text)

def show_chart(chart):
    fig, axis = plt.subplots(figsize=(7, 3.8))
    axis.set_title(chart["title"])
    if chart["kind"] == "heatmap":
        image = axis.imshow(chart["z"], cmap="Blues")
        xlabels, ylabels = chart["x_labels"], chart["y_labels"]
        axis.set_xticks(range(len(xlabels)), xlabels, rotation=55, ha="right")
        axis.set_yticks(range(len(ylabels)), ylabels)
        fig.colorbar(image, ax=axis)
    else:
        for series in chart["series"]:
            x = series.get("x", chart.get("x", list(range(len(series["y"])))))
            if chart["kind"] == "bar":
                axis.bar(x, series["y"], label=series["name"])
            elif chart["kind"] == "scatter":
                axis.scatter(x, series["y"], label=series["name"])
            else:
                axis.plot(x, series["y"], marker="o", label=series["name"])
        if len(chart["series"]) > 1:
            axis.legend()
    show_figure(fig)

for identifier, item in results.items():
    show_text("### " + item["title"])
    for table in item["tables"]:
        columns, rows = table["columns"], table["rows"]
        lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
        lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows[:12])
        show_text(chr(10).join(lines))
        if len(rows) > 12:
            show_text(f"Baris lengkap ({len(rows)}) tersedia di {identifier}.json.")
    for chart in item["charts"]:
        show_chart(chart)
    if identifier == "C4b":
        rows = item["tables"][0]["rows"]
        series = []
        for n in sorted({row[0] for row in rows}):
            selected = [row for row in rows if row[0] == n and row[2] == "awal"]
            series.append({"name": f"n={n}", "x": [row[1] for row in selected], "y": [row[7] for row in selected]})
        show_chart({"kind": "line", "title": "Precision@5 menurut jumlah share yang digabung", "series": series})
""")
    md("analysis", "## 10. Analisis\nTemuan dihitung dari keluaran setiap percobaan.")
    code("findings", """
for identifier, item in results.items():
    show_text(f"### {identifier}" + chr(10) + chr(10).join("- " + finding for finding in item["findings"]))
print("Hasil lengkap:", output)
""")
    md("kesimpulan", """
## 11. Kesimpulan
Bandingkan metode pada split yang sama sebelum menarik kesimpulan tentang kemiripan.
Semua share diperlukan untuk rekonstruksi identik. Peta Karnaugh menunjukkan bagaimana fungsi Boolean disederhanakan.
""")
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                             "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def execute(path):
    """Execute every code cell in a fresh process namespace."""
    notebook = json.loads(path.read_text(encoding="utf-8"))
    namespace = {"__name__": "__main__"}
    count = 0
    try:
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                exec(compile("".join(cell["source"]), cell["id"], "exec"), namespace)
                count += 1
    finally:
        if "source_tree" in namespace:
            namespace["source_tree"].cleanup()
    print(f"{count} sel kode selesai.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    build(args.output)
    if args.execute:
        execute(args.output)


if __name__ == "__main__":
    main()
