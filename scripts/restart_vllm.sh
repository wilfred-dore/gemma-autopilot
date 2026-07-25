#!/usr/bin/env bash
# Restart the vLLM deployment with a given attention backend (agent tool target).
set -e
BACKEND="${1:?usage: restart_vllm.sh <FLASH_ATTN|TRITON_ATTN|FLASHINFER>}"
pkill -f "vllm serv[e]" 2>/dev/null || true; sleep 5
export HF_HOME=${HF_HOME:-/workspace/hf}
VLLM_ATTENTION_BACKEND="$BACKEND" nohup vllm serve "${BENCH_MODEL:-google/gemma-4-12B-it}" --port 8000 --max-model-len 16384 --gpu-memory-utilization 0.92 --enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4 --chat-template /workspace/tool_chat_template_gemma4.jinja > /workspace/vllm_restart.log 2>&1 &
for i in $(seq 1 60); do curl -s -m 3 http://localhost:8000/v1/models >/dev/null 2>&1 && exit 0; sleep 10; done
exit 1
