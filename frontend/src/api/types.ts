/**
 * TypeScript types matching the backend Pydantic schemas.
 */

export type Category = 'water' | 'electricity' | 'sanitation' | 'roads' | 'streetlights' | 'other';
export type Priority = 'high' | 'normal' | 'low';
export type Status = 'open' | 'in_progress' | 'resolved' | 'rejected';

export interface ComplaintCreate {
  text: string;
  location: string;
  reporter_contact?: string | null;
}

export interface StatusUpdate {
  status: Status;
}

export interface Complaint {
  id: string;
  text: string;
  location: string;
  reporter_contact: string | null;
  category: Category;
  priority: Priority;
  status: Status;
  ai_summary: string | null;
  triaged_by: string;
  triage_latency_ms: number;
  created_at: string;
  updated_at: string;
}

export interface PaginatedComplaints {
  items: Complaint[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatsCategory {
  category: string;
  count: number;
}

export interface StatsPriority {
  priority: string;
  count: number;
}

export interface StatsResponse {
  by_category: StatsCategory[];
  by_priority: StatsPriority[];
  total: number;
}

export interface TriageOutcome {
  provider: string;
  latency_ms: number;
  fallback: boolean;
}

export interface ProviderInfo {
  active_provider: string;
  recent_outcomes: TriageOutcome[];
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidationErrorResponse {
  errors: ValidationError[];
}

export interface InvalidTransitionError {
  error: string;
  from: string;
  to: string;
}

export interface RateLimitError {
  error: string;
  retry_after: number;
}
