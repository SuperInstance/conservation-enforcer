# Changelog

All notable changes to `conservation-enforcer` are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.5] — 2026-07-20

### Fixed
- **`replenish_budget` now rejects negative amounts.** Passing a negative value to `replenish_budget()` would silently decrease the budget below zero, violating the invariant that `budget >= 0`. Added a `ValueError` guard with a descriptive message.

## [0.2.4] — 2026-07-20

### Fixed
- **Memory bounds checks now enforce strict bounds.** `Memory.store_i32` and `Memory.load_i32` previously silently no-opped on out-of-bounds addresses, which could mask policy bugs. Now raise `IndexError` with a descriptive message when address is outside valid range.
- **`RegisterFile.set()` now stores signed i32 values.** The register file now correctly preserves signed 32-bit values rather than truncating to unsigned. Fixes edge cases in VM state serialization where negative register values were corrupted.

## [0.2.3] — 2026-07-19

### Fixed
- **`RegisterFile.set()` stores signed i32 values.** Previous implementation truncated signed values through masking, causing negative register values to be stored incorrectly. Now preserves two's-complement representation throughout the register lifecycle.

## [0.2.2] — 2026-07-17

### Fixed
- **IDIV/IMOD signed division semantics.** Integer division and modulo operations now follow Python's floor-division semantics consistently. Previously, negative dividend/divisor combinations could produce unexpected results due to mismatched truncation rules.

## [0.2.1] — 2026-07-16

### Fixed
- **VM `running` flag was dead code** (`src/vm.py`). A top-level `RET` (no matching `CALL`) set `self.running = False` intending to halt the VM, but the main loop in `run()` never checked `self.running` — only `self.pc >= len(self.bytecode)`. So a custom policy with an unbalanced CALL/RET pair would silently fall through to whatever came next in the bytecode buffer. Fix: `reset()` now sets `running = True`, and the loop checks it. Regression test added: `TestLifecycleFixes.test_ret_with_empty_stack_halts_cleanly`.
- **`MOVI` no longer sign-extends negative i16 immediates** (`src/vm.py`). The decoder sign-extended the 16-bit field into a signed Python int, but `_h_movi` then masked with `0xFFFF`, throwing away the sign. `MOVI R0, -1` loaded 65535 instead of 0xFFFFFFFF. Fix: use `off & 0xFFFFFFFF` (Python's two's-complement on negatives gives the right answer). Behavior change for callers passing large unsigned values that round-trip through sign extension — but no existing test or policy is affected (every MOVI in the codebase is 0–14). Regression tests cover -1, -32768, +32767, and full assembler round-trip.

### Security / Hardening
- **`scope_discipline_policy(max_expansion=N)` is now capped at 1000.** The function emitted one IADD per unit of expansion, so unbounded `max_expansion` could produce prohibitively large bytecode (100k → 400KB in 0.59s). Now raises `ValueError` above 1000 with guidance to fork the policy if a looser limit is genuinely needed.

### Not fixed (carried)
- `Memory.store_i32` / `load_i32` silently no-op on out-of-bounds addresses. Defensible as a deliberate VM design (security boundary); a future `debug=True` mode could surface this.
- `audit.AuditLog.read_all()` raises `json.JSONDecodeError` on a partial/corrupted last line. Trivial fix deferred for a separate review.

## [0.2.0] — 2026-07-13

Initial public release on PyPI. Adds `CognitiveBudget` (γ/η chart-thickness formalization), `MetricsCollector`, all eight pre-built policies, the FLUX Micro-VM, the assembler, and full audit/metrics infrastructure.

[0.2.5]: https://github.com/SuperInstance/conservation-enforcer/releases/tag/v0.2.5
[0.2.4]: https://github.com/SuperInstance/conservation-enforcer/releases/tag/v0.2.4
[0.2.3]: https://github.com/SuperInstance/conservation-enforcer/releases/tag/v0.2.3
[0.2.2]: https://github.com/SuperInstance/conservation-enforcer/releases/tag/v0.2.2
[0.2.1]: https://github.com/SuperInstance/conservation-enforcer/releases/tag/v0.2.1
[0.2.0]: https://github.com/SuperInstance/conservation-enforcer/releases/tag/v0.2.0
