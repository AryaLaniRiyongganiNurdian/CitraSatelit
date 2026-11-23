import { useState } from "react";
import { ImagePicker } from "@/components/image-picker";
import { Button } from "@/components/ui/button";
import { Empty, Panel, RequestState, Workbench } from "@/components/workbench";
import { useInspector, useSharing } from "@/contexts";
import { post } from "@/lib/api";
import { useApiMutation, useMeta } from "@/lib/workbench";
import type { ImageMeta, SplitRequest, SplitResponse } from "@/types/api";
import { AttackTabs } from "./sharing/attack-tabs";
import { DownloadUploadPanel, ReconstructPanel } from "./sharing/reconstruction";
import { BitflipPanel, SecurityPanel, TamperPanel } from "./sharing/simulations";
import { ShareControls, ShareGallery } from "./sharing/split-panels";

type SplitInput = { request: SplitRequest; source: ImageMeta };

export function SharingPage() {
  const { data: meta } = useMeta();
  const { session, setSession } = useSharing();
  const { setLatest } = useInspector();
  const [image, setImage] = useState<ImageMeta | null>(session?.image ?? null);
  const split = useApiMutation(({ request }: SplitInput) => post<SplitResponse, SplitRequest>("/sharing/split", request), {
    onSuccess: (result, { request, source }) => {
      setSession({ session_id: result.session_id, request, image: source, result });
      setLatest("sharing", result.inspector);
    },
    success: "Citra berhasil dibagi.", failure: "Pembagian citra gagal.",
  });
  const activeSession = session?.expired ? null : session;

  return <Workbench title="Berbagi Rahasia" description="Bagi citra menjadi share XOR, gabungkan kembali, lalu ukur dampak perubahan pada share."
    page="sharing" links={[
      { id: "pembagian", title: "Pembagian" },
      ...(activeSession ? [
        { id: "galeri-share", title: "Galeri share" }, { id: "rekonstruksi", title: "Rekonstruksi" },
        { id: "tamper", title: "Perubahan share" }, { id: "keamanan", title: "Keamanan" }, { id: "bitflip", title: "Bit-flip" },
      ] : []),
      { id: "berkas-share", title: "Unduh dan unggah" }, { id: "demo-xor", title: "Demo XOR" },
    ]}>
    <div className="lab-layout">
      <Panel title="Citra sumber"><ImagePicker value={image} onSelect={setImage} /></Panel>
      <div className="lab-stack">
        <Panel title="Pembagian XOR" id="pembagian">
          <ShareControls image={image} meta={meta} defaults={session?.request} busy={split.isPending}
            onSplit={(request) => { if (image) split.run({ request, source: image }); }} />
          {session?.expired && <div className="lab-expired">
            <p role="status">Sesi share sudah berakhir. Buat sesi baru dengan parameter terakhir.</p>
            <Button type="button" variant="outline" disabled={split.isPending}
              onClick={() => split.run({ request: session.request, source: session.image })}>Buat ulang sesi</Button>
          </div>}
          {(split.isPending || split.error) && <RequestState pending={split.isPending} error={split.error} empty={null} loading="Membagi citra" />}
          {activeSession
            ? <p className="mono dim">Sesi aktif · {activeSession.image.id} · {activeSession.result.n} share</p>
            : !session && !split.isPending && !split.error && <Empty>Galeri share dan simulasi tersedia setelah citra dibagi.</Empty>}
        </Panel>
        {activeSession && <fieldset className="lab-fieldset lab-stack" key={activeSession.session_id} disabled={split.isPending}>
          <ShareGallery data={activeSession.result} image={activeSession.image} />
          <ReconstructPanel session={activeSession.result} />
        </fieldset>}
      </div>
    </div>
    <div className="lab-stack lab-section-gap">
      <DownloadUploadPanel session={activeSession?.result} reference={session?.request} />
      {activeSession && <fieldset className="lab-fieldset lab-stack" key={activeSession.session_id} disabled={split.isPending}>
        <TamperPanel session={activeSession.result} />
        <SecurityPanel session={activeSession.result} image={activeSession.image} />
        <BitflipPanel session={activeSession.result} />
      </fieldset>}
      <AttackTabs image={image} />
    </div>
  </Workbench>;
}
