import { useMemo } from "react";

export function resolveApiBase(): string {
  const envBase = import.meta.env.VITE_API_BASE as string | undefined;
  if (envBase) {
    return envBase;
  }

  const current = new URL(window.location.href);
  const protocol = "https:";
  let host = current.hostname;
  let port = "8000";

  if (host.endsWith(".github.dev")) {
    host = host.replace(/-5173\./, "-8000.");
    port = "";
  } else if (host === "localhost" || host === "127.0.0.1") {
    port = "8000";
  } else if (current.port && current.port !== "80" && current.port !== "443") {
    port = current.port === "5173" ? "8000" : current.port;
  }

  const origin = port ? `${protocol}//${host}:${port}` : `${protocol}//${host}`;
  return origin;
}

export function useApiBase(): string {
  return useMemo(() => resolveApiBase(), []);
}
