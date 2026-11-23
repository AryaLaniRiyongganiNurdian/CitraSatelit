import { lazy, Suspense, useEffect } from "react";
import { ArrowUpRight } from "lucide-react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import arrow from "@/assets/arrow.svg";
import disc from "@/assets/orbital-disc.svg";
import external from "@/assets/diagonal-external.svg";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const Home = lazy(() => import("@/pages/home").then((module) => ({ default: module.Home })));
const BooleanPage = lazy(() => import("@/pages/boolean").then((module) => ({ default: module.BooleanPage })));
const ExperimentsPage = lazy(() => import("@/pages/experiments").then((module) => ({ default: module.ExperimentsPage })));
const InspectorPage = lazy(() => import("@/pages/inspector").then((module) => ({ default: module.InspectorPage })));
const CbirPage = lazy(() => import("@/pages/cbir").then((module) => ({ default: module.CbirPage })));
const SharingPage = lazy(() => import("@/pages/sharing").then((module) => ({ default: module.SharingPage })));

const routes = [
  { path: "/", label: "Beranda" },
  { path: "/cbir", label: "CBIR" },
  { path: "/sharing", label: "Berbagi Rahasia" },
  { path: "/boolean", label: "Lab Boolean" },
  { path: "/percobaan", label: "Percobaan" },
  { path: "/inspector", label: "Inspektor Matematika" },
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

function NotFound() {
  return <section className="workbench placeholder">
    <div className="wrap">
      <h1>Halaman tidak ditemukan</h1>
      <p>Periksa kembali alamat yang dibuka.</p>
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

function RouteLoading({ home }: { home: boolean }) {
  return <section className={home ? "route-loading" : "workbench route-loading"}
    role="status" aria-label="Memuat halaman">
    <div className="wrap route-loading-grid">
      <Skeleton className="route-loading-title" />
      <Skeleton className="route-loading-copy" />
      <Skeleton className="route-loading-panel" />
    </div>
  </section>;
}

export function App() {
  const { pathname } = useLocation();
  return (
    <>
      <ScrollToRoute />
      <Header />
      <main id="main" tabIndex={-1}>
        <Suspense fallback={<RouteLoading home={pathname === "/"} />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/cbir" element={<CbirPage />} />
            <Route path="/sharing" element={<SharingPage />} />
            <Route path="/boolean" element={<BooleanPage />} />
            <Route path="/percobaan" element={<ExperimentsPage />} />
            <Route path="/inspector" element={<InspectorPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </main>
      <Footer />
    </>
  );
}
