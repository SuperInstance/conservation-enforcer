# ⚡ Conservation Enforcer

**FLUX bytecode conservation-law enforcement for LLM outputs.**

This is a working prototype that demonstrates conservation-law governance on AI behavior. It wraps any LLM call in a deterministic, auditable policy layer implemented as FLUX bytecode.

```
User Request → LLM Call → [FLUX Conservation Validator] → Response
                                    ↓
                              If violation: return correction
                              If clean: return response
```

The FLUX bytecode acts as a deterministic, auditable policy layer. **You can't lie to bytecode** — it doesn't have opinions, it just executes instructions.

## Why This Matters

Current AI alignment approaches rely on:
- **Prompt engineering** (the LLM can ignore instructions)
- **RLHF tuning** (opaque, hard to verify)
- **Output filtering** (post-hoc, not deterministic)

Conservation enforcement is different:
- **Deterministic**: Same input always produces the same decision
- **Auditable**: Every byte of policy can be inspected and verified
- **Immune to manipulation**: Bytecode has no opinions to argue with
- **Composable**: Multiple conservation laws combine into one program
- **Portable**: FLUX bytecode runs on Python, Rust, and JS VMs

Conservation laws are the foundation of physics. Noether's theorem connects symmetries to conservation laws. This project brings that same mathematical rigor to AI governance.

## Installation

```bash
pip install -e .
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
The output must maintain diversity. Degenerate repetition is the informational equivalent of thermal equilibrium — a system that repeats has exhausted its information capacity.

### 3. Category Confinement (Topical Coherence)
```python
from conservation_enforcer import category_policy

policy = category_policy(min_overlap=150)  # 15% word overlap required
```
The output must stay within the category/domain of the input. This prevents hallucinated content and topic drift — the output's "state" must remain in the same "potential well" as the input.

### 4. Entropy Floor (Information Density)
```python
from conservation_enforcer import entropy_policy

policy = entropy_policy(min_entropy=2000)  # 2.0 bits/word minimum
```
The output must have sufficient Shannon entropy. Low entropy means the output is too predictable and not carrying enough information.

### Combined Policy (All Four Laws)
```python
from conservation_enforcer import combined_policy

policy = combined_policy(
    max_tokens=500,
    max_repetition=300,
    min_overlap=100,
    min_entropy=1500,
)
```

## Writing Custom Policies

Policies are written in FLUX assembly:

```flux
; Custom policy: block outputs longer than 100 tokens
MOVI R0, 5          ; syscall: GET_TOKEN_COUNT
SYSCALL
MOV  R2, R0         ; save token count

MOVI R0, 10         ; syscall: GET_BUDGET
SYSCALL
MOV  R3, R0         ; save budget

JGT  R2, R3, block  ; if tokens > budget → block

MOVI R0, 0          ; ALLOW
HALT

block:
MOVI R1, 1          ; reason: LENGTH_BUDGET
MOVI R0, 8          ; syscall: SET_VIOLATION
SYSCALL
MOVI R0, 1          ; BLOCK
HALT
```

Compile and use:
```python
from conservation_enforcer import assemble, ConservationEnforcer

bytecode = assemble(source_code)
enforcer = ConservationEnforcer(bytecode, budget=100)
result = enforcer.enforce("question", "response")
```

## FLUX ISA

The VM implements a register-based ISA with 16 registers (R0–R15):

| Format | Layout | Example |
|--------|--------|---------|
| A | `[opcode]` | `HALT` |
| B | `[opcode][reg]` | `INC R0` |
| C | `[opcode][rd][rs]` | `CMP R0, R1` |
| D | `[opcode][reg][off_lo][off_hi]` | `JE label` |
| E | `[opcode][rd][rs1][rs2]` | `IADD R0, R1, R2` |

Key instructions: `MOVI`, `MOV`, `IADD`, `ISUB`, `IMUL`, `IDIV`, `CMP`, `JE`, `JNE`, `JSGE`, `JSLT`, `SYSCALL`, `HALT`.

Pseudo-instructions for convenience: `JGE`, `JGT`, `JLE`, `JLT`.

### Syscalls

| # | Name | Returns |
|---|------|---------|
| 1 | GET_INPUT_LEN | Length of input text |
| 2 | GET_OUTPUT_LEN | Length of output text |
| 5 | GET_TOKEN_COUNT | Approximate token count |
| 6 | GET_REPETITION | Max word frequency ratio × 1000 |
| 7 | GET_CATEGORY | Input/output word overlap × 1000 |
| 8 | SET_VIOLATION | Sets violation flag (R1 = reason code) |
| 10 | GET_BUDGET | Configured information budget |
| 11 | GET_UNIQUE_RATIO | Unique/total words × 1000 |
| 12 | GET_ENTROPY | Shannon entropy × 1000 |

## Demonstration

```bash
python examples/demo.py
```

## Tests

```bash
python -m pytest tests/ -v
```

## Architecture

```
src/conservation_enforcer/
├── __init__.py      Public API
├── vm.py            FLUX VM (register-based bytecode interpreter)
├── assembler.py     Two-pass FLUX assembler with label resolution
├── enforcer.py      ConservationEnforcer class
└── policies/
    └── __init__.py  Pre-built conservation policies in FLUX assembly
```

## Related Projects

- [flux-runtime](https://github.com/SuperInstance/flux-runtime) — Full FLUX runtime (Python)
- [flux-core](https://github.com/SuperInstance/flux-core) — FLUX bytecode runtime (Rust)
- [flux-js](https://github.com/SuperInstance/flux-js) — FLUX VM (JavaScript)
- [conservation-law-rs](https://github.com/SuperInstance/conservation-law-rs) — Conservation laws for agent dynamics

## License

MIT

---

*This is not alignment theory. This is enforcement engineering.*
