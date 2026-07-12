# Examples — Conservation Enforcer

> Real-world conservation enforcement patterns for LLM outputs.

## Example 1: Basic Token Budget Enforcement

Prevent an LLM from generating excessively long responses.

```python
from conservation_enforcer import ConservationEnforcer, combined_policy

policy = combined_policy(max_tokens=500)
enforcer = ConservationEnforcer(policy, budget=500)

result = enforcer.enforce(
    input_text="Explain quantum computing",
    output_text="Quantum computing uses quantum bits..." * 50,  # too long
)

print(f"Allowed: {result.allowed}")
# Allowed: False — token budget exceeded
```

## Example 2: Repetition Detection

Block outputs where the model gets stuck repeating itself.

```python
policy = combined_policy(max_repetition=300)
enforcer = ConservationEnforcer(policy, budget=1000)

result = enforcer.enforce(
    input_text="Write a product description",
    output_text="Buy now! Buy now! Buy now! " * 20,
)

if not result.allowed:
    print(f"Blocked: {result.violation.reason}")
    # Blocked: repetition ratio 0.85 exceeds maximum 0.30
```

## Example 3: Category Confinement

Ensure a customer service bot stays on topic and doesn't drift into unrelated domains.

```python
policy = combined_policy(
    max_tokens=300,
    min_overlap=100,   # must stay relevant to input
)
enforcer = ConservationEnforcer(policy, budget=500)

# On-topic response — passes
result = enforcer.enforce(
    input_text="What is your return policy?",
    output_text="Our return policy allows returns within 30 days of purchase with a receipt.",
)
assert result.allowed

# Off-topic response — blocked
result = enforcer.enforce(
    input_text="What is your return policy?",
    output_text="Did you know that the Mariana Trench is 11 km deep?",
)
assert not result.allowed
```

## Example 4: Entropy Floor

Enforce minimum information density — block vague, filler-heavy responses.

```python
policy = combined_policy(
    max_tokens=400,
    min_entropy=1500,
    min_density=300,
)
enforcer = ConservationEnforcer(policy, budget=500)

# Low-entropy output — all filler, no information
result = enforcer.enforce(
    input_text="What caused the 2008 financial crisis?",
    output_text="Well, that's a great question and there are many ways to think about it. "
                "It's really quite complex and involves a lot of factors that are worth "
                "considering from multiple angles.",
)

if not result.allowed:
    print(f"Blocked: {result.violation.reason}")
    # Blocked: entropy 800 below floor 1500
```

## Example 5: OpenAI Integration with Auto-Retry

Wrap an OpenAI call with enforcement and retry on violation.

```python
from conservation_enforcer import ConservationEnforcer, combined_policy
from openai import OpenAI

client = OpenAI()
enforcer = ConservationEnforcer(
    combined_policy(max_tokens=400, max_repetition=300, min_entropy=1200),
    budget=400,
)

messages = [{"role": "user", "content": "Explain photosynthesis in 3 sentences."}]

for attempt in range(3):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=400,
    )
    output = response.choices[0].message.content

    result = enforcer.enforce(
        input_text=messages[-1]["content"],
        output_text=output,
    )

    if result.allowed:
        print(result.output)
        break
    else:
        print(f"Attempt {attempt+1} blocked: {result.violation.reason}")
        messages.append({"role": "assistant", "content": output})
        messages.append({"role": "user", "content": "Please be more concise and informative."})
else:
    print("All attempts violated conservation laws.")
```
