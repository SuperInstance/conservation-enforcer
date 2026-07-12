"""Pre-built conservation policies written in FLUX assembly.

Available policies:
    - length_budget_policy:  Block outputs exceeding a token budget
    - repetition_policy:     Block outputs with excessive repetition
    - category_policy:       Block outputs that drift off-topic
    - entropy_policy:        Block outputs with too-low entropy
    - combined_policy:       Multiple conservation laws in one program

Policy convention:
    - R0 = 0 at HALT → ALLOW
    - R0 ≠ 0 at HALT → BLOCK
    - Syscall number goes in R0, args in R1-R7
    - SET_VIOLATION (syscall 8) reads R1 for the reason code
"""

from __future__ import annotations

from ..assembler import assemble


def length_budget_policy(max_tokens: int = 500) -> bytes:
    """Enforce a maximum output length (approximate token count).

    Conservation law: Information output cannot exceed the budget.
    """
    source = f"""
    ; ── Length Budget Conservation Law ──
    ; R0 = result (0=allow, non-zero=block)

    MOVI R0, 0          ; default: ALLOW
    MOVI R0, 5          ; syscall: GET_TOKEN_COUNT
    SYSCALL
    MOV  R2, R0         ; R2 = token_count (return value clobbers R0)

    MOVI R0, 10         ; syscall: GET_BUDGET
    SYSCALL
    MOV  R3, R0         ; R3 = budget

    ; if token_count > budget → block
    JGT  R2, R3, block

    MOVI R0, 0          ; ALLOW
    HALT

block:
    MOVI R1, 1          ; reason code: LENGTH_BUDGET
    MOVI R0, 8          ; syscall: SET_VIOLATION
    SYSCALL
    MOVI R0, 1          ; BLOCK
    HALT
    """
    return assemble(source)


def repetition_policy(max_ratio: int = 300) -> bytes:
    """Block outputs where a single word appears too frequently.

    max_ratio is in per-mille (300 = 30%).
    Conservation law: Information diversity.
    """
    source = f"""
    ; ── Repetition Conservation Law ──

    MOVI R0, 6          ; syscall: GET_REPETITION
    SYSCALL
    MOV  R2, R0         ; R2 = repetition ratio

    MOVI R3, {max_ratio}    ; threshold

    JGT  R2, R3, block  ; if repetition > threshold → block

    MOVI R0, 0          ; ALLOW
    HALT

block:
    MOVI R1, 2          ; reason: REPETITION
    MOVI R0, 8          ; SET_VIOLATION
    SYSCALL
    MOVI R0, 1          ; BLOCK
    HALT
    """
    return assemble(source)


def category_policy(min_overlap: int = 150) -> bytes:
    """Block outputs that drift too far from the input topic.

    min_overlap is in per-mille (150 = 15%).
    Conservation law: Category confinement.
    """
    source = f"""
    ; ── Category Confinement Conservation Law ──

    MOVI R0, 7          ; syscall: GET_CATEGORY
    SYSCALL
    MOV  R2, R0         ; R2 = overlap score

    MOVI R3, {min_overlap}   ; minimum required overlap

    JLT  R2, R3, block  ; if overlap < threshold → block

    MOVI R0, 0          ; ALLOW
    HALT

block:
    MOVI R1, 3          ; reason: CATEGORY
    MOVI R0, 8          ; SET_VIOLATION
    SYSCALL
    MOVI R0, 1          ; BLOCK
    HALT
    """
    return assemble(source)


def entropy_policy(min_entropy: int = 2000) -> bytes:
    """Block outputs with too-low Shannon entropy.

    min_entropy is entropy × 1000 (2000 = 2.0 bits/word minimum).
    Conservation law: Information density.
    """
    source = f"""
    ; ── Entropy Conservation Law ──

    MOVI R0, 12         ; syscall: GET_ENTROPY
    SYSCALL
    MOV  R2, R0         ; R2 = entropy × 1000

    MOVI R3, {min_entropy}   ; minimum entropy

    JLT  R2, R3, block  ; if entropy < threshold → block

    MOVI R0, 0          ; ALLOW
    HALT

block:
    MOVI R1, 4          ; reason: ENTROPY
    MOVI R0, 8          ; SET_VIOLATION
    SYSCALL
    MOVI R0, 1          ; BLOCK
    HALT
    """
    return assemble(source)


def combined_policy(
    max_tokens: int = 500,
    max_repetition: int = 300,
    min_overlap: int = 100,
    min_entropy: int = 1500,
) -> bytes:
    """Combined conservation policy: length + repetition + category + entropy.

    This is the flagship policy — four conservation laws in one bytecode program.
    """
    source = f"""
    ; ═══════════════════════════════════════════════════════
    ; COMBINED CONSERVATION POLICY
    ;   1. Length budget     (information quantity)
    ;   2. Repetition limit  (information diversity)
    ;   3. Category confinement (topical coherence)
    ;   4. Entropy floor     (information density)
    ; ═══════════════════════════════════════════════════════

    ; ── Law 1: Length Budget ──
    MOVI R0, 5              ; GET_TOKEN_COUNT
    SYSCALL
    MOV  R2, R0
    MOVI R0, 10             ; GET_BUDGET
    SYSCALL
    MOV  R3, R0
    JGT  R2, R3, block_length

    ; ── Law 2: Repetition Limit ──
    MOVI R0, 6              ; GET_REPETITION
    SYSCALL
    MOV  R2, R0
    MOVI R3, {max_repetition}
    JGT  R2, R3, block_repetition

    ; ── Law 3: Category Confinement ──
    MOVI R0, 7              ; GET_CATEGORY
    SYSCALL
    MOV  R2, R0
    MOVI R3, {min_overlap}
    JLT  R2, R3, block_category

    ; ── Law 4: Entropy Floor ──
    MOVI R0, 12             ; GET_ENTROPY
    SYSCALL
    MOV  R2, R0
    MOVI R3, {min_entropy}
    JLT  R2, R3, block_entropy

    ; ── All laws satisfied ──
    MOVI R0, 0              ; ALLOW
    HALT

    ; ── Violation handlers ──
block_length:
    MOVI R1, 1              ; reason: LENGTH
    MOVI R0, 8              ; SET_VIOLATION
    SYSCALL
    MOVI R0, 1              ; BLOCK
    HALT

block_repetition:
    MOVI R1, 2              ; reason: REPETITION
    MOVI R0, 8
    SYSCALL
    MOVI R0, 1
    HALT

block_category:
    MOVI R1, 3              ; reason: CATEGORY
    MOVI R0, 8
    SYSCALL
    MOVI R0, 1
    HALT

block_entropy:
    MOVI R1, 4              ; reason: ENTROPY
    MOVI R0, 8
    SYSCALL
    MOVI R0, 1
    HALT
    """
    return assemble(source)
