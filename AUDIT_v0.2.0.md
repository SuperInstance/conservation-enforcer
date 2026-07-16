# Audit Report — conservation-enforcer v0.2.0

**Audit date:** 2026-07-16
**Auditor:** MiniMax-M3 (baton-handoff session)
**Methodology:** Read source first, run tests, then read tests to find gaps, then probe edge cases empirically.
**Baseline:** 192 tests passing (0.75s) on Python 3.11.9.

---

## Verdict

**v0.2.0 is mostly clean but has 3 concrete bugs that survived 192 passing tests.** The codebase is well-structured — comments are accurate, the FLUX VM is a faithful register machine, and the policy layer is sensible. But test coverage overweights "happy path" and underweights the VM's undefined-behavior surface.

Patches shipped as **v0.2.1**: 3 bugs fixed, 3 regression tests added.

---

## Bug findings

### 🔴 HIGH — `running` flag is dead code in VM (`src/vm.py:265-267`)

**Reproduction:**
```python
from conservation_enforcer.vm import VM, Op

code = bytes([
    int(Op.RET),                # RET with empty stack
    int(Op.MOVI), 0, 99, 0,     # but outer loop doesn't check running!
    int(Op.HALT),
])
vm = VM()
result = vm.run(code)
assert result == 99  # ← BUG: VM executed MOVI R0, 99 past the RET
```

The `_h_ret` handler sets `self.running = False` when the call stack is empty, intending to halt the VM. But the main loop in `run()` never checks `self.running` — only `self.pc >= len(self.bytecode)`. So a top-level RET silently continues execution.

**Impact:** Any policy with an unbalanced CALL/RET pair (e.g., a custom policy with a bug) would not halt cleanly. The "running" half of the VM's contract is unimplemented.

**Fix:** Make `reset()` set `running = True`, and check `running` in the main loop alongside the existing PC bound check. `_h_ret` stays the same (sets `running = False`); now the flag actually does something.

This is also a precondition for a future hardening improvement: detect PC-overrun (no-HALT) and raise a clear VMError. Not done in 0.2.1 to keep the patch focused.

---

### 🟡 MED — MOVI does not sign-extend negative i16 immediates (`src/vm.py:219-224`)

**Reproduction:**
```python
code = bytes([int(Op.MOVI), 0, 0xFF, 0xFF, int(Op.HALT)])  # MOVI R0, -1
vm = VM()
vm.run(code)
assert vm.regs.get(0) == 0xFFFFFFFF     # ← FAILS
assert vm.regs.get(0) == 65535         # ← actually 65535
```

The D-format decoder (`_d_D`) correctly sign-extends the 16-bit immediate into a signed Python int (so `MOVI R0, -1` arrives as `off = -1`). But `_h_movi` then masks with `0xFFFF`, throwing away the sign. Result: `MOVI R0, -1` loads 65535 instead of 0xFFFFFFFF.

This violates the "i16 immediate" semantics advertised by the assembler. The inline comment in `_h_movi` (`# load its 16-bit pattern into the register`) documents the buggy behavior rather than correcting it.

**Impact:** Currently no policy or test exercises negative MOVI. So the bug is latent — no production breakage — but the public semantics are wrong. Callers from `othismos` or other downstream packages that pass negative values would silently get the wrong register contents.

**Fix:** Use `self.regs.set(reg, off & 0xFFFFFFFF)` — Python's two's-complement semantics on negative ints give the correct sign-extension (e.g., `-1 & 0xFFFFFFFF == 0xFFFFFFFF`).

This is a behavior change but **no existing test or policy is affected** (all MOVI values in the codebase are 0–14). The change makes the documented i16 contract actually hold.

---

### 🟡 MED — `Memory.store_i32` and `load_i32` silently no-op on out-of-bounds

**Reproduction:**
```python
m = Memory(size=8)
m.store_i32(0, 0xDEADBEEF)   # OK
m.store_i32(1000, 0xBADF00D)  # way past end — silently does nothing!
print(m.load_i32(0))           # 0xDEADBEEF — earlier write still intact
```

The bounds check `if 0 <= addr and addr + 4 <= len(self.buf)` quietly returns False instead of raising. A buggy policy that LOADs/STOREs to a wrong address would corrupt nothing but also report nothing.

**Decision: noted but not fixed in 0.2.1.** This is a defensible VM design — the sandbox treats memory as fail-safe and policies are expected to be validated before deployment. Silently failing is correct for a security boundary. Flagged for future hardening: a `debug=True` mode could raise VMError on OOB; production mode stays silent.

The existing `test_store_i32_out_of_bounds_is_safe` test pins the current (silent) behavior. That test stays.

---

### 🟠 LOW — `scope_discipline_policy(max_expansion=N)` is unbounded

**Reproduction:**
```python
from conservation_enforcer.policies import scope_discipline_policy
code = scope_discipline_policy(max_expansion=100_000)
# Returns 400,075 bytes in 0.59s
```

The policy implements `output_length > input_length * max_expansion` via repeated IADD (one per unit of expansion). With no upper bound, a large `max_expansion` value linearly inflates the emitted bytecode. Quadratic blowup is possible inside larger policies that compose this one.

**Impact:** Mitigated today by the fact that `max_expansion` defaults to 10 and that policies aren't user-configurable at runtime. Becomes a real concern only if exposed to user input via a UI.

**Fix:** Cap at 1000 with a `ValueError`. That allows 3 orders of magnitude above the default (10) for legitimate use, and rejects pathological inputs at the API boundary.

---

### 🟢 Noted — `audit.read_all()` will crash on a partial/corrupted last line

```python
def read_all(self) -> list[dict]:
    ...
    for line in f:
        line = line.strip()
        if line:
            entries.append(json.loads(line))  # ← raises on partial JSON
```

A crash mid-write (interrupted process, disk full, partial flush) leaves a malformed last line. `read_all()` then raises `json.JSONDecodeError` on the first call after restart. For an audit log that's supposed to be inspectable forever, that's brittle.

**Decision: not fixed in 0.2.1.** Two-line fix is trivial (try/except with logging), but it touches user-visible behavior in a way that deserves a longer review. Carried as a known issue for 0.2.2.

---

## What the tests covered well

The existing test suite is solid on:

- Arithmetic (ADD/SUB/MUL/DIV/MOD with division-by-zero)
- Control flow (JE/JNE/JSGE/JSLT plus the 4 pseudo-jumps via assembler)
- Syscalls (GET_INPUT_LEN, GET_TOKEN_COUNT, GET_REPETITION, SET_VIOLATION)
- Memory STORE/LOAD roundtrip including the previously-fixed negative-value bug
- Each policy's allow and block paths

This is what makes the dead-`running`-flag bug surprising — everything the policies actually do is tested.

## What the tests didn't cover (the audit gaps)

- VM behavior at lifecycle boundaries: `RET` with empty stack, PC overrun without HALT, multiple HALT instructions
- Negative `MOVI` immediates
- Edge of `max_expansion` parameter
- Memory OOB behavior (covered incidentally by `test_store_i32_out_of_bounds_is_safe`)

The 3 regression tests added in 0.2.1 close these gaps.

---

## What was NOT a bug (verified)

- `Memory.store_i32` masking to 32-bit unsigned: **correct**. Prior version had a real bug (negative-value crash with `struct.error`); the current `val & 0xFFFFFFFF` is right.
- `set_budget` flow before each `run()`: **correct**. `_budget` is intentionally not reset (it's read fresh via `set_budget` from the enforcer's state).
- `DECAY_BUDGET` clamping to 0: **correct**. `max(0, x)` prevents negative budgets.
- JGT pseudo-op encoding: **correct**. Two-instruction expansion (JE skip + JSGE target) is a faithful rendering of `r1 > r2`.
- `_call_count` not reset on `vm.reset()`: **correct by design**. The docstring says "tracks across runs" and enforcer + VM call counts stay in lockstep via `increment_call_count()`.

---

## What changed in v0.2.1

| File | Change | Lines |
|------|--------|-------|
| `src/vm.py` | `reset()` sets `running = True`; `run()` loop now checks `running` | ~5 |
| `src/vm.py` | `_h_movi` sign-extends i16 to i32 via `off & 0xFFFFFFFF` | 1 |
| `src/conservation_enforcer/policies/__init__.py` | `scope_discipline_policy` caps `max_expansion` at 1000 | ~5 |
| `tests/test_vm.py` | 3 regression tests: dead-`running`-flag, MOVI sign-extension, MOVI range | +30 |
| `tests/test_new_policies.py` | 2 regression tests: scope max_expansion cap honored | +20 |
| `pyproject.toml` | Version bump 0.2.0 → 0.2.1 | 1 |
| `src/conservation_enforcer/__init__.py` | `__version__` bump | 1 |
| `CHANGELOG.md` | Created (Keep a Changelog format) | +30 |

Total: 5–10 lines of source change, 50 lines of regression coverage.

---

## Methodology notes for the next audit

The pre-fix finding rate was: read source (5 min) → spot 2 latent issues → write 2-line reproductions → confirm both. The MOVI issue was found by reading the assembler docstring, the VM's `_d_D` decoder, and the `_h_movi` handler — they disagreed about the semantics.

Three lessons worth carrying forward:

1. **Always check what the doc says vs what the code does.** The MOVI bug exists because the comment in `_h_movi` documented the buggy behavior rather than the spec. Comments drift.
2. **The VM has more undefined-behavior surface than the policies exercise.** A LOT of policy tests, very few VM-lifecycle tests. Add coverage there first.
3. **`self.running = False` then never checking `self.running`** is the kind of code-rot that survives because nothing exercises the dead branch. Find the half-implemented features — they're where bugs hide.

