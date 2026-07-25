export interface AgentRun {
  id: string;
  parent_id: string | null;
  label: string;
  /** "running" while the agent is executing a benchmark; "done" when complete; "failed" on error */
  status: "running" | "done" | "failed";
  config?: {
    model?: string;
    precision?: string;
    max_num_seqs?: number;
    enable_prefix_caching?: boolean;
    power_cap_w?: number | null;
    concurrency?: number;
  };
  metrics?: {
    tokens_per_s: number;
    ttft_ms: number;
    itl_ms?: number;
  };
  energy?: {
    joules?: number;
    joules_per_token?: number;
    mean_power_w?: number;
  };
  /** The agent's reasoning text before this action */
  reasoning?: string;
  /** Structured decision metadata — what changed, why, and how it turned out */
  meta?: {
    action?: string;
    params_changed?: Record<string, { from: string | number | boolean; to: string | number | boolean }>;
    params_frozen?: Record<string, string | number | boolean | null>;
    hypothesis?: string;
    outcome?: "improved" | "regressed" | "neutral" | string;
    delta_vs_best?: Record<string, string | number>;
    tags?: string[];
  };
  ts: string;
}

/** Shared Env interface — both Worker and DO reference this. */
export interface Env {
  AGENT_HUB: DurableObjectNamespace;
  /** Set via: wrangler secret put API_KEY */
  API_KEY: string;
}
