/**
 * Typed API client for the CivicPulse backend.
 *
 * Uses /api/ prefix which is reverse-proxied through nginx (prod) or
 * Vite dev server proxy (dev), so no absolute backend URL is ever baked in.
 */

import type {
  Complaint,
  ComplaintCreate,
  PaginatedComplaints,
  ProviderInfo,
  StatsResponse,
  StatusUpdate,
  Category,
  Priority,
  Status,
} from './types';

const BASE = '/api';

async function request<T>(
  url: string,
  options: RequestInit = {},
): Promise<{ data: T; headers: Headers }> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers as Record<string, string> || {}) },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(body?.error || body?.errors?.[0]?.message || `HTTP ${res.status}`);
    (err as any).status = res.status;
    (err as any).body = body;
    throw err;
  }

  const data = await res.json();
  return { data, headers: res.headers };
}

/** POST /api/complaints */
export async function createComplaint(payload: ComplaintCreate): Promise<Complaint> {
  const { data } = await request<Complaint>(`${BASE}/complaints`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return data;
}

/** GET /api/complaints/{id} */
export async function getComplaint(id: string): Promise<Complaint> {
  const { data } = await request<Complaint>(`${BASE}/complaints/${id}`);
  return data;
}

/** GET /api/complaints */
export async function listComplaints(params: {
  category?: Category;
  priority?: Priority;
  status?: Status;
  page?: number;
  page_size?: number;
}): Promise<PaginatedComplaints> {
  const qs = new URLSearchParams();
  if (params.category) qs.set('category', params.category);
  if (params.priority) qs.set('priority', params.priority);
  if (params.status) qs.set('status', params.status);
  if (params.page) qs.set('page', String(params.page));
  if (params.page_size) qs.set('page_size', String(params.page_size));

  const { data } = await request<PaginatedComplaints>(`${BASE}/complaints?${qs.toString()}`);
  return data;
}

/** PATCH /api/complaints/{id}/status */
export async function updateStatus(id: string, payload: StatusUpdate): Promise<Complaint> {
  const { data } = await request<Complaint>(`${BASE}/complaints/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  return data;
}

/** GET /api/stats — returns data + X-Cache header */
export async function getStats(): Promise<{ stats: StatsResponse; cacheHit: boolean }> {
  const { data, headers } = await request<StatsResponse>(`${BASE}/stats`);
  const cacheHit = headers.get('X-Cache') === 'HIT';
  return { stats: data, cacheHit };
}

/** GET /api/meta/providers */
export async function getProviderInfo(): Promise<ProviderInfo> {
  const { data } = await request<ProviderInfo>(`${BASE}/meta/providers`);
  return data;
}
