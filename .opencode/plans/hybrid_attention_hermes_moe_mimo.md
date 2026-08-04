# DevMind IDE — Advanced Features Implementation Plan

## Objective
Implement hybrid linear attention (KDA/Kimi delta attention), Hermes agent with high-speed execution nodes, tool calling, reasoning, MoE (Mixture of Experts), LLM/VLM support, BigPixel/Mimo (multiple input multiple output), and multi-stream data handling.

## New Files to Create

### 1. `attention_engine.py` — Hybrid Linear Attention (KDA/Kimi Delta)
- `AttentionConfig` dataclass with head_dim, num_heads, use_kda, use_delta, compression_ratio
- `HybridLinearAttention` class with forward(), kda_attention(), kimi_delta_attention(), linear_attention(), compress_context()
- `AttentionRouter` class that routes attention computation based on model type and context length
- Integration: Called from agent.py ollama_chat() and dispatch_single_model() to compress context before sending to LLM

### 2. `hermes_agent.py` — Hermes High-Speed Execution Agent
- `HermesAgent(Agent)` with role="hermes", reasoning_depth, tool_calling_mode, max_execution_steps
- `async execute(task)` with reasoning + tool loop
- `async _reasoning_step(task)` for chain-of-thought reasoning
- `async _tool_execution_loop(task, max_steps)` for iterative tool call loop with loop detection
- `async _moe_route(task)` for routing to best expert model
- `HermesToolExecutor` with execute_with_retry(), execute_with_timeout(), validate_tool_params()
- `create_hermes_agents()` factory
- Integration: Registered with _orchestrator in server.py alongside existing specialists

### 3. `moe_router.py` — Mixture of Experts Runtime Router
- `ExpertProfile` dataclass with expert_name, model, capabilities, speed_tier, cost_per_token
- `MoERouter` with route_task(), route_model(), add_expert(), remove_expert(), get_expert_status()
- `TaskClassifier` with classify() and extract_keywords()
- `MoEPolicy` with select_expert() and balance_load()
- Integration: MoERouter instantiated in server.py startup, shared with AgentOrchestrator

### 4. `multimodal_engine.py` — LLM/VLM Support & BigPixel/Mimo
- `VLMEngine` with process_image(), process_multi_image(), validate_image(), compress_image()
- `MimoArchitecture` with process_multi_input(), merge_outputs()
- `BigPixelProcessor` with process_big_pixel(), stitch_results()
- `VisionConfig` dataclass
- `InputChannel` / `OutputChannel` dataclasses
- Integration: VLMEngine used in server.py WebSocket handler for image messages; MimoArchitecture used by HermesAgent for parallel subtask processing

### 5. `stream_manager.py` — Multi-Stream Data Handling
- `StreamManager` with register_stream(), merge_streams(), multiplex(), broadcast()
- `StreamChannel` with put(), get(), subscribe(), unsubscribe()
- `StreamRouter` with route(), register_handler()
- Integration: StreamManager instantiated in server.py, used in WebSocket chat handler to replace simulated streaming

### 6. `reasoning_engine.py` — Chain-of-Thought Reasoning
- `ReasoningConfig` dataclass with enabled, max_steps, style
- `ReasoningEngine` with generate_reasoning(), self_consistency_check(), extract_reasoning_blocks(), strip_reasoning(), verify_reasoning()
- `ReasoningTrace` with steps tracking
- Integration: ReasoningEngine.strip_reasoning() called in server.py alongside remove_tool_calls(); HermesAgent._reasoning_step() calls ReasoningEngine.generate_reasoning()

## Modifications to Existing Files

### agent_core.py
- Add `AgentStatus.EXECUTING = "executing"` to enum
- Add `reasoning_trace`, `attention_config`, `stream_channels` fields to Task dataclass
- Add `AgentOrchestrator.set_moe_router()` and `get_expert_status()` methods
- Modify `Agent.execute()` to accept optional reasoning_config and attention_config

### agent.py
- Add lazy imports for attention_engine, stream_manager, hermes_agent
- Modify compact_history() to use HybridLinearAttention.compress_context()
- Add hermes_execute(), process_vlm(), process_mimo() functions
- Modify ollama_chat() to accept attention_config parameter
- Add make_hermes_tool(), make_moe_router_tool(), make_vlm_tool(), make_mimo_tool(), make_reasoning_tool()
- Modify create_tool_registry() to conditionally register new tools

### server.py
- Add imports for hermes_agent, moe_router, multimodal_engine, stream_manager, reasoning_engine (lazy with try/except)
- At startup: register Hermes agents, initialize MoERouter, StreamManager, VLMEngine, ReasoningEngine
- Add WebSocket message types: "reasoning", "stream_status", "moe_routed", "vlm_processing"
- Add HTTP endpoints: /api/hermes/status, /api/moe/experts, /api/moe/route, /api/vlm/process, /api/mimo/process, /api/streams/*, /api/reasoning/config
- Modify WebSocket chat handler to support HermesAgent reasoning+tool loop pattern

### agent_specialists.py
- Add HermesAgent class (import from hermes_agent.py)
- Add MoEAgent class
- Modify create_default_agents() to include "hermes" and "moe_router" agents

### agent_command_center.py
- Add spawn_hermes_agent(), execute_mimo_task(), get_stream_status(), set_reasoning_depth(), route_task()

### config.json
- Add hermes, moe_router, vision, mimo, reasoning agent entries

### working_models.json
- Add vision-capable models with metadata
- Add hermes model entry

## Phased Implementation Order

### Phase 1: Foundation (Files: attention_engine.py, stream_manager.py, agent_core.py modifications)
### Phase 2: Hermes Agent & Reasoning (Files: hermes_agent.py, reasoning_engine.py, agent.py modifications)
### Phase 3: MoE Routing & VLM/MIMO (Files: moe_router.py, multimodal_engine.py, agent_core.py orchestrator integration)
### Phase 4: Multi-Stream & Polish (server.py WebSocket integration, all endpoints)
### Phase 5: Validation (tests, benchmarks, documentation)

## Key Architecture Decisions
1. Lazy imports with try/except — all new modules gracefully degrade if unavailable
2. No breaking changes to Agent base class — all new functionality is additive
3. Shared orchestrator singleton — _orchestrator is the single integration point
4. WebSocket-first streaming — replaces simulated streaming with StreamChannel-based streaming
5. Config-driven expert registration — new agents registered in config.json
6. Reasoning as first-class message type — distinct "reasoning" WebSocket message type