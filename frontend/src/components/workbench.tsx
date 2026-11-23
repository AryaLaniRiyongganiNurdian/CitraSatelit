import { useId, type ComponentProps, type ReactNode } from "react";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useInspector } from "@/contexts";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatNumber } from "@/lib/workbench";
import type { ImagePreview } from "@/types/api";
import "./workbench.css";

export function Workbench({ title, description, page, links, children }: {
  title: string;
  description: string;
  page: "cbir" | "sharing";
  links: { id: string; title: string }[];
  children: ReactNode;
}) {
  const { latest } = useInspector();
  return <section className="workbench lab">
    <div className="wrap">
      <div className="lab-hero">
        <div><p className="mono dim">Ruang kerja EuroSAT</p><h1>{title}</h1><p>{description}</p></div>
        {latest[page] && <Button asChild variant="outline">
          <Link to="/inspector" state={{ source: page }}>Buka Math Inspector <ArrowUpRight aria-hidden /></Link>
        </Button>}
      </div>
      <nav className="lab-nav mono" aria-label={"Bagian " + title}>
        {links.map((link) => <a key={link.id} href={"#" + link.id}>{link.title}</a>)}
      </nav>
      {children}
    </div>
  </section>;
}

export function Panel({ title, id, children }: { title: string; id?: string; children: ReactNode }) {
  const headingId = useId();
  return <section id={id} aria-labelledby={headingId} className="lab-panel">
    <Card className="lab-panel-card">
      <h2 id={headingId}>{title}</h2>
      {children}
    </Card>
  </section>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="lab-empty">{children}</p>;
}

export function Loading({ label }: { label: string }) {
  return <div className="lab-loading" role="status" aria-label={label}>
    <Skeleton /><Skeleton />
  </div>;
}

export function RequestState({ pending, error, empty, loading = "Memuat hasil", children }: {
  pending: boolean; error: Error | null; empty: ReactNode; loading?: string; children?: ReactNode;
}) {
  if (pending) return <Loading label={loading} />;
  if (error) return <Empty>{error.message}</Empty>;
  return children ?? <Empty>{empty}</Empty>;
}

export type Option<T> = { value: T; label: string; disabled?: boolean };

export function Choice<T extends string | number>({ label, value, options, onChange, disabled }: {
  label: string; value: T; options: Option<T>[]; onChange: (value: T) => void; disabled?: boolean;
}) {
  const id = useId();
  return <div className="lab-field">
    <label htmlFor={id}>{label}</label>
    <Select value={String(value)} disabled={disabled} onValueChange={(key) => {
      const option = options.find((item) => String(item.value) === key);
      if (option) onChange(option.value);
    }}>
      <SelectTrigger id={id}><SelectValue placeholder="Pilih" /></SelectTrigger>
      <SelectContent className="lab-select-menu" position="popper">
        {options.map((item) => <SelectItem key={item.value} value={String(item.value)} disabled={item.disabled}>{item.label}</SelectItem>)}
      </SelectContent>
    </Select>
  </div>;
}

export function NumberField({ label, ...props }: ComponentProps<typeof Input> & { label: string }) {
  const id = useId();
  return <div className="lab-field"><label htmlFor={id}>{label}</label>
    <Input type="number" id={id} {...props} />
  </div>;
}

export function Preview({ data, label }: { data: ImagePreview; label: string }) {
  return <figure className="lab-preview">
    <img src={data.data_uri} alt={label} width={data.width} height={data.height} className="pixelated" />
    <figcaption><span className="mono">{label}</span>{data.note && <small>{data.note}</small>}</figcaption>
  </figure>;
}

type Cell = string | number | boolean | null;

export function DataTable({ columns, rows, caption }: { columns: string[]; rows: Cell[][]; caption?: string }) {
  if (!rows.length) return <Empty>Belum ada baris data.</Empty>;
  return <Table>
    {caption && <TableCaption>{caption}</TableCaption>}
    <TableHeader><TableRow>{columns.map((column) => <TableHead key={column} scope="col">{column}</TableHead>)}</TableRow></TableHeader>
    <TableBody>{rows.map((row, index) => <TableRow key={index}>
      {row.map((cell, column) => <TableCell key={column}>{typeof cell === "boolean" ? (cell ? "Ya" : "Tidak") :
        typeof cell === "string" ? cell : formatNumber(cell)}</TableCell>)}
    </TableRow>)}</TableBody>
  </Table>;
}

export function Stats({ items }: { items: { label: string; value: ReactNode }[] }) {
  return <dl className="lab-stats">
    {items.map(({ label, value }) => <div key={label}><dt className="mono dim">{label}</dt><dd>{value}</dd></div>)}
  </dl>;
}
