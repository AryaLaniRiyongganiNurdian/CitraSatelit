import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { Toaster } from "sonner";
import type { Inspector, SplitRequest } from "@/types/api";

type SharingSession = { session_id: string; request: SplitRequest };
type SharingState = {
  session: SharingSession | null;
  setSession: (session: SharingSession | null) => void;
};
type InspectorPage = "cbir" | "sharing" | "boolean" | "percobaan" | "inspector";
type InspectorState = {
  latest: Partial<Record<InspectorPage, Inspector>>;
  setLatest: (page: InspectorPage, inspector: Inspector) => void;
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
  const [latest, setInspectors] = useState<InspectorState["latest"]>({});
  const sharing = useMemo(() => ({ session, setSession }), [session]);
  const inspector = useMemo<InspectorState>(() => ({
    latest,
    setLatest: (page, value) => setInspectors((current) => ({ ...current, [page]: value })),
  }), [latest]);

  return (
    <QueryClientProvider client={client}>
      <SharingContext.Provider value={sharing}>
        <InspectorContext.Provider value={inspector}>
          {children}
          <Toaster position="bottom-right" theme="light" toastOptions={{ className: "editorial-toast" }} />
        </InspectorContext.Provider>
      </SharingContext.Provider>
    </QueryClientProvider>
  );
}
