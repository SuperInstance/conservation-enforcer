# γ + η = C — Cognitive Budget Formal Specification

**Version:** 1.0 — 2026-07-13
**Status:** Active
**Implements:** The Conservation Law of Intelligence

---

## 1. Formal Definition

For any cognitive system with finite processing capacity:

```
γ + η = C
```

Where:
- **γ (gamma)** = allocated/committed capacity. The structure, framework, prior commitments. What the system has already spent its budget on.
- **η (eta)** = unallocated/available capacity. The discovery space. Genuine unknowns. Where new connections form.
- **C** = total cognitive capacity. A constant for a given system configuration.

**The constraint is a conservation law.** You cannot increase γ without decreasing η. Every framework token added to a prompt reduces the model's discovery capacity by exactly that amount.

---

## 2. Measurement Protocol

### 2.1 Measuring C (Total Capacity)

For an LLM system:

```
C = context_window_size × num_attention_heads × precision_bits
```

Practical approximation:

```
C ≈ context_window_size (in tokens)
```

Example configurations:

| Model | Context Window | C (tokens) |
|-------|---------------|------------|
| GPT-4 (128K) | 131,072 | 131,072 |
| Claude (200K) | 204,800 | 204,800 |
| GLM-5.2 (128K) | 131,072 | 131,072 |
| Ornith-35B (4K) | 4,096 | 4,096 |

### 2.2 Measuring γ (Allocated Capacity)

```
γ = len(system_prompt) + len(few_shot_examples) + len(injected_context) + len(cached_patterns)
```

In practice, γ is the token count of everything the model processes before seeing the user's query:

- System prompt / AGENTS.md / SOUL.md content
- Few-shot examples
- RAG-injected context
- Conversation history (accumulated turns)
- Tool call results injected into context

### 2.3 Computing η (Discovery Space)

```
η = C - γ - expected_output_tokens
```

η is the cognitive "room to maneuver" — the unmarked chart space where the model can discover new connections rather than regurgitating framework.

### 2.4 Chart Thickness

```
thickness = γ / C
```

| Classification | γ/C Range | Character |
|---------------|-----------|-----------|
| Thin chart | < 0.3 | High discovery, low synthesis. Genuine questions. |
| Balanced | 0.3 – 0.7 | Moderate discovery and synthesis. |
| Thick chart | > 0.7 | High synthesis, low discovery. Framework answers. |

---

## 3. The Socratic Casting Protocol

### 3.1 Rule

**Cast thin-chart model FIRST. Cast thick-chart model SECOND. Never reverse.**

### 3.2 Rationale

A thin-chart model (small, cheap, large η) asks genuine questions because it doesn't have framework answers. Its discoveries are real — it finds connections the thick-chart model's dense γ obscures.

A thick-chart model (large, expensive, dense γ) synthesizes discoveries into architecture. It builds the cathedral. But it cannot find the door — its η is too small.

Casting thick-first contaminates the discovery space. The thick model's framework answers anchor subsequent processing, preventing the thin model from finding genuinely novel connections.

### 3.3 Empirical Evidence

| Experiment | Thin Model | Thick Model | Result |
|------------|-----------|-------------|--------|
| Casting call (essay) | Seed-2.0-Mini | Seed-2.0-Pro | Mini found "skénna" — the name Pro couldn't find |
| Fiction writing | Ornith-35B | Hermes-405B | Ornith found stories Hermes couldn't |
| Excavation (7 models) | Multiple thin models | Multiple thick models | Divergence between models IS the signal |

### 3.4 Implementation

```python
from conservation_enforcer.budget import CognitiveBudget

# Thin model: small C, minimal γ → large η
thin_budget = CognitiveBudget(capacity=4096, allocated=500)   # η = 3596, thickness = 12%

# Thick model: large C, dense γ → small η
thick_budget = CognitiveBudget(capacity=131072, allocated=95000)  # η = 36072, thickness = 72%

# Protocol: thin first, thick second
results_thin = thin_model.explore(query)    # Discovery phase
results_thick = thick_model.synthesize(results_thin)  # Synthesis phase
```

---

## 4. Implementation

### 4.1 CognitiveBudget Class

Implemented in `conservation_enforcer/budget.py`:

```python
@dataclass
class CognitiveBudget:
    capacity: float      # C
    allocated: float     # γ (defaults to 0)
    
    @property
    def eta(self) -> float          # C - γ
    @property
    def thickness_ratio(self) -> float  # γ/C
    
    def is_thin(self) -> bool       # γ/C < 0.3
    def is_thick(self) -> bool      # γ/C > 0.7
    def is_balanced(self) -> bool   # 0.3 ≤ γ/C ≤ 0.7
    
    def spend(self, amount) -> None # Increase γ (raises BudgetExceededError at C)
    def release(self, amount) -> None  # Decrease γ (back to η)
    def reset(self) -> None         # γ = 0, full η
```

### 4.2 FLUX Bytecode Integration

The BUDGET instruction (opcode 0x10) sets a conservation budget. The SPEND instruction (0x11) consumes budget. The CHECK instruction (0x12) verifies remaining budget. These operate on the same γ/η/C principle:

```asm
; Conservation policy: 500-token budget
BUDGET tokens, 500      ; Set C = 500 for token dimension
MOVI R0, 0              ; γ = 0 initially
; ... agent generates output ...
SPEND tokens, 250       ; γ = 250, η = 250
CHECK tokens, addr      ; Verify η > 0
; ... more output ...
SPEND tokens, 250       ; γ = 500, η = 0
; Next SPEND → HALT (conservation violation)
```

### 4.3 Alerting

When γ/C exceeds a configurable threshold, the system alerts:

```python
budget = CognitiveBudget(capacity=8192, allocated=6000)
if budget.thickness_ratio > 0.7:
    print(f"⚠️ Over-frameworked: {budget.thickness_ratio:.1%}. "
          f"Consider reducing context. η = {budget.eta}")
```

---

## 5. Architecture Connections

| Component | γ/η Role |
|-----------|----------|
| **conservation-enforcer** | Enforces γ + η = C at runtime via FLUX bytecode |
| **skenna** | Navigates η space — finds safe paths through the unknown |
| **chart-room** | 4 panels with different γ allocations (fisherman=sparse, sailor=dense) |
| **flux-visual-editor** | Budget nodes ARE γ/η allocators — visual composition of C |
| **shepherds-console** | Wattage budget maps to C — energy IS cognition on the edge |
| **baton** | Carries γ allocations across model generations |
| **PLATO rooms** | Room protocols define γ budgets for agents entering the room |

---

## 6. The Deep Result

**Model size ≠ model creativity. Model size ≠ model capability.**

The conservation law proves that different models offer different *perspectives*, not just different *quality*. A 35B model with γ/C = 0.2 discovers things a 405B model with γ/C = 0.8 cannot. This is not despite the smaller model's limitations — it is *because of them*.

The thick model sees the shipping lane. The thin model sees the water. Both are looking at the same harbor. The chart that matters depends on what you're trying to do.

**Cast thin first. Cast thick second. Always.**

---

*This specification is the formal engineering companion to the paradigm essays: ON_SKENNA, THIN_CHARTS_AND_THE_SOCRATIC_SON, THE_EGG_AND_THE_ORGANISM, and THE-CONSERVATION-LAW-OF-INTELLIGENCE.*
