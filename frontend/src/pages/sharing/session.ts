import { useInspector, useSharing } from "@/contexts";
import { post } from "@/lib/api";
import { isSessionNotFound, useApiMutation } from "@/lib/workbench";
import type { Inspector } from "@/types/api";

export function useSharingOperation<T extends { inspector: Inspector }, V>(path: string, settings: {
  sessionId?: string; success?: string; failure: string;
}) {
  const { setLatest } = useInspector();
  const { expireSession } = useSharing();
  return useApiMutation((request: V) => post<T, V>(path, request), {
    ...settings,
    onSuccess: (data) => setLatest("sharing", data.inspector),
    onError: (error) => {
      if (settings.sessionId && isSessionNotFound(error)) expireSession(settings.sessionId);
    },
  });
}
