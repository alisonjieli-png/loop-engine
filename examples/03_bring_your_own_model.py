"""3 — Add a model: any provider, any key, or your own server.

    export OPENROUTER_API_KEY=...      # or OLLAMA_API_KEY / MISTRAL_API_KEY
    python examples/03_bring_your_own_model.py

Runs with no key too — and that is the point of the first half. `configure()`
tells you what this installation can actually do BEFORE you start a run, so a
missing or capped key is a setup message rather than a mystery failure twenty
minutes into a job.

What the loop does with a model is deliberate: the deterministic rail runs
first, and a model is asked only for the step that needs judgement. You are not
choosing "AI mode" — you are permitting an escalation.
"""

from loop_engine import configure, advice_function, call_with_failover
from loop_engine.static_architecture.custom_endpoint import CustomEndpoint


def show_what_this_installation_can_do():
    access = configure()
    print("=== what this installation can do ===")
    print(access.explain())
    print()
    return access


def use_your_own_server():
    """A friend's box, an internal gateway, vLLM, LM Studio, llama.cpp…

    Anything speaking OpenAI-compatible HTTP works; set wire="ollama" for
    Ollama's native shape. Nothing here is provider-specific."""
    return configure(endpoints=[CustomEndpoint(
        name="my_server",
        base_url="http://localhost:11434/v1",
        model="qwen2.5:7b",
        # api_key="..."   <- if your server wants one
    )])


def main():
    access = show_what_this_installation_can_do()

    advise = advice_function(access)
    if advise is None:
        print("No model provider is reachable, so this example stops here.")
        print("Deterministic loops still run — see examples 1 and 2.")
        print()
        print("To add one, set any of:")
        print("  OPENROUTER_API_KEY   (hundreds of models behind one key)")
        print("  OLLAMA_API_KEY       (Ollama Cloud)")
        print("  MISTRAL_API_KEY")
        print("  LOOP_ENGINE_ENDPOINTS     (your own server — see "
              "use_your_own_server() above)")
        return

    # One semantic call. `usage` always names the provider that answered, so a
    # token count can be checked later against a bill.
    text, usage = advise(
        "In two sentences: when is gradient boosting a poor choice for "
        "tabular data?")
    print("=== the model answered ===")
    print(text.strip()[:400])
    print()
    print(f"provider : {usage['provider']}")
    print(f"model    : {usage['model']}")
    print(f"tokens   : {usage['prompt_tokens']} in + "
          f"{usage['eval_tokens']} out  (provider-reported)")
    print(f"tried    : {usage['providers_tried']}")
    print()

    # Failover directly: first provider that answers wins, every attempt is
    # recorded. If all refuse, `ok` is False — it never quietly returns
    # something that did not come from a model.
    r = call_with_failover("Reply with one word: READY")
    print("=== failover detail ===")
    print(f"ok={r.ok} answered_by={r.provider or 'nobody'}")
    for a in r.attempts:
        print(f"  {a.provider:<14}{'ok' if a.ok else 'refused'}  "
              f"{a.error[:60]}")


if __name__ == "__main__":
    main()
