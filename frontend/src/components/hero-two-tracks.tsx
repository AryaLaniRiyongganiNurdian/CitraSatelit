import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import delta from "@/assets/lena-delta.jpg";
import diagonal from "@/assets/diagonal-light.svg";
import magnify from "@/assets/search.svg";
import action from "@/assets/search-arrow.svg";
import details from "@/assets/details-arrow.svg";
import plus from "@/assets/zoom-in.svg";
import minus from "@/assets/zoom-out.svg";
import expand from "@/assets/expand.svg";
import selection from "@/assets/selection-plus.svg";
import layers from "@/assets/layers.svg";
import chevron from "@/assets/down.svg";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { NumberTicker } from "@/components/magicui/number-ticker";
import { get } from "@/lib/api";
import { formatAccuracy, formatInteger, useQueryError } from "@/lib/home-data";
import type { ImageMeta, ImagePreview, MetaResponse } from "@/types/api";

const tracks = {
  cbir: { title: "Pencarian Citra", url: "/cbir", summary: "Bandingkan histogram dan fitur spektral untuk menemukan citra serupa." },
  xor: { title: "Berbagi Rahasia", url: "/sharing", summary: "Bagi citra menjadi beberapa share dan rekonstruksi kembali dengan XOR." },
};
type Track = keyof typeof tracks;

const views = { rgb: "Warna alami", ndvi: "NDVI", ndwi: "NDWI" };
type View = keyof typeof views;
type Scene = { id: string; view: View };

export function GalleryImage({ src, fallback, alt, className }: {
  src?: string; fallback: string; alt: string; className?: string;
}) {
  const [failed, setFailed] = useState<string>();
  const resolved = src && src !== failed ? src : fallback;
  return <img src={resolved} alt={alt} className={className} onError={() => setFailed(resolved)} />;
}

function SelectArrow() {
  return <img alt="" className="figma-icon" src={chevron} />;
}

function Metric({ label, pending, children }: {
  label: string; pending: boolean; children: React.ReactNode;
}) {
  return <div className="scene-stat"><dt>{label}</dt><dd>
    {pending ? <Skeleton className="metric-skeleton" aria-label={`Memuat ${label.toLowerCase()}`} /> : children}
  </dd></div>;
}

export function HeroTwoTracks({ meta, metaPending, best, bestPending, gallery, galleryPending }: {
  meta: MetaResponse | undefined; metaPending: boolean;
  best: { method: string; accuracy: number } | null; bestPending: boolean;
  gallery: ImageMeta[]; galleryPending: boolean;
}) {
  const [track, setTrack] = useState<Track>("cbir");
  const [term, setTerm] = useState("");
  const [draftId, setDraftId] = useState("reference");
  const [view, setView] = useState<View>("rgb");
  const [scene, setScene] = useState<Scene>({ id: "reference", view: "rgb" });
  const [failedSceneSrc, setFailedSceneSrc] = useState<string>();
  const [zoom, setZoom] = useState(1);
  const [notice, setNotice] = useState("");
  const current = tracks[track];
  const search = term.trim().toLowerCase();
  const matched = search ? gallery.filter((image) =>
    [image.id, image.cls, image.cls && meta?.class_labels_id[image.cls]]
      .some((value) => value?.toLowerCase().includes(search)),
  ) : gallery;
  const selected = gallery.find((item) => item.id === scene.id);
  const preview = useQuery({
    queryKey: ["images", scene.id, "preview", scene.view],
    enabled: Boolean(selected && scene.view !== "rgb"),
    queryFn: ({ signal }) => get<ImagePreview>(`/images/${encodeURIComponent(scene.id)}/preview`, { view: scene.view }, signal),
  });
  useQueryError("preview", "Pratinjau spektral tidak dapat dimuat.", preview.error);
  const imageSrc = scene.view === "rgb" ? selected?.thumb_url : preview.data?.data_uri ?? selected?.thumb_url;
  const imageFailed = Boolean(imageSrc && imageSrc === failedSceneSrc);
  const visibleScene = imageFailed ? undefined : selected;
  const sceneLabel = visibleScene
    ? (scene.view === "rgb" || preview.data ? views[scene.view] : views.rgb)
    : "Komposit warna semu";
  const imageLabel = visibleScene ? `Citra EuroSAT ${visibleScene.id}` : "Komposit satelit Delta Sungai Lena";
  const sceneImage = {
    src: visibleScene ? imageSrc : delta,
    alt: imageLabel,
    className: visibleScene ? "pixelated" : undefined,
    onError: () => { if (visibleScene) setFailedSceneSrc(imageSrc); },
  };
  const previewPending = Boolean(selected && scene.view !== "rgb" && preview.isPending);
  const pendingLabel = galleryPending ? "Memuat galeri EuroSAT" : previewPending ? "Memuat pratinjau spektral" : null;

  function show(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const chosen = matched.find((image) => image.id === draftId) ?? (search ? matched[0] : undefined);
    if (!chosen && search) {
      setNotice("Tidak ada citra yang sesuai dengan pencarian.");
      return;
    }
    setScene({ id: chosen?.id ?? "reference", view });
    setNotice(chosen ? `Menampilkan ${chosen.id}.` : "Menampilkan citra referensi.");
    setFailedSceneSrc(undefined);
    setZoom(1);
  }

  return <section className="workbench explorer" id="laboratorium" aria-labelledby="workbench-title">
    <div className="wrap explorer-inner">
      <div className="section-heading explorer-heading">
        <div><p className="mono dim">Penjelajah citra</p><h2 id="workbench-title">Lihat lebih dekat.</h2></div>
        <Link className="text-link mono" to="/cbir">Buka katalog citra <img className="figma-icon" src={diagonal} alt="" /></Link>
      </div>
      <form className="explorer-controls" aria-label="Pilih citra pratinjau" onSubmit={show}>
        <label className="scene-search">
          <img className="figma-icon" src={magnify} alt="" />
          <Input value={term} onChange={(event) => { setTerm(event.currentTarget.value); setDraftId("reference"); }}
            aria-label="Cari ID atau kelas citra" placeholder="Cari ID atau kelas citra" />
        </label>
        <Select value={track} onValueChange={(value) => { if (value === "cbir" || value === "xor") setTrack(value); }}>
          <SelectTrigger aria-label="Jalur eksplorasi" className="toolbar-select" hideIcon><SelectValue /><SelectArrow /></SelectTrigger>
          <SelectContent position="popper" className="toolbar-menu"><SelectItem value="cbir">Pencarian citra</SelectItem><SelectItem value="xor">Berbagi rahasia</SelectItem></SelectContent>
        </Select>
        <Select value={draftId} onValueChange={setDraftId}>
          <SelectTrigger aria-label="Citra galeri" className="toolbar-select" hideIcon>
            <SelectValue /><SelectArrow />
          </SelectTrigger>
          <SelectContent position="popper" className="toolbar-menu">
            <SelectItem value="reference">Citra referensi</SelectItem>
            {matched.map((image) => <SelectItem key={image.id} value={image.id}>{image.id}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={view} onValueChange={(value) => {
          if (value === "rgb" || value === "ndvi" || value === "ndwi") setView(value);
        }}>
          <SelectTrigger aria-label="Tampilan spektral" className="toolbar-select" hideIcon>
            <SelectValue /><SelectArrow />
          </SelectTrigger>
          <SelectContent position="popper" className="toolbar-menu">
            {Object.entries(views).map(([key, label]) => <SelectItem key={key} value={key}>{label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button type="submit" className="toolbar-submit">Tampilkan <img className="figma-icon" src={action} alt="" /></Button>
      </form>
      <p className="sr-only" role="status">{notice}</p>
      <div className="scene">
        <aside className="scene-sidebar">
          <div className="scene-index mono dim"><span>Ruang kerja</span><span>EuroSAT</span></div>
          <h3>{current.title}</h3>
          <Badge variant="default">{track === "cbir" ? "CBIR" : "XOR"}</Badge>
          <dl>
            <Metric label="Citra terindeks" pending={metaPending}>
              {meta ? <><span className="sr-only">{formatInteger(meta.dataset.n_total)}</span><NumberTicker aria-hidden value={meta.dataset.n_total} /></> : "—"}
            </Metric>
            <Metric label="Kelas EuroSAT" pending={metaPending}>{meta ? formatInteger(meta.classes.length) : "—"}</Metric>
            <Metric label="Akurasi terbaik C2" pending={bestPending}>{best ? formatAccuracy(best.accuracy) : "—"}</Metric>
          </dl>
          <p className="scene-copy">{current.summary}{best && track === "cbir" ? ` Metode C2 terbaik: ${best.method}.` : ""}</p>
          <Button variant="outline" asChild className="scene-action">
            <Link to={current.url}>Buka ruang kerja <img className="figma-icon" src={details} alt="" /></Link>
          </Button>
        </aside>
        <div className="scene-image">
          <div className="scene-visual" style={{ transform: `scale(${zoom})` }}>
            <img {...sceneImage} />
          </div>
          <span className="scene-tag mono">{sceneLabel}</span>
          <div className="scene-tools">
            <Button type="button" variant="secondary" size="icon" aria-label="Perbesar citra" disabled={zoom >= 2.5}
              onClick={() => setZoom((value) => Math.min(2.5, value + 0.25))}><img className="figma-icon" src={plus} alt="" /></Button>
            <Button type="button" variant="secondary" size="icon" aria-label="Perkecil citra" disabled={zoom <= 1}
              onClick={() => setZoom((value) => Math.max(1, value - 0.25))}><img className="figma-icon" src={minus} alt="" /></Button>
            <Dialog>
              <DialogTrigger asChild><Button variant="secondary" size="icon" aria-label="Buka citra penuh">
                <img className="figma-icon" src={expand} alt="" />
              </Button></DialogTrigger>
              <DialogContent className="scene-dialog" aria-describedby={undefined}>
                <DialogTitle>{imageLabel}</DialogTitle>
                <img {...sceneImage} />
              </DialogContent>
            </Dialog>
          </div>
          <div className="selection-box" aria-hidden="true">
            <span className="mono">Area pengamatan</span>
            <img className="figma-icon" src={selection} alt="" />
          </div>
          <div className="scene-caption">
            <p className="mono">{visibleScene?.id ?? "Delta Sungai Lena"}</p>
            <p>{visibleScene ? (visibleScene.cls && meta?.class_labels_id[visibleScene.cls]) ?? "Galeri EuroSAT" : "Citra referensi pengamatan bumi."}</p>
          </div>
          {!visibleScene && <span className="north-mark mono" aria-label="Utara">U ↑</span>}
        </div>
      </div>
      <div className="scene-attribution">
        <div>
          <p className="mono dim">{visibleScene ? "Sumber: galeri EuroSAT" : "Citra: NASA Earth Observatory / USGS · Landsat 7"}</p>
          {pendingLabel ? <Skeleton role="status" className="status-skeleton" aria-label={pendingLabel} /> :
            <p>{notice && !notice.startsWith("Menampilkan")
              ? notice
              : imageFailed ? "Citra EuroSAT tidak dapat dimuat. Menampilkan citra referensi."
                : !gallery.length ? "Galeri belum tersedia. Citra referensi tetap dapat dilihat."
                  : selected && preview.isError ? "Pratinjau spektral tidak tersedia. Menampilkan warna alami."
                    : "Pilih citra dan tampilan untuk memeriksa perbedaan antarkanal."}</p>}
        </div>
        <div className="mono"><img className="figma-icon" src={layers} alt="" /> {sceneLabel}</div>
      </div>
    </div>
  </section>;
}
