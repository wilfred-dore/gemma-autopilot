# Gemma²

**Gemma 4 optimizes its own deployment: and explains every decision.**

An autonomous agent built on Gemma 4's native function calling: it benchmarks a live vLLM deployment, reads the metrics (tokens/s, TTFT, joules/token), diagnoses the bottleneck in plain language, acts (quantization, batching, prefix caching, GPU power cap), and re-benchmarks: until gains flatten. Every configuration competes on a live leaderboard, including a hand-tuned human expert baseline.

Built in one day at the Paris Gemma 4 Hackathon (42 Paris). Full writeup on Kaggle.

*Scaffold: full README lands with the code (architecture, quickstart, metrics definitions, guardrails).*

## Optimization levers (the agent's action space, explained)

| Lever | What it does | Typical effect |
|---|---|---|
| `concurrency` (client) | How many requests hit the server at once | The saturation lever: our biggest win (8→64 took 406→1,377 tok/s); raises TTFT, hence the 500 ms guardrail |
| `max_num_seqs` (vLLM) | Max sequences batched together server-side | Ceiling for batching; too high wastes KV memory and queues requests |
| `enable_prefix_caching` | Reuses KV cache across prompts sharing a prefix | Near-free win on templated workloads like ours; cuts prefill work and energy |
| GPU power cap (`nvidia-smi -pl`) | Hardware power ceiling | 5-15% energy for a few % throughput; blocked in most containerized clouds (we report it honestly) |
| Model variant / QAT | Swap to `gemma-4-qat-q4_0` etc. | ~2x throughput and lower J/token for a quality trade-off; QAT keeps quality close |
| Attention backend (`restart_server`) | FLASH_ATTN / TRITON_ATTN / FLASHINFER | Kernel-level differences; workload-dependent, measured not assumed |

Every run documents hardware, model variant, precision and concurrency, and every decision ships with the agent's plain-language diagnosis. Energy is measured with NVML energy-counter deltas, not estimated.
