"""Connect a model provider, then make one loop-governed task call.

    export OPENROUTER_API_KEY=...      # or OLLAMA_API_KEY / MISTRAL_API_KEY
    python3 examples/03_connect_a_model/run.py

Runs with no key too: and that is the point of the first half. `configure()`
tells you what this installation can actually do BEFORE you start a run, so a
missing or capped key is a setup message rather than a mystery failure twenty
minutes into a job.

What the loop does with a model is deliberate: the deterministic rail runs
first, and a model is asked only for the step that needs judgement. You are not
choosing "AI mode": you are permitting an escalation.
"""

from loop_engine import configure, call_with_failover, LoopLedger
from loop_engine.loop.encapsulate import as_model_loop
from loop_engine.code_nodes.loop_report import report_from_ledger, render_text
from loop_engine.core.custom_endpoint import CustomEndpoint


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

    if not access.has_model:
        print("No model provider was configured and verified.")
        print("Deterministic loops still run. See examples 1 and 2.")
        print()
        print("To add one, set any of:")
        print("  OPENROUTER_API_KEY   (hundreds of models behind one key)")
        print("  OLLAMA_API_KEY       (Ollama Cloud)")
        print("  MISTRAL_API_KEY")
        print("  LOOP_ENGINE_ENDPOINTS     (your own server: see "
              "use_your_own_server() above)")
        return

    # configure() probes configured providers by use. The task below is one
    # additional semantic call, recorded inside its own loop.
    ledger = LoopLedger()
    task = as_model_loop(
        "identify when gradient boosting is a poor fit",
        lambda: call_with_failover(
            "In two sentences: when is gradient boosting a poor choice for "
            "tabular data?",
            order=tuple(access.providers_working)),
        ledger=ledger,
    )
    answer = task["value"]
    print("=== the model answered ===")
    print(answer.text.strip()[:400])
    print()
    print(f"provider : {answer.provider}")
    print(f"model    : {answer.model}")
    print(f"tokens   : {answer.prompt_tokens} in + "
          f"{answer.eval_tokens} out (provider-reported)")
    print(f"tried    : {[attempt.provider for attempt in answer.attempts]}")
    print()
    print(render_text(report_from_ledger(
        ledger.events, run_id="model-provider-task")))


if __name__ == "__main__":
    main()
