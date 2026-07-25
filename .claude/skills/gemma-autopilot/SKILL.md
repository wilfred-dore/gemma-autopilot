---
name: gemma-autopilot
description: Drive Gemma² (gemma-autopilot), the self-optimizing Gemma 4 deployment agent. Use when benchmarking a vLLM deployment, running the autonomous optimization loop, reading the run journal or leaderboard, or extending the agent's action space. Triggers include Gemma², autopilot session, optimization loop, deployment benchmark, joules per token.
---

# Gemma² (gemma-autopilot)

Gemma 4 optimizes its own vLLM deployment: benchmark, diagnose, act, re-benchmark, with energy metering and explained decisions.

## Run

```bash
# server (H100-class GPU, driver >= 580 for stock wheels)
vllm serve google/gemma-4-12B-it --port 8000 --max-model-len 16384 \
  --gpu-memory-utilization 0.92 --enable-auto-tool-choice \
  --tool-call-parser gemma4 --reasoning-parser gemma4 \
  --chat-template tool_chat_template_gemma4.jinja   # MANDATORY template

export BENCH_MODEL=google/gemma-4-12B-it BENCH_PRECISION=bf16 BRAIN_MODEL=$BENCH_MODEL
python3 -m autopilot.agent --iters 5      # journal in runs/, dashboard reads runs/state.json
python3 -m autopilot.bench_runner         # one-shot bench of a config
```

## Architecture

`autopilot/`: bench_runner (wraps `vllm bench serve`, energy-annotated RunResult documenting hardware/precision/concurrency), power (NVML energy deltas, set_power_cap), journal (JSONL + state.json + leaderboard, TTFT-constraint scoring, reloads persisted runs), tools (whitelisted: run_benchmark, set_power_cap, search_web SerpApi, search_papers OpenAIRE, restart_server backend-switch, report_done; guardrails return readable rejections), agent (native gemma4 function calling, JSON fallback, empty-reasoning voice-the-diagnosis fallback). Dashboard: dashboard.html polls runs/state.json (`?replay=1` uses datasets/state.sample.json).

## Gotchas (hard-won)

- CUDA variants: driver 12.8 hosts need cu12x wheels for torch AND vllm AND optional kernels (flashinfer, cutlass-dsl, quack); one cu13 wheel kills engine start. Driver 580+ = stock works.
- Never pkill a pattern contained in your own command line (bracket trick: `pkill -f 'vllm serv[e]'`).
- Empty tools list must omit tool_choice (vLLM 400).
- Power capping is blocked in containerized clouds: energy wins come from batch efficiency.
- Reference numbers (H100 PCIe, 12B bf16, 30-prompt suite): defaults 405.7 tok/s / 0.768 J/tok; agent best 1,377.5 / 0.353 with TTFT 255 ms.

## Roadmap (design intent)

Action-space ladder: settings (done) → backend flags (restart_server, done) → profiling → bottleneck diagnosis → agent-written Triton kernels → model surgery (QAT fine-tune). Leaderboard: public POST API for external submissions.
