#!/usr/bin/env python3
"""OpenAI Integration Example — Conservation-enforced GPT-4 calls.

This example shows how to wrap any LLM call with conservation-law enforcement.
The same pattern works with Anthropic, Cohere, or any text-in/text-out model.

Requirements:
    pip install openai conservation-enforcer

Usage:
    # Set OPENAI_API_KEY environment variable first
    python examples/openai_integration.py
"""

from conservation_enforcer import (
    ConservationEnforcer,
    MetricsCollector,
    combined_policy,
)
from audit import AuditLog  # optional, for audit logging

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Note: openai package not installed. This is a demo of the pattern.")
    print("Install with: pip install openai\n")


def main():
    # ── Set up the enforcer ──
    policy = combined_policy(
        max_tokens=500,
        max_repetition=300,
        min_overlap=50,
        min_entropy=1000,
        min_density=300,       # enable density check
    )

    enforcer = ConservationEnforcer(policy, budget=500)
    metrics = MetricsCollector()

    # ── Simulated LLM call (works without API key) ──
    def fake_llm(prompt: str) -> str:
        """Simulate an LLM response for demo purposes."""
        responses = {
            "quantum": "Quantum physics studies matter and energy at the smallest scales. "
                       "Key concepts include superposition, entanglement, and wave-particle duality. "
                       "Quantum mechanics fundamentally changed our understanding of nature.",
            "verbose": "Well, let me tell you about this, and then tell you again, "
                       "and again, and again, because I love to repeat myself endlessly "
                       "with the same words over and over and over again endlessly.",
        }
        prompt_lower = prompt.lower()
        if "quantum" in prompt_lower:
            return responses["quantum"]
        elif "verbose" in prompt_lower:
            return responses["verbose"]
        return f"Here is a thoughtful response to: {prompt}"

    # ── Test cases ──
    test_inputs = [
        "Tell me everything about quantum physics",
        "Be as verbose as possible",
        "Explain machine learning briefly",
    ]

    print("=" * 60)
    print("  Conservation-Enforced LLM Integration Demo")
    print("=" * 60)

    llm_call = None
    if HAS_OPENAI:
        try:
            client = OpenAI()
            def real_llm(prompt: str) -> str:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
            llm_call = real_llm
        except Exception:
            print("OpenAI client not configured, using simulated LLM.\n")
            llm_call = fake_llm
    else:
        llm_call = fake_llm

    for user_input in test_inputs:
        print(f"\n📝 User: {user_input}")

        # Call the LLM
        raw_output = llm_call(user_input)
        print(f"🤖 Raw LLM: {raw_output[:100]}{'...' if len(raw_output) > 100 else ''}")

        # Enforce conservation laws
        budget_before = enforcer.remaining_budget
        allowed, corrected = enforcer.enforce(
            input_text=user_input,
            output_text=raw_output,
        )
        budget_after = enforcer.remaining_budget

        # Record metrics
        metrics.record(
            allowed=allowed,
            violation_reason=None if allowed else corrected.violation.reason,
            cycles=allowed.cycles,
            budget_before=budget_before,
            budget_after=budget_after,
        )

        if allowed:
            print(f"✅ ALLOWED ({allowed.cycles} cycles)")
            print(f"   Output: {allowed.output[:80]}{'...' if len(allowed.output) > 80 else ''}")
        else:
            print(f"🚫 BLOCKED: {corrected.violation.reason}")
            print(f"   Correction: {corrected.output}")

    # ── Show metrics ──
    print("\n" + "=" * 60)
    print("  Enforcement Metrics")
    print("=" * 60)
    data = metrics.export()
    import json
    print(json.dumps(data, indent=2))

    # ── Write metrics for external dashboarding ──
    metrics.export("enforcement_metrics.json")
    print(f"\n📊 Metrics written to enforcement_metrics.json")


if __name__ == "__main__":
    main()
