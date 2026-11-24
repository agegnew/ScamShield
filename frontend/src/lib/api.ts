"use client";

import useSWR, { type SWRConfiguration } from "swr";
import type { components } from "./api-types";
import { clearSession, getToken } from "./auth";

export type Schemas = components["schemas"];
export type Case = Schemas["Case"];
export type CaseSummary = Schemas["CaseSummary"];
export type CaseList = Schemas["CaseList"];
export type RadarFeed = Schemas["RadarFeed"];
export type Reason = Schemas["Reason"];
export type Verdict = Schemas["Verdict"];
export type Evidence = Schemas["Evidence"];
export type Brand = Schemas["Brand"];
export type Metrics = Schemas["Metrics"];
export type Graph = Schemas["Graph"];
export type Takedown = Schemas["Takedown"];
export type CheckResponse = Schemas["CheckResponse"];
export type ScanResponse = Schemas["ScanResponse"];
export type BatchResponse = Schemas["BatchResponse"];
export type LoginResponse = Schemas["LoginResponse"];
export type UserInfo = Schemas["UserInfo"];
export type User = Schemas["User"];
export type DecisionLogEntry = Schemas["DecisionLogEntry"];
export type Health = Schemas["Health"];
export type Label = Schemas["Label"];
export type Source = Schemas["Source"];
export type VerdictLabel = Label | "UNKNOWN";

export const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** The API says in a header whether it serves demo cases or live data. */
export let apiMode: "mock" | "live" | null = null;
const modeListeners = new Set<(m: "mock" | "live") => void>();
export function onMode(cb: (m: "mock" | "live") => void) {
  modeListeners.add(cb);
  return () => {
    modeListeners.delete(cb);
  };
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  const mode = res.headers.get("x-scamshield-mode");
  if (mode === "mock" || mode === "live") {
    if (apiMode !== mode) {
      apiMode = mode;
      modeListeners.forEach((cb) => cb(mode));
    }
  }
  if (res.status === 401 && token) {
    // The token is missing, invalid or expired: drop it and send the person to sign in.
    clearSession();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/check")) {
      // A full navigation on purpose: this runs outside React, and every page's state is stale once the session is gone.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign(`/login?next=${encodeURIComponent(window.location.pathname)}`);
    }
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {
      /* no JSON body */
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function fetcher<T>(path: string) {
  return apiFetch<T>(path);
}

export function useApi<T>(path: string | null, config?: SWRConfiguration<T>) {
  return useSWR<T>(path, fetcher<T>, { revalidateOnFocus: false, ...config });
}

export const useHealth = () => useApi<Health>("/api/health", { refreshInterval: 15000 });
export const useBrands = () => useApi<Brand[]>("/api/brands");
export const useRadarFeed = (limit = 50) => useApi<RadarFeed>(`/api/radar/feed?limit=${limit}`, { refreshInterval: 8000 });
export const useMetrics = () => useApi<Metrics>("/api/metrics");
export const useGraph = () => useApi<Graph>("/api/graph");
/** With poll=true, refetches every 2 s until the worker has attached evidence. */
export const useCase = (id: string | null, poll = false) =>
  useApi<Case>(id ? `/api/cases/${id}` : null, poll ? { refreshInterval: (latest) => (latest?.evidence ? 0 : 2000) } : undefined);
export const useTakedown = (id: string | null) => useApi<Takedown>(id ? `/api/cases/${id}/takedown` : null);

export function useCases(params: Record<string, string | number | undefined>) {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "" && v !== null)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join("&");
  return useApi<CaseList>(`/api/cases${qs ? `?${qs}` : ""}`, { keepPreviousData: true });
}

export const decide = (id: string, action: "confirm" | "dismiss", reason: string) =>
  apiFetch<Case>(`/api/cases/${id}/decision`, { method: "POST", body: JSON.stringify({ action, reason }) });

export const scanUrl = (url: string) => apiFetch<ScanResponse>("/api/scan", { method: "POST", body: JSON.stringify({ url }) });
export const batchUrls = (urls: string[]) => apiFetch<BatchResponse>("/api/batch", { method: "POST", body: JSON.stringify({ urls }) });
export const checkInput = (input: string) => apiFetch<CheckResponse>("/api/check", { method: "POST", body: JSON.stringify({ input }) });
export const login = (username: string, password: string) =>
  apiFetch<LoginResponse>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
export const me = () => apiFetch<UserInfo>("/api/auth/me");

/** Admin only. */
export const useUsers = (enabled: boolean) => useApi<User[]>(enabled ? "/api/users" : null);
export const useDecisions = (enabled: boolean, limit = 100) => useApi<DecisionLogEntry[]>(enabled ? `/api/decisions?limit=${limit}` : null);
export const createUser = (username: string, password: string, role: "admin" | "analyst") =>
  apiFetch<User>("/api/users", { method: "POST", body: JSON.stringify({ username, password, role }) });

export const screenshotUrl = (path: string | null | undefined) => (path ? `${API}/artifacts/${path}` : null);
export const reportPdfUrl = (id: string) => `${API}/api/cases/${id}/report.pdf`;
export const exportJsonUrl = (id: string) => `${API}/api/cases/${id}/export.json`;

/** Fetch a file with the auth header and hand it to the browser as a download. */
export async function downloadFile(url: string, filename: string) {
  const token = getToken();
  const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) throw new ApiError(res.status, res.status === 501 ? "not_implemented" : res.statusText);
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
