# AUDIT v0.2.2 — IDIV/IMOD Signed Division Fix

**Audit date:** 2026-07-17
**Auditor:** GLM-5.2 (main session, wheel rotation)
**Package:** conservation-enforcer
**Version:** 0.2.1 → 0.2.2

## Bug Found

### CRITICAL: IDIV uses Python floor division instead of C-style truncated division

**File:** `src/conservation_enforcer/vm.py`, `_h_idiv()`

**Impact:** Any FLUX bytecode policy using IDIV with negative dividends
(stored as 2's complement unsigned values) gets wrong results.

**Root cause:** Python `//` is floor division. For positive operands this
matches C truncation. But for negative dividends stored as unsigned 32-bit
(e.g., -7 stored as 0xFFFFFFF9), floor division gives:

```
0xFFFFFFF9 // 2 = 2147483644 (0x7FFFFFFC)
```

When the correct C-style truncated result should be:

```
-7 / 2 = -3 → 0xFFFFFFFD = 4294967293
```

**Same bug in IMOD:** Python `%` follows the divisor's sign, while C/hardware
follows the dividend's sign. `-7 % 2` should be `-1` (C) not `1` (Python).

**Before (buggy):**
```python
self.regs.set(rd, self.regs.get(rs1) // d)
```

**After (fixed):**
```python
a = self._to_signed(self.regs.get(rs1))
b = self._to_signed(d)
q = abs(a) // abs(b)
if (a < 0) != (b < 0): q = -q
self.regs.set(rd, q & 0xFFFFFFFF)
```

## Regression Tests

6 new tests in `tests/test_vm.py::TestSignedDivision`:

1. `test_idiv_negative_dividend_positive_divisor` — -7 / 2 = -3
2. `test_idiv_negative_dividend_even` — -8 / 2 = -4
3. `test_idiv_both_negative` — -7 / -2 = 3
4. `test_imod_negative_dividend` — -7 % 2 = -1
5. `test_imod_both_negative` — -7 % -2 = -1
6. `test_idiv_positive_still_correct` — 100 / 7 = 14 (regression guard)

## Test Count

- Before: 201 tests
- After: 207 tests (201 original + 6 new regression tests)
- All pass.

## Published

- PyPI: https://pypi.org/project/conservation-enforcer/0.2.2/
- GitHub: https://github.com/SuperInstance/conservation-enforcer
- Commit: b38b5f5
