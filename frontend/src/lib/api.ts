/**
 * ZAPRICA API Client
 *
 * Handles all communication with the FastAPI backend.
 * Automatically attaches JWT tokens and handles errors.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestOptions extends RequestInit {
  token?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("zaprica_token");
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { token, ...fetchOptions } = options;
    const authToken = token || this.getToken();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(fetchOptions.headers as Record<string, string>),
    };

    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...fetchOptions,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        errorData.detail || `Request failed: ${response.statusText}`
      );
    }

    return response.json();
  }

  // ── Auth ──────────────────────────────────────────────────

  async register(data: {
    org_name: string;
    org_slug: string;
    email: string;
    password: string;
    full_name: string;
  }) {
    return this.request<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({
        name: data.org_name,
        slug: data.org_slug,
        email: data.email,
        password: data.password,
        full_name: data.full_name,
        role: "admin",
      }),
    });
  }

  async login(email: string, password: string) {
    return this.request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async getMe() {
    return this.request<User>("/api/v1/auth/me");
  }

  // ── Cases ─────────────────────────────────────────────────

  async createCase(data: CaseCreateInput) {
    return this.request<Case>("/api/v1/cases", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async listCases(params?: { status?: string; page?: number; page_size?: number }) {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const qs = query.toString();
    return this.request<CaseListResponse>(`/api/v1/cases${qs ? `?${qs}` : ""}`);
  }

  async getCase(caseId: string) {
    return this.request<Case>(`/api/v1/cases/${caseId}`);
  }

  async updateCase(caseId: string, data: Partial<CaseCreateInput>) {
    return this.request<Case>(`/api/v1/cases/${caseId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  // ── Investigations ────────────────────────────────────────

  async createInvestigation(caseId: string, data: InvestigationCreateInput) {
    return this.request<Investigation>(
      `/api/v1/cases/${caseId}/investigations`,
      { method: "POST", body: JSON.stringify(data) }
    );
  }

  async listInvestigations(caseId: string, status?: string) {
    const qs = status ? `?status=${status}` : "";
    return this.request<Investigation[]>(
      `/api/v1/cases/${caseId}/investigations${qs}`
    );
  }

  async getInvestigation(investigationId: string) {
    return this.request<InvestigationDetail>(
      `/api/v1/investigations/${investigationId}`
    );
  }

  async cancelInvestigation(investigationId: string) {
    return this.request<{ status: string }>(
      `/api/v1/investigations/${investigationId}/cancel`,
      { method: "POST" }
    );
  }

  // ── Graph ─────────────────────────────────────────────────

  async getInvestigationGraph(investigationId: string) {
    return this.request<GraphData>(
      `/api/v1/investigations/${investigationId}/graph`
    );
  }

  async getInvestigationEvidence(investigationId: string) {
    return this.request<Evidence[]>(
      `/api/v1/investigations/${investigationId}/evidence`
    );
  }

  // ── Tools ─────────────────────────────────────────────────

  async listTools() {
    return this.request<ToolDefinition[]>("/api/v1/tools");
  }

  // ── Health ────────────────────────────────────────────────

  async healthCheck() {
    return this.request<{ status: string; service: string; version: string }>(
      "/api/health"
    );
  }

  async systemStatus() {
    return this.request<SystemStatus>("/api/v1/status");
  }
}

// ── Error Class ───────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

// ── Types ─────────────────────────────────────────────────────

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Case {
  id: string;
  organization_id: string;
  created_by: string;
  title: string;
  description: string | null;
  status: string;
  authorization_attestation: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  investigation_count: number;
}

export interface CaseCreateInput {
  title: string;
  description?: string;
  authorization_attestation: boolean;
  tags?: string[];
}

export interface CaseListResponse {
  cases: Case[];
  total: number;
  page: number;
  page_size: number;
}

export interface Investigation {
  id: string;
  case_id: string;
  created_by: string;
  seed_type: string;
  seed_value: string;
  status: string;
  current_step: string | null;
  iteration_count: number;
  tool_call_count: number;
  max_iterations: number;
  max_tool_calls: number;
  max_time_seconds: number;
  plan: Record<string, unknown>[];
  findings_summary: string | null;
  entity_count: number;
  edge_count: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  error_count: number;
}

export interface InvestigationStep {
  id: string;
  investigation_id: string;
  step_number: number;
  step_type: string;
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  tool_output: Record<string, unknown> | null;
  entities_extracted: Record<string, unknown>[];
  edges_created: Record<string, unknown>[];
  status: string;
  error_message: string | null;
  duration_ms: number | null;
  started_at: string;
  completed_at: string | null;
}

export interface InvestigationDetail extends Investigation {
  steps: InvestigationStep[];
}

export interface GraphEntity {
  entity_type: string;
  value: string;
  normalized_value: string;
  properties: Record<string, unknown>;
  confidence: number;
  source_investigation_id: string | null;
}

export interface GraphEdge {
  source_type: string;
  source_value: string;
  target_type: string;
  target_value: string;
  relationship: string;
  properties: Record<string, unknown>;
  evidence_id: string | null;
}

export interface GraphData {
  nodes: GraphEntity[];
  edges: GraphEdge[];
}

export interface Evidence {
  id: string;
  investigation_id: string;
  evidence_type: string;
  source_url: string | null;
  collected_at: string;
  sha256_hash: string;
  s3_uri: string;
  file_size_bytes: number | null;
  content_type: string | null;
  description: string | null;
}

export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface SystemStatus {
  service: string;
  version: string;
  environment: string;
  features: {
    planner_llm: string;
    extractor_llm: string;
    max_concurrent_investigations: number;
  };
}

// ── Export singleton ──────────────────────────────────────────

export const api = new ApiClient(API_BASE);
