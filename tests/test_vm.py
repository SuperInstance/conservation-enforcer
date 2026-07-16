"""Tests for the FLUX VM."""

import pytest
from conservation_enforcer.vm import (
    VM, Op, VMError, VMDivisionByZero, VMInvalidOpcode, Memory,
)


class TestBasicArithmetic:
    def test_add(self):
        code = bytes([int(Op.MOVI),0,10,0, int(Op.MOVI),1,20,0, int(Op.IADD),2,0,1, int(Op.HALT)])
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 30

    def test_sub(self):
        code = bytes([int(Op.MOVI),0,50,0, int(Op.MOVI),1,20,0, int(Op.ISUB),2,0,1, int(Op.HALT)])
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 30

    def test_mul(self):
        code = bytes([int(Op.MOVI),0,7,0, int(Op.MOVI),1,6,0, int(Op.IMUL),2,0,1, int(Op.HALT)])
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 42

    def test_div(self):
        code = bytes([int(Op.MOVI),0,100,0, int(Op.MOVI),1,5,0, int(Op.IDIV),2,0,1, int(Op.HALT)])
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 20

    def test_div_by_zero(self):
        code = bytes([int(Op.MOVI),0,10,0, int(Op.MOVI),1,0,0, int(Op.IDIV),2,0,1, int(Op.HALT)])
        vm = VM()
        with pytest.raises(VMDivisionByZero):
            vm.run(code)

    def test_mod(self):
        code = bytes([int(Op.MOVI),0,17,0, int(Op.MOVI),1,5,0, int(Op.IMOD),2,0,1, int(Op.HALT)])
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 2


class TestControlFlow:
    def test_je_taken(self):
        # MOVI R0,5; MOVI R1,5; CMP R0,R1; JE +4; MOVI R0,99; HALT
        code = bytes([
            int(Op.MOVI),0,5,0, int(Op.MOVI),1,5,0,
            int(Op.CMP),0,1, int(Op.JE),0,4,0,
            int(Op.MOVI),0,99,0, int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 5  # didn't execute MOVI R0,99

    def test_jne_taken(self):
        code = bytes([
            int(Op.MOVI),0,5,0, int(Op.MOVI),1,3,0,
            int(Op.CMP),0,1, int(Op.JNE),0,4,0,
            int(Op.MOVI),0,99,0, int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 5

    def test_jsge_greater(self):
        code = bytes([
            int(Op.MOVI),0,10,0, int(Op.MOVI),1,5,0,
            int(Op.CMP),0,1, int(Op.JSGE),0,4,0,
            int(Op.MOVI),0,99,0, int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 10

    def test_jsge_less_should_not_jump(self):
        code = bytes([
            int(Op.MOVI),0,3,0, int(Op.MOVI),1,5,0,
            int(Op.CMP),0,1, int(Op.JSGE),0,4,0,
            int(Op.MOVI),0,99,0, int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 99  # fell through to MOVI R0,99

    def test_jslt_less(self):
        code = bytes([
            int(Op.MOVI),0,3,0, int(Op.MOVI),1,8,0,
            int(Op.CMP),0,1, int(Op.JSLT),0,4,0,
            int(Op.MOVI),0,99,0, int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 3

    def test_jslt_greater_should_not_jump(self):
        code = bytes([
            int(Op.MOVI),0,10,0, int(Op.MOVI),1,3,0,
            int(Op.CMP),0,1, int(Op.JSLT),0,4,0,
            int(Op.MOVI),0,99,0, int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 99


class TestSyscalls:
    def test_input_len(self):
        code = bytes([int(Op.MOVI),0,1,0, int(Op.SYSCALL), int(Op.HALT)])
        vm = VM(); vm.load_input("hello world"); vm.run(code)
        assert vm.regs.get(0) == 11

    def test_output_len(self):
        code = bytes([int(Op.MOVI),0,2,0, int(Op.SYSCALL), int(Op.HALT)])
        vm = VM(); vm.load_output("test response"); vm.run(code)
        assert vm.regs.get(0) == 13

    def test_token_count(self):
        code = bytes([int(Op.MOVI),0,5,0, int(Op.SYSCALL), int(Op.HALT)])
        vm = VM(); vm.load_output("a" * 40); vm.run(code)
        assert vm.regs.get(0) == 10

    def test_repetition(self):
        code = bytes([int(Op.MOVI),0,6,0, int(Op.SYSCALL), int(Op.HALT)])
        vm = VM(); vm.load_output("the the the the the"); vm.run(code)
        assert vm.regs.get(0) == 1000

    def test_get_budget(self):
        code = bytes([int(Op.MOVI),0,10,0, int(Op.SYSCALL), int(Op.HALT)])
        vm = VM(); vm.set_budget(750); vm.run(code)
        assert vm.regs.get(0) == 750

    def test_unique_ratio(self):
        code = bytes([int(Op.MOVI),0,11,0, int(Op.SYSCALL), int(Op.HALT)])
        vm = VM(); vm.load_output("apple banana apple banana cherry"); vm.run(code)
        assert vm.regs.get(0) == 600

    def test_violation_flag(self):
        code = bytes([
            int(Op.MOVI),1,2,0,
            int(Op.MOVI),0,8,0, int(Op.SYSCALL),
            int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        assert vm.violated is True
        assert "repetition" in vm.violation_reason.lower()


class TestStack:
    def test_push_pop(self):
        code = bytes([
            int(Op.MOVI),0,42,0, int(Op.PUSH),0,
            int(Op.MOVI),0,0,0, int(Op.POP),1, int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        assert vm.regs.get(1) == 42

    def test_inc_dec(self):
        code = bytes([
            int(Op.MOVI),0,5,0, int(Op.INC),0, int(Op.INC),0, int(Op.DEC),0, int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 6


class TestMemory:
    """Regression coverage for Memory.store_i32 / load_i32 round-tripping.

    Previously store_i32 corrupted genuine negatives and crashed with
    struct.error for register values >= 0x80000000 (how the register file
    represents negatives). These tests pin the fixed 32-bit-preservation
    behavior.
    """

    def test_store_load_i32_roundtrip(self):
        m = Memory()
        cases = [0, 1, 42, -1, -100, 2147483647, -2147483648]
        for i, val in enumerate(cases):
            m.store_i32(i * 4, val)
        for i, val in enumerate(cases):
            assert m.load_i32(i * 4) == val

    def test_store_i32_masks_to_32_bits(self):
        m = Memory()
        # 0x100000000 should wrap to 0
        m.store_i32(0, 0x100000000)
        assert m.load_i32(0) == 0

    def test_store_i32_out_of_bounds_is_safe(self):
        m = Memory(size=16)
        # Writing past the end must not raise and must not corrupt earlier data.
        m.store_i32(0, 7)
        m.store_i32(20, 99)  # out of bounds (16-byte buffer)
        assert m.load_i32(0) == 7

    def test_store_load_bytes_roundtrip(self):
        m = Memory(size=64)
        payload = b"\x01\x02\x03\x04hello"
        m.store_bytes(8, payload)
        assert m.load_bytes(8, len(payload)) == payload


class TestStoreLoadInstructions:
    """The STORE/LOAD instructions must preserve the full register bit pattern."""

    def test_store_load_preserves_negative_value(self):
        # R0 = 5 - 10 = -5 (held as 0xFFFFFFFB in the register file);
        # STORE R0 -> mem[0]; LOAD R2 <- mem[0]; the loaded bit pattern must
        # match the stored one. Pre-fix this raised struct.error.
        code = bytes([
            int(Op.MOVI),0,5,0,
            int(Op.MOVI),1,10,0,
            int(Op.ISUB),0,0,1,   # R0 = -5 (0xFFFFFFFB)
            int(Op.MOVI),1,0,0,   # R1 = addr 0
            int(Op.STORE),0,1,    # mem[R1] = R0
            int(Op.MOVI),3,0,0,   # R3 = addr 0
            int(Op.LOAD),2,3,     # R2 = mem[R3]
            int(Op.HALT),
        ])
        vm = VM(); vm.run(code)
        # Register file stores unsigned 32-bit, so the loaded value is the
        # unsigned representation of -5.
        assert vm.regs.get(2) == 0xFFFFFFFB
        assert vm.regs.get(2) == vm.regs.get(0)


class TestErrorPaths:
    def test_invalid_opcode_raises(self):
        # 0xAA is not a valid opcode.
        with pytest.raises(VMInvalidOpcode):
            vm = VM(); vm.run(bytes([0xAA]))

    def test_unhandled_valid_opcode_raises(self):
        # Construct a VM whose dispatch table is missing an entry for an opcode
        # that is otherwise valid, to exercise the "no handler" branch.
        vm = VM()
        saved = VM._DISPATCH[Op.NOP]
        try:
            VM._DISPATCH.pop(Op.NOP)
            with pytest.raises(VMInvalidOpcode):
                vm.run(bytes([int(Op.NOP)]))
        finally:
            VM._DISPATCH[Op.NOP] = saved

    def test_cycle_budget_exhaustion_raises(self):
        # Infinite loop: JMP -4 (back to itself).
        # JMP is D-format: opcode + reg(0) + off_lo + off_hi. off = -4.
        code = bytes([int(Op.JMP), 0, 0xFC, 0xFF])
        # Shrink the cap so the test is fast.
        original = VM.MAX_CYCLES
        VM.MAX_CYCLES = 1000
        try:
            with pytest.raises(VMError, match="Cycle budget"):
                vm = VM(); vm.run(code)
        finally:
            VM.MAX_CYCLES = original

    def test_mod_by_zero(self):
        code = bytes([int(Op.MOVI),0,10,0, int(Op.MOVI),1,0,0, int(Op.IMOD),2,0,1, int(Op.HALT)])
        vm = VM()
        with pytest.raises(VMDivisionByZero):
            vm.run(code)

    def test_halt_sets_result_register(self):
        # R0 at HALT is the decision value: 0 = allow.
        code = bytes([int(Op.MOVI),0,0,0, int(Op.HALT)])
        vm = VM()
        assert vm.run(code) == 0


class TestLifecycleFixes:
    """Regression coverage for bugs found in the v0.2.0 audit.

    BUG #1 (HIGH): ``running`` flag was dead code — a top-level RET with an
    empty call stack set ``self.running = False`` but the main loop never
    checked it, so the VM silently fell through to whatever came next.

    BUG #2 (MED): ``_h_movi`` stored the raw 16-bit pattern (``off & 0xFFFF``)
    instead of sign-extending the documented i16 immediate, so
    ``MOVI R0, -1`` loaded 65535 instead of 0xFFFFFFFF.
    """

    def test_ret_with_empty_stack_halts_cleanly(self):
        # RET (no CALL to return to) followed by a sentinel MOVI. Pre-fix the
        # VM executed the sentinel because ``running=False`` was unchecked.
        code = bytes([
            int(Op.RET),                # top-level RET
            int(Op.MOVI), 0, 99, 0,     # sentinel — must NOT execute
            int(Op.HALT),
        ])
        vm = VM()
        result = vm.run(code)
        # VM halted cleanly; R0 was never set so it should be 0 (initial value).
        assert result == 0, f"RET-with-empty-stack must halt; got R0={result}"
        assert vm.cycle_count == 1, f"RET must take exactly one cycle; got {vm.cycle_count}"

    def test_ret_after_balanced_call_still_returns(self):
        # CALL/RET balance still works after the lifecycle fix. CALL pushes
        # the post-decode PC (here = 4) onto the call stack and adds the
        # 16-bit offset (here = 4), so execution jumps to byte 8. RET pops
        # the return address (4) and execution continues at the HALT.
        code = bytes([
            int(Op.CALL), 0, 4, 0,    # 0..3: CALL +4 → pc=8 (after pushing 4)
            int(Op.HALT),              # 4:    return site — HALT terminates
            0, 0, 0,                   # 5..7: padding (skipped by CALL target)
            int(Op.IADD), 2, 0, 1,    # 8..11: called body (IADD R2, R0, R1)
            int(Op.RET),               # 12:   RET → pc=4 → HALT
        ])
        vm = VM()
        result = vm.run(code)
        assert result == 0
        assert vm.regs.get(2) == 0  # IADD did execute with R0=0, R1=0

    def test_movi_sign_extends_negatives(self):
        # MOVI R0, -1 must sign-extend i16 to i32: -1 → 0xFFFFFFFF.
        code = bytes([int(Op.MOVI), 0, 0xFF, 0xFF, int(Op.HALT)])
        vm = VM()
        vm.run(code)
        assert vm.regs.get(0) == 0xFFFFFFFF, (
            f"MOVI R0, -1 must give 0xFFFFFFFF; got {vm.regs.get(0)}"
        )

    def test_movi_min_i16_value(self):
        # MOVI R0, -32768 must give 0xFFFF8000 (sign-extended).
        code = bytes([int(Op.MOVI), 0, 0x00, 0x80, int(Op.HALT)])
        vm = VM()
        vm.run(code)
        assert vm.regs.get(0) == 0xFFFF8000

    def test_movi_max_i16_value(self):
        # MOVI R0, 32767 stays in the positive range (no sign bit set).
        code = bytes([int(Op.MOVI), 0, 0xFF, 0x7F, int(Op.HALT)])
        vm = VM()
        vm.run(code)
        assert vm.regs.get(0) == 32767

    def test_movi_round_trip_assembler_to_vm(self):
        # ``MOVI R0, -1`` assembled by the high-level assembler must round-trip
        # to 0xFFFFFFFF at runtime (was the user-visible symptom of BUG #2).
        from conservation_enforcer import assemble
        code = assemble("MOVI R0, -1\nHALT")
        vm = VM()
        vm.run(code)
        assert vm.regs.get(0) == 0xFFFFFFFF, (
            f"Assembler+VM round-trip of MOVI R0, -1 must give 0xFFFFFFFF; "
            f"got {vm.regs.get(0)}"
        )
