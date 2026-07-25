"""Lightweight OpenAI-compatible endpoint benchmark, stdlib only.

Runs the confidential-drafting prompt suite against any /v1/chat/completions
endpoint (vLLM, MAX, llama.cpp) and reports aggregate output tokens/s and
mean TTFT. Network latency inflates TTFT on remote endpoints; throughput at
concurrency stays server-bound. Comparable in shape, not in venue, with the
H100 journal numbers.

Usage:
    python3 scripts/max_bench.py --base-url https://HOST:PORT \
        --model google/gemma-4-E4B-it --concurrency 8 --num-prompts 30
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def load_prompts(path: str, n: int) -> list[str]:
    prompts = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            prompts.append(row.get("prompt") or row.get("text") or "")
            if len(prompts) >= n:
                break
    return prompts


def one_request(base_url: str, model: str, prompt: str, max_tokens: int) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    ttft = None
    completion_tokens = 0
    chunks = 0
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                usage = obj.get("usage")
                if usage and usage.get("completion_tokens"):
                    completion_tokens = usage["completion_tokens"]
                for choice in obj.get("choices", []):
                    if choice.get("delta", {}).get("content"):
                        chunks += 1
                        if ttft is None:
                            ttft = time.monotonic() - t0
    except Exception as exc:
        return {"error": str(exc)[:200]}
    elapsed = time.monotonic() - t0
    return {
        "elapsed_s": elapsed,
        "ttft_s": ttft if ttft is not None else elapsed,
        "completion_tokens": completion_tokens or chunks,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--dataset", default="datasets/confidential_drafting.jsonl")
    ap.add_argument("--num-prompts", type=int, default=30)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=512)
    args = ap.parse_args()

    prompts = load_prompts(args.dataset, args.num_prompts)
    print(f"{len(prompts)} prompts, concurrency {args.concurrency}, "
          f"max_tokens {args.max_tokens}")

    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(
            lambda p: one_request(args.base_url, args.model, p,
                                  args.max_tokens),
            prompts))
    wall = time.monotonic() - t0

    ok = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]
    total_tokens = sum(r["completion_tokens"] for r in ok)
    report = {
        "endpoint": args.base_url,
        "model": args.model,
        "num_prompts": len(prompts),
        "concurrency": args.concurrency,
        "completed": len(ok),
        "errors": len(errors),
        "wall_s": round(wall, 1),
        "total_output_tokens": total_tokens,
        "output_tokens_per_s": round(total_tokens / wall, 1) if wall else 0,
        "mean_ttft_ms": round(
            1000 * sum(r["ttft_s"] for r in ok) / len(ok), 0) if ok else None,
        "note": "remote benchmark: network inflates TTFT; throughput at "
                "concurrency stays server-bound",
    }
    print(json.dumps(report, indent=2))
    if errors:
        print("first error:", errors[0]["error"])


if __name__ == "__main__":
    main()
