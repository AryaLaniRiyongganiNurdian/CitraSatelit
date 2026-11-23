import { lazy, Suspense } from "react";
import { ArrowUpRight, PanelRightOpen } from "lucide-react";
import { Link } from "react-router-dom";
import { useInspector, type WorkbenchSource } from "@/contexts";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import "./inspector.css";

const InspectorView = lazy(() => import("./inspector-view").then((module) => ({ default: module.InspectorView })));

export function InspectorDrawer({ source }: { source: WorkbenchSource }) {
  const { latest } = useInspector();
  const inspector = latest[source];
  return <Dialog>
    <DialogTrigger asChild>
      <Button type="button" variant="outline">Buka Math Inspector <PanelRightOpen aria-hidden="true" /></Button>
    </DialogTrigger>
    <DialogContent className="workbench inspector-drawer">
      <div className="inspector-drawer-header">
        <DialogTitle>Inspektor Matematika</DialogTitle>
        <DialogDescription>Langkah perhitungan dari ruang kerja aktif.</DialogDescription>
      </div>
      {inspector ? <Suspense fallback={<Skeleton role="status" aria-label="Memuat langkah perhitungan" className="inspector-skeleton" />}>
        <InspectorView inspector={inspector} />
      </Suspense> : <p className="lab-empty">Jalankan komputasi di ruang kerja ini untuk menampilkan rumus dan langkahnya.</p>}
      <div className="lab-actions">
        <DialogClose asChild>
          <Button asChild variant="outline">
            <Link to={"/inspector?source=" + source}>Buka halaman penuh <ArrowUpRight aria-hidden="true" /></Link>
          </Button>
        </DialogClose>
      </div>
    </DialogContent>
  </Dialog>;
}
