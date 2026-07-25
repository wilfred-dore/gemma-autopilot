/**
 * Worker entry point.
 *
 * Routing (with Workers Assets, run_worker_first = false by default):
 *  GET  /          → served by Assets  (public/index.html)
 *  GET  /ws        → Worker → AgentHub (WebSocket)
 *  POST /api/push  → Worker → AgentHub (push a run)
 *  GET  /api/state → Worker → AgentHub (full state as JSON)
 *  POST /api/reset → Worker → AgentHub (delete all data)
 */

import { AgentHub } from "./hub";
import type { Env } from "./types";

export { AgentHub };

const CORS: HeadersInit = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function withCors(resp: Response): Response {
  const r = new Response(resp.body, resp);
  for (const [k, v] of Object.entries(CORS)) r.headers.set(k, v);
  return r;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // CORS preflight
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });

    const url = new URL(request.url);
    const hub = env.AGENT_HUB.get(env.AGENT_HUB.idFromName("main"));

    // ── WebSocket (no auth: read-only view) ─────────────────────────────
    if (url.pathname === "/ws") {
      return hub.fetch(request);
    }

    // ── Push API ─────────────────────────────────────────────────────────
    if (url.pathname === "/api/push" && request.method === "POST") {
      if (!authOk(request, env)) return unauthorized();
      return withCors(await hub.fetch(request));
    }

    // ── Reset API ─────────────────────────────────────────────────────────
    if (url.pathname === "/api/reset" && request.method === "POST") {
      if (!authOk(request, env)) return unauthorized();
      return withCors(await hub.fetch(request));
    }

    // ── State polling fallback ────────────────────────────────────────────
    if (url.pathname === "/api/state") {
      return withCors(await hub.fetch(request));
    }

    // Everything else → 404 (static assets handled before this Worker runs)
    return new Response("Not found", { status: 404 });
  },
};

function authOk(request: Request, env: Env): boolean {
  if (!env.API_KEY) return false; // key not configured → always reject
  const auth = request.headers.get("Authorization") ?? "";
  return auth === `Bearer ${env.API_KEY}`;
}

function unauthorized(): Response {
  return new Response(JSON.stringify({ error: "Unauthorized" }), {
    status: 401,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}
