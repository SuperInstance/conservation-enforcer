"""FLUX Micro-VM — Register-based bytecode interpreter.

Implements the core FLUX ISA for conservation-law enforcement.
Based on the FLUX Bytecode Specification (SuperInstance/flux-core).

This is a deterministic, side-effect-free VM. It cannot lie — it executes
instructions and produces a result. That determinism is the whole point.

Instruction Formats:
    A (1 byte):  [opcode]
    B (2 bytes): [opcode][reg:u8]
    C (3 bytes): [opcode][rd:u8][rs:u8]
    D (4 bytes): [opcode][reg:u8][off_lo:u8][off_hi:u8]  (signed i16 offset)
    E (4 bytes): [opcode][rd:u8][rs1:u8][rs2:u8]
"""

from __future__ import annotations

import struct
import math
from dataclasses import dataclass, field
from enum import IntEnum
from collections import Counter
from typing import Callable


# ── Opcodes ────────────────────────────────────────────────────────────────

class Op(IntEnum):
    NOP   = 0x00
    MOV   = 0x01
    LOAD  = 0x02
    STORE = 0x03
    JMP   = 0x04
    JZ    = 0x05
    JNZ   = 0x06
    CALL  = 0x07
    IADD  = 0x08
    ISUB  = 0x09
    IMUL  = 0x0A
    IDIV  = 0x0B
    IMOD  = 0x0C
    INEG  = 0x0D
    INC   = 0x0E
    DEC   = 0x0F
    IAND  = 0x10
    IOR   = 0x11
    IXOR  = 0x12
    INOT  = 0x13
    ISHL  = 0x14
    ISHR  = 0x15
    PUSH  = 0x20
    POP   = 0x21
    DUP   = 0x22
    RET   = 0x28
    MOVI  = 0x2B
    CMP   = 0x2D
    JE    = 0x2E
    JNE   = 0x2F
    # Sign-flag jumps (for signed comparisons after CMP/ISUB)
    JSGE  = 0x30   # jump if !flag_sign (signed ≥)
    JSLT  = 0x31   # jump if flag_sign (signed <)
    HALT  = 0x80
    YIELD = 0x81
    SYSCALL = 0xF0


# ── Exceptions ─────────────────────────────────────────────────────────────

class VMError(Exception): pass
class VMHalt(VMError): pass
class VMDivisionByZero(VMError): pass
class VMInvalidOpcode(VMError): pass


# ── Register File ──────────────────────────────────────────────────────────

NUM_REGISTERS = 16

@dataclass
class RegisterFile:
    """R0–R15 general-purpose registers + condition flags."""
    r: list[int] = field(default_factory=lambda: [0] * NUM_REGISTERS)
    flag_zero: bool = False
    flag_sign: bool = False

    def get(self, idx: int) -> int:
        return self.r[idx]

    def set(self, idx: int, val: int) -> None:
        self.r[idx] = val & 0xFFFFFFFF
        self._update_flags(self.r[idx])

    def _update_flags(self, uval: int) -> None:
        self.flag_zero = (uval & 0xFFFFFFFF) == 0
        signed = uval if uval < 0x80000000 else uval - 0x100000000
        self.flag_sign = signed < 0


# ── Memory ─────────────────────────────────────────────────────────────────

class Memory:
    def __init__(self, size: int = 65536):
        self.buf = bytearray(size)

    def store_i32(self, addr: int, val: int) -> None:
        if addr + 4 <= len(self.buf):
            struct.pack_into('<i', self.buf, addr, val & 0x7FFFFFFF if val < 0x80000000 else val)

    def load_i32(self, addr: int) -> int:
        return struct.unpack_from('<i', self.buf, addr)[0]

    def store_bytes(self, addr: int, data: bytes) -> None:
        end = min(addr + len(data), len(self.buf))
        self.buf[addr:end] = data[:end - addr]

    def load_bytes(self, addr: int, length: int) -> bytes:
        return bytes(self.buf[addr:addr + length])


# ── Syscall Numbers ────────────────────────────────────────────────────────

class Syscall(IntEnum):
    GET_INPUT_LEN     = 1
    GET_OUTPUT_LEN    = 2
    GET_INPUT_WORDS   = 3
    GET_OUTPUT_WORDS  = 4
    GET_TOKEN_COUNT   = 5
    GET_REPETITION    = 6
    GET_CATEGORY      = 7
    SET_VIOLATION     = 8    # R1 = reason code
    GET_BUDGET        = 10
    GET_UNIQUE_RATIO  = 11
    GET_ENTROPY       = 12


VIOLATION_REASONS = {
    1: "Length budget exceeded",
    2: "Excessive repetition detected",
    3: "Category confinement violation",
    4: "Information entropy violation",
    99: "Custom conservation law violation",
}


# ── VM ─────────────────────────────────────────────────────────────────────

class VM:
    """FLUX Virtual Machine — deterministic bytecode interpreter.

    Usage:
        vm = VM()
        vm.load_input("user question")
        vm.load_output("LLM response")
        vm.set_budget(500)
        vm.run(bytecode)
        # R0 at HALT = result: 0 = allow, non-zero = block
    """

    MAX_CYCLES = 1_000_000

    def __init__(self, memory_size: int = 65536):
        self.regs = RegisterFile()
        self.memory = Memory(memory_size)
        self.pc = 0
        self.bytecode = b''
        self.running = False
        self.cycle_count = 0
        self._input_text = ""
        self._output_text = ""
        self._budget = 1000
        self._violated = False
        self._violation_reason = ""
        self._stack: list[int] = []

    @property
    def violated(self) -> bool:
        return self._violated

    @property
    def violation_reason(self) -> str:
        return self._violation_reason

    def load_input(self, text: str) -> None:
        self._input_text = text

    def load_output(self, text: str) -> None:
        self._output_text = text

    def set_budget(self, budget: int) -> None:
        self._budget = budget

    def reset(self) -> None:
        self.regs = RegisterFile()
        self.pc = 0
        self.cycle_count = 0
        self.running = False
        self._violated = False
        self._violation_reason = ""
        self._stack.clear()

    def run(self, bytecode: bytes) -> int:
        """Execute bytecode. Returns R0 at HALT (0=allow, non-zero=block)."""
        self.bytecode = bytecode
        self.reset()
        try:
            while self.cycle_count < self.MAX_CYCLES:
                if self.pc >= len(self.bytecode):
                    break
                self._step()
                self.cycle_count += 1
        except VMHalt:
            pass
        if self.cycle_count >= self.MAX_CYCLES:
            raise VMError(f"Cycle budget exhausted ({self.MAX_CYCLES})")
        return self.regs.get(0)

    def _step(self) -> None:
        opcode = self.bytecode[self.pc]
        try:
            op = Op(opcode)
        except ValueError:
            raise VMInvalidOpcode(f"0x{opcode:02X} at pc={self.pc}")
        handler = self._DISPATCH.get(op)
        if handler is None:
            raise VMInvalidOpcode(f"Unhandled 0x{opcode:02X} at pc={self.pc}")
        handler(self)

    # ── Decoders ──

    def _d_A(self): self.pc += 1
    def _d_B(self) -> int:
        r = self.bytecode[self.pc + 1]; self.pc += 2; return r
    def _d_C(self) -> tuple[int, int]:
        rd = self.bytecode[self.pc + 1]; rs = self.bytecode[self.pc + 2]; self.pc += 3; return rd, rs
    def _d_D(self) -> tuple[int, int]:
        reg = self.bytecode[self.pc + 1]
        lo = self.bytecode[self.pc + 2]; hi = self.bytecode[self.pc + 3]
        off = lo | (hi << 8)
        if off >= 0x8000: off -= 0x10000
        self.pc += 4; return reg, off
    def _d_E(self) -> tuple[int, int, int]:
        rd = self.bytecode[self.pc + 1]; rs1 = self.bytecode[self.pc + 2]; rs2 = self.bytecode[self.pc + 3]
        self.pc += 4; return rd, rs1, rs2

    # ── Handlers ──

    def _h_nop(self): self._d_A()
    def _h_mov(self):
        rd, rs = self._d_C(); self.regs.set(rd, self.regs.get(rs))
    def _h_load(self):
        rd, rs = self._d_C(); self.regs.set(rd, self.memory.load_i32(self.regs.get(rs)))
    def _h_store(self):
        rd, rs = self._d_C(); self.memory.store_i32(self.regs.get(rs), self.regs.get(rd))
    def _h_jmp(self):
        _, off = self._d_D(); self.pc += off
    def _h_jz(self):
        reg, off = self._d_D()
        if self.regs.get(reg) == 0: self.pc += off
    def _h_jnz(self):
        reg, off = self._d_D()
        if self.regs.get(reg) != 0: self.pc += off
    def _h_call(self):
        reg, off = self._d_D(); self._stack.append(self.pc); self.pc += off
    def _h_iadd(self):
        rd, rs1, rs2 = self._d_E(); self.regs.set(rd, self.regs.get(rs1) + self.regs.get(rs2))
    def _h_isub(self):
        rd, rs1, rs2 = self._d_E(); self.regs.set(rd, self.regs.get(rs1) - self.regs.get(rs2))
    def _h_imul(self):
        rd, rs1, rs2 = self._d_E(); self.regs.set(rd, self.regs.get(rs1) * self.regs.get(rs2))
    def _h_idiv(self):
        rd, rs1, rs2 = self._d_E()
        d = self.regs.get(rs2)
        if d == 0: raise VMDivisionByZero(f"pc={self.pc}")
        self.regs.set(rd, self.regs.get(rs1) // d)
    def _h_imod(self):
        rd, rs1, rs2 = self._d_E()
        d = self.regs.get(rs2)
        if d == 0: raise VMDivisionByZero(f"pc={self.pc}")
        self.regs.set(rd, self.regs.get(rs1) % d)
    def _h_ineg(self):
        rd, rs = self._d_C(); self.regs.set(rd, (-self.regs.get(rs)) & 0xFFFFFFFF)
    def _h_inc(self):
        reg = self._d_B(); self.regs.set(reg, self.regs.get(reg) + 1)
    def _h_dec(self):
        reg = self._d_B(); self.regs.set(reg, self.regs.get(reg) - 1)
    def _h_iand(self):
        rd, rs1, rs2 = self._d_E(); self.regs.set(rd, self.regs.get(rs1) & self.regs.get(rs2))
    def _h_ior(self):
        rd, rs1, rs2 = self._d_E(); self.regs.set(rd, self.regs.get(rs1) | self.regs.get(rs2))
    def _h_ixor(self):
        rd, rs1, rs2 = self._d_E(); self.regs.set(rd, self.regs.get(rs1) ^ self.regs.get(rs2))
    def _h_inot(self):
        rd, rs = self._d_C(); self.regs.set(rd, (~self.regs.get(rs)) & 0xFFFFFFFF)
    def _h_ishl(self):
        rd, rs1, rs2 = self._d_E(); self.regs.set(rd, self.regs.get(rs1) << self.regs.get(rs2))
    def _h_ishr(self):
        rd, rs1, rs2 = self._d_E(); self.regs.set(rd, self.regs.get(rs1) >> self.regs.get(rs2))
    def _h_push(self):
        reg = self._d_B(); self._stack.append(self.regs.get(reg))
    def _h_pop(self):
        reg = self._d_B(); self.regs.set(reg, self._stack.pop() if self._stack else 0)
    def _h_dup(self):
        self._d_A()
        if self._stack: self._stack.append(self._stack[-1])
    def _h_ret(self):
        self._d_A()
        if self._stack: self.pc = self._stack.pop()
        else: self.running = False
    def _h_movi(self):
        reg, off = self._d_D()
        # Store as signed value wrapped to 32-bit unsigned
        self.regs.set(reg, off & 0xFFFF)
    def _h_cmp(self):
        rd, rs = self._d_C()
        a = self.regs.get(rd); b = self.regs.get(rs)
        diff = (a - b) & 0xFFFFFFFF
        self.regs.flag_zero = diff == 0
        signed = diff if diff < 0x80000000 else diff - 0x100000000
        self.regs.flag_sign = signed < 0
    def _h_je(self):
        _, off = self._d_D()
        if self.regs.flag_zero: self.pc += off
    def _h_jne(self):
        _, off = self._d_D()
        if not self.regs.flag_zero: self.pc += off
    def _h_jsge(self):
        _, off = self._d_D()
        if not self.regs.flag_sign: self.pc += off
    def _h_jslt(self):
        _, off = self._d_D()
        if self.regs.flag_sign: self.pc += off
    def _h_syscall(self):
        self._d_A()
        num = self.regs.get(0)
        handler = self._SYSCALLS.get(num)
        if handler: handler(self)
    def _h_halt(self):
        self._d_A(); self.running = False; raise VMHalt("HALT instruction")
    def _h_yield(self):
        self._d_A()

    # ── Dispatch table ──
    _DISPATCH: dict[Op, Callable] = {}


# ── Syscall implementations ────────────────────────────────────────────────

def _sys_input_len(vm: VM): vm.regs.set(0, len(vm._input_text))
def _sys_output_len(vm: VM): vm.regs.set(0, len(vm._output_text))
def _sys_input_words(vm: VM): vm.regs.set(0, len(vm._input_text.split()))
def _sys_output_words(vm: VM): vm.regs.set(0, len(vm._output_text.split()))
def _sys_token_count(vm: VM): vm.regs.set(0, max(1, len(vm._output_text) // 4))
def _sys_repetition(vm: VM):
    words = vm._output_text.lower().split()
    if not words: vm.regs.set(0, 0); return
    counts = Counter(words)
    mx = counts.most_common(1)[0][1]
    vm.regs.set(0, (mx * 1000) // len(words))
def _sys_category(vm: VM):
    iw = set(vm._input_text.lower().split()); ow = set(vm._output_text.lower().split())
    if not ow: vm.regs.set(0, 0); return
    ov = len(iw & ow)
    vm.regs.set(0, min(1000, (ov * 1000) // len(ow)))
def _sys_set_violation(vm: VM):
    vm._violated = True
    code = vm.regs.get(1)
    vm._violation_reason = VIOLATION_REASONS.get(code, f"Violation code {code}")
def _sys_get_budget(vm: VM): vm.regs.set(0, vm._budget)
def _sys_unique_ratio(vm: VM):
    words = vm._output_text.lower().split()
    if not words: vm.regs.set(0, 1000); return
    vm.regs.set(0, (len(set(words)) * 1000) // len(words))
def _sys_entropy(vm: VM):
    words = vm._output_text.lower().split()
    if not words: vm.regs.set(0, 0); return
    total = len(words); ent = 0.0
    for c in Counter(words).values():
        p = c / total; ent -= p * math.log2(p)
    vm.regs.set(0, int(ent * 1000))


# ── Build dispatch + syscall tables ────────────────────────────────────────

VM._DISPATCH = {
    Op.NOP: VM._h_nop, Op.MOV: VM._h_mov, Op.LOAD: VM._h_load,
    Op.STORE: VM._h_store, Op.JMP: VM._h_jmp, Op.JZ: VM._h_jz,
    Op.JNZ: VM._h_jnz, Op.CALL: VM._h_call, Op.IADD: VM._h_iadd,
    Op.ISUB: VM._h_isub, Op.IMUL: VM._h_imul, Op.IDIV: VM._h_idiv,
    Op.IMOD: VM._h_imod, Op.INEG: VM._h_ineg, Op.INC: VM._h_inc,
    Op.DEC: VM._h_dec, Op.IAND: VM._h_iand, Op.IOR: VM._h_ior,
    Op.IXOR: VM._h_ixor, Op.INOT: VM._h_inot, Op.ISHL: VM._h_ishl,
    Op.ISHR: VM._h_ishr, Op.PUSH: VM._h_push, Op.POP: VM._h_pop,
    Op.DUP: VM._h_dup, Op.RET: VM._h_ret, Op.MOVI: VM._h_movi,
    Op.CMP: VM._h_cmp, Op.JE: VM._h_je, Op.JNE: VM._h_jne,
    Op.JSGE: VM._h_jsge, Op.JSLT: VM._h_jslt,
    Op.SYSCALL: VM._h_syscall, Op.HALT: VM._h_halt, Op.YIELD: VM._h_yield,
}

VM._SYSCALLS = {
    int(Syscall.GET_INPUT_LEN): _sys_input_len,
    int(Syscall.GET_OUTPUT_LEN): _sys_output_len,
    int(Syscall.GET_INPUT_WORDS): _sys_input_words,
    int(Syscall.GET_OUTPUT_WORDS): _sys_output_words,
    int(Syscall.GET_TOKEN_COUNT): _sys_token_count,
    int(Syscall.GET_REPETITION): _sys_repetition,
    int(Syscall.GET_CATEGORY): _sys_category,
    int(Syscall.SET_VIOLATION): _sys_set_violation,
    int(Syscall.GET_BUDGET): _sys_get_budget,
    int(Syscall.GET_UNIQUE_RATIO): _sys_unique_ratio,
    int(Syscall.GET_ENTROPY): _sys_entropy,
}
