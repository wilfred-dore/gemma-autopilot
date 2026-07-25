# Architecture and diagrams

Technical documentation for Gemma². Mermaid diagrams render natively on GitHub; PlantUML sources are kept alongside for local rendering (`plantuml -tsvg docs/architecture.md` friendly blocks).

## The feedback loop

```mermaid
flowchart LR
  A[Profile: vllm bench serve] --> B["Diagnose: Gemma 4 reads tokens/s, TTFT, J/token"]
  B --> C{Action via native function calling}
  C -->|run_benchmark| A
  C -->|set_power_cap / restart_server| G[Guardrails: whitelist + bounded ranges]
  G -->|accepted| D[Deployment reconfigured]
  G -->|rejected with readable reason| B
  D --> A
  C -->|report_done| E[Final leaderboard]
  A --> J[journal.jsonl + runs/state.json]
  J --> L[Live dashboard]
```

## One iteration, end to end

```mermaid
sequenceDiagram
  participant AG as agent.py (Gemma 4 operator)
  participant VL as vLLM /v1/chat/completions
  participant TO as tools.py (guardrails)
  participant BR as bench_runner.py
  participant EM as power.py EnergyMeter (NVML)
  participant JN as journal.py

  AG->>VL: chat + TOOL_SCHEMAS
  VL-->>AG: tool_call run_benchmark(concurrency=64) + reasoning_content
  AG->>TO: dispatch(run_benchmark)
  TO->>BR: run_benchmark(config)
  BR->>EM: energy counter delta around the run
  BR-->>TO: RunResult (hardware, precision, metrics, joules/token)
  TO-->>AG: result JSON
  AG->>JN: record run + reasoning
  JN-->>JN: leaderboard scoring, state.json, live push
  AG->>VL: next turn with result in context
```

## Edge deployment target: air-gapped Industry 4.0

```mermaid
flowchart LR
  subgraph AIRGAP["Air-gapped factory network"]
    CAM[Inspection cameras] --> G4["Gemma 4 E4B on Jetson (multimodal)"]
    MIC[Machine acoustics] --> G4
    G4 -->|native function calling| PLC["PLC: stop line / flag defect"]
    OPT["Gemma² optimizer loop"] -->|tunes serving config, measures J/token| G4
  end
```

## PlantUML sources

Component view:

```plantuml
@startuml
package "gemma-autopilot" {
  [agent.py] --> [tools.py] : dispatch(tool_call)
  [tools.py] --> [bench_runner.py] : run_benchmark
  [tools.py] --> [power.py] : set_power_cap
  [bench_runner.py] --> [power.py] : EnergyMeter
  [agent.py] --> [journal.py] : record(run, reasoning)
  [journal.py] --> [dashboard.html] : runs/state.json
  [journal.py] --> [Cloudflare Worker] : live push (optional)
}
[agent.py] --> [vLLM server] : /v1/chat/completions (gemma4 parsers)
[bench_runner.py] --> [vLLM server] : vllm bench serve
@enduml
```

Iteration sequence:

```plantuml
@startuml
actor Operator
Operator -> agent : python -m autopilot.agent
loop until report_done or budget
  agent -> vllm : chat(messages, tools)
  vllm --> agent : tool_call + reasoning_content
  agent -> tools : dispatch (guardrails: whitelist, bounds)
  alt accepted
    tools -> bench_runner : run_benchmark
    bench_runner --> tools : RunResult + energy
  else rejected
    tools --> agent : {"error": "rejected", "reason": ...}
  end
  agent -> journal : record + live push
end
@enduml
```
