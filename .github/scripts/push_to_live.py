#!/usr/bin/env python3
"""
GitHub Actions script: push benchmark runs to the Gemma Autopilot live dashboard.

Reads SOURCE and RESET_FIRST from env (set by the workflow).
Data sources:
  - sample  → datasets/state.sample.json
  - journal → runs/journal.jsonl
  - both    → sample first, then journal (journal entries overwrite on id clash)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ["LIVE_ENDPOINT"].rstrip("/")
KEY  = os.environ["LIVE_API_KEY"]
SOURCE = os.environ.get("SOURCE", "journal")
RESET_FIRST = os.environ.get("RESET_FIRST", "false").lower() == "true"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {KEY}",
}


def api(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload or {}).encode() if payload is not None else b"{}"
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=HEADERS, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ✗ HTTP {e.code} on {path}: {body}", file=sys.stderr)
        sys.exit(1)


def push_run(run: dict) -> None:
    resp = api("/api/push", run)
    score = ""
    if run.get("metrics"):
        m = run["metrics"]
        ok = "✓" if m.get("ttft_ms", 9999) <= 500 else "✗ TTFT"
        score = f" {m.get('tokens_per_s', 0):.1f} t/s  {ok}"
    print(f"  {run['label']:24s}{score}")


# ── Build run list from sources ─────────────────────────────────────────────

def runs_from_sample() -> list[dict]:
    path = Path("datasets/state.sample.json")
    if not path.exists():
        print(f"  [skip] {path} not found")
        return []
    state = json.loads(path.read_text())
    raw_runs   = state.get("runs", [])
    reasoning_map = {r["label"]: r["text"] for r in state.get("reasoning", [])}

    # Build a minimal parent-id chain: each agent-iter-N links to the previous
    # Non-agent runs (vllm-defaults, human-expert) have no parent.
    def parent_for(label: str, all_labels: list[str]) -> str | None:
        if label.startswith("agent-iter-"):
            try:
                n = int(label.split("-")[-1])
            except ValueError:
                return None
            if n > 1:
                prev = f"agent-iter-{n - 1}"
                return prev if prev in all_labels else None
            # iter-1 branches from the first non-agent run if one exists
            base = next((l for l in all_labels if not l.startswith("agent-iter-")), None)
            return base
        return None

    all_labels = [r["label"] for r in raw_runs]
    result = []
    for r in raw_runs:
        label = r["label"]
        result.append({
            "id":        label,
            "parent_id": parent_for(label, all_labels),
            "label":     label,
            "status":    "done",
            "config":    r.get("config"),
            "metrics":   r.get("metrics"),
            "energy":    r.get("energy"),
            "reasoning": reasoning_map.get(label, ""),
            "ts":        r.get("ts", ""),
        })
    return result


def runs_from_journal() -> list[dict]:
    path = Path("runs/journal.jsonl")
    if not path.exists() or path.stat().st_size == 0:
        print(f"  [skip] {path} not found or empty")
        return []
    result = []
    prev_label: str | None = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        run = entry.get("run", {})
        reasoning = entry.get("reasoning", "")
        label = run.get("label", f"run-{len(result)+1}")
        result.append({
            "id":        label,
            "parent_id": prev_label,
            "label":     label,
            "status":    "done",
            "config":    run.get("config"),
            "metrics":   run.get("metrics"),
            "energy":    run.get("energy"),
            "reasoning": reasoning,
            "ts":        run.get("ts", ""),
        })
        prev_label = label
    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Pushing to {BASE}")
    print(f"Source: {SOURCE}  |  Reset first: {RESET_FIRST}")

    if RESET_FIRST:
        print("Resetting dashboard…")
        api("/api/reset")
        time.sleep(0.5)

    runs: list[dict] = []
    if SOURCE in ("sample", "both"):
        runs += runs_from_sample()
    if SOURCE in ("journal", "both"):
        runs += runs_from_journal()

    if not runs:
        print("No runs to push.")
        sys.exit(0)

    print(f"\nPushing {len(runs)} run(s):")
    for run in runs:
        push_run(run)
        time.sleep(0.3)

    print(f"\n✓ Done — dashboard: {BASE}")


if __name__ == "__main__":
    main()
