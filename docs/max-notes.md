# Modular MAX: attempts, autopsy, current sprint

Working notes on the max-exploration branch. Goal: a measured MAX column next to the vLLM journal numbers, same 30-prompt confidential-drafting suite.

## Attempt log

| # | Setup | Outcome |
|---|---|---|
| 1 | pixi + max-nightly channel, Brev host (CUDA 12.8 driver) | crashed at startup, driver too old for the nightly kernels |
| 2 | pixi + max-nightly, RunPod H100 SXM pod | `max serve` compiled the "vision + language" graph for 28 minutes, then worker Killed (OOM) at 15:26. Sentinel kept polling a dead server. Logs preserved: `/workspace/sprint.log`, `/workspace/max-serve.log` on pod vbojpsjqrs1m6v (stopped) |
| 3 | official Docker image `modular/max-nvidia-full:latest`, RunPod H100, `--model-path google/gemma-4-12B-it` | in flight (pod esi69jn6tqsqm7) |
| 4 | same image, RunPod A40, `--model-path google/gemma-4-E4B-it` (small graph = short compile; also the edge variant our writeup cites) | in flight (pod s1z2cx2sjdlw2d) |

## Lessons

- The official Docker image beats both pixi-nightly and a hand-built venv: their tested runtime, zero install, one flag. Attempt 2 lost half its budget to environment assembly that the image makes irrelevant.
- The remaining wall is multimodal graph compilation: RAM-hungry and long on 12B-class models. Mitigations to try in order: small variant first (E4B), keep the compile cache on a persistent volume, pick pods with large system RAM.
- RunPod stop preserves `/workspace` only; anything installed in `/root` (pixi envs, caches) dies with the container layer. Put toolchains and caches on the volume or use the Docker image.
- Modular Cloud hosts Gemma 4 (31B, 26B-A4B) as managed endpoints, but signups are currently limited; a sponsor contact from the event may unlock access.

## Measuring

`scripts/max_bench.py` (stdlib only) benchmarks any OpenAI-compatible endpoint with the same prompt suite and reports output tokens/s + mean TTFT:

```bash
python3 scripts/max_bench.py \
  --base-url https://<pod-id>-8000.proxy.runpod.net \
  --model google/gemma-4-E4B-it --concurrency 8
```

Caveat for honest reporting: remote benchmarks inflate TTFT with network latency; throughput at concurrency stays server-bound. Never present these numbers as same-venue comparisons with the H100 journal.

## Next

- If a pod serves: run max_bench at concurrency 1 and 8, record JSON here, then stop the pod.
- Reproduce locally later: `docker run --gpus 1 -p 8000:8000 -e HF_TOKEN=... modular/max-nvidia-full:latest --model-path google/gemma-4-E4B-it`
- Point the autopilot loop at a MAX endpoint (one env var) and let the agent compare stacks itself: the multi-stack story becomes a recorded session.
