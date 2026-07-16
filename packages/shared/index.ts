// Shared API types between apps/web and any future TS consumers.
// Mirrors apps/api/app/schemas.py — keep in sync when schemas change.

export type TokenT = { access_token: string; token_type: string; organization_id: string };
export type UserT = { id: string; email: string; name: string };
export type OrgT = { id: string; name: string; industry: string; settings: Record<string, unknown> };
export type MemberT = { id: string; user: UserT; role: string };

export type AgentT = {
  id: string;
  name: string;
  greeting: string;
  system_prompt: string;
  voice: string;
  language: string;
  transfer_number: string;
  transfer_after_booking: boolean;
  is_active: boolean;
  created_at: string;
};

export type DocumentT = {
  id: string;
  filename: string;
  content_type: string;
  status: "pending" | "processing" | "ready" | "failed";
  chunk_count: number;
  created_at: string;
};

export type TurnT = { position: number; role: "caller" | "agent" | "system"; content: string };
export type SummaryT = { content: string; intent: string; sentiment: string };

export type CallT = {
  id: string;
  agent_id: string | null;
  direction: string;
  caller_number: string;
  caller_name: string;
  to_number: string;
  status: "ringing" | "in_progress" | "completed" | "transferred" | "failed";
  started_at: string;
  ended_at: string | null;
  duration_seconds: number;
  transferred_to: string;
};

export type CallDetailT = CallT & { turns: TurnT[]; summary: SummaryT | null; has_recording: boolean };

export type AppointmentT = {
  id: string;
  call_id: string | null;
  contact_name: string;
  contact_phone: string;
  starts_at: string;
  ends_at: string;
  status: string;
};

export type IntegrationT = { id: string; provider: string; config: Record<string, unknown>; is_active: boolean };

export type AnalyticsT = {
  total_calls: number;
  completed_calls: number;
  transferred_calls: number;
  avg_duration_seconds: number;
  appointments_booked: number;
  calls_per_day: { day: string; count: number }[];
};

export type PageT<T> = { total: number; items: T[] };
