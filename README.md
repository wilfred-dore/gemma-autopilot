# Gemma Autopilot

**Gemma 4 optimizes its own deployment: and explains every decision.**

An autonomous agent built on Gemma 4's native function calling: it benchmarks a live vLLM deployment, reads the metrics (tokens/s, TTFT, joules/token), diagnoses the bottleneck in plain language, acts (quantization, batching, prefix caching, GPU power cap), and re-benchmarks: until gains flatten. Every configuration competes on a live leaderboard, including a hand-tuned human expert baseline.

Built in one day at the Paris Gemma 4 Hackathon (42 Paris). Full writeup on Kaggle.

*Scaffold: full README lands with the code (architecture, quickstart, metrics definitions, guardrails).*
