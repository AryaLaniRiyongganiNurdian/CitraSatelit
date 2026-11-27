import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import orbital from "@/assets/orbital.jpg";
import delta from "@/assets/lena-delta.jpg";
import archive from "@/assets/archive-status.svg";
import sight from "@/assets/hero-reticle.svg";
import scrollPlus from "@/assets/scroll-plus.svg";
import arrow from "@/assets/arrow.svg";
import lightArrow from "@/assets/diagonal-card-light.svg";
import inkArrow from "@/assets/diagonal-ink.svg";
import mutedArrow from "@/assets/diagonal-muted.svg";
import externalArrow from "@/assets/diagonal-external.svg";
import { GalleryImage, HeroTwoTracks } from "@/components/hero-two-tracks";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { get } from "@/lib/api";
import { bestC2, useQueryError } from "@/lib/home-data";
import type { ExperimentResult, ExperimentSummary, ImagesListResponse, MetaResponse } from "@/types/api";

const cards = [
  {
    path: "/cbir", mode: "CBIR", title: ["Temukan", "citra serupa."],
    description: "Telusuri galeri EuroSAT berdasarkan warna, momen, dan informasi spektral.",
    label: "Pencarian berbasis konten", tone: "stone",
  },
  {
    path: "/sharing", mode: "Berbagi rahasia", title: ["Bagi citra,", "satukan kembali."],
    description: "Bagi sebuah citra menjadi beberapa share dan uji rekonstruksinya dengan XOR.",
    label: "Pembagian dan rekonstruksi XOR", tone: "blue",
  },
  {
    path: "/boolean", mode: "Lab Boolean", title: ["Uji logika", "di balik citra."],
    description: "Telusuri tabel kebenaran, kesetaraan ekspresi, dan penyederhanaan peta Karnaugh.",
    label: "Aljabar Boolean dan gerbang logika", tone: "image",
  },
] as const;

const steps = [
  { title: "Pilih citra", copy: "Mulai dari contoh EuroSAT. Gunakan citra RGB atau multispektral sesuai pertanyaanmu.", path: "/cbir" },
  { title: "Pilih metode", copy: "Bandingkan fitur citra atau amati bagaimana pembagian XOR bekerja.", path: "/sharing" },
  { title: "Periksa hasil", copy: "Baca rumus, telusuri langkah hitung, dan bandingkan hasil percobaan.", path: "/inspector" },
] as const;

const colabUrl = import.meta.env.VITE_COLAB_NOTEBOOK_URL
  || "https://colab.research.google.com/github/AryaLaniRiyongganiNurdian/CitraSatelit/blob/main/notebooks/citrasatelit.ipynb";

function Banner() {
  return <figure className="earth-banner wrap" aria-label="Citra dari orbit">
    <div className="earth-photo">
      <img className="earth-image" src={orbital} alt="Citra malam Bumi dari orbit dengan panel surya di latar depan" fetchPriority="high" />
      <div className="earth-top mono">
        <span><img className="figma-icon" src={archive} alt="" /> Pengamatan Bumi dari orbit</span>
        <span>Perspektif orbital</span>
      </div>
      <div className="focus-reticle" aria-hidden="true"><img className="figma-icon" src={sight} alt="" /></div>
      <figcaption className="earth-bottom">
        <span className="earth-title">SATU BUMI.<br />{" "}BANYAK PERSPEKTIF.</span>
        <span className="earth-description"><span className="mono">Dari orbit ke piksel</span>
          Pola yang kita lihat berubah saat spektrum dan skala pengamatan berubah.</span>
        <a className="mono scroll-cue" href="#laboratorium">Gulir untuk menjelajah <img className="figma-icon" src={scrollPlus} alt="" /></a>
      </figcaption>
    </div>
  </figure>;
}

export function Home() {
  const imageParams = { gallery_only: true, limit: 250 };
  const meta = useQuery({ queryKey: ["meta"], queryFn: ({ signal }) => get<MetaResponse>("/meta", undefined, signal) });
  const experiments = useQuery({
    queryKey: ["experiments"], queryFn: ({ signal }) => get<ExperimentSummary[]>("/experiments", undefined, signal),
  });
  const gallery = useQuery({
    queryKey: ["images", imageParams], queryFn: ({ signal }) => get<ImagesListResponse>("/images", imageParams, signal),
  });
  const readyC2 = Boolean(experiments.data?.some((item) => item.id === "C2" && item.has_results));
  const c2 = useQuery({
    enabled: readyC2, queryKey: ["experiment", "C2"],
    queryFn: ({ signal }) => get<ExperimentResult>("/experiments/C2", undefined, signal),
  });
  useQueryError("meta", "Ringkasan dataset tidak dapat dimuat.", meta.error);
  useQueryError("experiments", "Daftar percobaan tidak dapat dimuat.", experiments.error);
  useQueryError("gallery", "Galeri EuroSAT tidak dapat dimuat.", gallery.error);
  useQueryError("c2", "Ringkasan akurasi C2 tidak dapat dimuat.", c2.error);
  const images = gallery.data?.items ?? [];
  const river = images.find((image) => image.cls === "River");

  return (
    <>
      <section className="intro wrap" aria-labelledby="home-title">
        <div className="intro-kicker mono"><span>Pengamatan bumi / proyek riset mahasiswa</span><span>Beranda</span></div>
        <div className="intro-grid">
          <h1 id="home-title">BUMI,<br />{" "}DALAM FOKUS.</h1>
          <div className="intro-copy">
            <p className="intro-lead">Perspektif baru untuk memahami Bumi.</p>
            <p className="mono">Pelajari citra satelit, cari pola, dan uji aljabar Boolean melalui EuroSAT.</p>
            <Button asChild className="hero-action"><a href="#laboratorium">Jelajahi citra <img className="figma-icon" src={arrow} alt="" /></a></Button>
          </div>
        </div>
      </section>
      <Banner />
      <section className="mission wrap" aria-label="Tujuan proyek">
        <div className="split-heading">
          <div><p className="mono dim">Tujuan proyek</p><p className="mission-label">Dari pengamatan<br />{" "}ke pemahaman.</p></div>
          <p className="mission-statement">Lihat lebih dari permukaan. Temukan pola yang membentuk bentang alam dan uji bagaimana pola itu diolah sebagai data.</p>
        </div>
        <div className="mission-links mono">
          <a href="#laboratorium">Jelajahi citra EuroSAT</a>
          <Link to="/sharing">Uji pembagian rahasia</Link>
          <Link to="/percobaan">Baca hasil percobaan</Link>
        </div>
      </section>
      <HeroTwoTracks meta={meta.data} metaPending={meta.isPending} best={bestC2(c2.data)}
        bestPending={experiments.isPending || (readyC2 && c2.isPending)}
        gallery={images} galleryPending={gallery.isPending} />
      <section className="applications wrap" aria-labelledby="application-title">
        <div className="section-heading">
          <div><p className="mono dim">Ruang praktik</p><h2 id="application-title">Tiga cara membaca<br />{" "}citra satelit.</h2></div>
          <p className="section-description">Dari pencarian berdasarkan kemiripan hingga logika di balik rekonstruksi.</p>
        </div>
        <div className="application-grid">
          {cards.map((card) => <Card key={card.path} className={`application-card application-${card.tone}`}>
            <Link to={card.path}>
              {card.tone === "image" && <GalleryImage src={river?.thumb_url} fallback={delta} alt="" className="card-image" />}
              <span className="card-top mono">{card.mode}<img className="figma-icon" alt="" src={card.tone === "stone" ? inkArrow : lightArrow} /></span>
              <span className="card-body"><span className="card-title">{card.title[0]}<br />{" "}{card.title[1]}</span>{card.description}</span>
              <span className="card-foot mono">{card.label}</span>
            </Link>
          </Card>)}
        </div>
      </section>
      <section className="workflow wrap" aria-labelledby="workflow-title">
        <div className="split-heading">
          <p className="mono dim">Alur eksplorasi</p>
          <h2 id="workflow-title">Dari piksel ke temuan.<br />{" "}Tiga langkah sederhana.</h2>
        </div>
        <ol className="step-grid">
          {steps.map((step, index) => <li key={step.path}>
            <Link to={step.path}>
              <span className="step-number mono">{String(index + 1).padStart(2, "0")} <img className="figma-icon" src={mutedArrow} alt="" /></span>
              <h3>{step.title}</h3><p>{step.copy}</p>
            </Link>
          </li>)}
        </ol>
      </section>
      <section className="further" aria-labelledby="further-title">
        <div className="wrap further-grid">
          <div>
            <p className="mono dim">Pendalaman</p>
            <h2 id="further-title">Pahami hasilnya<br />{" "}lebih jauh.</h2>
            <p>Periksa data percobaan dan langkah perhitungannya.</p>
          </div>
          <div className="further-list">
            <Link to="/percobaan"><span><strong>Percobaan</strong><small className="mono">Hasil C1–C4c</small></span><img className="figma-icon" src={externalArrow} alt="" /></Link>
            <Link to="/inspector"><span><strong>Inspektor Matematika</strong><small className="mono">Rumus dan substitusi</small></span><img className="figma-icon" src={externalArrow} alt="" /></Link>
          </div>
        </div>
      </section>
      <section className="launch" aria-labelledby="launch-title">
        <div className="wrap launch-grid">
          <h2 id="launch-title">MULAI EKSPLORASI<br />{" "}CITRA SATELIT.</h2>
          <div>
            <p>Buka penjelajah citra atau lanjutkan eksplorasi di Google Colab.</p>
            <Button asChild variant="secondary" className="launch-action"><Link to="/cbir">Mulai dari CBIR <img className="figma-icon" src={externalArrow} alt="" /></Link></Button>
            <a className="colab-link mono" href={colabUrl} target="_blank" rel="noreferrer">Buka Google Colab <img className="figma-icon" src={lightArrow} alt="" /></a>
          </div>
        </div>
      </section>
    </>
  );
}
