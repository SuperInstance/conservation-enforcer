# Changelog

All notable changes to `conservation-enforcer` are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

[0.2.1]: https://github.com/SuperInstance/conservation-enforcer/releases/tag/v0.2.1
[0.2.0]: https://github.com/SuperInstance/conservation-enforcer/releases/tag/v0.2.0
