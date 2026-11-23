import { lazy, Suspense, useEffect } from "react";
import { ArrowUpRight } from "lucide-react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import arrow from "@/assets/arrow.svg";
import disc from "@/assets/orbital-disc.svg";
import external from "@/assets/diagonal-external.svg";
import { Button } from "@/components/ui/button";
import { Home } from "@/pages/home";
import { Skeleton } from "@/components/ui/skeleton";

const CbirPage = lazy(() => import("@/pages/cbir").then((module) => ({ default: module.CbirPage })));
const SharingPage = lazy(() => import("@/pages/sharing").then((module) => ({ default: module.SharingPage })));

const routes = [
  { path: "/", label: "Beranda", description: "" },
  { path: "/cbir", label: "CBIR", description: "Pencarian citra berdasarkan kemiripan fitur." },
  { path: "/sharing", label: "Berbagi Rahasia", description: "Pembagian dan rekonstruksi citra dengan XOR." },
  { path: "/boolean", label: "Lab Boolean", description: "Eksperimen tabel kebenaran, gerbang logika, dan peta Karnaugh." },
  { path: "/percobaan", label: "Percobaan", description: "Perbandingan metode dan hasil pengukuran C1–C4c." },
  { path: "/inspector", label: "Inspektor Matematika", description: "Rumus dan langkah perhitungan dari hasil eksplorasi." },
] as const;

function Wordmark() {
  return <Link to="/" className="wordmark" aria-label="CitraSatelit — Beranda">
    <img className="figma-icon" src={disc} alt="" />
    <span>CITRASATELIT</span>
  </Link>;
}

function Header() {
  return <header className="site-header wrap">
    <a className="skip-link" href="#main">Lewati ke konten</a>
    <Wordmark />
    <nav aria-label="Navigasi utama" className="site-nav">
      {routes.map(({ path, label }) => <NavLink key={path} to={path} end={path === "/"}>{label}</NavLink>)}
    </nav>
    <Button asChild className="nav-action">
      <Link to="/cbir">Buka CBIR <img className="figma-icon" src={arrow} alt="" /></Link>
    </Button>
  </header>;
}

function Footer() {
  return <footer className="site-footer wrap">
    <div className="footer-main">
      <Link to="/" className="footer-logo">CITRASATELIT</Link>
      <p>Laboratorium citra satelit, probabilitas, dan logika berbasis EuroSAT.</p>
      <div className="footer-links mono">
        <Link to="/cbir">Jelajahi citra <img className="figma-icon" src={external} alt="" /></Link>
        <Link to="/percobaan">Hasil percobaan <img className="figma-icon" src={external} alt="" /></Link>
        <Link to="/inspector">Inspektor matematika <img className="figma-icon" src={external} alt="" /></Link>
      </div>
    </div>
    <div className="footer-line mono"><span>© CitraSatelit</span><span>Data eksperimen · EuroSAT</span></div>
  </footer>;
}

function WorkbenchPlaceholder({ title, description }: { title: string; description: string }) {
  return <section className="workbench placeholder">
    <div className="wrap">
      <span className="mono dim">CitraSatelit / {title}</span>
      <h1>{title}</h1>
      <p>{description}</p>
      <div className="placeholder-status mono">Ruang kerja sedang disiapkan.</div>
      <Button asChild variant="outline"><Link to="/">Kembali ke Beranda <ArrowUpRight aria-hidden /></Link></Button>
    </div>
  </section>;
}

function ScrollToRoute() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    const route = routes.find((item) => item.path === pathname);
    document.title = route ? `${route.label} — CitraSatelit` : "Halaman tidak ditemukan — CitraSatelit";
    if (hash) {
      document.getElementById(hash.slice(1))?.scrollIntoView();
    } else {
      window.scrollTo(0, 0);
    }
  }, [pathname, hash]);
  return null;
}

export function App() {
  return (
    <>
      <ScrollToRoute />
      <Header />
      <main id="main" tabIndex={-1}>
        <Suspense fallback={<Skeleton className="min-h-48" role="status" aria-label="Memuat ruang kerja" />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/cbir" element={<CbirPage />} />
            <Route path="/sharing" element={<SharingPage />} />
            {routes.slice(3).map(({ path, label, description }) => (
              <Route key={path} path={path} element={<WorkbenchPlaceholder title={label} description={description} />} />
            ))}
            <Route path="*" element={<WorkbenchPlaceholder title="Halaman tidak ditemukan" description="Periksa kembali alamat yang dibuka." />} />
          </Routes>
        </Suspense>
      </main>
      <Footer />
    </>
  );
}
