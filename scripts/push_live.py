#!/usr/bin/env python3
"""Standalone helper to push a single agent run to the Gemma² live dashboard.

Usage examples:

  # Mark a run as starting:
  python scripts/push_live.py --endpoint https://... --key MY_KEY \
      --id agent-iter-1 --label agent-iter-1 --status running \
      --reasoning "Trying aggressive batch with prefix caching"

  # Complete a run:
  python scripts/push_live.py --endpoint https://... --key MY_KEY \
      --id agent-iter-1 --label agent-iter-1 --status done \
      --tokens-per-s 143.2 --ttft-ms 412 --itl-ms 11.3 \
      --joules 1100 --joules-per-token 0.0042 --mean-power-w 298 \
      --max-num-seqs 128 --prefix-caching true --concurrency 8
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone


def main() -> None:
    p = argparse.ArgumentParser(description="Push an agent run to the live dashboard.")
    p.add_argument("--endpoint", required=True,
                   help="Worker base URL, e.g. https://gemma-autopilot-live.xyz.workers.dev")
    p.add_argument("--key", required=True, help="API key (Authorization: Bearer ...)")

    # Identity
    p.add_argument("--id", required=True, help="Unique run id (used as tree node id)")
    p.add_argument("--parent-id", default=None, help="Parent run id for tree edge")
    p.add_argument("--label", required=True, help="Display label")
    p.add_argument("--status", choices=["running", "done", "failed"], default="done")
    p.add_argument("--reasoning", default="", help="Agent reasoning text")
    p.add_argument("--ts", default=None, help="ISO-8601 timestamp (default: now)")

    # Metrics
    p.add_argument("--tokens-per-s", type=float, default=None)
    p.add_argument("--ttft-ms", type=float, default=None)
    p.add_argument("--itl-ms", type=float, default=None)

    # Energy
    p.add_argument("--joules", type=float, default=None)
    p.add_argument("--joules-per-token", type=float, default=None)
    p.add_argument("--mean-power-w", type=float, default=None)

    # Config
    p.add_argument("--max-num-seqs", type=int, default=None)
    p.add_argument("--prefix-caching", type=lambda v: v.lower() in ("1", "true", "yes"), default=None)
    p.add_argument("--concurrency", type=int, default=None)
    p.add_argument("--power-cap-w", type=int, default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--precision", default=None)

    # Structured decision summary (shown as a "Decision" card in the UI)
    p.add_argument("--meta-json", default=None,
                    help='JSON object, e.g. \'{"action":"run_benchmark","outcome":"improved","tags":["saturation"]}\'')

    args = p.parse_args()

    payload: dict = {
        "id":        args.id,
        "parent_id": args.parent_id,
        "label":     args.label,
        "status":    args.status,
        "reasoning": args.reasoning,
        "ts":        args.ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # Metrics (only if at least tokens_per_s is given)
    if args.tokens_per_s is not None:
        payload["metrics"] = {
            "tokens_per_s": args.tokens_per_s,
            "ttft_ms":      args.ttft_ms or 0.0,
            **({"itl_ms": args.itl_ms} if args.itl_ms is not None else {}),
        }

    # Energy
    energy: dict = {}
    if args.joules is not None:          energy["joules"]           = args.joules
    if args.joules_per_token is not None: energy["joules_per_token"] = args.joules_per_token
    if args.mean_power_w is not None:    energy["mean_power_w"]     = args.mean_power_w
    if energy:
        payload["energy"] = energy

    # Config
    config: dict = {}
    if args.max_num_seqs is not None:   config["max_num_seqs"]           = args.max_num_seqs
    if args.prefix_caching is not None: config["enable_prefix_caching"]  = args.prefix_caching
    if args.concurrency is not None:    config["concurrency"]             = args.concurrency
    if args.power_cap_w is not None:    config["power_cap_w"]             = args.power_cap_w
    if args.model:                      config["model"]                   = args.model
    if args.precision:                  config["precision"]               = args.precision
    if config:
        payload["config"] = config

    if args.meta_json:
        try:
            payload["meta"] = json.loads(args.meta_json)
        except json.JSONDecodeError as exc:
            print(f"✗ --meta-json is not valid JSON: {exc}", file=sys.stderr)
            sys.exit(1)

    url = args.endpoint.rstrip("/") + "/api/push"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {args.key}",
                 "User-Agent": "Mozilla/5.0 (gemma-autopilot push script)"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            print(f"✓ Pushed — {body}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"✗ HTTP {exc.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
