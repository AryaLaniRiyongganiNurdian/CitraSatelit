import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Choice, Panel, RequestState } from "@/components/workbench";
import { get } from "@/lib/api";
import { useQueryError } from "@/lib/home-data";
import type { BooleanLaw, ProveRequest } from "@/types/api";
import { ProofSteps } from "./expression";

export function LawProofsPanel({ onApply }: { onApply: (expressions: ProveRequest) => void }) {
  const [index, setIndex] = useState(0);
  const catalog = useQuery({
    queryKey: ["boolean", "laws"], queryFn: ({ signal }) => get<BooleanLaw[]>("/boolean/laws", undefined, signal),
  });
  useQueryError("boolean-laws", "Katalog hukum gagal dimuat.", catalog.error);
  const laws = catalog.data ?? [];
  const law = laws[index];

  return <Panel id="hukum" title="Katalog bukti aljabar">
    <RequestState pending={catalog.isPending} error={catalog.error} empty="Katalog bukti belum tersedia." loading="Memuat katalog hukum">
      {law && <>
        <Choice label={"Identitas (" + laws.length + " bukti)"} value={index}
          options={laws.map((item, value) => ({ value, label: item.lhs + " = " + item.rhs }))} onChange={setIndex} />
        <ProofSteps steps={law.steps} />
        <div className="lab-actions">
          <Button asChild variant="outline">
            <a href="#ekspresi" onClick={() => onApply({ lhs: law.lhs, rhs: law.rhs })}>Gunakan di editor</a>
          </Button>
        </div>
      </>}
    </RequestState>
  </Panel>;
}
