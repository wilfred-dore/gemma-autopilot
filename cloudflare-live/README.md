# Gemma² · Live Dashboard

Real-time Cloudflare Workers app that visualises agent runs as they happen — exploration tree, leaderboard, reasoning trace, energy metrics.

## Requirements

- [Cloudflare account](https://dash.cloudflare.com/sign-up) (free tier works for the Worker; **Durable Objects require the Workers Paid plan → $5/month**)
- `node` ≥ 18

---

## Deploy in 3 commands

```bash
cd cloudflare-live
npm install

# Set your secret push key (stored encrypted in Cloudflare, never in code)
npx wrangler secret put API_KEY
# → type any strong random string when prompted, e.g.:  openssl rand -hex 24

npx wrangler deploy
# → prints your URL: https://gemma-autopilot-live.<subdomain>.workers.dev
```

---

## Local development

```bash
npx wrangler dev
# → http://localhost:8787
```

---

## Push a run

### curl

```bash
curl -X POST https://gemma-autopilot-live.<subdomain>.workers.dev/api/push \
  -H "Authorization: Bearer <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "id":        "agent-iter-1",
    "parent_id": null,
    "label":     "agent-iter-1",
    "status":    "done",
    "config":    { "max_num_seqs": 128, "enable_prefix_caching": true, "concurrency": 8 },
    "metrics":   { "tokens_per_s": 143.2, "ttft_ms": 412, "itl_ms": 11.3 },
    "energy":    { "joules": 1100, "joules_per_token": 0.0042, "mean_power_w": 298 },
    "reasoning": "Starting with large batch + prefix caching. TTFT within constraint.",
    "ts":        "2026-07-25T10:00:00"
  }'
```

### Python helper script

```bash
python scripts/push_live.py \
  --endpoint https://gemma-autopilot-live.<subdomain>.workers.dev \
  --key <YOUR_API_KEY> \
  --label agent-iter-1 \
  --tokens-per-s 143.2 \
  --ttft-ms 412
```

---

## Integrate with the Python agent

Set two environment variables before running `autopilot/agent.py`:

```bash
export LIVE_ENDPOINT=https://gemma-autopilot-live.<subdomain>.workers.dev
export LIVE_API_KEY=<YOUR_API_KEY>

python -m autopilot.agent --iters 8
```

The journal will automatically:
1. Push a **"running"** node the moment the agent decides to benchmark (tree shows ⏳ in real-time)
2. Push a **"done"** node with full metrics once the benchmark completes

---

## API reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | — | Dashboard UI |
| `GET` | `/ws` | — | WebSocket (real-time updates) |
| `POST` | `/api/push` | Bearer | Upsert a run |
| `GET` | `/api/state` | — | Full state as JSON |
| `POST` | `/api/reset` | Bearer | Delete all runs |

### Run payload schema

```jsonc
{
  "id":        "string — unique, used for tree edges",
  "parent_id": "string | null — id of the parent run (null = root)",
  "label":     "string — display name",
  "status":    "running | done | failed",
  "config": {                         // optional
    "max_num_seqs": 128,
    "enable_prefix_caching": true,
    "concurrency": 8,
    "power_cap_w": 280,
    "model": "google/gemma-4-27b-it",
    "precision": "bf16"
  },
  "metrics": {                        // optional (omit when status=running)
    "tokens_per_s": 143.2,
    "ttft_ms": 412,
    "itl_ms": 11.3
  },
  "energy": {                         // optional
    "joules": 1100,
    "joules_per_token": 0.0042,
    "mean_power_w": 298
  },
  "reasoning": "Agent's explanation before this action",
  "meta": {                           // optional — structured decision summary shown in the UI
    "action": "run_benchmark",
    "params_changed": { "concurrency": { "from": 32, "to": 64 } },
    "params_frozen":  { "max_num_seqs": 256, "enable_prefix_caching": true, "power_cap_w": null },
    "hypothesis": "TTFT headroom suggests batch under-saturation",
    "outcome": "improved",            // improved | regressed | neutral
    "delta_vs_best": { "tokens_per_s": "+1.4%", "joules_per_token": "-2.1%" },
    "tags": ["saturation", "guardrail-recovery"]
  },
  "ts": "2026-07-25T10:00:00"        // ISO-8601
}
```

**Upsert semantics**: pushing the same `id` again updates the run (useful to upgrade `status: running → done`).

---

## Tree topology

The exploration tree is built from `parent_id` links:

```
null → agent-iter-1 → agent-iter-2 (TTFT violated)
                    ↘ agent-iter-3 → agent-iter-4 ★ best
                                   ↘ agent-iter-5 (running…)
human-expert (no parent, shown as sibling root)
```

Set `parent_id` to the previous run's `id` to build a chain, or to an earlier ancestor to show a branch.
