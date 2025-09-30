import { useMemo } from "react";

export function resolveApiBase(): string {
  const envBase = import.meta.env.VITE_API_BASE as string | undefined;
  if (envBase) return envBase;
  const url = new URL(window.location.href);
  if (url.port === "5173") {
    url.port = "8000";
  }
  return url.origin.replace(":5173", ":8000");
}

export function useApiBase(): string {
  return useMemo(() => resolveApiBase(), []);
}
