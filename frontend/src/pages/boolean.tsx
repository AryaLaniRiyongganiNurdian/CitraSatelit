import { useState } from "react";
import { Workbench } from "@/components/workbench";
import type { ProveRequest } from "@/types/api";
import { ExpressionWorkbench, presets, XorGateDemo } from "./boolean/expression";
import { KMapWorkbench } from "./boolean/kmap";
import { LawProofsPanel } from "./boolean/law-proofs";
import "./boolean/boolean.css";

const links = [
  { id: "ekspresi", title: "Ekspresi dan pembuktian" }, { id: "kmap", title: "Peta Karnaugh" },
  { id: "hukum", title: "Bukti aljabar" }, { id: "gerbang", title: "Gerbang XOR" },
];

export function BooleanPage() {
  const [expressions, setExpressions] = useState<ProveRequest>(() => ({
    lhs: presets[0]?.lhs ?? "", rhs: presets[0]?.rhs ?? "",
  }));
  return <Workbench title="Lab Boolean" description="Periksa ekspresi dengan tabel kebenaran, susun rangkaian, dan sederhanakan minterm di peta Karnaugh."
    page="boolean" links={links}>
    <div className="boolean-layout">
      <div className="lab-stack">
        <ExpressionWorkbench expressions={expressions} onChange={setExpressions} />
        <XorGateDemo />
      </div>
      <div className="lab-stack">
        <KMapWorkbench />
        <LawProofsPanel onApply={setExpressions} />
      </div>
    </div>
  </Workbench>;
}
