// Thin typed fetch wrapper. Token lives in localStorage (simple email auth).
import type {
  AgentT, AnalyticsT, AppointmentT, CallDetailT, CallT, DocumentT,
  IntegrationT, MemberT, OrgT, PageT, TokenT, UserT,
} from "@voxdesk/shared";

// Where the browser sends API calls. Deployed builds always use the
// same-origin /backend proxy (next.config.ts → VPS), so there is no CORS and
// no dependency on a NEXT_PUBLIC_API_URL dashboard var. Local dev hits the API
// directly. Decided at call time so a stale build-time env var can't break it.
function apiBase(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    }
    return "/backend";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export function getToken(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem("voxdesk_token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("voxdesk_token", token);
  else localStorage.removeItem("voxdesk_token");
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body && typeof init.body === "string") headers["Content-Type"] = "application/json";

  const res = await fetch(`${apiBase()}${path}`, { ...init, headers });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
    setToken(null);
    window.location.href = "/login";
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  register: (body: { email: string; password: string; name: string; organization_name: string; industry?: string }) =>
    request<TokenT>("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    request<TokenT>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => request<UserT>("/auth/me"),

  org: () => request<OrgT>("/organizations/current"),
  updateOrg: (body: Partial<OrgT>) =>
    request<OrgT>("/organizations/current", { method: "PATCH", body: JSON.stringify(body) }),
  members: () => request<MemberT[]>("/organizations/current/members"),
  invite: (body: { email: string; name: string; password: string; role: string }) =>
    request<MemberT>("/organizations/current/members", { method: "POST", body: JSON.stringify(body) }),

  agents: () => request<AgentT[]>("/agents"),
  agent: (id: string) => request<AgentT>(`/agents/${id}`),
  createAgent: (body: Partial<AgentT>) => request<AgentT>("/agents", { method: "POST", body: JSON.stringify(body) }),
  updateAgent: (id: string, body: Partial<AgentT>) =>
    request<AgentT>(`/agents/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteAgent: (id: string) => request<void>(`/agents/${id}`, { method: "DELETE" }),

  documents: () => request<DocumentT[]>("/documents"),
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentT>("/documents", { method: "POST", body: form });
  },
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  retrieve: (query: string) =>
    request<{ content: string; document_id: string; score: number }[]>("/documents/retrieve", {
      method: "POST", body: JSON.stringify({ query }),
    }),

  calls: (offset = 0, limit = 20) => request<PageT<CallT>>(`/calls?offset=${offset}&limit=${limit}`),
  call: (id: string) => request<CallDetailT>(`/calls/${id}`),
  simulateCall: (body: { agent_id: string; caller_number?: string; utterances: string[] }) =>
    request<CallDetailT>("/calls/simulate", { method: "POST", body: JSON.stringify(body) }),

  recordingUrl: async (callId: string): Promise<string> => {
    // <audio> can't send the bearer header, so fetch the audio and hand back a blob URL.
    const res = await fetch(`${apiBase()}/calls/${callId}/recording`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new ApiError(res.status, "Recording unavailable");
    return URL.createObjectURL(await res.blob());
  },

  appointments: () => request<AppointmentT[]>("/appointments"),
  integrations: () => request<IntegrationT[]>("/integrations"),
  upsertIntegration: (provider: string, body: { config: object; is_active: boolean; provider: string }) =>
    request<IntegrationT>(`/integrations/${provider}`, { method: "PUT", body: JSON.stringify(body) }),

  analytics: () => request<AnalyticsT>("/analytics"),
};
