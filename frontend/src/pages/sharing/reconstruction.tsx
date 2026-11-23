import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Empty, Panel, Preview, RequestState, Stats } from "@/components/workbench";
import { useInspector } from "@/contexts";
import { postForm } from "@/lib/api";
import { formatNumber, useApiMutation } from "@/lib/workbench";
import type { ReconMetrics, ReconstructRequest, ReconstructResponse, SplitRequest, SplitResponse } from "@/types/api";
import { useSharingOperation } from "./session";

export function ReconMetricsView({ metrics }: { metrics: ReconMetrics | null }) {
  if (!metrics) return <Empty>Metrik pembanding belum tersedia.</Empty>;
  return <Stats items={[
    { label: "Hasil", value: metrics.identical == null ? "—" : metrics.identical ? "Identik" : "Berbeda" },
    { label: "MSE", value: formatNumber(metrics.mse) },
    { label: "PSNR", value: metrics.psnr_is_infinite ? "tak hingga" : metrics.psnr_db == null ? "—" : formatNumber(metrics.psnr_db) + " dB" },
    { label: "Piksel berbeda", value: formatNumber(metrics.pixels_different) },
    { label: "Selisih maksimum", value: formatNumber(metrics.max_abs_diff) },
  ]} />;
}

function ReconstructionView({ result, uploaded = false }: { result: ReconstructResponse; uploaded?: boolean }) {
  return <div className="lab-stack">
    <div className="lab-preview-grid">
      <Preview data={result.preview} label="Hasil rekonstruksi" />
      <div className="lab-summary lab-stack">
        <Stats items={[
          { label: "Share digunakan", value: uploaded ? result.used_indices.length : result.used_indices.length + " / " + result.n_total },
          { label: "Entropi", value: formatNumber(result.entropy_bits) + " bit" },
        ]} />
        {!uploaded && !result.is_complete && <p className="dim">Subset parsial menghasilkan derau sampai semua share digabung.</p>}
        <ReconMetricsView metrics={result.metrics} />
      </div>
    </div>
  </div>;
}

export function ReconstructPanel({ session }: { session: SplitResponse }) {
  const [selected, setSelected] = useState(() => session.shares.map((share) => share.index));
  const reconstruct = useSharingOperation<ReconstructResponse, ReconstructRequest>("/sharing/reconstruct", {
    sessionId: session.session_id, success: "Rekonstruksi selesai.", failure: "Rekonstruksi gagal.",
  });
  return <Panel title="Rekonstruksi XOR" id="rekonstruksi">
    <fieldset className="lab-checklist">
      <legend>Pilih subset share</legend>
      {session.shares.map(({ index }) => <label key={index}>
        <input type="checkbox" checked={selected.includes(index)} onChange={(event) => {
          const checked = event.currentTarget.checked;
          setSelected((current) => checked ? [...current, index] : current.filter((value) => value !== index));
        }} /> Share {index + 1}
      </label>)}
    </fieldset>
    <div className="lab-actions">
      <Button type="button" disabled={!selected.length || reconstruct.isPending} onClick={() => reconstruct.run({
        session_id: session.session_id, share_indices: [...selected].sort((a, b) => a - b),
      })}>Rekonstruksi dari pilihan</Button>
    </div>
    <RequestState pending={reconstruct.isPending} error={reconstruct.error} empty="Hasil akan muncul setelah share digabung.">
      {reconstruct.data && <ReconstructionView result={reconstruct.data} />}
    </RequestState>
  </Panel>;
}

export function DownloadUploadPanel({ session, reference }: { session?: SplitResponse; reference?: SplitRequest }) {
  const [files, setFiles] = useState<File[]>([]);
  const [compare, setCompare] = useState(true);
  const { setLatest } = useInspector();
  const upload = useApiMutation((form: FormData) => postForm<ReconstructResponse>("/sharing/reconstruct-upload", form), {
    success: "Share unggahan berhasil digabung.", failure: "Share unggahan gagal digabung.",
    onSuccess: (data) => setLatest("sharing", data.inspector),
  });
  const validCount = files.length >= 2 && files.length <= 8;
  const invalidFormat = files.some((file) => !/\.(png|npy)$/i.test(file.name));

  return <Panel title="Unduh dan unggah ulang" id="berkas-share">
    {session ? <div className="lab-stack">
      <h3>Unduh share sesi</h3>
      {session.shares.map((share) => <div key={share.index} className="lab-actions">
        <span className="mono">Share {share.index + 1}</span>
        {share.download_urls.png && <Button asChild variant="outline" size="sm">
          <a href={share.download_urls.png} aria-label={"Unduh PNG Share " + (share.index + 1)}>PNG</a>
        </Button>}
        <Button asChild variant="outline" size="sm">
          <a href={share.download_urls.npy} aria-label={"Unduh NPY Share " + (share.index + 1)}>NPY</a>
        </Button>
      </div>)}
      {session.band_mode === "ms13" && <small className="dim">Share 13 band tersedia dalam format NPY.</small>}
    </div> : <Empty>Bagi citra untuk memperoleh tautan unduhan sesi.</Empty>}
    <form className="lab-stack" onSubmit={(event) => {
      event.preventDefault();
      if (!validCount || invalidFormat) {
        toast.error("Pilih 2 sampai 8 berkas PNG atau NPY.");
        return;
      }
      const form = new FormData();
      files.forEach((file) => form.append("files", file));
      if (reference && compare && reference.band_mode !== "band") {
        form.append("original_image_id", reference.image_id);
        form.append("band_mode", reference.band_mode);
      }
      upload.run(form);
    }}>
      <div className="lab-field">
        <label htmlFor="share-files">Berkas share PNG atau NPY (2–8)</label>
        <Input id="share-files" type="file" multiple accept=".png,.npy" disabled={upload.isPending}
          onChange={(event) => { setFiles(Array.from(event.currentTarget.files ?? [])); }} />
      </div>
      {files.length > 0 && <small className={validCount && !invalidFormat ? "dim" : "lab-inline-error"}>
        {invalidFormat ? "Gunakan berkas PNG atau NPY." : validCount ? files.length + " berkas dipilih." : "Pilih minimal 2 dan maksimal 8 berkas."}
      </small>}
      {reference && reference.band_mode !== "band" && <label className="lab-check">
        <input type="checkbox" checked={compare} onChange={(event) => setCompare(event.currentTarget.checked)} />
        Bandingkan dengan citra sumber sesi
      </label>}
      {reference?.band_mode === "band" && <small className="dim">Perbandingan unggah ulang untuk satu band memerlukan indeks band pada API.</small>}
      <div className="lab-actions"><Button type="submit" disabled={!validCount || invalidFormat || upload.isPending}>Rekonstruksi unggahan</Button></div>
    </form>
    <RequestState pending={upload.isPending} error={upload.error} empty="Unggah share yang ingin digabung.">
      {upload.data && <ReconstructionView result={upload.data} uploaded />}
    </RequestState>
  </Panel>;
}
