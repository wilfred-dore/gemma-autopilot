import { DurableObject } from "cloudflare:workers";
import type { AgentRun, Env } from "./types";

/**
 * AgentHub — single Durable Object instance ("main") that:
 *  - Persists all agent runs in SQLite
 *  - Fans out real-time updates to all connected WebSocket clients
 *  - Exposes /api/push, /api/state, /api/reset and /ws
 */
export class AgentHub extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    this.ctx.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS runs (
        id          TEXT    PRIMARY KEY,
        parent_id   TEXT,
        label       TEXT    NOT NULL,
        status      TEXT    NOT NULL DEFAULT 'running',
        config      TEXT,
        metrics     TEXT,
        energy      TEXT,
        reasoning   TEXT,
        meta        TEXT,
        ts          TEXT    NOT NULL,
        updated_at  INTEGER NOT NULL
      )
    `);
    // Migration: older DO instances were created before the `meta` column existed.
    try {
      this.ctx.storage.sql.exec(`ALTER TABLE runs ADD COLUMN meta TEXT`);
    } catch {
      /* column already exists — fine */
    }
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // ── WebSocket upgrade ──────────────────────────────────────────────────
    if (url.pathname === "/ws") {
      if (request.headers.get("Upgrade") !== "websocket") {
        return new Response("Expected WebSocket upgrade", { status: 426 });
      }
      const pair = new WebSocketPair();
      const [client, server] = Object.values(pair);
      this.ctx.acceptWebSocket(server);
      server.send(JSON.stringify({ type: "init", runs: this.getState() }));
      return new Response(null, { status: 101, webSocket: client });
    }

    // ── Push a new / updated run ───────────────────────────────────────────
    if (url.pathname === "/api/push" && request.method === "POST") {
      let run: Partial<AgentRun>;
      try {
        run = (await request.json()) as Partial<AgentRun>;
      } catch {
        return json({ error: "Invalid JSON body" }, 400);
      }
      if (!run.id || !run.label) {
        return json({ error: "Fields 'id' and 'label' are required" }, 400);
      }
      this.upsertRun(run as AgentRun);
      this.broadcast();
      return json({ ok: true, id: run.id });
    }

    // ── Get current state (REST polling fallback) ──────────────────────────
    if (url.pathname === "/api/state") {
      return json({ runs: this.getState() });
    }

    // ── Delete all data (dev/demo reset) ──────────────────────────────────
    if (url.pathname === "/api/reset" && request.method === "POST") {
      this.ctx.storage.sql.exec("DELETE FROM runs");
      this.broadcast();
      return json({ ok: true });
    }

    return new Response("Not found", { status: 404 });
  }

  // Hibernatable WebSocket handlers (no-ops — we only push server→client)
  webSocketMessage(_ws: WebSocket, _msg: string | ArrayBuffer): void {}
  webSocketClose(_ws: WebSocket, _code: number, _reason: string): void {}
  webSocketError(_ws: WebSocket, _err: unknown): void {}

  // ── Private helpers ──────────────────────────────────────────────────────

  private upsertRun(run: AgentRun): void {
    this.ctx.storage.sql.exec(
      `INSERT INTO runs (id,parent_id,label,status,config,metrics,energy,reasoning,meta,ts,updated_at)
       VALUES (?,?,?,?,?,?,?,?,?,?,?)
       ON CONFLICT(id) DO UPDATE SET
         parent_id  = excluded.parent_id,
         label      = excluded.label,
         status     = excluded.status,
         config     = excluded.config,
         metrics    = excluded.metrics,
         energy     = excluded.energy,
         reasoning  = excluded.reasoning,
         meta       = excluded.meta,
         ts         = excluded.ts,
         updated_at = excluded.updated_at`,
      run.id,
      run.parent_id ?? null,
      run.label,
      run.status ?? "done",
      run.config ? JSON.stringify(run.config) : null,
      run.metrics ? JSON.stringify(run.metrics) : null,
      run.energy ? JSON.stringify(run.energy) : null,
      run.reasoning ?? null,
      run.meta ? JSON.stringify(run.meta) : null,
      run.ts ?? new Date().toISOString(),
      Date.now(),
    );
  }

  private getState(): AgentRun[] {
    const cursor = this.ctx.storage.sql.exec(
      "SELECT * FROM runs ORDER BY updated_at ASC",
    );
    const rows: AgentRun[] = [];
    for (const row of cursor) {
      rows.push({
        id: row.id as string,
        parent_id: (row.parent_id as string | null) ?? null,
        label: row.label as string,
        status: row.status as AgentRun["status"],
        config: row.config ? JSON.parse(row.config as string) : undefined,
        metrics: row.metrics ? JSON.parse(row.metrics as string) : undefined,
        meta: row.meta ? JSON.parse(row.meta as string) : undefined,
        energy: row.energy ? JSON.parse(row.energy as string) : undefined,
        reasoning: (row.reasoning as string | null) ?? undefined,
        ts: row.ts as string,
      });
    }
    return rows;
  }

  private broadcast(): void {
    const msg = JSON.stringify({ type: "update", runs: this.getState() });
    for (const ws of this.ctx.getWebSockets()) {
      try {
        ws.send(msg);
      } catch {
        /* client already closed */
      }
    }
  }
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
