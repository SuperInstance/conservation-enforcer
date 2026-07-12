"""FLUX Assembler — human-readable assembly → bytecode.

Single clean implementation. Two-pass with label resolution.

Supported syntax:
    ; line comments       # also comments
    label:                ; label definition
    MOVI R0, 42           ; D-format: reg + i16 immediate
    IADD R0, R1, R2       ; E-format: three registers
    MOV R0, R1            ; C-format: two registers
    INC R0                ; B-format: one register
    HALT                  ; A-format: no operands
    CMP R0, R1            ; set flags from R0 - R1
    JE  label             ; jump if equal (flag_zero)
    JNE label             ; jump if not equal
    JSGE label            ; jump if signed ≥ (after CMP/ISUB)
    JSLT label            ; jump if signed <
    JMP label             ; unconditional jump
    SYSCALL               ; dispatch using R0

Convenience aliases (multi-instruction expansions):
    JGE Rd, Rs, label     → CMP Rd, Rs + JSGE label
    JLT Rd, Rs, label     → CMP Rd, Rs + JSLT label
    JGT Rd, Rs, label     → CMP Rd, Rs + JE skip + JSGE label
    JLE Rd, Rs, label     → CMP Rd, Rs + JE label + JSLT label
"""

from __future__ import annotations

import re
from typing import Optional

from .vm import Op, NUM_REGISTERS


SIMPLE = {
    'NOP': (Op.NOP, 'A'), 'HALT': (Op.HALT, 'A'), 'YIELD': (Op.YIELD, 'A'),
    'DUP': (Op.DUP, 'A'), 'RET': (Op.RET, 'A'), 'SYSCALL': (Op.SYSCALL, 'A'),
    'INC': (Op.INC, 'B'), 'DEC': (Op.DEC, 'B'),
    'PUSH': (Op.PUSH, 'B'), 'POP': (Op.POP, 'B'),
    'MOV': (Op.MOV, 'C'), 'LOAD': (Op.LOAD, 'C'), 'STORE': (Op.STORE, 'C'),
    'NEG': (Op.INEG, 'C'), 'INEG': (Op.INEG, 'C'),
    'NOT': (Op.INOT, 'C'), 'INOT': (Op.INOT, 'C'),
    'CMP': (Op.CMP, 'C'),
    'JMP': (Op.JMP, 'D'), 'JZ': (Op.JZ, 'D'), 'JNZ': (Op.JNZ, 'D'),
    'CALL': (Op.CALL, 'D'), 'MOVI': (Op.MOVI, 'D'),
    'JE': (Op.JE, 'D'), 'JNE': (Op.JNE, 'D'),
    'JSGE': (Op.JSGE, 'D'), 'JSLT': (Op.JSLT, 'D'),
    'ADD': (Op.IADD, 'E'), 'IADD': (Op.IADD, 'E'),
    'SUB': (Op.ISUB, 'E'), 'ISUB': (Op.ISUB, 'E'),
    'MUL': (Op.IMUL, 'E'), 'IMUL': (Op.IMUL, 'E'),
    'DIV': (Op.IDIV, 'E'), 'IDIV': (Op.IDIV, 'E'),
    'MOD': (Op.IMOD, 'E'), 'IMOD': (Op.IMOD, 'E'),
    'AND': (Op.IAND, 'E'), 'IAND': (Op.IAND, 'E'),
    'OR': (Op.IOR, 'E'), 'IOR': (Op.IOR, 'E'),
    'XOR': (Op.IXOR, 'E'), 'IXOR': (Op.IXOR, 'E'),
    'SHL': (Op.ISHL, 'E'), 'ISHL': (Op.ISHL, 'E'),
    'SHR': (Op.ISHR, 'E'), 'ISHR': (Op.ISHR, 'E'),
}

FMT_SIZE = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 4}
PSEUDO = {'JGE', 'JLE', 'JGT', 'JLT'}


class AssemblerError(Exception):
    pass


def assemble(source: str) -> bytes:
    """Assemble FLUX source code to bytecode."""
    raw: list[dict] = []
    labels: dict[str, int] = {}  # label → instruction index

    # ── Parse ──
    for line_num, line in enumerate(source.split('\n'), 1):
        text = line
        for marker in (';', '#'):
            idx = text.find(marker)
            if idx >= 0:
                text = text[:idx]
        text = text.strip()
        if not text:
            continue

        # Label?
        m = re.match(r'^([A-Za-z_]\w*):\s*(.*)$', text)
        if m:
            label = m.group(1)
            if label in labels:
                raise AssemblerError(f"Duplicate label '{label}'")
            labels[label] = len(raw)
            text = m.group(2).strip()
            if not text:
                continue

        # Parse mnemonic
        parts = text.split(None, 1)
        mnem = parts[0].upper()
        rest = parts[1].strip() if len(parts) > 1 else ""

        def reg(tok: str) -> int:
            tok = tok.strip().upper()
            if not re.match(r'^R\d+$', tok):
                raise AssemblerError(f"Line {line_num}: expected register, got '{tok}'")
            n = int(tok[1:])
            if n >= NUM_REGISTERS:
                raise AssemblerError(f"Line {line_num}: R{n} out of range")
            return n

        if mnem in PSEUDO:
            ps = [p.strip() for p in rest.split(',')]
            if len(ps) != 3:
                raise AssemblerError(f"Line {line_num}: {mnem} needs Rd, Rs, label")
            rd, rs = reg(ps[0]), reg(ps[1])
            lbl = ps[2]

            # CMP rd, rs (3 bytes)
            raw.append({'op': Op.CMP, 'fmt': 'C', 'rd': rd, 'rs': rs, 'size': 3})

            if mnem == 'JGE':
                raw.append({'op': Op.JSGE, 'fmt': 'D', 'label': lbl, 'size': 4})
            elif mnem == 'JLT':
                raw.append({'op': Op.JSLT, 'fmt': 'D', 'label': lbl, 'size': 4})
            elif mnem == 'JLE':
                raw.append({'op': Op.JE, 'fmt': 'D', 'label': lbl, 'size': 4})
                raw.append({'op': Op.JSLT, 'fmt': 'D', 'label': lbl, 'size': 4})
            elif mnem == 'JGT':
                # JE skip (skip the next JSGE instruction if equal)
                raw.append({'op': Op.JE, 'fmt': 'D', 'imm': 4, 'size': 4})
                raw.append({'op': Op.JSGE, 'fmt': 'D', 'label': lbl, 'size': 4})

        elif mnem in SIMPLE:
            op, fmt = SIMPLE[mnem]
            entry = {'op': op, 'fmt': fmt, 'size': FMT_SIZE[fmt]}

            if fmt == 'A':
                pass
            elif fmt == 'B':
                entry['rd'] = reg(rest)
            elif fmt == 'C':
                ps = [p.strip() for p in rest.split(',')]
                entry['rd'] = reg(ps[0])
                entry['rs'] = reg(ps[1])
            elif fmt == 'D':
                ps = [p.strip() for p in rest.split(',')]
                if len(ps) == 1:
                    entry['label'] = ps[0]
                elif len(ps) == 2:
                    entry['rd'] = reg(ps[0])
                    v = ps[1]
                    if v and (v[0].isdigit() or (v[0] == '-' and len(v) > 1)):
                        entry['imm'] = int(v)
                    else:
                        entry['label'] = v
            elif fmt == 'E':
                ps = [p.strip() for p in rest.split(',')]
                entry['rd'] = reg(ps[0])
                entry['rs1'] = reg(ps[1])
                entry['rs2'] = reg(ps[2])

            raw.append(entry)
        else:
            raise AssemblerError(f"Line {line_num}: unknown instruction '{mnem}'")

    # ── Compute byte offsets ──
    offset = 0
    for instr in raw:
        instr['offset'] = offset
        offset += instr['size']

    # Build label → byte-offset map
    label_bytes: dict[str, int] = {}
    for lbl, idx in labels.items():
        label_bytes[lbl] = raw[idx]['offset'] if idx < len(raw) else offset

    # ── Emit ──
    out = bytearray()
    for instr in raw:
        fmt = instr['fmt']
        out.append(int(instr['op']))

        if fmt == 'A':
            pass
        elif fmt == 'B':
            out.append(instr['rd'])
        elif fmt == 'C':
            out.append(instr['rd'])
            out.append(instr['rs'])
        elif fmt == 'D':
            out.append(instr.get('rd', 0))
            if 'label' in instr:
                if instr['label'] not in label_bytes:
                    raise AssemblerError(f"Undefined label: '{instr['label']}'")
                rel = label_bytes[instr['label']] - (instr['offset'] + 4)
                out.append(rel & 0xFF)
                out.append((rel >> 8) & 0xFF)
            else:
                imm = instr.get('imm', 0)
                out.append(imm & 0xFF)
                out.append((imm >> 8) & 0xFF)
        elif fmt == 'E':
            out.append(instr['rd'])
            out.append(instr['rs1'])
            out.append(instr['rs2'])

    return bytes(out)
