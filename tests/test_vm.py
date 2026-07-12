"""Tests for the FLUX VM."""

import pytest
from conservation_enforcer.vm import VM, Op, VMError, VMDivisionByZero


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
