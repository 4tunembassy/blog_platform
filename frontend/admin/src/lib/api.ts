import {
  AllowedTransitionsResponse,
  ContentEvent,
  ContentListResponse,
  TransitionRequest,
  TransitionResponse,
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8001";

const TENANT_SLUG = process.env.NEXT_PUBLIC_TENANT_SLUG?.trim() || "default";

function tenantHeaders(extra?: HeadersInit): HeadersInit {
  return {
    "X-Tenant-Slug": TENANT_SLUG,
    ...(extra || {}),
  };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: tenantHeaders(init?.headers),
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      detail = body?.detail ? String(body.detail) : JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export async function listContent(params: {
  limit: number;
  offset: number;
  sort?: string;
  q?: string;
}): Promise<ContentListResponse> {
  const sp = new URLSearchParams();
  sp.set("limit", String(params.limit));
  sp.set("offset", String(params.offset));
  if (params.sort) sp.set("sort", params.sort);
  if (params.q) sp.set("q", params.q);

  return apiFetch<ContentListResponse>(`/content?${sp.toString()}`, {
    method: "GET",
  });
}

export async function getAllowed(
  contentId: string
): Promise<AllowedTransitionsResponse> {
  return apiFetch<AllowedTransitionsResponse>(`/content/${contentId}/allowed`, {
    method: "GET",
  });
}

export async function getEvents(contentId: string): Promise<ContentEvent[]> {
  return apiFetch<ContentEvent[]>(`/content/${contentId}/events`, {
    method: "GET",
  });
}

export async function transitionContent(
  contentId: string,
  body: TransitionRequest
): Promise<TransitionResponse> {
  return apiFetch<TransitionResponse>(`/content/${contentId}/transition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
