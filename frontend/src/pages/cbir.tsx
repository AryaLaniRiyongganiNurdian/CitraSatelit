import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ImagePicker } from "@/components/image-picker";
import { Panel, RequestState, Workbench } from "@/components/workbench";
import { post } from "@/lib/api";
import { useQueryError } from "@/lib/home-data";
import { useInspectorResult, useMeta } from "@/lib/workbench";
import type { FeaturesRequest, FeaturesResponse, ImageMeta, SearchRequest, SearchResponse } from "@/types/api";
import { defaults, FeatureControls, type Criteria, type Settings } from "./cbir/feature-controls";
import { QueryPanel, ResultGrid } from "./cbir/search-panels";
import { EvalPanel, LivePanel } from "./cbir/evaluation-panels";
import { BayesPanel } from "./cbir/bayes-panel";

const links = [
  { id: "pencarian", title: "Pencarian" }, { id: "evaluasi", title: "Evaluasi" },
  { id: "percobaan-langsung", title: "Percobaan langsung" }, { id: "bayes", title: "Bayes" },
];

export function CbirPage() {
  const { data: meta } = useMeta();
  const [image, setImage] = useState<ImageMeta | null>(null);
  const [configured, setConfigured] = useState<Settings>();
  const settings: Settings = configured ?? { ...(meta?.defaults ?? defaults), database: "all" };
  const [submitted, setSubmitted] = useState<SearchRequest>();
  const moment = meta?.feature_modes.find((item) => item.mode === settings.mode)?.kind === "moment";
  const criteria: Criteria = { mode: settings.mode, bins: moment ? defaults.bins : settings.bins,
    metric: moment ? "euclid" : settings.metric };
  const featureRequest = submitted && { image_id: submitted.image_id, mode: submitted.mode, bins: submitted.bins };
  const features = useQuery({
    queryKey: ["features", featureRequest], enabled: Boolean(featureRequest),
    queryFn: ({ signal }) => {
      if (!featureRequest) throw new Error("Pilih citra untuk ekstraksi fitur.");
      return post<FeaturesResponse, FeaturesRequest>("/cbir/features", featureRequest, signal);
    },
  });
  const search = useQuery({
    queryKey: ["search", submitted], enabled: Boolean(submitted),
    queryFn: ({ signal }) => {
      if (!submitted) throw new Error("Pilih citra untuk pencarian.");
      return post<SearchResponse, SearchRequest>("/cbir/search", submitted, signal);
    },
  });
  useQueryError("cbir-features", "Ekstraksi fitur gagal.", features.error);
  useQueryError("cbir-search", "Pencarian citra gagal.", search.error);
  useInspectorResult("cbir", features.data?.inspector, features.dataUpdatedAt);
  useInspectorResult("cbir", search.data?.inspector, search.dataUpdatedAt);

  return <Workbench title="CBIR" description="Cari citra EuroSAT yang mirip dan periksa fitur, jarak, serta peluang kelasnya."
    page="cbir" links={links}>
    <div className="lab-layout">
      <Panel title="Citra kueri"><ImagePicker value={image} onSelect={(selected) => {
        if (selected.id !== image?.id) setSubmitted(undefined);
        setImage(selected);
      }} /></Panel>
      <div className="lab-stack">
        <Panel title="Konfigurasi pencarian" id="pencarian">
          <FeatureControls settings={settings} onChange={setConfigured} meta={meta} image={image}
            busy={features.isFetching || search.isFetching} onSubmit={() => {
              if (!image || settings.k === "") return;
              const request: SearchRequest = { ...criteria, image_id: image.id, k: settings.k, database: settings.database };
              if (features.isError && featureRequest?.image_id === request.image_id && featureRequest.mode === request.mode && featureRequest.bins === request.bins) void features.refetch();
              if (search.isError && submitted?.image_id === request.image_id && submitted.mode === request.mode &&
                submitted.bins === request.bins && submitted.metric === request.metric && submitted.k === request.k &&
                submitted.database === request.database) void search.refetch();
              setSubmitted(request);
            }} />
        </Panel>
        <Panel title="Hasil pencarian">
          <RequestState pending={Boolean(submitted) && (search.isPending || search.isFetching)} error={search.error}
            empty="Pilih citra lalu jalankan pencarian.">
            {search.data && <ResultGrid result={search.data} meta={meta} />}
          </RequestState>
        </Panel>
        <Panel title="Fitur citra kueri">
          <RequestState pending={Boolean(submitted) && (features.isPending || features.isFetching)} error={features.error}
            empty="Ekstraksi fitur dijalankan bersama pencarian.">
            {features.data && <QueryPanel features={features.data} />}
          </RequestState>
        </Panel>
        <EvalPanel criteria={criteria} meta={meta} />
        <LivePanel criteria={criteria} meta={meta} k={settings.k || defaults.k} />
        <BayesPanel key={image?.id} image={image} meta={meta} />
      </div>
    </div>
  </Workbench>;
}
