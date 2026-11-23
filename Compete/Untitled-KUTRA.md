


Based on the KURTA blueprint you provided, the core principle for model selection is: **match complexity to task, tier the models, and never use a top-tier model for tasks that a lightweight model can handle.**

The pipeline already contains 13 stages with vastly different requirements: some steps (S4 validation, S8 policy) are pure code or deterministic logic that **do not require LLMs at all**; some steps (S1, S5, S11) are structured input/output with minimal reasoning required; only a few steps (S2, S3, S7, S9) genuinely require semantic understanding, planning, or judgment capabilities.

## Recommended Model Allocation Strategy

| Stage | Task Nature | Recommended Model Tier | Rationale & Reference Pricing |
|---|---|---|---|
| **S4 Plan validation** | Pure code, Kahn cycle detection, construction-time validation | **No LLM** | The blueprint explicitly states "zero LLM"; introducing a model only adds latency and cost |
| **S8 Policy decision** | OPA/Rego deterministic rules | **No LLM** | Policies must be replayable and provable; LLM non-determinism is a liability |
| **S1 Goal intake** | Receiving raw text + permalinks, no interpretation | **No LLM** (or nano-tier only for routing/classification) | Blueprint states "nothing is interpreted here" |
| **S5 Tool execution** | Structured ToolCallRequest → ToolResult | **Lightweight tier** | Requires JSON Schema compliance and tool calling capability; no deep reasoning needed |
| **S6 Document parsing** | Parser + chunking + embedding + ACL synchronization | **Lightweight tier** (extraction confidence threshold 0.7 already enforced) | Extraction is pattern-matching work; high accuracy is not required, but confidence filtering is |
| **S11 Gated mutation** | Executing writes after approval, idempotency guarantee | **Lightweight tier** | Deterministic execution + compensation logic; LLM only assists in formatting |
| **S2 Goal parsing → GoalSpec** | Natural language → typed contract, confidence floor 0.85 | **Mid-tier** | Requires semantic understanding and structured output; but blueprint already limits repair rounds ≤2 |
| **S9 Self-correction** | SCHEMA_DRIFT, FIELD_ALIAS_REMAP and similar recovery strategies | **Mid-tier** | Requires understanding error types and selecting mappings; bounded retries ≤3 |
| **S10 HITL approval** | Bundling evidence, generating human-readable decision packages | **Mid-tier** | Requires organizing blast_radius, cites, policy decision summaries; output is read by humans, not machine-executed |
| **S7 Anomaly scoring** | Feature engineering + IForest/GBM, model sees only numeric features | **Mid-tier** (LLM only for policy_hit citation) | Core scoring is traditional ML; LLM may assist in binding SpanRef |
| **S3 Plan compile** | Top-tier LLM + playbook library, known goals matched via playbook DAG | **Top-tier** (only when playbook has no match) | This is the only stage requiring complex planning; but blueprint already specifies "known goals map to vetted playbook DAGs", **most requests should not invoke free planning** |
| **S12/S13 Trace/ROI** | Append-only writes / SQL aggregation | **No LLM** | Deterministic data operations |

## Key Cost Control Points

**S3 is the biggest cost risk, not the model itself.** The blueprint already designs the "planbook match short-circuits free planning" mechanism [file content]. Ensure routing logic is: GoalSpec hits playbook → return template DAG directly, do not call top-tier model; only truly novel goals go through free planning. Reference data: In the AgentOpt benchmark, Opus achieved 72% on BFCL at a cost of $60.78, while Qwen3 Next achieved 71% (only 1 point lower) at a cost of **$1.87**—a 32x cost difference . The marginal value of top-tier models is very low outside of the S3/S2 critical paths.

**Lightweight tiers are already very capable.** Current small model pricing has dropped to very low levels: GPT-5 nano input $0.05/M, output $0.40/M ; Claude Haiku 4.5 input $1/M, output $5/M . For structured tasks like S5/S6/S11, small models with JSON mode and tool calling are entirely sufficient.

**Mid-tier models should be the mainstay.** Claude Sonnet 4.5 ($3/$15) or GPT-5 ($1.25/$10)  offer a good balance between capability and cost for S2, S7, S9, S10. They can handle schema-constrained generation and error diagnosis without wasting budget like top-tier models.

## Specific Recommendations

```
This is a well-designed, cost-effective tiered model routing architecture. The core philosophy is spot-on: keep deterministic logic in code and policy engines (OPA), use lightweight models for high-frequency extraction, and reserve mid-to-high-tier models strictly for complex reasoning and fallback handling, while using Playbook hit rates to continuously drive down frontier model costs.
From an architectural, latency, and cost-optimization standpoint, here is an evaluation along with a few targeted adjustments:

1. Architectural Strengths

• Zero LLM for Deterministic Tasks: Keeping S1 (routing), S4 (pure code), S8 (OPA policy engine), and S12/S13 completely off LLMs guarantees deterministic execution, low latency, and zero hallucinations for core checks and state transitions.
• Gated High-Tier Usage (S3): Restricting top-tier models (Opus 4.5 / GPT-5.6-sol) strictly to playbook miss edge cases is smart. As your Playbook library matures, S3 invocation volume will naturally shrink.
• Confidence Filtering at S6: Pairing a lightweight model with confidence filtering is a proven pattern to catch silent failures early and trigger retries or model escalation.

2. Optimization Opportunities (Latency & Cost)


Stage	Current Setup	Suggested Adjustment	Rationale
S7	Mid-tier (only for policy_hit citation binding)	Downgrade to Lightweight (Haiku / mini) + Regex/String Verification	Citation binding is fundamentally span alignment and extraction, not deep reasoning. A lightweight model followed by a deterministic check (verifying the quoted substring exists in the source text) is faster, cheaper, and just as accurate.
S9	Mid-tier (error classification & recovery strategy)	Rule-based lookup first -> Mid-tier fallback	Place a regex/error-code mapper in front of S9. Known transient errors (timeouts, schema mismatches, missing fields) should map directly to recovery actions in code; invoke the mid-tier model only for novel or ambiguous failures.
S10	Mid-tier (human-readable decision package)	Template Engine + Lightweight Polish (if structured)	If the decision package follows a fixed layout (e.g., JSON-to-Markdown summary), deterministic templating is instant and error-free. Keep the mid-tier model only if S10 requires synthesizing unstructured narrative across multiple conflicting evidence sources.
S11	Lightweight (execution layer)	Enforce Strict Structured Outputs (JSON Schema)	Since S11 interfaces directly with downstream APIs or tool calls, enforce strict schema decoding to prevent lightweight models from breaking execution with minor formatting drift.


3. Three Key Production Guardrails

1. Calibrating S6 Confidence Scores: LLMs are notoriously overconfident when asked to self-report confidence scores. Instead of relying solely on prompted scores, use token logprobs or self-consistency (sampling the lightweight model 2–3 times at low temperature and checking agreement) to make escalation decisions.
2. Closing the S3 → Playbook Loop: Every time S3 resolves a playbook miss, trigger an asynchronous background job to distill that execution trace into a candidate Playbook rule. Once reviewed and merged, future similar requests bypass S3 entirely.
3. Payload Pruning Across Stages: Across a 13-stage pipeline, passing full historical context downstream will inflate token costs and Time-To-First-Token (TTFT). Enforce strict state schemas so each node only receives the exact fields required for its step.
If you'd like to refine this further, let me know:
• The specific use case (e.g., compliance/risk review, automated ops, customer support)
• The exact responsibility of each stage (S1–S13)
• Your primary bottleneck (end-to-end latency vs. token cost)
I can help you design the exact escalation thresholds or the inter-stage JSON state schema.
```

**Final principle**: The LLM Gateway on the KURTA blueprint should be configured with **at least three tiers of routing** (nano/mini-level, mid-tier, top-tier), and pin different stages to different model versions in the code. Blueprint S12 already records `llm_ctx(model, prompt hash, seed, temp)` for each call, so cost attribution and model switching are naturally traceable. Don't let S2's parsing errors propagate to S3 and trigger an expensive top-tier plan; instead, trigger the "clarification-request" mechanism (blueprint S2 failure handling already specifies this).

_____________________________________________________________-------------------------------------------------------------________________________________________________________________--------------------

Based on the KURTA pipeline's tiered model architecture, here is the concrete parameter configuration (temperature, max_tokens, system prompt) for each LLM-involved stage. The core principle: **structured extraction and deterministic tasks use low temperature (0.1–0.2); planning and error diagnosis use medium temperature (0.3–0.6); no stage uses high temperature, because KURTA's outputs are contracts, not creative content.**

---

## S2 Goal parse → GoalSpec (Mid-tier: Claude Sonnet 4.5 / GPT-5)

| Parameter | Value | Rationale |
|---|---|---|
| **temperature** | **0.1** | Converting natural language to typed contracts is structured extraction; low temperature ensures consistent field values  |
| **max_tokens** | **1024** | GoalSpec contains ~10 fields, each short (objective ≤500 chars, enum, list); 1024 is sufficient and won't preempt capacity  |
| **System prompt** | See below | |

```
You are KURTA's goal parser. Convert the user's raw goal into a strictly-typed GoalSpec JSON.
Rules:
- Output ONLY valid JSON matching the provided schema. No prose, no markdown.
- If a field cannot be inferred with ≥0.85 confidence and a blocking ambiguity exists, set parsed_confidence honestly and populate ambiguity_flags. Do NOT guess.
- budget_cap must be integer minor units (cents) + ISO-4217 currency. Floats are rejected.
- acceptance_criteria must have at least one item. If none are explicit, infer the minimum reasonable criterion from the deliverable enum.
- Repair rounds are capped at 2; if still invalid, emit a clarification-request signal, never a fabricated spec.
```

**Validation:** Blueprint S2 already specifies the "confidence 0.85 floor while blocking ambiguity exists" refusal rule; temperature 0.1 makes the confidence score itself more stable.

---

## S3 Plan compile (Top-tier: Claude Opus 4.5 / GPT-5.6-sol)

This is **the only stage that truly needs a top-tier model**, and it should **only be called when the playbook has no match**.

| Parameter | Value | Rationale |
|---|---|---|
| **temperature** | **0.4** | Planning requires some exploratory paths (playbook miss = novel goal), but not creativity; 0.4 balances structured reasoning with room for alternative DAGs  |
| **max_tokens** | **2048** | PlanStep[] contains steps, args_schema_ref, gate ids, spend; 2048 supports 5–8 step plans without truncation  |
| **System prompt** | See below | |

```
You are KURTA's planner. Compile a GoalSpec into a CompiledPlan DAG.
Rules:
- Every step must declare step_id, args_schema_ref, declared IO fields, spend (minor units), and a gate id if it mutates state or sends externally.
- An ungated mutating step makes the entire plan invalid — do not emit one.
- Prefer the simplest DAG that satisfies all acceptance_criteria within budget_cap.
- Set temperature ceiling to 0.4; if you need multiple plan variants, return the single highest-confidence plan, not alternatives.
- goal_sha256 must be the SHA-256 of the canonical GoalSpec JSON (sorted keys, no whitespace).
```

**Critical cost control:** The blueprint already specifies `plan-cache (goal_sha→plan)`. The code must check this cache **before** calling the model; playbook matches should short-circuit free planning entirely. The top-tier model is a fallback, not the default path.

---

## S5 Tool execution (Lightweight: Claude Haiku 4.5 / GPT-5-mini)

| Parameter | Value | Rationale |
|---|---|---|
| **temperature** | **0** | Tool calls must be deterministic; the same ToolCallRequest must produce the same arguments  |
| **max_tokens** | **256** | ToolResult/error structures are bounded; 256 is sufficient for `ok`, `data`, `error.kind`, `usage`  |
| **System prompt** | See below | |

```
You are KURTA's connector. Execute the tool call exactly as specified.
Rules:
- Do not modify arguments. If a field is missing or malformed, return error kind=INVALID_ARGS, do not guess.
- On schema mismatch, return error kind=SCHEMA_DRIFT with observed vs expected versions. Do not attempt to reconcile.
- Output must be ToolResult JSON: {ok, data: {columns_dtypes, rows}, error: {kind, message, observed?, expected?}, usage}.
- temperature=0. Deterministic execution only.
```

**Note:** S5's core work is HTTP calls to external APIs; the LLM is only invoked for parameter validation and error classification. If the connector already implements typed validation, the LLM can be skipped entirely for successful calls.

---

## S6 Document ingestion (Lightweight: Haiku 4.5 / GPT-5-mini)

| Parameter | Value | Rationale |
|---|---|---|
| **temperature** | **0.1** | Entity extraction is structured; but extracts require span quotes, so slight flexibility helps handle parser variations  |
| **max_tokens** | **2048** | Per-document IngestedItem may contain multiple entities with spans; 2048 supports a medium-length document batch  |
| **System prompt** | See below | |

```
You are KURTA's entity extractor. Extract ClauseEntity items from parsed document chunks.
Rules:
- Every entity MUST carry a span: {start, end} within the chunk, plus extractor version.
- confidence < 0.7 is rejected by the contract — if you are below that, do not emit the entity.
- content_sha256 and doc_version_sha256 are computed by the parser, not by you; leave them as provided.
- Do not summarize or paraphrase. The span IS the evidence.
```

**Validation:** Blueprint S6 refusal case "low-confidence extraction rejected: Input should be greater than or equal to 0.7" — the system prompt reinforces this, but the schema validator is the enforcement.

---

## S9 Self-correction (Mid-tier: Sonnet 4.5 / GPT-5)

| Parameter | Value | Rationale |
|---|---|---|
| **temperature** | **0.3** | Selecting a recovery strategy (FIELD_ALIAS_REMAP vs ALTERNATE_SOURCE vs REPLAN) requires judgment, but must stay bounded  |
| **max_tokens** | **512** | SelfCorrectionEvent is compact: strategy enum, rows_revalidated, outcome, mapping preview |
| **System prompt** | See below | |

```
You are KURTA's recovery middleware. Given a ToolError, select exactly one strategy from the closed enum.
Rules:
- SCHEMA_DRIFT → prefer FIELD_ALIAS_REMAP if a known field-map exists; else ALTERNATE_SOURCE; else REPLAN_SUBGRAPH.
- AUTH → never retry; emit ESCALATE_HUMAN.
- RATE_LIMIT → RETRY_BACKOFF with the provided retry_after; do not invent a delay.
- Bounded retries ≤3. After the 3rd failure, ESCALATE_HUMAN with mapping preview.
- Output SelfCorrectionEvent JSON only. Free text goes in reason field, not in strategy.
```

**Critical constraint:** The blueprint explicitly states "bounded retries ≤3 then escalate." The system prompt must enforce this; otherwise the model will invent retry 4.

---

## S10 HITL approval (Mid-tier: Sonnet 4.5 / GPT-5)

| Parameter | Value | Rationale |
|---|---|---|
| **temperature** | **0.2** | Building evidence bundles is structured summarization; low temperature ensures the bundle doesn't fabricate  |
| **max_tokens** | **1024** | ApprovalRequest contains blast_radius[], evidence cites, policy sha, expiry; 1024 covers a complex bundle |
| **System prompt** | See below | |

```
You are KURTA's approval packager. Assemble an ApprovalRequest for a human signer.
Rules:
- Every blast_radius item must be a reversible enum value; do not invent new ones.
- evidence_cites must reference actual SpanRef ids from the trace — do not summarize or paraphrase.
- policy_decision_sha256 is provided; copy it exactly.
- If any required evidence is missing, do not fill gaps; emit incomplete=true and list the missing refs.
- The human is the decision-maker. Your job is to make the decision easy, not to make it for them.
```

**Validation:** Blueprint S10 refusal case "reject without reason rejected: rejections without a reason never teach the agent" — the system prompt should also instruct: if the eventual decision is REJECT, the reason field is mandatory (this is enforced at the ApprovalDecision level, but the model can prompt for it in the request UI copy).

---

## Stages with No LLM (confirm in configuration)

| Stage | Why no LLM | Config action |
|---|---|---|
| **S1 Goal intake** | Blueprint: "nothing is interpreted here" | No model config; pure ingestion endpoint |
| **S4 Plan validation** | Blueprint: "pure code, zero LLM" | No model; Pydantic validators + Kahn cycle check |
| **S8 Policy decision** | Blueprint: "same input ⇒ same decision — provable, replayable" | No model; OPA/Rego only. LLM non-determinism would break the replay guarantee |
| **S11 Gated mutation** | Executor is deterministic write path | No model for the write itself; compensation logic is code |
| **S12 Trace append** | Append-only writer | No model; LLM_ctx from upstream steps is recorded, not generated |
| **S13 ROI aggregation** | SQL/dbt nightly job | No model; derived from trace rows only |

---

## Global Configuration Notes

1. **GPT-5+ models have no `temperature` parameter.** If you use GPT-5 for any stage, the routing layer must omit `temperature` from the request and use `max_completion_tokens` instead of `max_tokens` . The tier table above assumes Sonnet/Opus-class models where both parameters exist; if GPT-5 is used, temperature is managed by the model and you only control `max_completion_tokens`.

2. **`llm_ctx` in S12 TraceRow must record the exact params used.** The blueprint already specifies `llm_ctx(model, prompt hash, seed, temp)`. Every call above must write these values into the trace row, so cost attribution and reproducibility are queryable.

3. **Prompt hash, not prompt text, in logs.** The blueprint's TraceRow `llm_ctx.prompt hash` implies the system prompt itself is versioned separately (e.g., in a prompt registry), and only the hash is logged. This keeps the trace store WORM-compatible and avoids PII leakage.

4. **Temperature is per-call, not per-model.** The same Sonnet 4.5 is used at S2 (0.1), S9 (0.3), and S10 (0.2) — the routing layer must pass temperature per call, not pin it to the model ID.