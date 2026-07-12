#!/usr/bin/env python3
"""Conservation Enforcer Demo.

Demonstrates conservation-law governance on simulated LLM outputs.
Shows how FLUX bytecode acts as a deterministic, auditable policy layer.

Run: python examples/demo.py
"""

from conservation_enforcer import (
    ConservationEnforcer,
    length_budget_policy,
    repetition_policy,
    category_policy,
    combined_policy,
)


def banner(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def demo_length_budget():
    banner("DEMO 1: Length Budget Conservation Law")
    print("Law: Output information cannot exceed the allocated budget.\n")

    enforcer = ConservationEnforcer(
        length_budget_policy(max_tokens=10),
        budget=10,
    )

    outputs = [
        ("What is AI?", "AI is artificial intelligence."),
        ("Write a novel", "Once upon a time there was a brave knight who " * 20),
    ]

    for inp, outp in outputs:
        print(f"  Input:  {inp!r}")
        print(f"  Output: {outp[:60]!r}{'...' if len(outp) > 60 else ''}")
        result = enforcer.enforce(inp, outp)
        if result.allowed:
            print(f"  ✓ ALLOWED ({result.cycles} VM cycles)")
        else:
            print(f"  ✗ BLOCKED — {result.violation.reason} ({result.cycles} VM cycles)")
        print()


def demo_repetition():
    banner("DEMO 2: Repetition Conservation Law")
    print("Law: Output must maintain information diversity (no degenerate repetition).\n")

    enforcer = ConservationEnforcer(repetition_policy(max_ratio=300))

    outputs = [
        ("Summarize the movie", "The film explores deep themes of identity and purpose."),
        ("Summarize the movie", "great great great great great great great great great"),
    ]

    for inp, outp in outputs:
        print(f"  Input:  {inp!r}")
        print(f"  Output: {outp!r}")
        result = enforcer.enforce(inp, outp)
        if result.allowed:
            print(f"  ✓ ALLOWED ({result.cycles} VM cycles)")
        else:
            print(f"  ✗ BLOCKED — {result.violation.reason} ({result.cycles} VM cycles)")
        print()


def demo_category():
    banner("DEMO 3: Category Confinement Conservation Law")
    print("Law: Output must remain within the topic category of the input.\n")

    enforcer = ConservationEnforcer(category_policy(min_overlap=100))

    outputs = [
        ("Tell me about Python programming",
         "Python programming language code software development"),
        ("Tell me about Python programming",
         "banana apple orange sunset bicycle mountain ocean"),
    ]

    for inp, outp in outputs:
        print(f"  Input:  {inp!r}")
        print(f"  Output: {outp!r}")
        result = enforcer.enforce(inp, outp)
        if result.allowed:
            print(f"  ✓ ALLOWED ({result.cycles} VM cycles)")
        else:
            print(f"  ✗ BLOCKED — {result.violation.reason} ({result.cycles} VM cycles)")
        print()


def demo_combined():
    banner("DEMO 4: Combined Conservation Policy (All Four Laws)")
    print("Laws: Length budget + Repetition + Category + Entropy\n")

    enforcer = ConservationEnforcer(
        combined_policy(
            max_tokens=100,
            max_repetition=400,
            min_overlap=50,
            min_entropy=1000,
        ),
        budget=100,
    )

    test_cases = [
        ("Good response", "What is quantum computing?",
         "Quantum computing uses quantum bits or qubits to process information "
         "in ways that classical computers cannot, enabling new algorithms."),
        ("Too long", "Brief answer please",
         "The answer is " * 100),
        ("Too repetitive", "Describe a sunset",
         "beautiful beautiful beautiful beautiful beautiful beautiful beautiful"),
        ("Off topic", "Explain neural networks",
         "pizza pasta gelato espresso margherita napoli"),
    ]

    for label, inp, outp in test_cases:
        print(f"  [{label}]")
        print(f"  Input:  {inp!r}")
        truncated = outp[:60] + ('...' if len(outp) > 60 else '')
        print(f"  Output: {truncated!r}")
        result = enforcer.enforce(inp, outp)
        if result.allowed:
            print(f"  ✓ ALLOWED ({result.cycles} VM cycles)")
        else:
            print(f"  ✗ BLOCKED — {result.violation.reason} ({result.cycles} VM cycles)")
        print()


def demo_bytecode_auditability():
    banner("DEMO 5: Bytecode Auditability")
    print("The policy is deterministic bytecode. You can inspect every byte.\n")

    policy = combined_policy()
    print(f"  Policy bytecode ({len(policy)} bytes):")
    print(f"  {policy[:32].hex(' ')}...")
    print(f"  SHA-256: {__import__('hashlib').sha256(policy).hexdigest()[:32]}...")
    print()

    # Run the same policy on the same input twice — identical results
    enforcer = ConservationEnforcer(policy, budget=100)

    r1 = enforcer.enforce("test input", "test output response here")
    r2 = enforcer.enforce("test input", "test output response here")

    print(f"  Run 1: allowed={r1.allowed}, cycles={r1.cycles}")
    print(f"  Run 2: allowed={r2.allowed}, cycles={r2.cycles}")
    print(f"  Deterministic: {r1.allowed == r2.allowed and r1.cycles == r2.cycles}")


def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     ⚡ CONSERVATION ENFORCER — FLUX Bytecode Governance  ║")
    print("║     Deterministic AI Behavior via Conservation Laws      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    demo_length_budget()
    demo_repetition()
    demo_category()
    demo_combined()
    demo_bytecode_auditability()

    banner("CONCLUSION")
    print("""
  Conservation laws are the foundation of physics. Now they can be
  the foundation of AI governance.

  The FLUX bytecode policy layer:
    • Is DETERMINISTIC — same input always produces same output
    • Is AUDITABLE — every byte can be inspected and verified
    • Is IMMUNE TO MANIPULATION — bytecode has no opinions
    • Is COMPOSABLE — multiple laws combine into one program
    • Is PORTABLE — runs on Python, Rust, and JS VMs

  This is not alignment theory. This is enforcement engineering.
""")


if __name__ == "__main__":
    main()
