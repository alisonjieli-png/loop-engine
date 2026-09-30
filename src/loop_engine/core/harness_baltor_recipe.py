"""Baltor's text-response harness behind the existing isolated process edge.

The owning Loop supplies one assignment and retains planning, tools, budgets
and acceptance. This adapter makes one request to the private local broker.
It has no provider credential, native tool dispatcher or persistent session.
Only the standard library is imported inside the sandbox.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

RESULT_RECORD = "baltor_harness_text_result/v1"
CONFIGURATION_FIELDS = {"model", "base_url", "task_path", "output_allowance", "maximum_bytes"}
RESPONSE_BYTE_CEILING = 16 * 1024 * 1024
RELAY_CREDENTIAL = "loop-engine-local-relay"


class RefuseBrokerRedirect(HTTPRedirectHandler):
    """The private broker may not redirect a native turn to another address."""
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError("private_broker_redirect_refused")


urlopen = build_opener(ProxyHandler({}), RefuseBrokerRedirect()).open


def local_broker(base_url):
    parts = urlsplit(base_url)
    if (parts.scheme != "http" or parts.hostname != "127.0.0.1" or not parts.port
            or parts.path != "/v1" or parts.username or parts.password or parts.query or parts.fragment):
        raise ValueError("isolated_loopback_relay_required")
    return base_url


def prepare_baltor_recipe(style, config, base_url):
    if style != "baltor":
        raise ValueError("unsupported_baltor_harness_style")
    local_broker(base_url)
    workspace = Path(config.get("workspace_path", "/work"))
    task = Path(config.get("task_path", "/relay/task.txt"))
    if not workspace.is_absolute() or not task.is_absolute():
        raise ValueError("absolute_private_paths_required")
    record = {"model": config["model"], "base_url": base_url, "task_path": str(task),
              "output_allowance": config["output_allowance"], "maximum_bytes": RESPONSE_BYTE_CEILING}
    configuration = workspace / "baltor-harness.json"
    configuration.write_text(json.dumps(record, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return tuple(config["command_prefix"] + ["--config", str(configuration)]), {}, None


def extract_baltor_output(style, stdout, expected):
    if style != "baltor" or not isinstance(expected, str) or not expected:
        return ""
    answer = json.loads(stdout)
    if (type(answer) is dict and set(answer) == {"record_type", "text"}
            and answer["record_type"] == RESULT_RECORD and answer["text"] == expected):
        return expected
    return ""


def invoke(configuration):
    if type(configuration) is not dict or set(configuration) != CONFIGURATION_FIELDS:
        raise ValueError("baltor_harness_configuration_invalid")
    origin = local_broker(configuration["base_url"])
    ceiling = configuration["maximum_bytes"]
    allowance = configuration["output_allowance"]
    if (type(ceiling) is not int or not 1 <= ceiling <= RESPONSE_BYTE_CEILING
            or type(allowance) is not int or allowance < 1
            or type(configuration["model"]) is not str or not configuration["model"]):
        raise ValueError("baltor_harness_allocation_invalid")
    task = Path(configuration["task_path"])
    if not task.is_absolute() or task.is_symlink():
        raise ValueError("absolute_private_task_required")
    with task.open("rb") as stream:
        raw = stream.read(ceiling + 1)
    if len(raw) > ceiling:
        raise ValueError("baltor_harness_task_limit")
    body = json.dumps({"model": configuration["model"],
                       "messages": [{"role": "user", "content": raw.decode("utf-8")}],
                       "max_tokens": allowance, "stream": False}, ensure_ascii=False).encode("utf-8")
    request = Request(origin + "/chat/completions", body,
                      {"Content-Type": "application/json", "Authorization": "Bearer " + RELAY_CREDENTIAL})
    # The owning process enforces its declared deadline and cancellation.
    with urlopen(request) as response:
        received = response.read(ceiling + 1)
    if len(received) > ceiling:
        raise ValueError("baltor_harness_response_limit")
    answer = json.loads(received)
    text = answer["choices"][-1]["message"]["content"]
    if not isinstance(text, str):
        raise ValueError("baltor_harness_text_required")
    return {"record_type": RESULT_RECORD, "text": text}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(invoke(json.loads(args.config.read_text(encoding="utf-8"))), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
