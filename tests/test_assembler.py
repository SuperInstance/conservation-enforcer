"""Tests for the FLUX assembler."""

import pytest
from conservation_enforcer.assembler import assemble, AssemblerError
from conservation_enforcer.vm import VM, Op


class TestAssembler:
    def test_simple_halt(self):
        assert assemble("HALT") == bytes([int(Op.HALT)])

    def test_nop(self):
        assert assemble("NOP") == bytes([int(Op.NOP)])

    def test_movi(self):
        assert assemble("MOVI R0, 42") == bytes([int(Op.MOVI), 0, 42, 0])

    def test_add(self):
        assert assemble("IADD R2, R0, R1") == bytes([int(Op.IADD), 2, 0, 1])

    def test_mov(self):
        assert assemble("MOV R0, R1") == bytes([int(Op.MOV), 0, 1])

    def test_inc(self):
        assert assemble("INC R5") == bytes([int(Op.INC), 5])

    def test_cmp(self):
        assert assemble("CMP R0, R1") == bytes([int(Op.CMP), 0, 1])

    def test_multiple_instructions(self):
        code = assemble("MOVI R0, 10\nMOVI R1, 20\nIADD R2, R0, R1\nHALT")
        expected = bytes([int(Op.MOVI),0,10,0, int(Op.MOVI),1,20,0, int(Op.IADD),2,0,1, int(Op.HALT)])
        assert code == expected

    def test_comments(self):
        code = assemble("; comment\nMOVI R0, 5  # inline\nHALT")
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 5

    def test_unknown_instruction(self):
        with pytest.raises(AssemblerError, match="unknown instruction"):
            assemble("BOGUS R0, R1")

    def test_undefined_label(self):
        with pytest.raises(AssemblerError, match="Undefined label"):
            assemble("JE nowhere\nHALT")


class TestLabels:
    def test_je_label(self):
        code = assemble("""
            MOVI R0, 0
            CMP R0, R0
            JE done
            MOVI R0, 99
done:
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 0

    def test_jmp_label(self):
        code = assemble("""
            MOVI R0, 1
            JMP skip
            MOVI R0, 99
skip:
            MOVI R0, 42
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(0) == 42


class TestPseudoJumps:
    def test_jge_taken_greater(self):
        code = assemble("""
            MOVI R0, 10
            MOVI R1, 5
            JGE R0, R1, hit
            MOVI R2, 0
            HALT
hit:
            MOVI R2, 1
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 1

    def test_jge_taken_equal(self):
        code = assemble("""
            MOVI R0, 5
            MOVI R1, 5
            JGE R0, R1, hit
            MOVI R2, 0
            HALT
hit:
            MOVI R2, 1
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 1

    def test_jge_not_taken(self):
        code = assemble("""
            MOVI R0, 3
            MOVI R1, 5
            JGE R0, R1, hit
            MOVI R2, 99
            HALT
hit:
            MOVI R2, 1
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 99  # didn't jump

    def test_jlt_taken(self):
        code = assemble("""
            MOVI R0, 3
            MOVI R1, 5
            JLT R0, R1, hit
            MOVI R2, 0
            HALT
hit:
            MOVI R2, 1
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 1

    def test_jgt_taken(self):
        code = assemble("""
            MOVI R0, 10
            MOVI R1, 5
            JGT R0, R1, hit
            MOVI R2, 0
            HALT
hit:
            MOVI R2, 1
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 1

    def test_jgt_not_taken_equal(self):
        code = assemble("""
            MOVI R0, 5
            MOVI R1, 5
            JGT R0, R1, hit
            MOVI R2, 99
            HALT
hit:
            MOVI R2, 1
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 99  # equal, not greater

    def test_jle_taken_equal(self):
        code = assemble("""
            MOVI R0, 5
            MOVI R1, 5
            JLE R0, R1, hit
            MOVI R2, 0
            HALT
hit:
            MOVI R2, 1
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 1

    def test_jle_taken_less(self):
        code = assemble("""
            MOVI R0, 3
            MOVI R1, 5
            JLE R0, R1, hit
            MOVI R2, 0
            HALT
hit:
            MOVI R2, 1
            HALT
        """)
        vm = VM(); vm.run(code)
        assert vm.regs.get(2) == 1
