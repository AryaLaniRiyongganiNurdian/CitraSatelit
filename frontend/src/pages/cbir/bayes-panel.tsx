import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Choice, DataTable, NumberField, Panel, RequestState, Stats } from "@/components/workbench";
import { post } from "@/lib/api";
import { classLabel, formatNumber, formatPercent, useApiMutation } from "@/lib/workbench";
import { useInspector } from "@/contexts";
import type { BayesRequest, BayesResponse, EvidenceFeature, GnbMode, GnbRequest, GnbResponse, ImageMeta, MetaResponse } from "@/types/api";

const evidences: Record<EvidenceFeature, string> = { mean_gray: "Rata-rata keabuan", mean_ndvi: "Rata-rata NDVI", mean_ndwi: "Rata-rata NDWI" };
const gnbModes: GnbMode[] = ["mle", "grid2", "grid4", "ms_mle"];

export function BayesPanel({ image, meta }: { image: ImageMeta | null; meta: MetaResponse | undefined }) {
  const [evidence, setEvidence] = useState<EvidenceFeature>("mean_gray");
  const [mode, setMode] = useState<GnbMode>("mle");
  const { setLatest } = useInspector();
  const bayes = useApiMutation((body: BayesRequest) => post<BayesResponse, BayesRequest>("/cbir/bayes", body), {
    failure: "Klasifikasi Bayes gagal.", onSuccess: (result) => setLatest("cbir", result.inspector),
  });
  const gnb = useApiMutation((body: GnbRequest) => post<GnbResponse, GnbRequest>("/cbir/gnb", body), {
    failure: "Gaussian Naive Bayes gagal.", onSuccess: (result) => setLatest("cbir", result.inspector),
  });

  return <Panel title="Klasifikasi Bayes" id="bayes">
    <Tabs defaultValue="discrete">
      <TabsList variant="line" aria-label="Metode klasifikasi">
        <TabsTrigger value="discrete">Bayes diskret</TabsTrigger>
        <TabsTrigger value="gnb">Gaussian Naive Bayes</TabsTrigger>
      </TabsList>
      <TabsContent value="discrete" className="lab-stack">
        <form className="lab-stack" onSubmit={(event) => {
          event.preventDefault();
          if (!image) return;
          const values = new FormData(event.currentTarget);
          bayes.run({ image_id: image.id, evidence, levels: Number(values.get("levels")), alpha: Number(values.get("alpha")) });
        }}>
          <div className="lab-fields">
            <Choice label="Bukti" value={evidence} onChange={setEvidence}
              options={(meta?.evidence_options ?? ["mean_gray"]).map((value) => ({
                value, label: evidences[value], disabled: value !== "mean_gray" && !image?.has_ms,
              }))} />
            <NumberField label="Tingkat kuantisasi" name="levels" min={4} max={16} defaultValue={8} required />
            <NumberField label="Alpha Laplace" name="alpha" min={Number.MIN_VALUE} step="any" defaultValue={1} required />
          </div>
          <div className="lab-actions"><Button type="submit" disabled={!image || bayes.isPending}>Hitung Bayes diskret</Button></div>
        </form>
        <RequestState pending={bayes.isPending} error={bayes.error} empty="Pilih citra dan hitung posterior Bayes.">
          {bayes.data && <>
            <Stats items={[
              { label: "Prediksi", value: classLabel(meta, bayes.data.predicted) },
              { label: "Nilai bukti", value: formatNumber(bayes.data.evidence_value) },
              { label: "Bin bukti", value: bayes.data.evidence_bin },
              { label: "P(B)", value: formatPercent(bayes.data.evidence_total) },
            ]} />
            <DataTable columns={["Kelas", "Prior", "Likelihood", "P(A ∩ B)", "Posterior"]} rows={bayes.data.rows.map((row) => [
              classLabel(meta, row.cls), formatPercent(row.prior), formatPercent(row.likelihood), formatPercent(row.joint), formatPercent(row.posterior),
            ])} />
          </>}
        </RequestState>
      </TabsContent>
      <TabsContent value="gnb" className="lab-stack">
        <form className="lab-stack" onSubmit={(event) => {
          event.preventDefault();
          if (image) gnb.run({ image_id: image.id, mode });
        }}>
          <Choice label="Fitur Gaussian" value={mode} onChange={setMode}
            options={gnbModes.map((value) => ({ value, label: meta?.feature_modes.find((item) => item.mode === value)?.label ?? value,
              disabled: value === "ms_mle" && !image?.has_ms }))} />
          <div className="lab-actions"><Button type="submit" disabled={!image || gnb.isPending}>Hitung Gaussian Naive Bayes</Button></div>
        </form>
        <RequestState pending={gnb.isPending} error={gnb.error} empty="Pilih citra dan hitung posterior Gaussian.">
          {gnb.data && <>
            <Stats items={[{ label: "Prediksi", value: classLabel(meta, gnb.data.predicted) }]} />
            <DataTable columns={["Kelas", "Prior", "Log posterior tak ternormalisasi", "Posterior"]} rows={gnb.data.rows.map((row) => [
              classLabel(meta, row.cls), formatPercent(row.prior), row.log_posterior_unnorm, formatPercent(row.posterior),
            ])} />
          </>}
        </RequestState>
      </TabsContent>
    </Tabs>
  </Panel>;
}
