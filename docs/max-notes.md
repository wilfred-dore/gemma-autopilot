# Modular MAX: attempts, autopsy, current sprint

Working notes on the max-exploration branch. Goal: a measured MAX column next to the vLLM journal numbers, same 30-prompt confidential-drafting suite.

## Attempt log

| # | Setup | Outcome |
|---|---|---|
| 1 | pixi + max-nightly channel, Brev host (CUDA 12.8 driver) | crashed at startup, driver too old for the nightly kernels |
| 2 | pixi + max-nightly, RunPod H100 SXM pod | `max serve` compiled the "vision + language" graph for 28 minutes, then worker Killed (OOM) at 15:26. Sentinel kept polling a dead server. Logs preserved: `/workspace/sprint.log`, `/workspace/max-serve.log` on pod vbojpsjqrs1m6v (stopped) |
| 3 | official Docker image `modular/max-nvidia-full:latest`, RunPod H100, `--model-path google/gemma-4-12B-it` | container crash-loop (uptime resets to seconds, CPU/GPU 0%); port never opened in 40 min; pod stopped |
| 4 | same image, RunPod A40, `--model-path google/gemma-4-E4B-it` | same instant crash-loop on a different GPU and model size: systemic, not OOM. Diagnosis: the stable `latest` tag predates Gemma 4 day-zero support, which lives in the nightlies (hence the handbook's max-nightly channel) |
| 5 | `modular/max-nvidia-full:nightly` (built 2026-07-25, the day-zero build), RunPod A40, E4B | same crash-loop (uptime 7s after 35 min rented). Not an architecture-support issue alone, then. Open hypotheses: A40 is Ampere (SM86) and the day-zero kernels may target Hopper/Blackwell; gated-model auth failing repeatedly; entrypoint arg mismatch. Undiagnosable blind: RunPod's GraphQL API does not expose container logs |

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

## Next (Monday session)

- Debug with eyes: run the nightly image on a machine where docker logs are readable (RunPod web console, or a VM), the crash reason is one `docker logs` away. Blind GraphQL-only debugging was tonight's real handicap.
- Retry nightly on Hopper (H100/L40S) in case the day-zero kernels have an Ampere floor.
- If a pod serves: run max_bench at concurrency 1 and 8, record JSON here, then stop the pod.
- Reproduce locally later: `docker run --gpus 1 -p 8000:8000 -e HF_TOKEN=... modular/max-nvidia-full:latest --model-path google/gemma-4-E4B-it`
- Point the autopilot loop at a MAX endpoint (one env var) and let the agent compare stacks itself: the multi-stack story becomes a recorded session.
