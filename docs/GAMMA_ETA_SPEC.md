# γ + η = C: The Cognitive Budget Specification

**Status:** Experimental — Mathematical Foundation
**Version:** 1.0.0-draft
**Authors:** SuperInstance
**Dependencies:** conservation-enforcer v0.2.0+, FLUX bytecode ISA

---

## 1. Abstract

Every cognitive system — human, animal, or artificial — operates under a
finite capacity budget **C**. This budget is partitioned into two
complementary allocations:

- **γ (gamma):** *Marked capacity* — the charted, committed, structured
  portion. System prompts, cached patterns, framework instructions,
  few-shot exemplars, fine-tuned priors.
- **η (eta):** *Unmarked capacity* — the negative space. The genuinely
  available, uncommitted portion where novel discovery can occur.

These satisfy a conservation law:

> **γ + η = C**

This is not metaphor. It is a measurable, falsifiable constraint on LLM
behaviour that predicts empirical phenomena observed in multi-model
casting experiments. This document specifies the mathematical definition,
measurement protocols, operational consequences, and implementation hooks
for enforcement within the SuperInstance architecture.

---

## 2. Mathematical Definitions

### 2.1 Total Cognitive Capacity: C

For a transformer-based language model, total cognitive capacity is a
function of the architectural inference envelope:

```
C = W × H × P
```

Where:

| Symbol | Quantity | Unit |
|--------|----------|------|
| **W** | Maximum context window length | tokens |
| **H** | Number of attention heads (effective) | dimensionless |
| **P** | Effective precision bits per parameter activation | bits |

For practical purposes, we use a simplified capacity metric:

```
C_effective = W_context × H_heads
```

This captures the information-theoretic channel capacity of a single
forward pass: how many distinct token-head attention allocations the
model can make before saturation.

**Examples:**

| Model | Context (W) | Heads (H) | C_effective |
|-------|-------------|-----------|-------------|
| GPT-4 (128k) | 128,000 | 128 | 16,384,000 |
| Claude 3 Opus | 200,000 | 96 | 19,200,000 |
| Llama 3 70B | 8,000 | 64 | 512,000 |
| Ornith-35B | 4,000 | 32 | 128,000 |

### 2.2 Marked Capacity: γ (Gamma)

Marked capacity is the portion of C committed to structured instructions,
patterns, and priors at inference time:

```
γ = γ_system + γ_fewshot + γ_context + γ_framework
```

| Component | Source | Measurable As |
|-----------|--------|---------------|
| γ_system | System prompt tokens | Token count × head saturation factor |
| γ_fewshot | Few-shot exemplar tokens | Token count |
| γ_context | Injected context (RAG, tool results, conversation history) | Token count |
| γ_framework | Fine-tuned behavioral patterns, RLHF priors | Estimated from model size and training data overlap |

For measurement purposes:

```
γ_measured = tokens(system_prompt) + tokens(few_shot) + tokens(injected_context)
```

This is a lower bound. The true γ also includes implicit framework
weight from training, which is not directly measurable at inference time
but can be estimated by comparing behaviour across models of the same
family with different fine-tuning levels.

### 2.3 Unmarked Capacity: η (Eta)

Unmarked capacity is the residual:

```
η = C − γ
```

This is the space of genuinely novel associations the model can form
during inference. It is where:

- Unexpected connections arise (cross-domain synthesis)
- "Hallucinations" that are actually creative leaps occur
- Thin-chart models outperform thick-chart models on discovery tasks
- The model can surprise both the user and itself

**Key insight:** Increasing framework (instructions, constraints, context)
**strictly decreases** discovery capacity. Every token of instruction is
a token of foreclosed possibility space.

### 2.4 Chart Thickness: γ/C Ratio

The dimensionless ratio that characterises a model configuration's
position on the discovery–synthesis spectrum:

```
τ = γ / C          (chart thickness)
```

| Range | Classification | Behaviour |
|-------|---------------|-----------|
| τ < 0.15 | Ultra-thin | Raw, unfocused, high noise, maximal discovery |
| 0.15 ≤ τ < 0.30 | Thin | High discovery, moderate coherence |
| 0.30 ≤ τ ≤ 0.70 | Balanced | Moderate discovery and synthesis |
| 0.70 < τ ≤ 0.85 | Thick | High synthesis, low discovery |
| τ > 0.85 | Ultra-thick | Rigid, deterministic, near-zero discovery |

### 2.5 Conservation Constraint

The constraint γ + η = C is **exact and non-violable**. There is no
"hidden" cognitive capacity. Every unit of C is either allocated (γ)
or available (η). This means:

- You cannot add framework without removing discovery.
- You cannot maximise both structure and surprise simultaneously.
- Every system prompt token has an opportunity cost measured in η.
- The only way to increase both γ and η is to increase C (larger model,
  longer context, more heads).

This is the fundamental tension that the conservation-enforcer exists to
maintain awareness of.

---

## 3. Measurement Protocols

### 3.1 Measuring γ

```python
γ = tokenize(system_prompt) + tokenize(few_shot_examples) + tokenize(injected_context)
```

For models with known fine-tuning load, add an estimate:

```python
γ_total = γ_measured + γ_finetune_estimate
```

Where `γ_finetune_estimate` can be derived by comparing the model's
behavioural compliance rate against its base model (higher compliance =
higher γ_finetune).

### 3.2 Estimating η

```python
η = C_effective − γ_measured − tokens(expected_output)
```

The expected output allocation reduces available η because the model
must reserve capacity for generation. This is analogous to reserving
working memory for speech production.

### 3.3 Measuring Chart Thickness

```python
τ = γ_measured / C_effective
```

Classification:

- **Thin chart:** τ < 0.30 — optimised for discovery
- **Balanced chart:** 0.30 ≤ τ ≤ 0.70
- **Thick chart:** τ > 0.70 — optimised for synthesis

### 3.4 Measurement Procedure

```
PROCEDURE measure-cognitive-budget(model, prompt_config):
  1. Identify model parameters: context_window, attention_heads
  2. Compute C_effective = context_window × attention_heads
  3. Tokenize each γ component:
     - system_prompt tokens
     - few_shot_example tokens
     - injected_context tokens (RAG, history, tools)
  4. Sum: γ = γ_system + γ_fewshot + γ_context
  5. Compute: η = C_effective − γ − reserved_output_tokens
  6. Compute: τ = γ / C_effective
  7. Classify chart: thin / balanced / thick
  8. Report {C, γ, η, τ, classification}
```

---

## 4. Socratic Casting Protocol

### 4.1 Principle

The casting experiments of July 2026 empirically demonstrated that
**thin-chart models discover what thick-chart models cannot**, and
**thick-chart models synthesise what thin-chart models cannot**. This
is not a quality difference — it is a **budget allocation difference**.

The Socratic Casting Protocol exploits this by always casting in the
correct order:

### 4.2 Protocol Steps

```
PROCEDURE socratic-cast(task):
  ┌─────────────────────────────────────────────┐
  │ PHASE 1: DISCOVERY (thin-chart model FIRST) │
  │                                             │
  │ 1. Select model with τ < 0.30               │
  │ 2. Provide MINIMAL prompt (low γ)           │
  │ 3. Ask open-ended question                  │
  │ 4. Collect raw outputs (high η discoveries) │
  │ 5. Do NOT constrain format or structure     │
  └──────────────────────┬──────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────┐
  │ PHASE 2: SYNTHESIS (thick-chart model)      │
  │                                             │
  │ 1. Select model with τ > 0.50               │
  │ 2. Provide discovery outputs as context     │
  │ 3. Provide STRUCTURED framework (high γ)    │
  │ 4. Ask for architecture/synthesis           │
  │ 5. Collect refined output                   │
  └─────────────────────────────────────────────┘
```

### 4.3 Ordering Constraint

**NEVER reverse this order.** Casting a thick-chart model first
contaminates the discovery space because:

1. The thick-chart model's output reflects its priors, not the space
   of possibilities.
2. When this output is fed to a thin-chart model as context, it
   increases the thin model's γ, destroying its η advantage.
3. The result is two models producing the same blind spots.

Casting thin-first ensures that the thick model's synthesis phase
operates on genuinely novel raw material rather than its own reflected
assumptions.

### 4.4 Empirical Evidence

| Experiment | Date | Finding |
|------------|------|---------|
| Casting Call | 2026-07-12 | Ornith-35B (τ ≈ 0.15) produced fiction rated 9/10, beating Hermes-405B (τ ≈ 0.65) at 4/10 |
| DeepSeek vs Hermes | 2026-07-12 | DeepSeek-V4-Flash (τ ≈ 0.20) delivered 8/10 creative work at fraction of cost |
| Seed-2.0-pro | 2026-07-12 | Large model with low τ (minimal prompt) produced 9/10 essay work — confirming that τ matters more than model size |

**Conclusion:** Model size ≠ model creativity. Chart thickness (τ)
predicts creative discovery capacity better than parameter count.

---

## 5. Implementation Specification

### 5.1 CognitiveBudget Class

```python
from conservation_enforcer.cognitive_budget import CognitiveBudget, ChartThickness

# At prompt construction time:
budget = CognitiveBudget(
    context_window=128000,
    attention_heads=128,
)

# Add framework components:
budget.add_system_prompt(system_text)
budget.add_few_shot(examples_text)
budget.add_context(rag_results)

# Check status:
print(budget.chart_thickness)      # ChartThickness.THIN
print(f"γ = {budget.gamma}")       # marked capacity
print(f"η = {budget.eta}")         # available capacity
print(f"τ = {budget.tau:.3f}")     # γ/C ratio

# Alerts:
if budget.is_over_frameworked:
    print(f"⚠️  Over-frameworked: τ = {budget.tau:.3f}")
    print(f"   Reduce context by {budget.excess_gamma} tokens")
```

### 5.2 Budget Alert Thresholds

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Over-frameworked | τ > 0.70 | Reduce context, trim few-shot, or use larger model |
| Discovery-impaired | τ > 0.50 and task = creative | Switch to thinner prompt or smaller model |
| Under-structured | τ < 0.10 and task = synthesis | Add framework context or switch to larger model |
| η exhausted | η < reserved_output_tokens | Cannot generate — increase C or reduce γ |

### 5.3 FLUX Bytecode Integration: BUDGET Instruction

The conservation-enforcer FLUX VM shall support budget checking via
existing syscall mechanisms:

```
; FLUX policy: check γ + η = C conservation
; R0 = syscall number (15 = GET_GAMMA)
MOVI R0, 15
SYSCALL
MOV R5, R0          ; R5 = γ

MOVI R0, 16          ; GET_ETA
SYSCALL
MOV R6, R0          ; R6 = η

MOVI R0, 17          ; GET_CAPACITY
SYSCALL
MOV R7, R0          ; R7 = C

; Verify: γ + η should equal C
IADD R8, R5, R6     ; R8 = γ + η
CMP R8, R7          ; Compare with C
JNE _violation       ; If not equal, conservation violated

MOVI R0, 0          ; Allow
HALT

_violation:
MOVI R1, 99         ; Custom violation
MOVI R0, 8          ; SET_VIOLATION
SYSCALL
MOVI R0, 1          ; Block
HALT
```

**New Syscalls:**

| Number | Name | Returns in R0 |
|--------|------|---------------|
| 15 | GET_GAMMA | Current γ (marked tokens × head factor) |
| 16 | GET_ETA | Current η (C − γ − reserved output) |
| 17 | GET_CAPACITY | Total C (context_window × attention_heads) |
| 18 | GET_CHART_THICKNESS | τ as fixed-point (τ × 1000) |

### 5.4 Module API

```python
class CognitiveBudget:
    """Tracks the γ + η = C cognitive budget for an LLM inference."""

    def __init__(
        self,
        context_window: int,
        attention_heads: int,
        reserved_output_tokens: int = 0,
        head_saturation_factor: float = 1.0,
    ) -> None: ...

    @property
    def capacity(self) -> int: ...        # C
    @property
    def gamma(self) -> int: ...           # γ (marked)
    @property
    def eta(self) -> int: ...             # η (unmarked)
    @property
    def tau(self) -> float: ...           # γ/C ratio
    @property
    def chart_thickness(self) -> ChartThickness: ...

    def add_system_prompt(self, text: str) -> int: ...
    def add_few_shot(self, text: str) -> int: ...
    def add_context(self, text: str) -> int: ...
    def add_framework(self, token_count: int) -> int: ...
    def reset_gamma(self) -> None: ...

    @property
    def is_over_frameworked(self) -> bool: ...
    @property
    def is_under_structured(self) -> bool: ...
    @property
    def excess_gamma(self) -> int: ...    # tokens to remove to reach τ = 0.70

    def classify_for_task(self, task: str) -> str: ...
    def recommend_casting_order(budgets: list["CognitiveBudget"]) -> list[int]: ...
    def to_dict(self) -> dict: ...


class ChartThickness(Enum):
    ULTRA_THIN = "ultra_thin"    # τ < 0.15
    THIN = "thin"                # 0.15 ≤ τ < 0.30
    BALANCED = "balanced"        # 0.30 ≤ τ ≤ 0.70
    THICK = "thick"              # 0.70 < τ ≤ 0.85
    ULTRA_THICK = "ultra_thick"  # τ > 0.85
```

---

## 6. SuperInstance Architecture Integration

### 6.1 conservation-enforcer

The γ + η = C law is **the** conservation law that the
conservation-enforcer is built to enforce. The existing FLUX bytecode
policies (length budget, repetition, entropy, density, scope discipline)
are all special cases of γ/η management:

- **Length budget:** Prevents γ_output from exceeding C_output
- **Repetition policy:** Prevents γ from being wasted on redundant patterns
- **Entropy policy:** Ensures minimum η utilisation in output
- **Information density:** Balances γ_output/η_output ratio
- **Scope discipline:** Prevents γ drift across domain boundaries
- **Budget decay:** Models γ accumulation over a conversation

The `CognitiveBudget` class provides the analytical foundation these
policies operate on.

### 6.2 skenna (Negative-Space Navigator)

Skenna operates in the η space — the unmarked territory between charted
knowledge. Its navigation algorithm:

1. **Map current γ** — what is already known, structured, documented.
2. **Estimate η** — what is unknown but reachable within C.
3. **Navigate toward η boundaries** — find the edges of the chart.
4. **Report discoveries** — convert η findings into new γ for downstream
   consumers.

The CognitiveBudget class provides skenna with the γ/η measurements
needed to determine where the chart ends and negative space begins.

### 6.3 chart-room (4-Panel Display)

The chart-room's four panels represent different γ allocations:

| Panel | γ Level | η Level | Purpose |
|-------|---------|---------|---------|
| Overview | Low γ (thin chart) | High η | Broad scan, discovery |
| Detail | High γ (thick chart) | Low η | Focused analysis, synthesis |
| Process | Medium γ | Medium η | Workflow, balanced view |
| Archive | Variable | Variable | Historical reference |

The budget tracker ensures each panel operates within its intended
τ range, preventing γ leakage between panels.

### 6.4 flux-visual-editor

Budget nodes in the visual editor ARE γ/η allocators:

- Each node has a CognitiveBudget instance
- Visual edges represent γ flow (context passing)
- Node colour reflects τ value:
  - 🔵 Blue: thin chart (τ < 0.30)
  - 🟢 Green: balanced (0.30 ≤ τ ≤ 0.70)
  - 🟠 Orange: thick chart (τ > 0.70)
  - 🔴 Red: over-frameworked (τ > 0.85)

### 6.5 shepherds-console

The shepherd's wattage budget maps directly to C:

```
wattage_budget ↔ C (total cognitive capacity)
allocated_watts ↔ γ (committed capacity)
available_watts ↔ η (discovery capacity)
```

When the shepherd allocates wattage to a process, it is setting γ for
that process's CognitiveBudget. The conservation law ensures that
wattage_alloc + wattage_available = wattage_total at all times.

---

## 7. Operational Decision Tree

```
                    ┌── task = discovery/exploration ──→ cast THIN first
                    │                                    (τ < 0.30)
                    │
   measure τ ───────┼── task = synthesis/architecture ──→ cast THICK second
                    │                                    (τ > 0.50)
                    │
                    ├── task = balanced ──→ τ ∈ [0.30, 0.70]
                    │
                    └── τ > 0.85 ──→ ⚠️ OVER-FRAMEWORKED
                                      reduce γ or increase C
```

---

## 8. Test Protocol

The accompanying `tests/test_cognitive_budget.py` validates:

1. Capacity computation (C = W × H)
2. Gamma accumulation from components
3. Eta derivation from conservation law (η = C − γ)
4. Conservation invariant (γ + η = C always holds)
5. Chart thickness classification (all 5 bands)
6. Over-framework detection (τ > 0.70)
7. Under-structure detection (τ < 0.10)
8. Excess gamma computation (tokens to remove)
9. Task-based recommendation (discovery vs synthesis)
10. Casting order protocol (thin before thick)
11. Reset functionality
12. Dictionary export for integration

---

## 9. Glossary

| Term | Symbol | Definition |
|------|--------|------------|
| Cognitive Budget | C | Total inference capacity of a model |
| Marked Capacity | γ | Allocated/committed capacity (system prompt, context, framework) |
| Unmarked Capacity | η | Available/discovery capacity |
| Chart Thickness | τ | Dimensionless ratio γ/C |
| Thin Chart | τ < 0.30 | High discovery, low synthesis |
| Thick Chart | τ > 0.70 | High synthesis, low discovery |
| Socratic Casting | — | Protocol of casting thin-chart models before thick-chart models |
| Discovery Space | η-space | The region of unmarked capacity where novel associations form |
| γ Leakage | — | Unintentional context transfer that increases a receiving model's γ |
| η Contamination | — | Reduction of a model's discovery space by premature γ injection |

---

## 10. References

1. **Casting Call Experiment** (2026-07-12) — SuperInstance internal. Demonstrated that Ornith-35B at τ ≈ 0.15 outperformed Hermes-405B at τ ≈ 0.65 on creative fiction tasks.
2. **Noether's Theorem for AI** — conservation-enforcer `NEXT_HORIZONS.md` §6. Symmetry-conservation correspondence in AI systems.
3. **FLUX Bytecode Specification** — SuperInstance/flux-core. The deterministic policy VM that enforces conservation laws.
4. **The Marked and the Unmarked** — Essay series establishing γ + η = C as the fundamental tension in all cognitive systems.

---

*The chart is not the territory. But the chart takes up space that the territory needs.*
