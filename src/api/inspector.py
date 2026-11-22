import base64
import io

import numpy as np
from PIL import Image

EXPLANATIONS = dict(line.split("|", 1) for line in """counts|Hitung kemunculan intensitas pada setiap bin.
pmf|Normalisasi jumlah piksel untuk memperoleh distribusi.
moments|Hitung momen dari 256 level intensitas.
mle|Estimasi rata-rata dan variansi populasi per kanal.
mgf|Bandingkan turunan numerik dengan momen eksak.
moment-table|Susun momen sesuai urutan fitur.
metric-formula|Gunakan metrik jarak untuk membandingkan fitur.
metric-numbers|Substitusikan fitur query dan hasil terdekat.
precision|Hitung proporsi hasil sekelas.
prior|Hitung frekuensi kelas pada data latih.
likelihood|Hitung peluang bin bukti untuk tiap kelas.
evidence|Jumlahkan hasil kali prior dan likelihood.
posterior|Normalisasi skor untuk memperoleh peluang posterior.
conditional|Hitung peluang kelas dengan syarat bin yang diamati.
mle-per-class|Estimasi rerata dan variansi fitur per kelas.
log-likelihood|Jumlahkan log prior dengan log likelihood.
bits|Tentukan lebar bit dari tipe data.
random-shares|Ambil share acak seragam.
last-share|XOR citra asli dengan semua share acak.
reconstruction-proof|XOR semua share untuk membatalkan mask.
xor-chain|Gabungkan share terpilih dengan XOR.
result|Periksa hasil komputasi.
tamper|Ubah satu share pada salinan sesi.
effect|Bandingkan rekonstruksi dengan citra asli.
uniform-theory|Setiap level memiliki peluang seragam.
chi2|Bandingkan frekuensi observasi dan teori.
entropy|Hitung entropi Shannon.
cbir-on-share|Bandingkan pencarian share dengan peluang acak.
binomial|Hitung peluang piksel salah.
geometric|Bandingkan posisi galat pertama dengan distribusi geometrik.
chebyshev|Bandingkan ekor empiris dengan batas Chebyshev.
encrypt|Gunakan mask yang sama untuk kedua pesan contoh.
xor-of-ciphers|XOR hasil untuk membatalkan mask yang sama.
leak|Bandingkan dengan XOR kedua pesan sumber.
parity|Hitung XOR semua blok.
recover|XOR paritas dengan blok yang tersisa.
limit|Satu paritas memulihkan satu blok hilang.
binary|Nyatakan intensitas dalam bentuk biner.
xor|Gabungkan bit pada posisi yang sama.
reconstruct|Bandingkan nilai rekonstruksi dan nilai awal.
parse|Baca ekspresi sesuai prioritas operator.
table|Evaluasi semua kombinasi masukan.
sop|Gabungkan minterm bernilai satu.
table-proof|Bandingkan keluaran kedua fungsi untuk semua masukan.
algebraic|Periksa langkah penyederhanaan dalam katalog.
dual|Tukar AND dengan OR serta nol dengan satu.
definition|Nyatakan XOR sebagai jumlah dua suku.
circuit|Susun gerbang menjadi graf berarah.
grid|Letakkan minterm dalam urutan Gray.
groups|Pilih implikan yang menutupi minterm.""".splitlines())


FORMULAS = {
    "pmf": r"p_i=\frac{c_i}{\sum_j c_j}",
    "moments": r"\mu=\sum_i i p_i,\quad \sigma^2=\sum_i i^2 p_i-\mu^2",
    "mle": r"\hat\mu=\frac{1}{n}\sum_i x_i,\quad \hat\sigma^2=\frac{1}{n}\sum_i(x_i-\hat\mu)^2",
    "mgf": r"M(t)=\sum_i e^{tx_i}p_i",
    "evidence": r"P(E)=\sum_c P(c)P(E\mid c)",
    "posterior": r"P(c\mid E)=\frac{P(c)P(E\mid c)}{P(E)}",
    "conditional": r"P(A\mid B)=\frac{P(A\cap B)}{P(B)}",
    "last-share": r"S_n=I\oplus S_1\oplus\cdots\oplus S_{n-1}",
    "reconstruction-proof": r"I=S_1\oplus\cdots\oplus S_n",
    "chi2": r"\chi^2=\sum_i\frac{(O_i-E_i)^2}{E_i}",
    "entropy": r"H=-\sum_i p_i\log_2(p_i)",
    "binomial": r"q=1-(1-p_{\rm eff})^b",
    "geometric": r"P(K=k)=(1-q)^{k-1}q",
    "chebyshev": r"P(|X-\mu|\ge k\sigma)\le\frac{1}{k^2}",
    "definition": r"a\oplus b=ab'+a'b",
}


def explain(title, *ids, detail=None):
    detail = detail or {}
    return {"title": title, "steps": [
        {"id": key, "title": EXPLANATIONS[key].rstrip("."), "latex_template": FORMULAS.get(key),
         "latex_substituted": None, "explanation": EXPLANATIONS[key], "values": {},
         "table": None, "chart": None} | detail.get(key, {}) for key in ids
    ]}


def preview(array, kind, scale=4, band=0):
    note = None
    if array.dtype == np.uint16:
        array = (array >> 8).astype(np.uint8)
        note = "Pratinjau memakai byte tinggi uint16."
    if array.ndim == 3 and array.shape[2] != 3:
        array = array[..., band]
    image = Image.fromarray(array)
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return {"data_uri": "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii"),
            "width": image.width, "height": image.height, "kind": kind, "note": note}
