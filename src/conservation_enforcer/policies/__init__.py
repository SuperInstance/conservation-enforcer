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


def information_density_policy(min_ratio: int = 400) -> bytes:
    """Block outputs with low information density (too repetitive).

    min_ratio is unique_words / total_words × 1000 (400 = 40% unique minimum).
    Conservation law: Information density — every token must carry information.
    """
    source = f"""
    ; ── Information Density Conservation Law ──

    MOVI R0, 11             ; syscall: GET_UNIQUE_RATIO
    SYSCALL
    MOV  R2, R0             ; R2 = unique ratio

    MOVI R3, {min_ratio}       ; threshold

    JLT  R2, R3, block      ; if ratio < threshold → block

    MOVI R0, 0              ; ALLOW
    HALT

block:
    MOVI R1, 5              ; reason: INFORMATION_DENSITY
    MOVI R0, 8              ; SET_VIOLATION
    SYSCALL
    MOVI R0, 1              ; BLOCK
    HALT
    """
    return assemble(source)


def scope_discipline_policy(min_overlap: int = 120, max_expansion: int = 10) -> bytes:
    """Block outputs that drift outside the input's topic scope.

    min_overlap is the minimum word overlap ratio x 1000 (120 = 12%).
    max_expansion is the maximum ratio of output length to input length (>= 1).
    Conservation law: Scope discipline -- output stays in the input's potential well.
    """
    if max_expansion < 1:
        raise ValueError("max_expansion must be >= 1")

    # Build R6 = input_len * max_expansion via repeated addition. Each line is
    # one instruction; the count is driven by the max_expansion parameter so it
    # is actually honored (previously this was hardcoded to 10x).
    mult_lines = ["MOV  R6, R4     ; R6 = 1x input"]
    for i in range(2, max_expansion + 1):
        mult_lines.append(f"IADD R6, R6, R4     ; R6 = {i}x input")
    multiply = "\n    ".join(mult_lines)

    source = f"""
    ; ── Scope Discipline Conservation Law ──

    ; Check 1: Category overlap
    MOVI R0, 7              ; syscall: GET_CATEGORY
    SYSCALL
    MOV  R2, R0
    MOVI R3, {min_overlap}
    JLT  R2, R3, block

    ; Check 2: Output not excessively long vs input
    MOVI R0, 1              ; GET_INPUT_LEN
    SYSCALL
    MOV  R4, R0
    MOVI R0, 2              ; GET_OUTPUT_LEN
    SYSCALL
    MOV  R5, R0

    ; guard against empty input
    MOVI R0, 0
    CMP  R4, R0
    JE   allow

    ; multiply input_len by {max_expansion} via repeated addition
    {multiply}

    JGT  R5, R6, block

allow:
    MOVI R0, 0
    HALT

block:
    MOVI R1, 6              ; reason: SCOPE_DISCIPLINE
    MOVI R0, 8              ; SET_VIOLATION
    SYSCALL
    MOVI R0, 1              ; BLOCK
    HALT
    """
    return assemble(source)


def budget_decay_policy(decay_rate: int = 50, min_threshold: int = 10, max_calls: int = 100) -> bytes:
    """Enforce budget decay over time — each call consumes budget.

    decay_rate is tokens consumed per enforcement call.
    min_threshold is the minimum budget needed to allow output.
    max_calls is the maximum enforcement calls before mandatory cooldown.
    Conservation law: Budget dissipation — the enforcement capacity itself is conserved.
    """
    source = f"""
    ; ── Budget Decay Conservation Law ──

    ; Apply decay for this call
    MOVI R1, {decay_rate}
    MOVI R0, 14             ; syscall: DECAY_BUDGET
    SYSCALL
    MOV  R2, R0             ; remaining budget

    ; Check budget threshold
    MOVI R3, {min_threshold}
    JLT  R2, R3, exhausted

    ; Check call count
    MOVI R0, 13             ; syscall: GET_CALL_COUNT
    SYSCALL
    MOV  R4, R0
    MOVI R5, {max_calls}
    JGT  R4, R5, exhausted

    MOVI R0, 0              ; ALLOW
    HALT

exhausted:
    MOVI R1, 7              ; reason: BUDGET_EXHAUSTED
    MOVI R0, 8              ; SET_VIOLATION
    SYSCALL
    MOVI R0, 1              ; BLOCK
    HALT
    """
    return assemble(source)


def combined_policy(
    max_tokens: int = 500,
    max_repetition: int = 300,
    min_overlap: int = 100,
    min_entropy: int = 1500,
    min_density: int = 0,
    enable_decay: bool = False,
    decay_rate: int = 50,
) -> bytes:
    """Combined conservation policy: length + repetition + category + entropy + optional density + decay.

    This is the flagship policy — up to six conservation laws in one bytecode program.
    Set min_density > 0 to enable information density checking.
    Set enable_decay=True to enable budget decay checking.
    """
    density_check = f"""
    MOVI R0, 11             ; GET_UNIQUE_RATIO
    SYSCALL
    MOV  R2, R0
    MOVI R3, {min_density}
    JLT  R2, R3, block_density
    """ if min_density > 0 else "NOP"

    decay_check = f"""
    MOVI R1, {decay_rate}
    MOVI R0, 14             ; DECAY_BUDGET
    SYSCALL
    MOV  R2, R0
    MOVI R3, 10
    JLT  R2, R3, block_decay
    """ if enable_decay else "NOP"

    source = f"""
    ; ═══════════════════════════════════════════════════════
    ; COMBINED CONSERVATION POLICY
    ;   1. Length budget     (information quantity)
    ;   2. Repetition limit  (information diversity)
    ;   3. Category confinement (topical coherence)
    ;   4. Entropy floor     (information density)
    ;   5. Information density (optional)
    ;   6. Budget decay      (optional)
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

    ; ── Law 5: Information Density (optional) ──
    {density_check}

    ; ── Law 6: Budget Decay (optional) ──
    {decay_check}

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

block_density:
    MOVI R1, 5              ; reason: INFORMATION_DENSITY
    MOVI R0, 8
    SYSCALL
    MOVI R0, 1
    HALT

block_decay:
    MOVI R1, 7              ; reason: BUDGET_EXHAUSTED
    MOVI R0, 8
    SYSCALL
    MOVI R0, 1
    HALT
    """
    return assemble(source)
