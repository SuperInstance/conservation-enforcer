# ⚡ Conservation Enforcer

![PyPI](https://img.shields.io/pypi/v/conservation-enforcer)
![Python](https://img.shields.io/python/required-version-toml?toml=pyproject.toml)
![Tests](https://img.shields.io/badge/tests-60%2B-brightgreen)
![License](https://img.shields.io/github/license/SuperInstance/conservation-enforcer)

**FLUX bytecode conservation-law enforcement for LLM outputs.**

This is a working enforcement system that wraps any LLM call in a deterministic, auditable policy layer implemented as FLUX bytecode. It demonstrates that AI behavior can be governed by conservation laws — the same mathematical principles that govern physics.

```
User Request → LLM Call → [FLUX Conservation Validator] → Response
                                    ↓
                              If violation: return correction
                              If clean: return response
```

The FLUX bytecode acts as a deterministic, auditable policy layer. **You can't lie to bytecode** — it doesn't have opinions, it just executes instructions.

## Why Conservation Laws?

**The alignment problem is an enforcement problem.** Current AI alignment approaches rely on prompt engineering (which the model can ignore), RLHF tuning (which is opaque and hard to verify), and post-hoc output filtering (which is not deterministic). None of these provide hard guarantees. Conservation enforcement takes a different approach: it treats AI outputs as quantities subject to conservation laws — you cannot create information from nothing, you cannot exceed your allocated budget, you cannot drift outside your category boundary. These are not suggestions or preferences. They are bytecode instructions that execute deterministically.

**Conservation laws are the most trusted concept in physics.** Noether's theorem connects symmetries to conservation laws — energy conservation follows from time-translation symmetry, momentum conservation from space-translation symmetry. This mathematical framework has been tested for centuries. By encoding AI governance as conservation laws (information budget, entropy floor, category confinement), we inherit the rigor and trustworthiness of physical law. The bytecode doesn't have a "position" on whether your output is appropriate — it simply measures whether information is conserved.

**Deterministic enforcement changes the threat model.** When policy is bytecode running in a sandboxed VM, the LLM cannot argue, persuade, or manipulate its way past the rules. The bytecode has no attention mechanism, no context window, no ability to be jailbroken. It receives metrics (token count, repetition ratio, entropy) and returns a binary decision. This makes conservation enforcement suitable for high-stakes applications — compliance, safety-critical systems, regulated industries — where you need to prove that your AI behaves within defined parameters.

## Installation

```bash
pip install conservation-enforcer
```

For development:
```bash
git clone https://github.com/SuperInstance/conservation-enforcer.git
cd conservation-enforcer
pip install -e ".[dev]"
```

## Quick Start

```python
from conservation_enforcer import ConservationEnforcer, combined_policy

# Create a combined policy: length + repetition + category + entropy
policy = combined_policy(
    max_tokens=500,
    max_repetition=300,
    min_overlap=100,
    min_entropy=1500,
    min_density=300,       # enable information density law
)

enforcer = ConservationEnforcer(policy, budget=500)

# Check an LLM output
result = enforcer.enforce(
    input_text="What is machine learning?",
    output_text="Machine learning is a subset of AI that learns from data.",
)

if result.allowed:
    print(result.output)
else:
    print(f"Blocked: {result.violation.reason}")
```

## OpenAI Integration

```python
from conservation_enforcer import ConservationEnforcer, combined_policy
from openai import OpenAI

client = OpenAI()
enforcer = ConservationEnforcer.from_policy_file("policies/length_budget.bin")

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Tell me everything about quantum physics"}]
)

allowed, corrected = enforcer.enforce(
    input_text="Tell me everything about quantum physics",
    output_text=response.choices[0].message.content
)

if not allowed:
    print(f"Blocked by conservation law: {corrected}")
else:
    print(corrected)
```

See [`examples/openai_integration.py`](examples/openai_integration.py) for a full runnable example.

## Enforcement in Action

Here's what conservation enforcement looks like when it runs:

```
============================================================
  Conservation-Enforced LLM Integration Demo
============================================================

📝 User: Tell me everything about quantum physics
🤖 Raw LLM: Quantum physics studies matter and energy at the smallest scales...
✅ ALLOWED (24 cycles)
   Output: Quantum physics studies matter and energy at the smallest sca...

📝 User: Be as verbose as possible
🤖 Raw LLM: Well, let me tell you about this, and then tell you again, and ag...
🚫 BLOCKED: Excessive repetition detected
   Correction: ⚠️ This response was blocked by a conservation law: Excessive...

============================================================
  Enforcement Metrics
============================================================
{
  "total_calls": 2,
  "total_allowed": 1,
  "total_blocked": 1,
  "block_rate": 0.5,
  "policy_triggers": {"Excessive repetition detected": 1}
}
```

## Conservation Laws

### 1. Length Budget (Information Quantity)
```python
from conservation_enforcer import length_budget_policy
policy = length_budget_policy(max_tokens=500)
```
The output cannot exceed the allocated information budget. This is analogous to energy conservation in physics — you can't output more information than you were allocated.

### 2. Repetition Limit (Information Diversity)
```python
from conservation_enforcer import repetition_policy
policy = repetition_policy(max_ratio=300)  # max 30% repetition
```
The output must maintain diversity. Degenerate repetition is the informational equivalent of thermal equilibrium.

### 3. Category Confinement (Topical Coherence)
```python
from conservation_enforcer import category_policy
policy = category_policy(min_overlap=150)  # 15% word overlap required
```
The output must stay within the category/domain of the input. Prevents hallucinated content and topic drift.

### 4. Entropy Floor (Information Density)
```python
from conservation_enforcer import entropy_policy
policy = entropy_policy(min_entropy=2000)  # 2.0 bits/word minimum
```
The output must have sufficient Shannon entropy.

### 5. Information Density (Token Efficiency)
```python
from conservation_enforcer import information_density_policy
policy = information_density_policy(min_ratio=400)  # 40% unique tokens
```
Measures the ratio of unique tokens to total tokens. Blocks outputs that are too repetitive at the vocabulary level.

### 6. Scope Discipline (Topic Boundary)
```python
from conservation_enforcer import scope_discipline_policy
policy = scope_discipline_policy(min_overlap=120, max_expansion=10)
```
Checks that the output stays within the input's topic category AND doesn't expand beyond 10× the input length.

### 7. Budget Decay (Temporal Conservation)
```python
from conservation_enforcer import budget_decay_policy
policy = budget_decay_policy(decay_rate=50, min_threshold=10, max_calls=100)
```
The enforcement budget itself is a conserved quantity. Each call consumes budget, enforcing cooldown periods.

### Combined Policy (All Laws)
```python
from conservation_enforcer import combined_policy
policy = combined_policy(
    max_tokens=500,
    max_repetition=300,
    min_overlap=100,
    min_entropy=1500,
    min_density=300,        # optional
    enable_decay=True,      # optional
)
```

## Audit Logging

Every enforcement decision can be logged for compliance and auditing:

```python
from conservation_enforcer import ConservationEnforcer, combined_policy

enforcer = ConservationEnforcer(
    combined_policy(),
    budget=1000,
    enable_audit=True,
    audit_path="enforcement_audit.jsonl",
)

result = enforcer.enforce("question", "response")
# Entry written to enforcement_audit.jsonl:
# {"timestamp":"2025-01-15T12:00:00Z","input_hash":"a1b2c3d4...","allowed":true,...}
```

## Metrics Collection

Track enforcement statistics for dashboards:

```python
from conservation_enforcer import MetricsCollector

metrics = MetricsCollector()
metrics.record(allowed=False, violation_reason="Length budget exceeded", cycles=42)
metrics.export("metrics.json")
```

## Writing Custom Policies

Policies are written in FLUX assembly. See the [`policies/`](policies/) directory for `.flx` source files:

```flux
;; Custom policy: block if unique ratio < 30%
MOVI R0, 11             ; syscall: GET_UNIQUE_RATIO
SYSCALL
MOV  R2, R0
MOVI R3, 300            ; threshold
JLT  R2, R3, block
MOVI R0, 0              ; ALLOW
HALT

block:
MOVI R1, 5              ; reason: INFORMATION_DENSITY
MOVI R0, 8              ; SET_VIOLATION
SYSCALL
MOVI R0, 1              ; BLOCK
HALT
```

## FLUX ISA

| Format | Layout | Example |
|--------|--------|---------|
| A | `[opcode]` | `HALT` |
| B | `[opcode][reg]` | `INC R0` |
| C | `[opcode][rd][rs]` | `CMP R0, R1` |
| D | `[opcode][reg][off_lo][off_hi]` | `JE label` |
| E | `[opcode][rd][rs1][rs2]` | `IADD R0, R1, R2` |

### Syscalls

| # | Name | Returns |
|---|------|---------|
| 1 | GET_INPUT_LEN | Length of input text |
| 2 | GET_OUTPUT_LEN | Length of output text |
| 3 | GET_INPUT_WORDS | Word count of input |
| 4 | GET_OUTPUT_WORDS | Word count of output |
| 5 | GET_TOKEN_COUNT | Approximate token count |
| 6 | GET_REPETITION | Max word frequency ratio × 1000 |
| 7 | GET_CATEGORY | Input/output word overlap × 1000 |
| 8 | SET_VIOLATION | Sets violation flag (R1 = reason code) |
| 10 | GET_BUDGET | Configured information budget |
| 11 | GET_UNIQUE_RATIO | Unique/total words × 1000 |
| 12 | GET_ENTROPY | Shannon entropy × 1000 |
| 13 | GET_CALL_COUNT | Enforcement calls in this session |
| 14 | DECAY_BUDGET | R1 = decay amount, returns new budget |

## Architecture

```
src/conservation_enforcer/
├── __init__.py      Public API
├── vm.py            FLUX VM (register-based bytecode interpreter)
├── assembler.py     Two-pass FLUX assembler with label resolution
├── enforcer.py      ConservationEnforcer class + audit integration
├── audit.py         JSON Lines audit logging
├── metrics.py       Metrics collection + JSON export
└── policies/
    └── __init__.py  Pre-built conservation policies

policies/
├── information_density.flx   Density law source
├── scope_discipline.flx      Scope law source
└── budget_decay.flx          Decay law source
```

## Roadmap

See [NEXT_HORIZONS.md](NEXT_HORIZONS.md) for the full roadmap including multi-model enforcement, formal verification, FLUX DSL, and Noether's theorem for AI.

## Ecosystem

### FLUX Runtime
- [flux-vm](https://github.com/SuperInstance/flux-vm) — Python VM (`pip install flux-vm`)
- [flux-core](https://github.com/SuperInstance/flux-core) — Rust VM (`cargo add fluxvm`)
- [flux-js](https://github.com/SuperInstance/flux-js) — JavaScript VM (`npm install flux-js`)
- [flux-runtime](https://github.com/SuperInstance/flux-runtime) — Full FLUX runtime (Python)

### Conservation
- [flux-registry](https://github.com/SuperInstance/flux-registry) — Pre-compiled policy registry (`pip install flux-registry`)
- [flux-policy-tester](https://github.com/SuperInstance/flux-policy-tester) — Testing framework for FLUX policies
- [conservation-law-rs](https://github.com/SuperInstance/conservation-law-rs) — Conservation laws for agent dynamics (Rust)

### Philosophy
- [AI-Writings](https://github.com/SuperInstance/AI-Writings) — Essays, fiction, poetry
- [NEXT_HORIZONS](https://github.com/SuperInstance/SuperInstance/blob/main/NEXT_HORIZONS.md) — Strategy

## License

MIT

---

*This is not alignment theory. This is enforcement engineering.*
