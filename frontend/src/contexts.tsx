import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { Toaster } from "sonner";
import type { ImageMeta, Inspector, SplitRequest, SplitResponse } from "@/types/api";

type SharingSession = { session_id: string; request: SplitRequest; image: ImageMeta; result: SplitResponse; expired?: boolean };
type SharingState = {
  session: SharingSession | null;
  setSession: (session: SharingSession | null) => void;
  expireSession: (id: string) => void;
};
export type WorkbenchSource = "cbir" | "sharing" | "boolean";
export type InspectorSource = WorkbenchSource | "inspector";
type InspectorState = {
  latest: Partial<Record<InspectorSource, Inspector>>;
  activeSource: InspectorSource | null;
  setLatest: (page: InspectorSource, inspector: Inspector) => void;
};

export const SharingContext = createContext<SharingState | null>(null);
export const InspectorContext = createContext<InspectorState | null>(null);

export function useSharing() {
  const context = useContext(SharingContext);
  if (!context) throw new Error("SharingContext belum tersedia.");
  return context;
}

export function useInspector() {
  const context = useContext(InspectorContext);
  if (!context) throw new Error("InspectorContext belum tersedia.");
  return context;
}

export function AppProviders({ children, queryClient }: { children: ReactNode; queryClient?: QueryClient }) {
  const [client] = useState(() => queryClient ?? new QueryClient({
    defaultOptions: { queries: { staleTime: Infinity, retry: false } },
  }));
  const [session, setSession] = useState<SharingSession | null>(null);
  const [inspectors, setInspectors] = useState<Pick<InspectorState, "latest" | "activeSource">>({
    latest: {}, activeSource: null,
  });
  const expireSession = useCallback((id: string) => {
    setSession((current) => current?.session_id === id && !current.expired ? { ...current, expired: true } : current);
  }, []);
  const setLatest = useCallback<InspectorState["setLatest"]>((page, value) => {
    setInspectors((current) => current.latest[page] === value && current.activeSource === page ? current : {
      latest: { ...current.latest, [page]: value }, activeSource: page,
    });
  }, []);
  const sharing = useMemo(() => ({ session, setSession, expireSession }), [session, expireSession]);
  const inspector = useMemo(() => ({ ...inspectors, setLatest }), [inspectors, setLatest]);

  return (
    <QueryClientProvider client={client}>
      <SharingContext.Provider value={sharing}>
        <InspectorContext.Provider value={inspector}>
          {children}
          <Toaster position="bottom-right" theme="light" toastOptions={{
            className: "editorial-toast",
            style: {
              borderRadius: "var(--radius)", boxShadow: "none", background: "var(--surface)", color: "var(--ink)",
              border: "var(--hairline) solid var(--line)", fontFamily: "var(--font-display)",
            },
          }} />
        </InspectorContext.Provider>
      </SharingContext.Provider>
    </QueryClientProvider>
  );
}
