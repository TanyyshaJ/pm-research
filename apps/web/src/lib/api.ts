export type User = { id: string; email: string };
export type Project = {
  id: string;
  name: string;
  question: string;
  audience: string;
  geography: string;
  created_at: number;
};
export type Evidence = {
  id: string;
  source_id: string;
  title: string;
  location: string;
  kind: string;
  excerpt: string;
  limitation: string;
  url?: string;
  retrieved_at?: number;
};
export type Block = {
  id: string;
  type: string;
  text: string;
  evidence_ids: string[];
  limitation?: string;
};
export type Brief = {
  id: string;
  title: string;
  subtitle: string;
  mode: string;
  version: number;
  notice: string;
  sections: { id: string; title: string; eyebrow: string; blocks: Block[] }[];
  evidence: Evidence[];
  limitations: string[];
  run_id?: string;
  competitors?: Competitor[];
  review?: { removed_claims: number; human_reviewed: boolean };
};

export type CompetitorFact = {
  id: string;
  dimension: string;
  text: string;
  evidence_ids: string[];
};
export type Competitor = { name: string; facts: CompetitorFact[] };
export type Plan = {
  objective: string;
  questions: string[];
  market_queries: string[];
  competitor_queries: string[];
  completion_criteria: string[];
  assumptions: string[];
};
export type ResearchRun = {
  id: string;
  project_id: string;
  status: string;
  model: string;
  error: string;
  plan: Plan | null;
  brief?: Brief | null;
  created_at: number;
  cancel_requested: number;
  stages: { name: string; status: string; error: string }[];
  usage: {
    model_requests: number;
    max_requests: number;
    input_tokens: number;
    output_tokens: number;
    unknown_requests: number;
    cost_usd: null;
  };
};
export type AIConnection = {
  configured: boolean;
  model: string;
  provider: string;
  key_storage: string;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body === undefined
        ? {}
        : {
            "Content-Type": "application/json",
            "X-Requested-With": "Fieldnotes",
          },
    credentials: "same-origin",
    cache: "no-store",
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    const message =
      typeof result.detail === "string"
        ? result.detail
        : "Please check the form and try again.";
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
